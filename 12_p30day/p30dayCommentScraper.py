import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy
from pprint import pp

async def main():
    schema = {
        "name": "Comment P30day",
        "baseSelector": "#main #posts article > .comments ul li > .content article aside",
        "fields": [
            {"name": "name", "selector": "figure strong", "type": "text"},
            {"name": "text", "selector": "p", "type": "text"},
            {"name": "dateH", "selector": "figure time", "type": "text"},
            {"name": "dateM", "selector": "figure time", "type": "attribute", "attribute": "datetime"},   
        ]
    }

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.p30day.ir/fc-26-ps4-1-381325.html",
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=JsonCssExtractionStrategy(schema)
            )
        )
        

        data = json.loads(result.extracted_content)
        with open('data.json', 'w', encoding="utf-8") as f:
            json.dump(data, f,ensure_ascii=False, indent=4)

        
if __name__ == "__main__":
    asyncio.run(main())
