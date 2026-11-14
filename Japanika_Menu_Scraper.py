import csv
import requests
from bs4 import BeautifulSoup

URL = "https://japanika.net/menu/#18"
OUTPUT_CSV = "japanika_menu.csv"

def fetch_page(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text

def parse_menu(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # Each dish is a div with class menuItem
    for item in soup.select("div.menuItem"):
        # Dish name
        title_el = item.select_one("div.menuItem__title h3")
        name = title_el.get_text(strip=True) if title_el else ""

        # Price
        price_el = item.select_one("div.menuItem__price p")
        price = price_el.get_text(strip=True) if price_el else ""

        # Take all the text in the item, then strip out the name and the price to get the description
        all_text = " ".join(s.strip() for s in item.stripped_strings)
        desc = all_text

        if name:
            desc = desc.replace(name, "", 1).strip()
        if price:
            desc = desc.replace(price, "", 1).strip()

        description = desc

        if name and price:
            items.append(
                {
                    "name": name,
                    "description": description,
                    "price": price,
                }
            )

    return items

def save_to_csv(items, path: str):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "description", "price"])
        writer.writeheader()
        writer.writerows(items)

def main():
    html = fetch_page(URL)
    items = parse_menu(html)
    print(f"נמצאו {len(items)} מנות")
    save_to_csv(items, OUTPUT_CSV)
    print(f"המידע נשמר לקובץ: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()