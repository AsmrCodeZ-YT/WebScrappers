import asyncio
import logging
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import json
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from collections.abc import MutableMapping

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("jobvision")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://jobvision.ir"
LIST_ENDPOINT = "https://candidateapi.jobvision.ir/api/v1/JobPost/List"
DETAIL_ENDPOINT = "https://candidateapi.jobvision.ir/api/v1/JobPost/Detail"
PAGE_SIZE = 30
DETAIL_CONCURRENCY = 10  # Max parallel detail requests
TOTAL_PAGE = 5


# Time range options
TIME_RANGES: Dict[int, str] = {
    0: "ALL",
    1: "3 Days Ago",
    2: "7 Days Ago",
    3: "15 Days Ago",
    4: "30 Days Ago",
}


# ---------------------------------------------------------------------------
# Helper: flatten nested dicts
# ---------------------------------------------------------------------------
def flatten_dict(
    d: Dict[str, Any], parent_key: str = "", sep: str = "."
) -> Dict[str, Any]:
    """
    Recursively flatten nested JSON/dict into a single-level dict.
    Nested dicts: parent.child
    List of dicts: parent.0.child, parent.1.child, ...
    Other lists: kept as JSON string.
    """
    items: List[Tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            if v and all(isinstance(item, MutableMapping) for item in v):
                for i, item in enumerate(v):
                    indexed_key = f"{new_key}{sep}{i}"
                    items.extend(flatten_dict(item, indexed_key, sep=sep).items())
            else:
                items.append((new_key, json.dumps(v, ensure_ascii=False)))
        else:
            items.append((new_key, v))
    return dict(items)


def flatten_json_to_df(json_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of nested JSON records into a flat DataFrame."""
    flat_records = [flatten_dict(record) for record in json_data]
    return pd.DataFrame(flat_records)


# ---------------------------------------------------------------------------
# HTML to text
# ---------------------------------------------------------------------------
def html_to_text(html: Optional[str]) -> str:
    """Extract visible text from HTML string."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


# ---------------------------------------------------------------------------
# Async scraper class
# ---------------------------------------------------------------------------
class JobVisionScraper:
    def __init__(self, category: str, search_time_range: int) -> None:
        self.category = category
        self.search_time_range = search_time_range
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        # Fetch a page to get cookies if needed
        await self.session.get(BASE_URL)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def _fetch_json(
        self, method: str, url: str, json_payload: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Helper to perform HTTP request and return JSON, with error logging."""
        try:
            async with self.session.request(
                method, url, json=json_payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(
                        f"HTTP {response.status} for {method} {url}: {await response.text()}"
                    )
                    return None
        except Exception as e:
            logger.exception(f"Request failed: {method} {url}")
            return None

    # async def get_total_pages(self) -> int:
    #     """Fetch first page to determine total number of pages."""
    #     payload = {
    #         "pageSize": PAGE_SIZE,
    #         "requestedPage": 1,
    #         "sortBy": 0,
    #         "searchTimeRange": self.search_time_range,
    #         "jobCategoryUrlTitle": self.category,
    #         "searchId": "null",
    #     }
    #     data = await self._fetch_json("POST", LIST_ENDPOINT, json_payload=payload)
    #     if not data or "data" not in data:
    #         logger.error("Could not fetch initial page for page count.")
    #         return 0
    #     total_count = data["data"].get("totalCount", 0)
    #     total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    #     logger.info(f"Total job posts: {total_count}, total pages: {total_pages}")
    #     return total_pages

    async def fetch_page(self, page: int) -> List[Dict[str, Any]]:
        """Fetch a single page of job postings and return flattened records."""
        payload = {
            "pageSize": PAGE_SIZE,
            "requestedPage": page,
            "sortBy": 0,
            "searchTimeRange": self.search_time_range,
            "jobCategoryUrlTitle": self.category,
            "searchId": "null",
        }
        data = await self._fetch_json("POST", LIST_ENDPOINT, json_payload=payload)
        if not data:
            return []
        job_posts = data.get("data", {}).get("jobPosts", [])
        logger.debug(f"Page {page}: got {len(job_posts)} posts")
        return job_posts

    async def fetch_all_pages(self) -> pd.DataFrame:
        """Retrieve all job postings across all pages."""
        total_pages = TOTAL_PAGE
        if total_pages == 0:
            logger.warning("No job posts found.")
            return pd.DataFrame()

        # Fetch pages concurrently (respect the server with a small concurrency limit)
        sem = asyncio.Semaphore(5)  # Max 5 parallel page requests

        async def fetch_page_safe(page: int) -> List[Dict[str, Any]]:
            async with sem:
                return await self.fetch_page(page)

        tasks = [fetch_page_safe(page) for page in range(1, total_pages + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_posts = []
        for page, res in enumerate(results, start=1):
            if isinstance(res, Exception):
                logger.error(f"Error on page {page}: {res}")
                continue
            all_posts.extend(res)

        logger.info(f"Fetched {len(all_posts)} job posts in total.")
        if not all_posts:
            return pd.DataFrame()
        return flatten_json_to_df(all_posts)

    async def fetch_job_detail(self, job_id: int) -> Dict[str, Any]:
        """Fetch full detail for a single job ID."""
        url = f"{DETAIL_ENDPOINT}?jobPostId={job_id}"
        async with self.semaphore:  # Limit concurrency
            data = await self._fetch_json("GET", url)
            if not data:
                logger.warning(f"Failed to fetch detail for job ID {job_id}")
                return {}
            return flatten_dict(data)

    async def fetch_details(self, ids: List[int]) -> pd.DataFrame:
        """Fetch details for a list of job IDs concurrently."""
        if not ids:
            return pd.DataFrame()
        tasks = [self.fetch_job_detail(jid) for jid in ids]
        results = await asyncio.gather(*tasks)
        # Filter out empty dicts (failed requests)
        valid = [r for r in results if r]
        df = pd.DataFrame(valid)
        if not df.empty and "data.description" in df.columns:
            df["data.description"] = df["data.description"].apply(html_to_text)
        return df


# ---------------------------------------------------------------------------
# Main async orchestration
# ---------------------------------------------------------------------------
async def main() -> None:
    logger.info("Starting JobVision scraper")

    # User input
    url_input = input(
        "Enter the URL (e.g. https://jobvision.ir/jobs/category/data-science?page=1&sort=0): "
    ).strip()
    if not url_input:
        logger.error("No URL provided. Exiting.")
        sys.exit(1)

    # Extract category from URL
    match = re.search(r"category/([^?]+)", url_input)
    if not match:
        logger.error("Could not extract job category from URL.")
        sys.exit(1)
    category = match.group(1)
    logger.info(f"Category: {category}")

    # Time range selection
    print("\nAvailable time ranges:")
    for key, val in TIME_RANGES.items():
        print(f"  {key}: {val}")
    try:
        search_time_range = int(input("Enter time range number: ").strip())
        if search_time_range not in TIME_RANGES:
            raise ValueError
    except ValueError:
        logger.error("Invalid time range. Exiting.")
        sys.exit(1)
    logger.info(f"Selected time range: {TIME_RANGES[search_time_range]}")

    this_time = datetime.now().strftime("%d-%m-%Y")
    filename_list = f"{category}_{this_time}.csv"
    filename_details = f"{category}_{this_time}_BYID.csv"

    async with JobVisionScraper(category, search_time_range) as scraper:
        # Phase 1: fetch all job postings
        logger.info("Phase 1: fetching all job postings...")
        df_all = await scraper.fetch_all_pages()
        if df_all.empty:
            logger.warning("No job postings found. Exiting.")
            sys.exit(0)
        df_all.to_csv(filename_list, index=False, encoding="utf-8-sig")
        logger.info(f"Saved {len(df_all)} records to {filename_list}")

        # Phase 2: fetch details for first 20 jobs (or all if fewer)
        job_ids = df_all["id"].dropna().astype(int).tolist()[:20]
        logger.info(f"Phase 2: fetching details for {len(job_ids)} jobs...")
        df_details = await scraper.fetch_details(job_ids)
        df_details.to_csv(filename_details, index=False, encoding="utf-8-sig")
        logger.info(f"Saved {len(df_details)} detailed records to {filename_details}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user.")
    except Exception as e:
        logger.exception("Unhandled exception")
        sys.exit(1)
