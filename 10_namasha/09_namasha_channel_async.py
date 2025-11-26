import asyncio
import httpx
import time
from bs4 import BeautifulSoup
import pandas as pd
import json
import requests


# clear function comment
def clean_comments(x):
    rm_list = ["(", ")", "نظرات"]

    for trash_words in rm_list:
        if trash_words in x:
            x = x.replace(trash_words, "")

    if x == "":
        return 0

    return int(x)


def collection_links():
    url = f"https://www.namasha.com/{ID}"
    all_links = []

    for i in range(1, PAGENUMBER):
        res = requests.get(url)
        soup = BeautifulSoup(res.content, "html.parser")

        video_ids = [
            i.get("data-id") for i in soup.find_all("div", attrs={"class": "thumbnail"})
        ]
        video_links = [
            i.get("href")
            for i in soup.find_all(
                "a", attrs={"class": "thumbnail-title thumbnail-url flex-shrink-1 stretched-link"}
            )
        ]
        all_links.append(video_links)
        url = f"https://www.namasha.com/{ID}?page={i}&qm=&lastId={video_ids[-1]}"
        print(url)

    urls = []
    for i in all_links:
        for j in i:
            urls.append(j)
    return urls


async def main():
    tasks = []
    df = pd.DataFrame()
    count = 0

    async with httpx.AsyncClient() as client:
        for url in urls:
            print(url)
            tasks.append(client.get(url))

        res = await asyncio.gather(*tasks)
        for i in res:
            soup = BeautifulSoup(i.text, "html.parser")
            title = soup.find(
                "h1",
                attrs={
                    "class": "video-title font-size-base font-size-lg-lg font-weight-bold mb-1"
                },
            ).text.strip()
            link = soup.find("span", attrs={"class": "video-like-count"}).text
            count_comment = soup.find(
                "h4", attrs={"class": "font-size-base font-size-lg-sm mb-0"}
            ).text.strip()
            time = soup.find(
                "time",
                attrs={
                    "class",
                    "text-dynamic-half-dark font-size-xs font-weight-light font-weight-lg-medium mt-2",
                },
            ).text.strip()

            data = {
                "titles": [title],
                "likes": [link],
                "comments": [count_comment],
                "times": [time],
                "urls": url,
            }

            df2 = pd.DataFrame(data)
            df = pd.concat([df, df2], ignore_index=True)

            count += 1
            # if count // 20:

    FILENAME = f"namasha_{ID}_{PAGENUMBER}.csv"
    df["likes"] = df["likes"].apply(lambda x: int(x))
    df["comments"] = df["comments"].apply(lambda x: clean_comments(x))
    df.to_csv(FILENAME)

if __name__ == "__main__":
    print("Welcome To My Scraper. I'm TheCodeZ!")
    ID = input("Give Channel Nmae: ")
    PAGENUMBER = int(input("Give me Number of Page U Need? (More > 1): "))
    
    if PAGENUMBER <= 1:
        print("PLS GIVE ME RIGHT NUMBER!")
        exit()
        
    s = time.perf_counter()

    urls = collection_links()
    asyncio.run(main())

    dt = time.perf_counter() - s
    print(dt)
