import requests
from bs4 import BeautifulSoup
import json

def scrape_google_gemini_article(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    selector = ".module--text.module--text__article"
    divs = soup.select(selector)

    texts = []
    for div in divs:
        text = div.get_text(separator="\n", strip=True)
        texts.append(text)

    return texts


if __name__ == "__main__":
    url = "https://blog.google/products/gemini/gemini-3-gemini-app/"
    texts = scrape_google_gemini_article(url)

    # Save to JSON
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False, indent=4)

    print("Saved to output.json")