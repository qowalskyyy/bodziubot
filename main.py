import requests
from bs4 import BeautifulSoup
import time
import os

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
LOCATION = "Horsens"
MIN_PROFIT_PLN = 300
MIN_DISCOUNT_PERCENT = 40
DKK_TO_PLN = 0.61

seen_ids = set()

def fetch_facebook_offers():
    url = f"https://www.facebook.com/marketplace/{LOCATION}/search?query=elektronika"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    offers = []
    # Prosta ekstrakcja (przykład) - trzeba dopracować selektory
    for item in soup.select("div[role='article']"):
        try:
            title = item.select_one("span").text
            price_str = item.select_one("span[aria-label*='DKK']").text
            price = int(''.join(filter(str.isdigit, price_str)))
            link = item.find("a")["href"]
            id_ = link.split("/")[-1]
            offers.append({"id": id_, "title": title, "price_dkk": price, "url": link})
        except Exception:
            continue
    return offers

def fetch_olx_min_price(title):
    search_url = f"https://www.olx.pl/oferty/q-{title.replace(' ', '-')}/"
    r = requests.get(search_url)
    soup = BeautifulSoup(r.text, "html.parser")
    prices = []
    for el in soup.select(".offer-wrapper .price"):
        try:
            price_str = el.text.strip().replace("zł", "").replace(" ", "")
            price = int(price_str)
            prices.append(price)
        except:
            continue
    if prices:
        return min(prices)
    return None

def send_discord_alert(offer, profit_pln, profit_percent):
    message = (
        f"🔥 **OKAZJA:** {offer['title']} – {offer['price_dkk']} DKK (~{int(offer['price_dkk']*DKK_TO_PLN)} PLN)\n"
        f"📍 {LOCATION}\n"
        f"💰 Cena w PL: {profit_pln + int(offer['price_dkk']*DKK_TO_PLN)} PLN\n"
        f"📈 Zysk: +{profit_pln} PLN (~{profit_percent}%)\n"
        f"🔗 {offer['url']}"
    )
    requests.post(WEBHOOK_URL, json={"content": message})

def main():
    while True:
        offers = fetch_facebook_offers()
        for offer in offers:
            if offer["id"] in seen_ids:
                continue
            seen_ids.add(offer["id"])
            pl_price = fetch_olx_min_price(offer["title"])
            if pl_price is None:
                continue
            dkk_price_pln = int(offer["price_dkk"] * DKK_TO_PLN)
            profit = pl_price - dkk_price_pln
            profit_percent = int(profit / dkk_price_pln * 100)
            if profit >= MIN_PROFIT_PLN and profit_percent >= MIN_DISCOUNT_PERCENT:
                send_discord_alert(offer, profit, profit_percent)
        time.sleep(1500)  # 25 minut

if __name__ == "__main__":
    main()
