import re
import requests
from bs4 import BeautifulSoup
import csv

def parse_date(date_str):
    date_str = date_str.strip()
    if " - " in date_str:
        date_part, time_part = date_str.split(" - ", 1)
    else:
        date_part, time_part = date_str, "00:00:00"

    if "،" in date_part:
        week_day, rest = date_part.split("،", 1)
    else:
        week_day, rest = "", date_part

    rest = rest.strip()
    parts = rest.split(" ")
    day = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else None
    month = parts[1] if len(parts) > 1 else ""
    year = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

    time_parts = time_part.split(":")
    hour = int(time_parts[0]) if len(time_parts) > 0 and time_parts[0].isdigit() else 0
    minute = int(time_parts[1]) if len(time_parts) > 1 and time_parts[1].isdigit() else 0
    second = int(time_parts[2]) if len(time_parts) > 2 and time_parts[2].isdigit() else 0

    return {
        "week_day": week_day.strip(),
        "day": day,
        "month": month.strip(),
        "year": year,
        "hour": hour,
        "minute": minute,
        "second": second
    }

def parse_page(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    rows = soup.select("table tr")

    data = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        a = cells[0].find("a")
        if not a:
            continue

        title = a.get_text(strip=True)

        href = a["href"].strip()
        href = href.replace("https://www.iranjib.ir", "")
        link = "https://www.iranjib.ir" + href

        views_raw = cells[1].get_text(strip=True)
        views_num = re.sub(r"\D", "", views_raw)
        views = int(views_num) if views_num else 0

        date_raw = cells[2].get_text(" ", strip=True)
        date_cleaned = parse_date(date_raw)

        data.append({
            "title": title,
            "link": link,
            "views": views,
            **date_cleaned
        })
    return data

END_PAGE = 20
urls = [f"https://www.iranjib.ir/jax/showarchive.php?p=1&_id={i}" for i in range(1,END_PAGE)]

all_data = []
for u in urls:
    all_data.extend(parse_page(u))
# EXPORT
keys = ["title", "link", "views", "week_day", "day", "month", "year", "hour", "minute", "second"]
with open("iranjib_news.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    writer.writerows(all_data)

print("CSV saved with", len(all_data), "rows.")
