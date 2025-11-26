import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd

PAGENUMBER = 150

PROXIES = "socks5://127.0.0.1:10808"  # V2Ray SOCKS proxy
df = pd.DataFrame()

def clean_vote(inpt):
    if len(inpt) < 4:
        return None
    else:
        return inpt[2]

def spread(i):
    text = i.find_all("span", attrs={"class": "res_item"})
    return [t.text for t in text]

async def fetch_page(session, num):
    url = f"https://digimoviez.com/page/{num}/"
    async with session.get(url, proxy=PROXIES) as res:
        html = await res.text()
        soup = BeautifulSoup(html, 'html.parser')

        titles = [i.text for i in soup.find_all("h2", attrs={"class": "lato_font iranYekanReg"})]
        rate = [i.text.split(" ")[1] for i in soup.find_all("div", attrs={"class": "rate_num"})]
        votes = [clean_vote(i.text.split(" ")) for i in soup.find_all("div", attrs={"class": "rate_num"})]

        quality, duration, genre, director, stars = [], [], [], [], []

        for i in soup.find_all("div", attrs={"class": "meta_item"}):
            quality.append([spread(i) for i in i.find_all("li")][0][0].split(" ")[0])
            duration.append([spread(i) for i in i.find_all("li")][1][0].split(" ")[0])
            genre.append("|".join([spread(i) for i in i.find_all("li")][2]))
            director.append("|".join([spread(i) for i in i.find_all("li")][3]))
            stars.append(",".join([spread(i) for i in i.find_all("li")][4]))

        print(f"{num}/{PAGENUMBER} ->", len(titles), len(rate), len(votes), len(quality))
        
        return pd.DataFrame(
            list(zip(titles, rate, votes, quality, duration, genre, director, stars)),
            columns=['titles', 'rate', "votes", "quality", "duration", "genre", "director", "stars"]
        )

async def main():
    global df
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_page(session, num) for num in range(1, PAGENUMBER)]
        results = await asyncio.gather(*tasks)
        df = pd.concat(results, ignore_index=True)
        df.to_csv(f"digimovies_{PAGENUMBER}.csv", index=False)
        print("Saved to CSV.")

if __name__ == "__main__":
    asyncio.run(main())
