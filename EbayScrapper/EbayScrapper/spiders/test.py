import scrapy

class TorTestSpider(scrapy.Spider):
    name = "tor_test"
    start_urls = ['https://httpbin.org/ip']  # Simple API to return IP

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={
                    'proxy': 'http://127.0.0.1:9080'
                }
            )

    def parse(self, response):
        print("IP Response:", response.text)