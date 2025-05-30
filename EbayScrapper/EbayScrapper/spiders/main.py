import json
from pathlib import Path
import scrapy
from scrapy.exceptions import CloseSpider

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
                pass


    def parse_suggestions(self, response):
        try:
            response_text = response.text
            data = json.loads(response_text)

            # Process the JSON response
            data.get("richRes", {}).get("sug", [])

            if sug_list and isinstance(sug_list, list):
                suggestions_sources = [data.get("richRes", {}).get("sug", []), data.get("richRes", {}).get("sug2", [])]
        
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from suggestion response for '{response.url}'. Body: {response.text[:300]}")
            return
        except Exception as e:
            self.logger.error(f"Unexpected error while parsing suggestions for '{response.url}': {str(e)}")
            return
        
        
        search_params = self.search_params_template.copy()
        search_params['_nkw'] = response.meta['original_keyword']
        search_params['_pgn'] = 1
        for sacat in self.allowed_categories:
            search_params['_sacat'] = sacat
            full_search_url = self.search_base_url_template.format(**search_params)
        yield self._make_request(full_search_url, callback=self.parse_search_results, meta=request_meta)
            

        
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



    def parse(self, response):
        # Implement parsing logic here
        pass












    def start_requests(self):
        # Ensure keywords exist, then yield requests
        if not self.base_keywords:
            raise CloseSpider(reason="No base keywords configured. Aborting crawl.")

        for kw in self.base_keywords:
            params = self.search_params_template.copy()
            params['_nkw'] = kw
            url = scrapy.utils.url.build_url(self.search_base_url_template, params)
            yield scrapy.Request(url, self.parse)

    def parse(self, response):
        # parsing logic here
        pass
