import scrapy
import json
import re
import html
from urllib.parse import urlencode, urljoin, urlparse
from pathlib import Path

from Scrapper.items import ScrapperItem

class MainSpider(scrapy.Spider):
    name = "main"
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
    }


    def _make_request(self, url, callback, meta=None, method='GET', body=None, headers=None):
        if meta is None:
            meta = {}
        if self.use_tor and self.tor_proxy:
            meta['proxy'] = self.tor_proxy
        return scrapy.Request(url, callback=callback, meta=meta, method=method, body=body, headers=headers, errback=self.errback_handler)


    def start_requests(self):  # Changed to synchronous for simplicity

        
        for keyword in self.base_keywords:
            if self.use_suggestions_setting and self.suggestion_url_template:
                suggestion_params = self.suggestion_base_params.copy()
                suggestion_params['kwd'] = keyword
                final_suggestion_url = f"{self.suggestion_url_template}?{urlencode(suggestion_params)}"
                self.logger.info(f"Fetching suggestions for '{keyword}' from: {final_suggestion_url}")
                request_meta = {'original_keyword': keyword}
                yield self._make_request(final_suggestion_url, callback=self.parse_suggestions, meta=request_meta)
            else:
                self.logger.info(f"Using base keyword directly: '{keyword}'")
                search_params = self.search_params_template.copy()
                search_params['_nkw'] = keyword
                search_params['_sacat'] = self.default_category_id_config
                search_params['_pgn'] = 1
                full_search_url = f"{self.search_base_url_template}?{urlencode(search_params)}"
                request_meta = {
                    'source_keyword': keyword,
                    'current_keyword': keyword,
                    'category_id': search_params['_sacat'],
                    'search_page_number': 1,
                    'search_url_template': self.search_base_url_template
                }
                yield self._make_request(full_search_url, callback=self.parse_search_results, meta=request_meta)

    def parse_suggestions(self, response):
        original_keyword = response.meta['original_keyword']
        self.logger.info(f"Received suggestions for '{original_keyword}' from {response.url}")
        
        try:
            response_text = response.text
            callback_name = self.suggestion_base_params.get("callback", "0")
            if callback_name and response_text.startswith(callback_name + "(") and response_text.endswith(")"):
                response_text = response_text[len(callback_name)+1:-1]
            data = json.loads(response_text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from suggestion response for '{original_keyword}'. Body: {response.text[:300]}")
            search_params = self.search_params_template.copy()
            search_params['_nkw'] = original_keyword
            search_params['_sacat'] = self.default_category_id_config
            search_params['_pgn'] = 1
            full_search_url = f"{self.search_base_url_template}?{urlencode(search_params)}"
            request_meta = {
                'source_keyword': original_keyword,
                'current_keyword': original_keyword,
                'category_id': search_params['_sacat'],
                'search_page_number': 1,
                'search_url_template': self.search_base_url_template
            }
            yield self._make_request(full_search_url, callback=self.parse_search_results, meta=request_meta)
            return
        
        processed_suggestions = False
        suggestions_sources = [
            data.get("richRes", {}).get("sug", []),
            data.get("rcser", {}).get("sug", []),
            data.get("sug", [])
        ]
        
        for sug_list in suggestions_sources:
            if sug_list and isinstance(sug_list, list):
                processed_suggestions = True
                self.logger.info(f"Processing suggestions for '{original_keyword}' from list of size {len(sug_list)}")
                for sug_item in sug_list:
                    if not isinstance(sug_item, dict):
                        continue
                    kwd = sug_item.get("kwd")
                    cat_id_to_use = self.default_category_id_config
                    category_info = sug_item.get("category", [])
                    if isinstance(category_info, list) and category_info and category_info[0]:
                        cat_id_to_use = str(category_info[0])
                    if kwd:
                        self.logger.info(f" Suggested keyword: '{kwd}', Category ID: '{cat_id_to_use}'")
                        search_params = self.search_params_template.copy()
                        search_params['_nkw'] = kwd
                        search_params['_sacat'] = cat_id_to_use
                        search_params['_pgn'] = 1
                        full_search_url = f"{self.search_base_url_template}?{urlencode(search_params)}"
                        request_meta = {
                            'source_keyword': original_keyword,
                            'current_keyword': kwd,
                            'category_id': cat_id_to_use,
                            'search_page_number': 1,
                            'search_url_template': self.search_base_url_template
                        }
                        yield self._make_request(full_search_url, callback=self.parse_search_results, meta=request_meta)
                break
        if not processed_suggestions:
            self.logger.warning(f"No valid suggestions for '{original_keyword}'. Using original keyword.")
            search_params = self.search_params_template.copy()
            search_params['_nkw'] = original_keyword
            search_params['_sacat'] = self.default_category_id_config
            search_params['_pgn'] = 1
            full_search_url = f"{self.search_base_url_template}?{urlencode(search_params)}"
            request_meta = {
                'source_keyword': original_keyword,
                'current_keyword': original_keyword,
                'category_id': search_params['_sacat'],
                'search_page_number': 1,
                'search_url_template': self.search_base_url_template
            }
            yield self._make_request(full_search_url, callback=self.parse_search_results, meta=request_meta)

    def parse_search_results(self, response):
        source_keyword = response.meta['source_keyword']
        current_keyword = response.meta['current_keyword']
        category_id = response.meta['category_id']
        current_page_num = response.meta['search_page_number']
        
        if source_keyword != current_keyword:
            display_keyword_log = f"{current_keyword} (source: {source_keyword})"
        else:
            display_keyword_log = current_keyword
        
        self.logger.info(f"Parsing search results for '{display_keyword_log}', Category: '{category_id}', Page: {current_page_num} from {response.url}")
        
        total_results_text = response.css('div.srp-controls__count h1.srp-controls__count-heading span.BOLD:first-child::text').get()
        total_results = int(total_results_text.strip()) if total_results_text else 0
        self.logger.info(f"Total results reported: {total_results}")
        
        product_items = response.css('li.s-item, li.srp-river-answer')
        product_count_on_page = 0
        collected_items = 0
        
        for i, item in enumerate(product_items):
            if i < 2:
                continue
            
            if item.css('span.BOLD:contains("Results matching fewer words")').get():
                self.logger.info(f"Found 'Results matching fewer words' marker on page {current_page_num}. Stopping collection.")
                break
            
            link = item.css('a.s-item__link::attr(href)').get()
            if link:
                full_url = response.urljoin(link)
                product_id_match = re.search(r'/itm/(\d+)', full_url)
                if product_id_match:
                    product_id = product_id_match.group(1)
                    meta = {
                        'source_keyword': source_keyword,
                        'current_keyword': current_keyword,
                        'category_id': category_id,
                        'search_page_number': current_page_num,
                        'search_url': response.url,
                        'product_id_from_link': product_id,
                        'total_results': total_results
                    }
                    yield self._make_request(full_url, callback=self.parse_product_page, meta=meta)
                    product_count_on_page += 1
                    collected_items += 1
        
        self.logger.info(f"Enqueued {product_count_on_page} product page requests from page {current_page_num} for '{display_keyword_log}'.")
        
        if current_page_num < self.max_pages and collected_items < total_results:
            next_page_link = response.css('a.pagination__next::attr(href)').get()
            if next_page_link:
                next_page_url = response.urljoin(next_page_link)
                self.logger.info(f"Found next page link: {next_page_url}")
                meta = response.meta.copy()
                meta['search_page_number'] += 1
                yield self._make_request(next_page_url, callback=self.parse_search_results, meta=meta)
            else:
                self.logger.info(f"No 'next page' link found on page {current_page_num}. Reached last page.")
        else:
            if collected_items >= total_results:
                self.logger.info(f"Collected {collected_items} items, matching or exceeding total results ({total_results}). Stopping pagination.")
            else:
                self.logger.info(f"Reached max pages ({self.max_pages}) for '{display_keyword_log}'. Stopping pagination.")

    def parse_product_page(self, response):
        item = ScrapperItem()
        
        # Check if we landed on a challenge page
        if "splashui/challenge" in response.url or "distil_r_captcha.html" in response.url or "SecCaptcha" in response.url:
            self.logger.warning(f"Hit a challenge/CAPTCHA page, cannot extract data: {response.url}")
            product_id_from_meta = response.meta.get('product_id_from_link')
            original_url = response.meta.get('redirect_urls', [response.url])[0] if response.meta.get('redirect_urls') else response.url
            
            if not product_id_from_meta:
                product_id_match = re.search(r'/itm/(\d+)', original_url)
                product_id_from_meta = product_id_match.group(1) if product_id_match else "UNKNOWN_CHALLENGE_PID"

            item['product_id'] = product_id_from_meta
            item['link'] = original_url 
            item['title'] = "CHALLENGE_PAGE_HIT"
            # Populate other fields with None or appropriate 'error' state if desired
            item['price'] = None
            item['images'] = []
            item['description'] = None
            item['condition'] = None
            item['brand'] = None
            item['location'] = None
            item['seller_name'] = None
            item['seller_link'] = None
            item['seller_feedback_count'] = None
            item['seller_positive_feedback'] = None
            item['top_rated_seller'] = None
            item['accurate_description_rating'] = None
            item['reasonable_shipping_cost_rating'] = None
            item['fast_shipping_rating'] = None
            item['communication_rating'] = None
            item['seller_items_sold'] = None
            item['seller_verified'] = None
            item['category_id'] = response.meta.get('category_id')
            self.logger.error(f"Failed to parse (challenge page): {item['link']}")
            yield item 
            return

        product_id = response.meta.get('product_id_from_link')
        if not product_id: # Fallback if not in meta
            product_id_match = re.search(r'/itm/(\d+)', response.url)
            product_id = product_id_match.group(1) if product_id_match else None
        
        item['product_id'] = product_id
        item['link'] = response.url

        # Helper function to extract first non-empty value, stripping whitespace
        def extract_first(selectors, default=None):
            for sel in selectors:
                value = response.xpath(sel).get() if sel.startswith('/') else response.css(sel).get()
                if value:
                    cleaned_value = html.unescape(value.strip())
                    if cleaned_value: # Ensure it's not just whitespace after unescape
                        return cleaned_value
            return default

        # Helper function to extract and join all text, stripping whitespace
        def extract_all_text(selectors, default=None, join_char=' '):
            for sel in selectors:
                texts = response.xpath(sel).getall() if sel.startswith('/') else response.css(sel).getall()
                if texts:
                    cleaned_texts = [html.unescape(t.strip()) for t in texts if t and t.strip()]
                    if cleaned_texts:
                        return join_char.join(cleaned_texts)
            return default

        # --- CORRECTED: Assign title using selectors ---
        title_selectors = [
            'div[data-testid="x-item-title"] h1.x-item-title__mainTitle span.ux-textspans--BOLD::text',
            'h1.x-item-title__mainTitle span.ux-textspans::text', # More general for title elements
            'h1.x-item-title__mainTitle ::text', # Get all text nodes within the H1
            'meta[property="og:title"]::attr(content)',
        ]
        # Using extract_all_text for title as it might be split into multiple spans or text nodes
        item['title'] = extract_all_text(title_selectors)
        
        # Price: Prioritize USD, then any primary price
        price_text_usd_approx = extract_first([
            'div.x-price-approx[data-testid="x-price-approx"] span.ux-textspans--BOLD:contains("US $")::text',
        ])
        price_text_primary = extract_first([
            'div.x-price-primary[data-testid="x-price-primary"] span.ux-textspans:contains("US $")::text', # Primary USD
            'div.x-price-primary[data-testid="x-price-primary"] span.ux-textspans::text', # Any primary
            'span[itemprop="price"]::attr(content)', # Schema.org
        ])

        final_price = None
        if price_text_usd_approx and "US $" in price_text_usd_approx:
            final_price = price_text_usd_approx.strip()
        elif price_text_primary:
            final_price = price_text_primary.strip()
        
        item['price'] = final_price

        description_selectors = [
            'div#desc_ifr::attr(src)', 
            '//div[@id="मंत्री_tbl"]//text()', 
            'meta[name="description"]::attr(content)',
            'meta[property="og:description"]::attr(content)',
            'div[data-testid="d-item-description"] #desc_ifr + noscript ::text', 
        ]
        item['description'] = extract_all_text(description_selectors)
        
        image_selectors = [
            'div.ux-image-carousel-item img::attr(data-zoom-src)', 
            'div.ux-image-carousel-container img[data-zoom-src]:not([data-zoom-src=""])::attr(data-zoom-src)',
            'div.ux-image-carousel-item img::attr(src)',
            'div[data-testid="grid-container"] button.ux-image-grid-item img::attr(src)',
            'img#icImg::attr(src)', 
            'div.vim.vi-evo-row-gap img::attr(src)', 
            'meta[property="og:image"]::attr(content)',
        ]
        image_urls = []
        for sel_type in ['xpath', 'css']: 
            for sel in image_selectors:
                if (sel_type == 'xpath' and sel.startswith('/')) or \
                   (sel_type == 'css' and not sel.startswith('/')):
                    current_urls = response.xpath(sel).getall() if sel.startswith('/') else response.css(sel).getall()
                    image_urls.extend(u.strip() for u in current_urls if u and u.strip())
        
        abs_image_urls = set()
        for url in image_urls:
            if url:
                url = re.sub(r'/s-l\d+\.(jpg|jpeg|png|webp)', r'/s-l1600.\1', url, flags=re.I)
                abs_image_urls.add(response.urljoin(url))
        item['images'] = list(abs_image_urls) if abs_image_urls else [] # Default to empty list

        condition_selectors = [
            'div[data-testid="x-item-condition"] div.x-item-condition-text span.ux-textspans::text',
            '//dl[contains(@class, "ux-labels-values--condition")]//dd//span[contains(@class, "ux-textspans")]//text()',
            'div#vi-itm-cond::text',
        ]
        item['condition'] = extract_all_text(condition_selectors, join_char=' ')

        brand_selectors = [
            '//div[@class="ux-layout-section-evo__col"]//span[text()="Brand"]/ancestor::dt/following-sibling::dd//span/text()',
            '//span[text()="Brand"]/ancestor::dt/following-sibling::dd//span[@class="ux-textspans"]/text()', 
            'div.ux-labels-values--brand dd span.ux-textspans::text', 
            'div[data-testid="x-item-specifics"] span:contains("Brand") ~ div span.ux-textspans::text',
        ]
        item['brand'] = extract_first(brand_selectors)

        location_selectors = [
            '//span[contains(text(),"Located in:")]/text()',
            '//div[contains(@class, "ux-labels-values--deliverto")]//span[contains(@class, "ux-textspans--SECONDARY") and starts-with(normalize-space(.), "Located in:")]/text()',
            '//span[text()="Item location"]/ancestor::dt/following-sibling::dd//span[@class="ux-textspans"]/text()',
        ]
        location_text = extract_first(location_selectors)
        if location_text and "Located in:" in location_text:
            item['location'] = location_text.replace("Located in:", "").strip()
        elif location_text:
            item['location'] = location_text.strip()
        else:
            item['location'] = None

        seller_name_selectors = [
            'div.x-store-information__store-name a span.ux-textspans--BOLD::text',
            'div.x-store-information__store-name::attr(title)',
            'div.x-sellercard-atf__info__about-seller a span.ux-textspans--BOLD::text',
            'a[data-testid="seller-profile-link"] span::text',
        ]
        item['seller_name'] = extract_first(seller_name_selectors)

        seller_link_selectors = [
            'div.x-store-information__store-name a::attr(href)',
            'div.x-store-information__header div.ux-action-avatar a::attr(href)',
            'div.x-sellercard-atf__info__about-seller a[href*="/str/"]::attr(href)',
            'a[data-testid="seller-profile-link"]::attr(href)',
        ]
        seller_link_raw = extract_first(seller_link_selectors)
        item['seller_link'] = response.urljoin(seller_link_raw) if seller_link_raw else None
        
        feedback_count_text = extract_first([
            'h2.fdbk-detail-list__title span.SECONDARY::text', 
            'div.x-sellercard-atf__data-item span.ux-textspans--SECONDARY:contains("Feedback")::text', # This might include "Feedback" string
            'div.x-sellercard-atf__data-item span.ux-textspans--SECONDARY ~ span.ux-textspans--SECONDARY', # Try to get the count part if it's separate
            'a[href*="fdbk/feedback_profile"] span::text',
            '//h4[contains(@class, "x-store-information__highlights")]/span[contains(text(), "feedback")]/preceding-sibling::span[1][not(contains(text(), "%"))]/text()',
        ])
        
        item['seller_feedback_count'] = None # Default
        if feedback_count_text:
            count_match = re.search(r'\(?(\d[\d,.]*[KM]?)\)?', feedback_count_text) 
            if count_match:
                count_str = count_match.group(1).replace(',', '').upper()
                if 'K' in count_str:
                    item['seller_feedback_count'] = int(float(count_str.replace('K', '')) * 1000)
                elif 'M' in count_str:
                    item['seller_feedback_count'] = int(float(count_str.replace('M', '')) * 1000000)
                elif count_str.isdigit():
                    item['seller_feedback_count'] = int(count_str)

        positive_feedback_selectors = [
            'div.x-store-information__highlights span.ux-textspans:contains("% positive feedback")::text',
            'div.x-sellercard-atf__data-item span.ux-textspans--POSITIVE::text',
            'div.x-sellercard-atf__data-item span:contains("%")::text',
        ]
        positive_feedback_text = extract_first(positive_feedback_selectors)
        item['seller_positive_feedback'] = None # Default
        if positive_feedback_text:
            match = re.search(r'(\d+\.?\d*%)', positive_feedback_text)
            if match:
                item['seller_positive_feedback'] = match.group(1)
        
        top_rated_product_page_selectors = [
            'div.x-sellercard-atf__badge span.ux-textspans:contains("Top Rated Seller")::text',
            '//div[contains(@class, "seller-ratings-summary__profile-info-container")]//span[contains(text(), "Top Rated Seller")]/text()',
            'span.ux-icon--medal-outline-control + span.ux-textspans:contains("Top Rated")::text',
        ]
        top_rated_text = extract_first(top_rated_product_page_selectors)
        is_top_rated = False # Default
        if top_rated_text and "top rated" in top_rated_text.lower():
            is_top_rated = True
        elif response.meta.get('is_top_rated_listing'):
            is_top_rated = True
        item['top_rated_seller'] = is_top_rated

        dsr_base_path = '//div[@class="fdbk-detail-seller-rating" and descendant::span[text()="{field_name}"]]//span[@class="fdbk-detail-seller-rating__value"]/text()'
        # Default values for DSR are None if not found by extract_first
        item['accurate_description_rating'] = extract_first([dsr_base_path.format(field_name="Accurate description")])
        item['reasonable_shipping_cost_rating'] = extract_first([dsr_base_path.format(field_name="Reasonable shipping cost")])
        item['fast_shipping_rating'] = extract_first([dsr_base_path.format(field_name="Shipping speed")])
        item['communication_rating'] = extract_first([dsr_base_path.format(field_name="Communication")])
        
        items_sold_text = extract_first([
            '//h4[contains(@class, "x-store-information__highlights")]/span[contains(text(), "items sold")]/text()',
        ])
        item['seller_items_sold'] = None # Default
        if items_sold_text:
            sold_match = re.search(r'(\d[\d,.]*)\s*items sold', items_sold_text, re.IGNORECASE)
            if sold_match:
                item['seller_items_sold'] = int(sold_match.group(1).replace(',', ''))

        item['seller_verified'] = None 
        item['category_id'] = response.meta.get('category_id') # Will be None if not in meta

        # Log warnings for missing critical fields
        if not all([item.get('title'), item.get('price'), item.get('product_id')]):
            self.logger.warning(f"Missing critical fields for {response.url}: Title={bool(item.get('title'))}, Price={bool(item.get('price'))}, PID={item.get('product_id')}")
            
            if not item.get('title'):
                title_snippet_raw = response.css('div[data-testid="x-item-title"]').get() 
                if "splashui/challenge" in response.url: # Should not reach here if challenge check is effective
                    title_snippet_raw = response.css('title::text').get() or response.body[:200].decode('utf-8', errors='ignore')
                title_snippet = title_snippet_raw[:200] if isinstance(title_snippet_raw, str) else "N/A (selector not found or not string)"
                self.logger.debug(f"Title extraction failed for {response.url}. HTML snippet for title area: {title_snippet}")

            if not item.get('price'):
                price_snippet_raw = response.css('div.x-bin-price__content').get() 
                if "splashui/challenge" in response.url: # Should not reach here
                    price_snippet_raw = response.body[:200].decode('utf-8', errors='ignore')
                price_snippet = price_snippet_raw[:200] if isinstance(price_snippet_raw, str) else "N/A (selector not found or not string)"
                self.logger.debug(f"Price extraction failed for {response.url}. HTML snippet for price area: {price_snippet}")
        
        yield item
