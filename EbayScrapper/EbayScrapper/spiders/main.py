import scrapy


class MainSpider(scrapy.Spider):
    name = "main"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com"]

    def parse(self, response):
        pass
