import json
from pathlib import Path
import scrapy
from scrapy.exceptions import CloseSpider
import re

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
                'total_results': total_results
            }
            yield self._make_request(link, callback=self.parse_product_page,meta=meta, headers={'Referer': response.url})
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
        pass