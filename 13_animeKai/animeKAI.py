import asyncio
import aiohttp
from aiohttp import ClientConnectorError, ClientResponseError
from bs4 import BeautifulSoup
import random
import time
import json

BASE = "https://animekai.to"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    # add more realistic UAs as needed
]

ACCEPT_LANGS = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
]

CONCURRENCY = 6            
MAX_RETRIES = 5            
BASE_DELAY = 0.5           
TIMEOUT = aiohttp.ClientTimeout(total=30)  

def make_headers(url=None):
    ua = random.choice(USER_AGENTS)
    lang = random.choice(ACCEPT_LANGS)
    headers = {
        "User-Agent": ua,
        "Accept-Language": lang,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": random.choice([BASE, "https://google.com", "https://bing.com"]),
        "Connection": "keep-alive",
    }
    return headers

def jitter_backoff(attempt, base=1.0, cap=30.0):
    """exponential backoff with jitter"""
    exp = min(cap, base * (2 ** (attempt - 1)))
    return exp * (0.5 + random.random() / 2)  

async def fetch(session, url, sem: asyncio.Semaphore):
    attempt = 0
    while True:
        attempt += 1
        headers = make_headers(url)
        async with sem:  # محدودیت تعداد همزمانی
            try:
                await asyncio.sleep(BASE_DELAY * random.random())
                async with session.get(url, headers=headers, timeout=TIMEOUT) as resp:
                    text = await resp.text()
                    status = resp.status
                    if status == 200:
                        return text
                    if 500 <= status < 600:
                        raise ClientResponseError(
                            request_info=resp.request_info,
                            history=resp.history,
                            status=resp.status,
                            message=f"Server error {resp.status}",
                            headers=resp.headers
                        )
                    return text
            except (ClientResponseError, ClientConnectorError, asyncio.TimeoutError) as e:
                if attempt >= MAX_RETRIES:
                    print(f"[ERROR] {url} -> failed after {attempt} attempts. Last error: {repr(e)}")
                    return None
                
              
                backoff = jitter_backoff(attempt, base=1.0, cap=30.0)
                print(f"[WARN] {url} -> attempt {attempt} error: {repr(e)}. retrying in {backoff:.1f}s")
                await asyncio.sleep(backoff)
            except Exception as e:
                # capture unexpected errors
                print(f"[EXC] unexpected error for {url}: {repr(e)}")
                return None

# ----- parse helper -----
def extract_links_from_list(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.aitem a.poster")
    links = [BASE + a["href"] for a in items if a.get("href")]
    return links

def safe_text(soup, selector):
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else None

def extract_details(html, url):
    soup = BeautifulSoup(html, "html.parser")
    data = {
        "url": url,
        "title": safe_text(soup, "h1.title"),
        "alt_titles": safe_text(soup, "small.al-title"),
        "rating": safe_text(soup, "div.info span.rating"),
        "sub_count": safe_text(soup, "div.info span.sub"),
        "dub_count": safe_text(soup, "div.info span.dub"),
        "type": safe_text(soup, "div.info span b"),
        "description": safe_text(soup, "div.desc"),
        "country": safe_text(soup, "div.detail a[href*='/countries/']"),
        "genres": [g.get_text(strip=True) for g in soup.select("div.detail a[href*='/genres/']")] or None,
        "premiered": safe_text(soup, "div.detail a[href*='season=']"),
        "date_aired": safe_text(soup, "span[itemprop='dateCreated']"),
        "duration": safe_text(soup, "div.detail div:contains('Duration') span") if soup.select_one("div.detail") else None,
        "studio": safe_text(soup, "div.detail a[href*='/studios/']"),
        "site_rating": safe_text(soup, "div.rate-box span.value"),
        "site_reviews": safe_text(soup, "div.rate-box span:not(.value)"),
    }
    return data

# ----- main crawler -----
async def crawl(pages=3):
    
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY, limit=0, ssl=False)  # limit_per_host helps
    async with aiohttp.ClientSession(connector=connector) as session:
        list_urls = [f"{BASE}/recent?page={i}" for i in range(1, pages + 1)]
        fetch_tasks = [fetch(session, u, sem) for u in list_urls]
        list_htmls = await asyncio.gather(*fetch_tasks)

        all_links = set()
        for html, u in zip(list_htmls, list_urls):
            if html:
                links = extract_links_from_list(html)
                print(f"[INFO] {u} -> found {len(links)} items")
                all_links.update(links)
            else:
                print(f"[WARN] {u} -> no html (skipped)")

        print(f"[INFO] total unique links collected: {len(all_links)}")

        detail_tasks = []
        for link in all_links:
            async def task_wrapper(session, link):
                html = await fetch(session, link, sem)
                if not html:
                    return None
                return extract_details(html, link)
            detail_tasks.append(task_wrapper(session, link))

        details = []
        for coro in asyncio.as_completed(detail_tasks):
            item = await coro
            if item:
                details.append(item)
                print(f"[OK] scraped: {item.get('title') or item.get('url')}")
            else:
                print("[SKIP] an item failed to scrape")

        print("[DONE] Total details:", len(details))
        with open("anime_details.json", "w", encoding="utf-8") as f:
            json.dump(details, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(crawl(pages=100))
