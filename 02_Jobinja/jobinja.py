import asyncio
import json
import math
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai import JsonCssExtractionStrategy
import pandas as pd


schema = {
    "name": "Jobinja Job Item",
    "baseSelector": "li.o-listView__item__application",
    "fields": [
        {"name": "title", "selector": ".c-jobListView__titleLink", "type": "text"},
        {
            "name": "company",
            "selector": ".c-jobListView__metaItem:nth-child(1) span",
            "type": "text",
        },
        {
            "name": "location",
            "selector": ".c-jobListView__metaItem:nth-child(2) span",
            "type": "text",
        },
        {
            "name": "contract_type",
            "selector": ".c-jobListView__metaItem:nth-child(3) span span:nth-child(1)",
            "type": "text",
        },
        {
            "name": "salary",
            "selector": ".c-jobListView__metaItem:nth-child(3) span span:nth-child(2)",
            "type": "text",
        },
        {
            "name": "posted_date",
            "selector": ".c-jobListView__passedDays",
            "type": "text",
        },
        {
            "name": "company_logo",
            "selector": ".o-listView__itemIndicatorImage",
            "type": "attribute",
            "attribute": "src",
        },
        {
            "name": "job_url",
            "selector": ".c-jobListView__titleLink",
            "type": "attribute",
            "attribute": "href",
        },
    ],
}


async def crawl_jobinja(base_url, total_results):
    # هر صفحه دقیقاً ۲۱ نتیجه دارد
    results_per_page = 21
    total_pages = math.ceil(total_results / results_per_page)

    print(f"Total results: {total_results}")
    print(f"Pages to crawl: {total_pages}")

    all_items = []

    async with AsyncWebCrawler() as crawler:
        for page in range(1, total_pages + 1):
            url = f"{base_url}&page={page}"
            print(f"Fetching page: {page} -> {url}")

            result = await crawler.arun(
                url=url,
                config=CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    extraction_strategy=JsonCssExtractionStrategy(schema),
                ),
            )

            try:
                items = json.loads(result.extracted_content)
                print(f"Extracted {len(items)} items from page {page}")
                all_items.extend(items)
            except:
                print(f"Failed to parse page {page}")

    return all_items


async def main():
    # URL بدون page= فقط انتهای لینک باید page= اضافه شود
    base_url = (
        "https://jobinja.ir/jobs?filters[keywords][0]=data+engineer&filters[job_categories][0]=%D9%88%D8%A8%D8%8C%E2%80%8C+%D8%A8%D8%B1%D9%86%D8%A7%D9%85%D9%87%E2%80%8C%D9%86%D9%88%DB%8C%D8%B3%DB%8C+%D9%88+%D9%86%D8%B1%D9%85%E2%80%8C%D8%A7%D9%81%D8%B2%D8%A7%D8%B1&preferred_before=1763299515&sort_by=published_at_desc&_pjax=%23js-jobSeekerSearchResult"
    )

    total_results = 307  # 👈 این را خودت می‌دهی

    items = await crawl_jobinja(base_url, total_results)

    print(f"\nTotal extracted items: {len(items)}")

    df = pd.DataFrame(items)
    df.to_csv("jobinja_all_jobs.csv", index=False, encoding="utf-8-sig")

    print("\nSaved jobinja_all_jobs.csv")


if __name__ == "__main__":
    asyncio.run(main())


