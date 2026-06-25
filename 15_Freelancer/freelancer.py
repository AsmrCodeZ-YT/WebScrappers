"""
Freelancer Async Scraper
- Supports modes: users, latest, custom (with custom URL template)
- Random User-Agent per request
- Fully async with httpx, concurrent request limiting, progress bar
- Flattens nested JSON into pandas DataFrame
- Type hints, clean logging, robust
"""

import asyncio
import json
import logging
import random
import sys
from collections.abc import MutableMapping
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pandas as pd
from rich.logging import RichHandler
from tqdm import tqdm

# ── Logging setup ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, rich_tracebacks=True)]
)
log = logging.getLogger("fl_scraper")

# ── User-Agent pool ────────────────────────────────────────────
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0",
]

# ── JSON flattening utilities ─────────────────────────────────
def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """Recursively flatten nested dicts, expanding lists of dicts with indices."""
    items: List[Tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            if v and all(isinstance(item, MutableMapping) for item in v):
                for i, item in enumerate(v):
                    indexed_key = f"{new_key}{sep}{i}"
                    items.extend(flatten_dict(item, indexed_key, sep).items())
            else:
                items.append((new_key, json.dumps(v, ensure_ascii=False)))
        else:
            items.append((new_key, v))
    return dict(items)

def flatten_json_to_df(json_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert list of records (or single record) into a flat DataFrame."""
    if isinstance(json_data, dict):
        json_data = [json_data]
    flat_records = [flatten_dict(record) for record in json_data]
    return pd.DataFrame(flat_records)

# ── URL builders ──────────────────────────────────────────────
def build_url(mode: str, custom_url_template: Optional[str] = None) -> str:
    """Return base URL template with {offset} placeholder."""
    if mode == "users":
        return (
            "https://www.freelancer.com/api/users/0.1/users/directory/"
            "?limit=20&offset={offset}&query=&avatar=true&country_details=true"
            "&display_info=true&job_ranks=true&jobs=true&location_details=true"
            "&online_offline_details=true&preferred_details=true&profile_description=true"
            "&pool_details=true&qualification_details=true&reputation=true"
            "&rising_star=true&status=true&webapp=1&compact=true&new_errors=true&new_pools=true"
        )
    elif mode == "latest":
        return (
            "https://www.freelancer.com/api/projects/0.1/projects/active"
            "?limit=20&offset={offset}&full_description=true&job_details=true"
            "&local_details=true&location_details=true&upgrade_details=true"
            "&owner_info=true&languages[]=en&sort_field=submitdate&webapp=1"
            "&compact=true&new_errors=true&new_pools=true"
        )
    elif mode == "custom":
        if not custom_url_template:
            raise ValueError("custom_url_template is required for 'custom' mode")
        return custom_url_template
    else:
        raise ValueError(f"Unknown mode: {mode}")

# ── Core async fetcher ────────────────────────────────────────
async def fetch_page(
    client: httpx.AsyncClient,
    url: str,
    sem: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Fetch one page with random UA, using semaphore for concurrency limiting."""
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with sem:
        try:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.error(f"Failed to fetch {url}: {e}")
            raise

async def scrape_all(
    mode: str = "users",
    custom_url_template: Optional[str] = None,
    items_key: Optional[str] = None,
    limit: int = 20,
    max_concurrent: int = 10,
) -> pd.DataFrame:
    """
    Main async scraping routine.
    - mode: "users" / "latest" / "custom"
    - custom_url_template: string with {offset} placeholder (for custom mode)
    - items_key: key inside result dict that holds the list of items (auto‑detected if None)
    - limit: items per page (default 20, must match the URL)
    """
    # Prepare base URL template
    base_template = build_url(mode, custom_url_template)

    # First request to discover total_count and the first page of data
    async with httpx.AsyncClient(http2=True) as client:
        sem = asyncio.Semaphore(max_concurrent)
        first_url = base_template.format(offset=0)
        first_page = await fetch_page(client, first_url, sem)
        result = first_page.get("result", first_page)  # some endpoints wrap, some not
        total_count: int = result["total_count"]
        # Determine item list key if not provided
        if items_key is None:
            if mode == "users":
                items_key = "users"
            elif mode in ("latest", "custom"):
                items_key = "projects"
            else:
                raise ValueError("Cannot guess items_key; please provide it explicitly")
        items = result[items_key]
        log.info(f"Total items: {total_count:,} | Items per page: {limit} | Pages: {(total_count + limit - 1)//limit:,}")

        # Process first page
        df_list = [flatten_json_to_df(items)]
        pbar = tqdm(total=total_count, unit="items", desc="Scraping", dynamic_ncols=True)
        pbar.update(len(items))

        # Prepare URLs for remaining pages
        offsets = range(limit, total_count, limit)
        urls = [base_template.format(offset=offset) for offset in offsets]

        # Define per-page worker that updates the global progress bar
        async def worker(url: str) -> pd.DataFrame:
            page = await fetch_page(client, url, sem)
            items_page = page.get("result", page)[items_key]
            pbar.update(len(items_page))
            return flatten_json_to_df(items_page)

        # Gather remaining pages concurrently
        tasks = [worker(url) for url in urls]
        remaining_dfs = await asyncio.gather(*tasks)
        df_list.extend(remaining_dfs)
        pbar.close()

    # Combine all DataFrames
    final_df = pd.concat(df_list, ignore_index=True)
    log.info(f"✅ Scraping complete. DataFrame shape: {final_df.shape}")
    return final_df

# ── CLI entry point ───────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Async Freelancer scraper")
    parser.add_argument(
        "mode",
        choices=["users", "latest", "custom"],
        help="Scraping mode: users, latest projects, or custom URL"
    )
    parser.add_argument(
        "--url",
        help="Custom URL template with {offset} placeholder (required for custom mode)",
        default=None,
    )
    parser.add_argument(
        "--items-key",
        help="Key in API response that contains the list (e.g. 'users', 'projects')",
        default=None,
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent requests (default: 10)",
    )
    parser.add_argument(
        "-o", "--output",
        default="scraped_data.csv",
        help="Output CSV filename (default: scraped_data.csv)",
    )
    args = parser.parse_args()

    # Validate custom mode
    if args.mode == "custom" and not args.url:
        parser.error("--url is required for custom mode")

    # Run async scraping
    df = asyncio.run(
        scrape_all(
            mode=args.mode,
            custom_url_template=args.url,
            items_key=args.items_key,
            max_concurrent=args.max_concurrent,
        )
    )

    # Save result
    df.to_csv(args.output, index=False)
    log.info(f"💾 Data saved to {args.output}")