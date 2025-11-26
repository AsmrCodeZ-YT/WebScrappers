import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd


FROM_PAGE = 1
TO_PAGE = 2
MAX_REQUESTS = 20

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

def try_extract(soup, element_name, attrs1, attrs2):
    try:
        return soup.find(element_name, attrs={attrs1: attrs2}).text
    except:
        return None

def try_all_extract(soup, element_name, attrs1, attrs2):
    try:
        return [i.text for i in soup.find_all(element_name, attrs={attrs1: attrs2})]
    except:
        return None

def try_all_extract_list(soup, datalist):
    extracted_data = []
    for i in datalist:
        try:
            extracted_data.append(soup.find("dd", attrs={"data-qa": i}).text)
        except:
            continue
    return extracted_data



async def scrape_game_details(session, url):
    html = await fetch(session, url)
    soup = BeautifulSoup(html, 'html.parser')
    
    details = {
        "title": try_extract(soup, "h1", "data-qa", "mfe-game-title#name"),
        "publisher": try_extract(soup, "div", "data-qa", "mfe-game-title#publisher"),
        "rating_from_5": try_extract(soup, "div", "data-qa", "mfe-game-title#average-rating"),
        "rating_count": try_extract(soup, "span", "data-qa", "mfe-star-rating#overall-rating#total-ratings"),
        "finalPrice": try_extract(soup, "span", "data-qa", "mfeCtaMain#offer0#finalPrice"),
        "originalPrice": try_extract(soup, "span", "data-qa", "mfeCtaMain#offer0#originalPrice"),
        "discountInfo": try_extract(soup, "span", "data-qa", "mfeCtaMain#offer0#discountInfo"),
        "offer": try_extract(soup, "span", "class", "psw-t-overline psw-t-bold psw-l-line-left psw-fill-x"),
        "discountDescriptor": try_extract(soup, "span", "data-qa", "mfeCtaMain#offer0#discountDescriptor"),
        "release": try_extract(soup, "dd", "data-qa", "gameInfo#releaseInformation#releaseDate-value"),
        "genre": try_extract(soup, "dd", "class", "gameInfo#releaseInformation#genre-value"),
        "product_tag": try_all_extract(soup, "span", "class", "psw-p-x-2 psw-p-y-1 psw-t-tag"),
        "noticesListItem3": try_all_extract(soup, "li", "class", "psw-l-line-none psw-l-space-x-xs psw-l-shrink-wrap"),
        "discribtionTag": try_all_extract(soup, "div", "class", "psw-l-switcher psw-with-dividers"),
        "ratingProgresBar": try_all_extract(soup, "div", "class", "psw-rating-progress-bar psw-l-stack psw-fill-x"),
        "subtitles": try_all_extract_list(soup, ["gameInfo#releaseInformation#subtitles-value", "gameInfo#releaseInformation#ps5Subtitles-value", "gameInfo#releaseInformation#ps4Subtitles-value"]),
        "voices": try_all_extract_list(soup, ["gameInfo#releaseInformation#Voice-value", "gameInfo#releaseInformation#ps5Voice-value", "gameInfo#releaseInformation#ps4Voice-value"])
    }
    return details

async def main():

    with open("links.txt", "r") as file:
        selected_links = [file.readline().strip() for _ in range(100,500)]


    
    # درخواست و استخراج اطلاعات بازی‌ها
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_game_details(session, url) for url in selected_links]
        game_details = await asyncio.gather(*tasks)
    
        filename = "output1.csv"
        df = pd.DataFrame(game_details)
        df.to_csv(filename, index=False, encoding="utf-8")
 

asyncio.run(main())

