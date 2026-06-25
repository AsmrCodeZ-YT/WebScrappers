# Freelancer Async Scraper

![](./src/pick.png)

A fast and friendly command-line tool to download public freelancer profiles or project listings from Freelancer.com into a clean CSV spreadsheet.

No browser needed – just run a command and get a ready-to-analyze file.
for see columns you can see this pick. ---> [Columns](./src/code.png) <---

## What it does

- 📥 Scrapes **freelancer profiles** (name, skills, location, rating, etc.)
- 📥 Scrapes **latest open projects** (title, budget, category, etc.)
- 🔧 Can scrape **any other Freelancer API endpoint** if you provide a custom URL
- 🚀 Uses parallel requests (async) to fetch thousands of items quickly
- 🧹 Flattens complex nested data into a simple flat table
- 💾 Saves everything into a **CSV file** you can open with Excel, Google Sheets, or Python

## Quick start

1. **Install dependencies** (Python 3.8+ required)

```bash
pip install httpx pandas tqdm rich
```

2. **Run the scraper** – choose your mode:

### Scrape freelancer profiles (users)

```bash
python freelancer.py users -o freelancers.csv
```

This downloads public freelancer directory data. Output columns include:  
`username`, `display_name`, `country.name`, `reputation.overall`, `hourly_rate`, `skills`, and many more.

### Scrape latest open projects (jobs)

```bash
python freelancer.py latest -o projects.csv
```

This fetches currently active projects. The CSV will contain fields like:  
`title`, `budget.minimum`, `budget.maximum`, `currency.code`, `category.name`, `submitdate`, and detailed project descriptions.

### Scrape a custom API endpoint

If you have a specific Freelancer API URL, use `custom` mode. You **must** include `{offset}` in the URL for pagination.

Example:

```bash
python freelancer.py custom \
  --url "https://www.freelancer.com/api/projects/0.1/projects/active?limit=20&offset={offset}&languages[]=en" \
  --items-key projects \
  -o custom_projects.csv
```

The `--items-key` tells the scraper which JSON field contains the list of items (usually `users` or `projects`).

## Command options

| Argument | Description | Default |
|----------|-------------|---------|
| `mode` | `users`, `latest`, or `custom` | required |
| `--url` | URL template for `custom` mode (use `{offset}`) | required for custom |
| `--items-key` | Key holding the list of items (e.g. `users`, `projects`) | auto-detected |
| `--max-concurrent` | Max number of simultaneous requests (speed vs. politeness) | 10 |
| `-o`, `--output` | Output CSV filename | `scraped_data.csv` |

## Output format

The script generates a CSV file with **one row per item** (per user or per project).  
Nested fields are flattened with dots, for example:

- `reputation.overall` – user’s overall reputation score  
- `location.country.name` – country name  
- `budget.minimum` – minimum project budget

You can open the CSV in any spreadsheet application or load it with `pandas` for analysis.

## How many items can I get?

The scraper respects the API’s pagination – it automatically discovers the total number of items and downloads all pages. For the `users` endpoint, you can usually get the whole directory; for `projects`, all currently active listings.

Enjoy exploring Freelancer data! 🕵️‍♀️
