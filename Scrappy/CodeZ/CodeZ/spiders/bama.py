import scrapy
from scrapy.crawler import CrawlerProcess
# from scrapy.utils.project import get_project_settings
# import warnings

class Bama(scrapy.Spider):
    
    name = "BamaBot"
    start_urls = [
        "https://bama.ir/car/"
    ]
    # warnings.filterwarnings("ignore", category=scrapy.exceptions.ScrapyDeprecationWarning)
    def parse(self, response):
        for car in response.css("div.bama-ad listing"):
            
            name =  car.css("p.bama-ad__title::text").get()
            price =  car.css("span.bama-ad__price::text").get()
            "span.bama-ad__price"
            yield{
                "name" : name,
                "price" : price,
                # "price" : car.css("span.bama-ad__price::text").getall(),
                }
            
# process = CrawlerProcess(
#     settings={
#         "FEEDS":{
#             "items.csv": {"format": "csv"}}})
# # process = CrawlerProcess(get_project_settings())
# process.crawl(Bama)
# process.start()