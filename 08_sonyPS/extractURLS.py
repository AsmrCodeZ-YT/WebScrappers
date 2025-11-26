import asyncio
import aiohttp
from bs4 import BeautifulSoup

FROM_PAGE = 1
TO_PAGE = 417

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def scrape_page(session, i):
    url = f'https://store.playstation.com/en-us/pages/browse/{i}'
    html = await fetch(session, url)
    soup = BeautifulSoup(html, 'html.parser')
    links = ["https://store.playstation.com" + a.attrs["href"] for a in soup.find_all("a", attrs={"class": "psw-link psw-content-link"})]
    print(f"{i}/{TO_PAGE}")
    return links

async def main():
    all_links = []
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_page(session, i) for i in range(FROM_PAGE, TO_PAGE)]
        results = await asyncio.gather(*tasks)
    
    all_links = [link for links in results for link in links]
    
    with open("links.txt", "w") as file:
        for link in all_links:
            file.write(link + "\n")

    print("Links saved to links.txt")
asyncio.run(main())
