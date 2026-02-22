import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy
from pprint import pp

async def main():
    url = "https://www.linkedin.com/advice/1/youre-facing-tight-deadlines-integrating-new-data-uk04c"
    schema = {
        "name": "Comment P30day",
        "baseSelector": "li.contribution",
        "fields": [
            {"name": "name", "selector": "span", "type": "text"},
            {"name": "title", "selector": ".md\:text-md", "type": "text"},
            {"name": "like", "selector": ".\!no-underline", "type": "text"},   
            {"name": "text", "selector": ".contribution .left__border", "type": "text"},
        ]
    }

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=JsonCssExtractionStrategy(schema)
            )
        )
        ### The JSON output is stored in 'extracted_content'
        # pp(json.loads(json.dumps(result.extracted_content))) # for show 

        data = json.loads(result.extracted_content)

        pp(data)
  
        with open('data.json', 'w', encoding="utf-8") as f:
            json.dump(data, f,ensure_ascii=False, indent=4)

        
if __name__ == "__main__":
    asyncio.run(main())
