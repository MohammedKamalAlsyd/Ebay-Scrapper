import json
from pathlib import Path
import scrapy
from scrapy.exceptions import CloseSpider
import re
from EbayScrapper.items import EbayscrapperItem
import time
from scrapy_playwright.page import PageMethod

class MainSpider(scrapy.Spider):
    name = "main"
    search_keywords = ["rtx 5090 founder edition"]
    use_suggestions = False
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
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'PLAYWRIGHT_MAX_CONTEXTS': 4,
    }

    def _make_request(self, url, callback, meta=None, method='GET', body=None, headers=None):
        if meta is None:
            meta = {}
        if self.use_tor and self.tor_proxy_address:
            meta['proxy'] = self.tor_proxy_address
        return scrapy.Request(url, callback=callback, meta=meta, method=method, body=body, headers=headers, errback=self.error_handler)


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
            print(sug_list)
            for cat_id in self.allowed_categories:
                search_params = self.search_base_params.copy()
                search_params['_sacat'] = cat_id
                search_params['_pgn'] = 1
                if sug_list and isinstance(sug_list, list):
                    for sug_item in sug_list:
                        kwd = sug_item.get("kwd")
                        search_params['_nkw'] = kwd
                        self.logger.info(f" Suggested keyword: '{sug_item}', Category ID: '{cat_id}'")
                        sug_url = self.search_base_url_template.format(**search_params)
                        request_meta = {
                            'source_keyword': response.meta.get('original_keyword', ''),
                            'current_keyword': kwd,
                            'category_id': cat_id,
                            'search_page_number': 1,
                            'search_url_template': self.search_base_url_template
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
                "playwright_include_page": True, # to take screenshots if needed
                'playwright_page_methods': [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                        PageMethod("wait_for_selector", "h1.x-item-title__mainTitle span.ux-textspans--BOLD"),
                    ]
            }
            yield self._make_request(link, callback=self.parse_product_page,meta=meta)
            product_count_on_page += 1

        self.logger.info(f"Total products processed on page {current_page_num} for '{display_keyword_log}': {product_count_on_page}")
        
        # check if we need to fetch more pages (Appear only if products spread on many pages)
        ebay_current_search_page_num = response.xpath(
            '//h2[contains(@class, "clipped") and contains(text(), "Results Pagination")]/text()'
        ).re_first(r'Page (\d+)')
        if ebay_current_search_page_num is None:
            self.logger.warning(f"Could not extract current search page number from response for '{display_keyword_log}' in category '{category_id}'. Assuming page 1.")
            return
        elif current_page_num < self.max_search_pages_per_keyword and int(ebay_current_search_page_num) == current_page_num:
            next_page_num = current_page_num + 1
            self.logger.info(f"Preparing to fetch next page {next_page_num} for '{display_keyword_log}' in category '{category_id}'.")
            meta = response.meta.copy()
            meta['search_page_number'] += 1
            search_params = self.search_base_params.copy()
            search_params['_pgn'] = next_page_num
            search_params['_nkw'] = current_keyword
            yield self._make_request(
                search_url_template.format(**search_params),
                callback=self.parse_search_results,
                meta=meta
            )
        else:
            self.logger.info(f"Reached maximum search pages for '{display_keyword_log}' in category '{category_id}' or no more pages available.")


    async def parse_product_page(self, response):
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
            match = re.search(r'/itm/(\d+)', response.url)
            product_id = match.group(1) if match else response.url.split('/')[-1].split('?')[0]

        extraction_successful = True # Flag to track if we got essential data

        try:
            # --- Product Information ---
            # Title
            item['title'] = response.css('h1.x-item-title__mainTitle span.ux-textspans--BOLD::text').get()
            if item['title']:
                item['title'] = item['title'].strip()
            else:
                self.logger.warning(f"Could not extract title for {response.url}")
                extraction_successful = False # Title is critical

            # Price
            item['price'] = None  # Initialize to None

            approx_price_selector = 'div[data-testid="x-price-approx"] span.x-price-approx__price span.ux-textspans::text'
            approx_price_text = response.css(approx_price_selector).get()

            if approx_price_text and "US $" in approx_price_text:
                item['price'] = approx_price_text.strip()
            
            if not item['price']:
                primary_price_selector = 'div[data-testid="x-price-primary"] span.ux-textspans::text'
                primary_price_text = response.css(primary_price_selector).get()

                if primary_price_text and "US $" in primary_price_text:
                    item['price'] = primary_price_text.strip()
            
            if not item['price']:
                primary_price_text_for_log = response.css('div[data-testid="x-price-primary"] span.ux-textspans::text').get()
                if primary_price_text_for_log:
                    self.logger.warning(f"Could not extract US price for {response.url}. Primary price found was: '{primary_price_text_for_log.strip()}'")
                else:
                    self.logger.warning(f"Could not extract any price (including US price) for {response.url}")
                extraction_successful = False  # Price is critical
            # Category
            breadcrumbs_texts = response.css('nav.breadcrumbs ul li a span::text').getall()
            if not breadcrumbs_texts:
                breadcrumbs_texts = response.xpath("//nav[contains(@aria-label, 'breadcrumb')]//li//a/descendant-or-self::*/text()").getall()
            item['category'] = " > ".join([b.strip() for b in breadcrumbs_texts if b.strip()]) if breadcrumbs_texts else response.meta.get('category_id', "N/A")

            # Description (Handling iframe)
            iframe_src = response.css('iframe#desc_ifr::attr(src)').get()
            if iframe_src:
                desc_url = response.urljoin(iframe_src)
                yield self._make_request(
                    url=desc_url,
                    callback=self.parse_description,
                    meta={'item': item, 
                          'product_id_from_link': product_id, 
                          },
                )
            else:
                item['description'] = "Description not found (no iframe)."
                self.logger.warning(f"Description iframe not found for {response.url}. Item will not have a detailed description.")
                extraction_successful = False # Description is critical if not found
            
            # Condition
            item['condition'] = response.css('div.x-item-condition-text span.ux-textspans::text').get()
            if item['condition']:
                item['condition'] = item['condition'].strip()

            # Brand
            brand_selector_xpath = "//dl[contains(@class, 'ux-labels-values--brand')]/dd//span[@class='ux-textspans']/text()"
            item['brand'] = response.xpath(brand_selector_xpath).get()
            if item['brand']:
                item['brand'] = item['brand'].strip()

            # Location
            raw_loc = response.xpath("//span[contains(@class, 'ux-textspans--SECONDARY') and starts-with(normalize-space(.), 'Located in:')]/text()").get()
            if raw_loc:
                item['location'] = raw_loc.replace('Located in:', '').strip()

            # Free Returns
            raw_returns = response.xpath("//div[contains(@class, 'ux-labels-values--returns')]//div[@class='ux-labels-values__values-content']//text()").get()
            if raw_returns:
                item['return_policy'] = raw_returns.strip()

            # --- Seller Information ---
            # Seller Name
            item['seller_name'] = response.css('div.x-sellercard-atf__info__about-seller a span.ux-textspans--BOLD::text').get()
            if item['seller_name']:
                item['seller_name'] = item['seller_name'].strip()

            # Seller feedback count
            seller_feedback_count_text = response.css('div.x-sellercard-atf__about-seller-item span.ux-textspans--SECONDARY::text').get()
            if seller_feedback_count_text:
                item['seller_feedback_count'] = seller_feedback_count_text.strip('()')

            # Extract seller rating (percentage)
            seller_rating_percentage = response.css('div.x-sellercard-atf__data-item button span.ux-textspans--PSEUDOLINK::text').get()
            if seller_rating_percentage:
                item['seller_positive_feedback_percentage'] = seller_rating_percentage.strip()

            # Extract seller link
            item['seller_link'] = response.css('div.x-sellercard-atf__info__about-seller a::attr(href)').get()

            # Extract top rated seller status
            item['top_rated_seller'] = False
            if response.css('span.ux-program-badge svg use[href="#icon-top-rated-seller-24"]').get():
                item['top_rated_seller'] = True

            # --- Image URLs for ImagesPipeline ---
            image_urls = response.css('div.ux-image-grid button.ux-image-grid-item img[src*="s-l"]::attr(src)').getall()
            item['image_urls'] = image_urls if image_urls else response.css('//*[@id="PicturePanel"]/div[1]/div/div[1]/div[1]/div[1]/div[3]/div/img/@src').get()
            if not item['image_urls']:
                self.logger.warning(f"No images found for {response.url} though download_product_images is True.")
                extraction_successful = False # Images are critical if download is enabled


        except Exception as e:
            self.logger.error(f"Unexpected error during initial parsing of product page {response.url}: {e}", exc_info=True)
            extraction_successful = False 

        # --- Final check for critical extraction success and save debug files if failed ---
        if not extraction_successful:
            self.logger.warning(f"Failed to extract sufficient details for product: {product_id} from {response.url}. Saving debug info.")
            debug_dir = Path('debug_pages')
            try:
                debug_dir.mkdir(parents=True, exist_ok=True)
            except Exception as dir_e:
                self.logger.error(f"Failed to create debug directory {debug_dir}: {dir_e}")
                return # Do not yield item if debug dir can't be made

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_product_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(product_id))
            filename_base = f"debug_{safe_product_id}_{timestamp}"

            # Save HTML content
            html_file_path = debug_dir / f"{filename_base}.html"
            try:
                with open(html_file_path, 'wb') as f:
                    f.write(response.body)
                self.logger.info(f"Saved HTML to {html_file_path}")
            except Exception as html_e:
                self.logger.error(f"Failed to save HTML for {response.url} to {html_file_path}: {html_e}")

            # Save Screenshot if Playwright page object is available
            playwright_page = response.meta.get('playwright_page')
            if playwright_page and hasattr(playwright_page, 'screenshot') and callable(playwright_page.screenshot):
                screenshot_path = debug_dir / f"{filename_base}.png"
                try:
                    await playwright_page.screenshot(path=str(screenshot_path), full_page=True)
                    self.logger.info(f"Screenshot saved to {screenshot_path}")
                except Exception as ss_e:
                    self.logger.error(f"Could not save screenshot for {response.url} to {screenshot_path}: {ss_e}")
            elif self.settings.getbool('PLAYWRIGHT_INCLUDE_PAGE') and not playwright_page:
                self.logger.warning(f"Playwright page object not found in response.meta for {response.url}. Cannot save screenshot. Ensure 'playwright_include_page': True was correctly set and Playwright integration is working.")
            
            return # Do not yield item if extraction failed critically

        # If all went well (or well enough based on your criteria for 'extraction_successful')
        # Only yield if description was not handled by iframe, otherwise it's yielded by parse_description
        if not iframe_src:
            self.logger.info(f"Successfully parsed product: {item.get('title', 'N/A')[:60]}... from {response.url}. Yielding item.")
            yield item


    def parse_description(self, response):
        item = response.meta['item'] # Retrieve the item passed from parse_product_page

        # Extract text from the iframe's HTML body.
        # This typically involves getting all text nodes within the <body> tag
        # and then joining and cleaning them.
        description_html = response.css('body').get()
        if description_html:
            # Use scrapy.Selector to parse the HTML from the iframe's response body
            # and extract all text, then clean up whitespace.
            full_description_text = " ".join(scrapy.Selector(text=description_html).xpath("//text()").getall())
            item['description'] = re.sub(r'\s+', ' ', full_description_text).strip()
            self.logger.debug(f"Extracted description (first 100 chars): {item['description'][:100]}...")
        else:
            item['description'] = "Description not found."
            self.logger.warning(f"Description not found in iframe for {response.url}")
        # After processing the description, yield the complete item
        self.logger.info(f"Successfully appended description and yielding item for {item.get('title', 'N/A')[:60]}...")
        yield item