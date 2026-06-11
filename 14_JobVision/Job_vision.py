from click import option
import pandas as pd
import json
from collections.abc import MutableMapping
from bs4 import BeautifulSoup
import json
import re
import requests
from datetime import datetime
from pprint import pp

PAGE_NUMBER = 2




# url = "https://jobvision.ir/jobs/category/data-science?page=1&sort=0"
url =  input("Enter the URL (e.g. https://jobvision.ir/jobs/category/data-science?page=1&sort=0): ")
if not url:
    exit()

option = {
    "ALL": 0,
    "3 Days Ago": 1,
    "7 Days Ago": 2,
    "15 Days Ago": 3,
    "30 Days Ago": 4
}
pp(option, indent=4)

searchTimeRange = int(input("Range Time: "))



def flatten_dict(d, parent_key="", sep="."):
    """
    Recursively flatten nested JSON/dict into a single-level dict.
    - Nested dicts: parent.child
    - List of dicts: parent.0.child, parent.1.child, ... (index embedded)
    - Other lists (primitives/mixed): kept as JSON string
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # If the list contains only dicts, flatten each with its index
            if v and all(isinstance(item, MutableMapping) for item in v):
                for i, item in enumerate(v):
                    indexed_key = f"{new_key}{sep}{i}"
                    items.extend(flatten_dict(item, indexed_key, sep=sep).items())
            else:
                # Keep other lists as a JSON string
                items.append((new_key, json.dumps(v, ensure_ascii=False)))
        else:
            items.append((new_key, v))
    return dict(items)


def flatten_json_to_df(json_data):
    """
    Convert deeply nested JSON (list of records or single record) into a flat DataFrame.
    Lists of dicts get individual columns per index: e.g. labelDetails.0.title
    Missing columns across records are filled with NaN automatically.
    """
    if isinstance(json_data, dict):
        json_data = [json_data]
    flat_records = [flatten_dict(record) for record in json_data]
    return pd.DataFrame(flat_records)


def totext(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.text


# -------------- Main Code --------------
THIS_TIME = datetime.now().strftime(r"%d-%m-%Y")


category = ""
pattern = r"category/([^?]+)"
match = re.search(pattern, url)
if match:
    category = match.group(1)


FILENAME = f"{category}_{THIS_TIME}.csv"

url = "https://candidateapi.jobvision.ir/api/v1/JobPost/List"
df = pd.DataFrame()

for i in range(PAGE_NUMBER):

    payload = {
        "pageSize": 30,
        "requestedPage": i,
        "sortBy": 0,
        "searchTimeRange": searchTimeRange,
        "jobCategoryUrlTitle": category,
        "searchId": "null",
    }

    session = requests.Session()
    session.get("https://jobvision.ir/")
    response = session.post(url, json=payload)

    data = {}
    if response.status_code == 200:
        data = response.json()

    list_of_dict = data["data"]["jobPosts"]
    for i in list_of_dict:
        df2 = flatten_json_to_df(i)
        df = pd.concat([df, df2], ignore_index=True)


df.to_csv(FILENAME)  # Store file


FILE_NAME_JOB_ID = f"{category}_{THIS_TIME}_BYID.csv"
ids = df["id"].values[:20]
lenght_ids = len(ids)
df = pd.DataFrame()

for idx, id_number in enumerate(ids):
    url = (
        f"https://candidateapi.jobvision.ir/api/v1/JobPost/Detail?jobPostId={id_number}"
    )

    res = requests.get(url)
    data = json.loads(res.text)
    df2 = flatten_json_to_df(data)
    df = pd.concat([df, df2], ignore_index=True)
    print(f"Find ID {id_number} -- {idx}/{lenght_ids}.")


df["data.description"] = df["data.description"].apply(lambda x: totext(x))
df.to_csv(FILE_NAME_JOB_ID)  # Store file
