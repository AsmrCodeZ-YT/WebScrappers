import scrapy


class ScrapemeSpider(scrapy.Spider):
    name = "scrapeme"
    allowed_domains = ["scrapeme.live"]
    start_urls = ["https://scrapeme.live/shop/"]

    def parse(self, response):
        pass
