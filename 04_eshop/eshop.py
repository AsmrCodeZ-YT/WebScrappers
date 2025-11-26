import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json


HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0"
}


async def fetch(session, url):
    """دریافت HTML هر صفحه"""
    try:
        async with session.get(url, headers=HEADERS, timeout=30) as response:
            if response.status == 200:
                return await response.text()
            else:
                print(f"⚠️ وضعیت {response.status} برای {url}")
                return None
    except Exception as e:
        print(f"❌ خطا در دریافت {url}: {e}")
        return None


def parse_products(html):
    """پارس HTML و استخراج داده‌ها"""
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for article in soup.select("article.product-miniature"):
        try:
            product = {
                "product_id": article.get("data-id-product"),
                "title": article.select_one("h5.product-name span").get_text(strip=True)
                if article.select_one("h5.product-name span")
                else None,
                "description": article.select_one(
                    "div.product-description-short"
                ).get_text(strip=True)
                if article.select_one("div.product-description-short")
                else None,
                "price": article.select_one("span.price.product-price").get_text(
                    strip=True
                )
                if article.select_one("span.price.product-price")
                else None,
                "currency": article.select_one("span.price-currency").get_text(
                    strip=True
                )
                if article.select_one("span.price-currency")
                else None,
                "product_code": article.select_one(
                    "div.product-reference span"
                ).get_text(strip=True)
                if article.select_one("div.product-reference span")
                else None,
                "image_url": article.select_one("img").get("src")
                if article.select_one("img")
                else None,
                "product_link": article.select_one("a").get("href")
                if article.select_one("a")
                else None,
                "availability": article.select_one("meta[itemprop='availability']").get(
                    "content"
                )
                if article.select_one("meta[itemprop='availability']")
                else None,
                "price_valid_until": article.select_one(
                    "meta[itemprop='priceValidUntil']"
                ).get("content")
                if article.select_one("meta[itemprop='priceValidUntil']")
                else None,
                "price_currency_code": article.select_one(
                    "meta[itemprop='priceCurrency']"
                ).get("content")
                if article.select_one("meta[itemprop='priceCurrency']")
                else None,
                "sku": article.select_one("meta[itemprop='sku']").get("content")
                if article.select_one("meta[itemprop='sku']")
                else None,
            }
            products.append(product)
        except Exception as e:
            print(f"⚠️ خطا در پارس یکی از محصولات: {e}")
            continue

    return products


async def scrape_eca(start_page=1, end_page=3):
    """اسکرپ صفحات محصولات جدید"""
    url = "https://eshop.eca.ir/268-%D9%85%DB%8C%D9%86%DB%8C-%DA%A9%D8%A7%D9%85%D9%BE%DB%8C%D9%88%D8%AA%D8%B1-mini-pc"
    base_url = url + "?page={}"
    all_products = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for page in range(start_page, end_page + 1):
            url = base_url.format(page)
            tasks.append(fetch(session, url))

        pages_html = await asyncio.gather(*tasks)

        for page_num, html in enumerate(pages_html, start=start_page):
            if html:
                products = parse_products(html)
                print(f"✅ {len(products)} محصول از صفحه {page_num} استخراج شد")
                all_products.extend(products)

    with open("eca_products.json", "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"\n📦 مجموع محصولات استخراج‌شده: {len(all_products)}")
    print("💾 خروجی ذخیره شد در: eca_products.json")


if __name__ == "__main__":
    asyncio.run(scrape_eca(start_page=1, end_page=6))
