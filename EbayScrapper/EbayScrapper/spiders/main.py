import json
from pathlib import Path
import scrapy
from scrapy.exceptions import CloseSpider
import re
from EbayScrapper.items import EbayscrapperItem
import time

class MainSpider(scrapy.Spider):
    name = "main"
    search_keywords = ["rtx"]
    use_suggestions = True
    suggestion_api_url = "https://autosug.ebaystatic.com/autosug"
    suggestion_base_params = {
        "sId": "0",
            "_rs": "1",
            "_richres": "1",
            "callback": "0",
            "_store": "1",
            "_help": "0",
            "_richsug": "1",
            "_eprogram": "1",
            "_td": "1",
            "_nearme": "1",
            "_nls": "0"
    }
    suggestion_url_template = "https://autosug.ebaystatic.com/autosug?kwd={kwd}&sId={sId}&_rs={_rs}&_richres={_richres}&callback={callback}&_store={_store}&_help={_help}&_richsug={_richsug}&_eprogram={_eprogram}&_td={_td}&_nearme={_nearme}&_nls={_nls}"
    search_base_url = "https://www.ebay.com/sch/i.html"
    search_base_params = {
        "_from": "R40",
        "rt": "nc",
        "_sacat": "0",
        "_ipg": "240",
        "_sop": "12"
    }
    search_base_url_template = "https://www.ebay.com/sch/i.html?_nkw={_nkw}&_from={_from}&rt={rt}&_sacat={_sacat}&_ipg={_ipg}&_sop={_sop}"
    allowed_categories = ["0"]  # Default category ID for all items
    use_tor = False
    tor_proxy_address = "http://127.0.0.1:9080",
    max_search_pages_per_keyword = 3
    download_product_images = True
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
    }

    def _make_request(self, url, callback, meta=None, method='GET', body=None, headers=None):
        if meta is None:
            meta = {}
        if self.use_tor and self.tor_proxy:
            meta['proxy'] = self.tor_proxy
        return scrapy.Request(url, callback=callback, meta=meta, method=method, body=body, headers=headers, errback=self.errback_handler)


    def error_handler(self, failure):
        self.logger.error(f"Request failed: {failure.request.url}")
        self.logger.error(f"Failure reason: {failure.value}")


    async def start(self):
        for kwd in self.search_keywords:
            if self.use_suggestions and self.suggestion_url_template:
                params = {**self.suggestion_base_params, 'kwd': kwd}
                suggestion_url = self.suggestion_url_template.format(**params)
                self.logger.info(f"Fetching suggestions for '{kwd}' from: {suggestion_url}")
                yield self._make_request(suggestion_url, callback=self.parse_suggestions,meta={'original_keyword': kwd})
            else:
                for cat in self.allowed_categories:
                    self.logger.info(f"Using category ID: {cat} for keyword: '{kwd}'")
                    search_params = self.search_base_params.copy()
                    search_params['_nkw'] = kwd
                    search_params['_sacat'] = cat
                    search_params['_pgn'] = 1
                    full_search_url = self.search_base_url_template.format(**search_params)
                    request_meta = {
                        'source_keyword': kwd,
                        'current_keyword': kwd,
                        'category_id': cat,
                        'search_page_number': 1,
                        'search_url_template': self.search_base_url_template
                    }
                    yield self._make_request(full_search_url, callback=self.parse_search_results, meta=request_meta)


    def parse_suggestions(self, response):
        try:
            response_text = response.text
            data = json.loads(response_text)

            # Process the JSON response
            sug_list = data.get("richRes", {}).get("sug", [])
            for cat_id in self.allowed_categories:
                search_params = self.search_params_template.copy()
                search_params['_sacat'] = cat_id
                search_params['_pgn'] = 1
                if sug_list and isinstance(sug_list, list):
                    sug_items = [data.get("richRes", {}).get("sug", [])]
                    for sug_item in sug_items:
                        kwd = sug_item.get("kwd")
                        search_params['_nkw'] = kwd
                        self.logger.info(f" Suggested keyword: '{sug_item}', Category ID: '{cat_id}'")
                        sug_url = self.search_base_url_template.format(**search_params)
                        request_meta = {
                            'source_keyword': response.meta.get('original_keyword', ''),
                            'current_keyword': kwd,
                            'category_id': cat_id,
                            'search_page_number': 1,
                            'search_urls': self.search_base_url_template
                        }
                        yield self._make_request(sug_url, callback=self.parse_search_results, meta=request_meta)
                else:
                    self.logger.warning(f"No valid suggestions for '{kwd}'. Using original keyword.")
                    search_params['_nkw'] = response.meta.get('original_keyword', '')
                    full_search_url = self.search_base_url_template.format(**search_params)
                    request_meta = {
                        'source_keyword': response.meta.get('original_keyword', ''),
                        'current_keyword': response.meta.get('original_keyword', ''),
                        'category_id': cat_id,
                        'search_page_number': 1,
                        'search_url_template': self.search_base_url_template
                    }
                    yield self._make_request(full_search_url, callback=self.parse_search_results, meta=request_meta)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from suggestion response for '{response.url}'. Body: {response.text[:300]}")
            return
        except Exception as e:
            self.logger.error(f"Unexpected error while parsing suggestions for '{response.url}': {str(e)}")
            return
        


    def parse_search_results(self, response):
        source_keyword = response.meta['source_keyword']
        current_keyword = response.meta['current_keyword']
        category_id = response.meta['category_id']
        current_page_num = response.meta['search_page_number']
        search_url_template = response.meta['search_url_template']

        if source_keyword != current_keyword:
            display_keyword_log = f"{current_keyword} (source: {source_keyword})"
        else:
            display_keyword_log = current_keyword
        
        self.logger.info(f"Parsing search results for '{display_keyword_log}', Category: '{category_id}', Page: {current_page_num} from {response.url}")

        # Extract total results
        total_results_text = response.css('div.srp-controls__count h1.srp-controls__count-heading span.BOLD:first-child::text').get()
        total_results = int(total_results_text.strip()) if total_results_text else 0
        self.logger.info(f"Total results reported: {total_results}")


        if total_results == 0:
            self.logger.info(f"No results found for '{display_keyword_log}' in category '{category_id}' on page {current_page_num}.")
            return
        
        # Extract product links
        separator_xpath = "//li[contains(@class, 'srp-river-answer srp-river-answer--REWRITE_START')]"
        link_path_within_item = "/div[contains(@class, 's-item__wrapper')]/div[contains(@class, 's-item__info')]/a[contains(@class, 's-item__link')]/@href"

        # Check if the separator exists
        separator_node = response.xpath(separator_xpath).get()
        product_links = []
        if separator_node:
            self.logger.info(f"Separator found in {search_url_template}. Fetching items listed above it.")
            items_above_separator_xpath = f"{separator_xpath}/preceding-sibling::li[contains(@class, 's-item')]{link_path_within_item}"
            product_links = response.xpath(items_above_separator_xpath).getall()
        else:
            self.logger.info("Separator not found. Fetching all items on the page.")
            all_items_xpath = f"//li[contains(@class, 's-item')]{link_path_within_item}"
            product_links = response.xpath(all_items_xpath).getall()
            # ignore the first two links which are not product links
            product_links = product_links[2:] if len(product_links) >= 2 else None

        if not product_links:
            self.logger.info(f"No product links found for '{display_keyword_log}' in category '{category_id}' on page {current_page_num}.")
            return
        
        self.logger.info(f"Found {len(product_links)} product links for '{display_keyword_log}' in category '{category_id}' on page {current_page_num}.")
        product_count_on_page = 0
        for link in product_links:
            product_id_match = re.search(r'/itm/(\d+)', link)
            if not product_id_match:
                self.logger.warning(f"Could not extract product ID from link: {link}")
                continue
            meta = {
                'source_keyword': source_keyword,
                'current_keyword': current_keyword,
                'category_id': category_id,
                'search_page_number': current_page_num,
                'search_url': response.url,
                'product_id_from_link': product_id_match.group(1),
                'total_results': total_results,
                'playwright': True,
                "playwright_include_page": True # to take screenshots if needed
            }
            yield self._make_request(link, callback=self.parse_product_page,meta=meta)
            product_count_on_page += 1

        self.logger.info(f"Total products processed on page {current_page_num} for '{display_keyword_log}': {product_count_on_page}")
        
        # check if we need to fetch more pages
        ebay_current_search_page_num = response.xpath(
            '//h2[contains(@class, "clipped") and contains(text(), "Results Pagination")]/text()'
        ).re_first(r'Page (\d+)')
        if current_page_num < self.max_search_pages_per_keyword and int(ebay_current_search_page_num) == current_page_num:
            next_page_num = current_page_num + 1
            self.logger.info(f"Preparing to fetch next page {next_page_num} for '{display_keyword_log}' in category '{category_id}'.")
            meta = response.meta.copy()
            meta['search_page_number'] += 1
            search_params = response.meta.get('search_url_template', self.search_base_url_template)
            search_params['_pgn'] = next_page_num
            yield self._make_request(
                search_url_template.format(**search_params),
                callback=self.parse_search_results,
                meta=meta
            )
        else:
            self.logger.info(f"Reached maximum search pages for '{display_keyword_log}' in category '{category_id}' or no more pages available.")


    def parse_product_page(self, response):
        self.logger.info(f"Parsing product page: {response.url}")
        item = EbayscrapperItem()

        # Populate meta fields from the search result context
        item['derived_from_keyword'] = response.meta.get('current_keyword')
        item['category_context_from_search'] = response.meta.get('category_id')
        item['link'] = response.url

        # Try to get a product ID from meta, fallback to parsing from URL
        product_id_from_meta = response.meta.get('product_id_from_link')
        if product_id_from_meta:
            product_id = product_id_from_meta
        else:
            # Basic extraction from URL as a fallback
            match = re.search(r'/itm/(\d+)', response.url)
            product_id = match.group(1) if match else response.url.split('/')[-1].split('?')[0]

        extraction_successful = True # Flag to track if we got essential data

        try:
            # --- Product Information ---
            self.logger.debug(f"Extracting title for {response.url}")
            item['title'] = response.css('h1.x-item-title__mainTitle span.ux-textspans--BOLD::text').get()
            if not item['title']:
                item['title'] = response.css('h1.x-item-title__mainTitle span.ux-textspans::text').get() # Broader span
            if not item['title']: 
                item['title'] = response.xpath("//h1[contains(@class,'x-item-title__mainTitle')]/text()").get() # Direct text of h1
            if not item['title']: # Fallback for older page structures or variations
                item['title'] = response.css('h1#itemTitle::text').get()
                if item['title']: # it might come with "Details about" or similar prefix
                    item['title'] = item['title'].replace("Details about", "").replace("Details about", "").strip()
            
            if item['title']:
                item['title'] = item['title'].strip()
                self.logger.debug(f"Extracted title: {item['title'][:50]}...")
            else:
                self.logger.warning(f"Could not extract title for {response.url}")
                extraction_successful = False # Title is critical

            self.logger.debug(f"Extracting price for {response.url}")
            item['price'] = response.css('div.x-price-primary span.ux-textspans::text').get()
            if not item['price']:
                item['price'] = response.xpath('//div[contains(@class, "x-price-primary")]//span[contains(@itemprop, "price")]/@content').get() # Check itemprop
            if not item['price']: 
                item['price'] = response.css('span#prcIsum::text').get() # Older primary price
            if not item['price']:
                item['price'] = response.css('span.ux-textspans--price::text').get() # Common class for price text
            if not item['price']:
                 item['price'] = response.xpath("string(//span[@itemprop='price'])").get() # String of itemprop price

            if item['price']:
                item['price'] = item['price'].strip()
                self.logger.debug(f"Extracted price: {item['price']}")
            else:
                self.logger.warning(f"Could not extract price for {response.url}")
                # extraction_successful = False # Uncomment if price is also critical

            self.logger.debug(f"Extracting description for {response.url}")
            # Description can be tricky, often within specific divs or even iframes (iframe not handled here)
            description_selectors = [
                'div#desc_div',                           # Primary description div
                'div#descriptioncontent',                 # Another common description container
                'div.itemAttrDetails',                    # Sometimes details are here
                'div[itemprop="description"]'             # Using itemprop
            ]
            description_html = None
            for selector in description_selectors:
                description_html = response.css(selector).get()
                if description_html:
                    break
            
            if description_html:
                # Extract all text nodes and join them, then clean up whitespace
                full_description_text = " ".join(scrapy.Selector(text=description_html).xpath("//text()").getall())
                item['description'] = re.sub(r'\s+', ' ', full_description_text).strip()
                self.logger.debug(f"Extracted description (first 100 chars): {item['description'][:100]}...")
            else:
                item['description'] = "Description not found."
                self.logger.warning(f"Description not found for {response.url}")
            
            self.logger.debug(f"Extracting category (breadcrumbs) for {response.url}")
            breadcrumbs_texts = response.css('nav.breadcrumbs ul li a span::text').getall()
            if not breadcrumbs_texts:
                 breadcrumbs_texts = response.xpath("//nav[contains(@aria-label, 'breadcrumb')]//li//a/descendant-or-self::*/text()").getall()
            item['category'] = " > ".join([b.strip() for b in breadcrumbs_texts if b.strip()]) if breadcrumbs_texts else response.meta.get('category_id', "N/A")
            self.logger.debug(f"Extracted category: {item['category']}")

            self.logger.debug(f"Extracting condition for {response.url}")
            item['condition'] = response.css('div.x-item-condition-text span.ux-textspans--BOLD::text').get()
            if not item['condition']:
                item['condition'] = response.xpath("string(//div[@itemprop='itemCondition'])").get()
            if not item['condition']: # Try to find it in item specifics if not in main area
                item['condition'] = response.xpath("//div[contains(@class,'x-specifications__raw-value') and preceding-sibling::div[contains(@class,'x-specifications__label')]/span[normalize-space(.)='Condition']]/span/text()").get()
            
            if item['condition']:
                item['condition'] = item['condition'].strip()
                self.logger.debug(f"Extracted condition: {item['condition']}")

            self.logger.debug(f"Extracting brand for {response.url}")
            # Brand is often in item specifics. Look for "Brand" label then its value.
            brand_selectors_xpaths = [
                "//div[contains(@class, 'x-specifications__raw-value') and preceding-sibling::div[contains(@class, 'x-specifications__label')]/span[normalize-space(.)='Brand']]/span/text()",
                "//span[@itemprop='brand']/descendant-or-self::*/text()",
                "//div[contains(text(), 'Brand:')]/following-sibling::div/span/text()", # Simple text search
                "//dt[normalize-space(.)='Brand:']/following-sibling::dd/text()" # Definition list
            ]
            for xpath_selector in brand_selectors_xpaths:
                item['brand'] = response.xpath(xpath_selector).get()
                if item['brand']:
                    item['brand'] = item['brand'].strip()
                    break
            if item['brand']:
                 self.logger.debug(f"Extracted brand: {item['brand']}")
            else:
                 self.logger.debug(f"Brand not found using primary selectors for {response.url}")


            self.logger.debug(f"Extracting location for {response.url}")
            item['location'] = response.css('div.ux-labels-values--location span.ux-textspans--BOLD::text').get()
            if not item['location']:
                item['location'] = response.xpath("normalize-space(//span[@itemprop='itemLocation']/descendant-or-self::*/text())").get()
            if not item['location']:
                 item['location'] = response.xpath("//div[contains(@class,'ux-labels-values--location')]//span[contains(@class,'ux-textspans--SECONDARY')]/text()").get()
            if item['location']:
                item['location'] = item['location'].strip()
                self.logger.debug(f"Extracted location: {item['location']}")

            self.logger.debug(f"Extracting free returns status for {response.url}")
            returns_policy_text = response.css('div.ux-labels-values--returns span.ux-textspans--BOLD::text').get()
            if not returns_policy_text:
                returns_policy_text = response.xpath("//span[contains(text(), 'returns') or contains(text(), 'Returns')]/text()").get()

            if returns_policy_text and "free returns" in returns_policy_text.lower():
                item['free_returns'] = True
            else:
                item['free_returns'] = False
            self.logger.debug(f"Free returns: {item['free_returns']}")

            # --- Seller Information ---
            self.logger.debug(f"Extracting seller name for {response.url}")
            item['seller_name'] = response.css('div.x-sellercard-atf__info__about-seller a span::text').get()
            if not item['seller_name']:
                item['seller_name'] = response.xpath("//a[contains(@href, '_ssn=')]/span/text()").get()
            if not item['seller_name']:
                 item['seller_name'] = response.xpath("string(//span[@itemprop='name'])").get() # Seller info block

            if item['seller_name']:
                item['seller_name'] = item['seller_name'].strip()
                self.logger.debug(f"Extracted seller_name: {item['seller_name']}")

            self.logger.debug(f"Extracting seller rating and feedback count for {response.url}")
            # Modern layout
            seller_feedback_spans = response.css('div.x-sellercard-atf__seller-feedback span.ux-textspans::text').getall()
            if seller_feedback_spans:
                if len(seller_feedback_spans) > 0:
                    item['seller_rating'] = seller_feedback_spans[0].strip().replace(" Positive feedback", "")
                if len(seller_feedback_spans) > 1: # Usually the count is the second span
                    feedback_count_text = seller_feedback_spans[1].strip()
                    match = re.search(r'([\d,]+(?:\.\d+)?K?)', feedback_count_text) # (12345) or (1.2K ratings)
                    if match:
                        item['seller_feedback_count'] = match.group(1)
            
            # Fallback for older or different layouts
            if not item.get('seller_rating'):
                item['seller_rating'] = response.xpath("//div[contains(@class, 'seller-ratings')]//span[contains(@class,'ux-textspans--BOLD')]/text()").get()
                if item['seller_rating']: item['seller_rating'] = item['seller_rating'].strip().replace(" Positive feedback", "")

            if not item.get('seller_feedback_count'):
                feedback_count_raw = response.xpath("//span[contains(@class,'ux-textspans--PSEUDOLINK')]//text()").re_first(r'([\d,]+(?:\.\d+)?K?)')
                if feedback_count_raw:
                    item['seller_feedback_count'] = feedback_count_raw
            
            if item.get('seller_rating'): self.logger.debug(f"Extracted seller_rating: {item['seller_rating']}")
            if item.get('seller_feedback_count'): self.logger.debug(f"Extracted seller_feedback_count: {item['seller_feedback_count']}")


            self.logger.debug(f"Extracting seller link for {response.url}")
            item['seller_link'] = response.css('div.x-sellercard-atf__info__about-seller a::attr(href)').get()
            if not item['seller_link']:
                item['seller_link'] = response.xpath("//a[contains(@href, '_ssn=')]/@href").get()
            if item['seller_link']: self.logger.debug(f"Extracted seller_link: {item['seller_link'][:60]}...")

            self.logger.debug(f"Extracting top rated seller status for {response.url}")
            top_rated_texts = response.css('div.x-sellercard-atf__signal span.ux-textspans--BOLD::text').getall()
            item['top_rated_seller'] = any("top-rated seller" in t.lower() for t in top_rated_texts)
            if not item['top_rated_seller']: # Check for icon or other indicators
                if response.css('span.ux-icon--medal-icon-gold-small, span.TOP_RATED_SELLER_BADGE_SMALL_ICON, svg[aria-label="Top-rated seller"]').get():
                     item['top_rated_seller'] = True
            self.logger.debug(f"Top rated seller: {item['top_rated_seller']}")


            # Image URLs
            if self.download_product_images:
                self.logger.debug(f"Extracting image URLs for {response.url}")
                image_urls = []
                # Try to get high-resolution images from main carousel/gallery
                # Common patterns for image containers:
                img_selectors = [
                    'div.ux-image-carousel-item img::attr(data-zoom-src)', # Zoomed image preferred
                    'div.ux-image-carousel-item img::attr(data-src)',
                    'div.ux-image-carousel-item img::attr(src)',
                    'div.ux-image-grid-inner img::attr(src)', # Gallery images
                    'button.ux-image-filmstrip-carousel-item--selected img::attr(src)', # Thumbnails might give clues
                    'img#icImg::attr(src)', # Older main image ID
                    '//div[@id="vi_main_img_fs"]//img/@src', # Another older pattern for main image
                    '//button[contains(@data-gallery-img-idx, "")]//img/@src' # Thumbnails in filmstrip
                ]
                
                extracted_image_sources = set()

                for selector in img_selectors:
                    if selector.startswith("//"): # XPath
                        current_images = response.xpath(selector).getall()
                    else: # CSS
                        current_images = response.css(selector).getall()
                    
                    for img_url in current_images:
                        if img_url and img_url not in extracted_image_sources and not img_url.startswith('data:image'):
                            # Attempt to get a larger version if it's a thumbnail URL
                            # eBay often uses s-l followed by a number for size (e.g., s-l225, s-l500, s-l1600)
                            img_url = re.sub(r'/s-l\d+\.(jpg|png|webp)', r'/s-l1600.\1', img_url)
                            if not img_url.startswith('http'):
                                img_url = response.urljoin(img_url)
                            extracted_image_sources.add(img_url)
                
                item['image_urls'] = list(extracted_image_sources)
                if item['image_urls']:
                    self.logger.debug(f"Found {len(item['image_urls'])} image URLs. First one: {item['image_urls'][0]}")
                else:
                    self.logger.warning(f"No images found for {response.url} though download_product_images is True.")
            else:
                item['image_urls'] = []
                self.logger.debug(f"Image download disabled, skipping image URL extraction for {response.url}")

        except Exception as e:
            self.logger.error(f"Unexpected error parsing product page {response.url}: {e}", exc_info=True)
            extraction_successful = False # Mark as failed if any exception occurs

        # --- Final check for critical extraction success and save debug files if failed ---
        if not item.get('title'): # Re-check critical field if an exception didn't already set it
             self.logger.error(f"Critical information (title) is missing after parsing attempt for {response.url}. Marking as extraction failure.")
             extraction_successful = False

        if not extraction_successful:
            self.logger.warning(f"Failed to extract sufficient details for product: {product_id} from {response.url}. Saving debug info.")
            debug_dir = Path('debug_pages')
            debug_dir.mkdir(parents=True, exist_ok=True) # Ensure directory exists
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            # Sanitize product_id for filename if it's a URL part
            safe_product_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(product_id))
            filename_base = f"debug_{safe_product_id}_{timestamp}"

            html_file_path = debug_dir / f"{filename_base}.html"
            try:
                with open(html_file_path, 'wb') as f:
                    f.write(response.body)
                self.logger.info(f"Saved HTML to {html_file_path}")
            except Exception as html_e:
                self.logger.error(f"Failed to save HTML for {response.url}: {html_e}")

            # Attempt to save screenshot if Playwright page object is available in meta
            # This requires scrapy-playwright to be configured to pass the page object.
            playwright_page = response.meta.get('playwright_page')
            if playwright_page and hasattr(playwright_page, 'screenshot'):
                screenshot_path = debug_dir / f"{filename_base}.png"
                try:
                    # IMPORTANT: playwright_page.screenshot() is an async function.
                    # Calling it directly from a synchronous Scrapy callback like this
                    # will NOT work as intended and will likely raise an error or block
                    # indefinitely if not handled correctly with an asyncio event loop.
                    # A robust solution involves:
                    # 1. Making this callback `async def parse_product_page(self, response):`
                    #    and then using `await playwright_page.screenshot(path=str(screenshot_path))`.
                    #    This requires TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
                    #    in settings.py (which you have).
                    # 2. Or, relying on scrapy-playwright's built-in screenshot capabilities on error,
                    #    if configured.
                    # For now, this just logs the intent and path.
                    self.logger.info(f"Playwright page object found in meta. If this callback were async, screenshot would be attempted at: {screenshot_path}")
                    # Example of how it *would* be called in an async context:
                    # await playwright_page.screenshot(path=str(screenshot_path))
                    # self.logger.info(f"Screenshot saved to {screenshot_path}")
                except Exception as ss_e:
                    # This error will likely occur if called synchronously.
                    self.logger.error(f"Could not save screenshot for {response.url} (likely due to sync call of async method): {ss_e}")
            elif playwright_page:
                 self.logger.warning(f"Playwright page object found in meta for {response.url}, but it does not have a 'screenshot' method as expected.")
            else:
                self.logger.info(f"Playwright page object not found in meta for {response.url}, cannot save screenshot via this method.")
            
            return # Do not yield item if extraction failed critically

        # If all went well (or well enough based on your criteria for 'extraction_successful')
        self.logger.info(f"Successfully parsed product: {item.get('title', 'N/A')[:60]}... from {response.url}")
        yield item

# don't forget to set user agent and the image middleware pipeline in settings.py