# Global Settings
BOT_NAME = "EbayScrapper"
SPIDER_MODULES = ["EbayScrapper.spiders"]
NEWSPIDER_MODULE = "EbayScrapper.spiders"
ROBOTSTXT_OBEY = False

# Playwright Integration
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "firefox"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,
    "timeout": 20 * 1000,  # 20 seconds
}

# Concurrency & Throttling
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS_PER_IP = 8
# AUTOTHROTTLE_ENABLED = True
# AUTOTHROTTLE_START_DELAY = 1
# AUTOTHROTTLE_MAX_DELAY = 10
# CONCURRENT_REQUESTS = 16
# CONCURRENT_REQUESTS_PER_DOMAIN = 8


# Image Pipelines
ITEM_PIPELINES = {
    "scrapy.pipelines.images.ImagesPipeline": 1
}
IMAGES_STORE = "Scrapped_Images"

# Future-proof Defaults
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
