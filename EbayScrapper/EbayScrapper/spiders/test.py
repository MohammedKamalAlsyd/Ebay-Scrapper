import scrapy
from scrapy_playwright.page import PageMethod


class EbaySpider(scrapy.Spider):
    name = "ebay_spider"
    custom_settings = {
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,  # 60 seconds
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": False},
    }

    def start_requests(self):
        # Start from a search result or category page
        search_url = "https://www.ebay.com/sch/i.html?_nkw=rtx+5090+founder+edition"
        yield scrapy.Request(url=search_url, callback=self.parse_listing)

    async def parse_listing(self, response):
        # Extract product links from the listing page
        product_links = response.css("a.s-item__link::attr(href)").getall()

        for link in product_links:
            # Use response.follow for Playwright-enabled requests
            yield response.follow(
                url=link,
                callback=self.parse_product,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", "h1.x-item-title__mainTitle span.ux-textspans--BOLD"),
                    ],
                },
                errback=self.errback,
            )

    async def parse_product(self, response):
        # Save product page content to file
        title = response.css("h1.x-item-title__mainTitle span.ux-textspans--BOLD::text").get(default="no-title").strip()
        filename = f"ebay_product_{title.replace(' ', '_')}.html"
        with open(filename, "wb") as f:
            f.write(response.body)
        self.logger.info(f"Saved product page: {filename}")

    async def errback(self, failure):
        self.logger.error(f"Request failed: {failure}")
