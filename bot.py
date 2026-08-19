import requests
from bs4 import BeautifulSoup
import time
import re

URL = "https://www.ss.lv/lv/electronics/phones/mobile-phones/apple/"

BOT_TOKEN = "8935933040:AAEfLk_llaTbsuUfse57oekzvi0vS-_E7Tg"
CHAT_ID = "5309553879"

seen_links = set()

headers = {
    "User-Agent": "Mozilla/5.0"
}


def send_message(text):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text
        }
    )

    print("sendMessage:", response.text)


while True:
    try:
        response = requests.get(URL, headers=headers, timeout=10)

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a", href=True)

        for link in links:

            href = link["href"]

            if "/msg/" not in href:
                continue

            full_link = "https://www.ss.lv" + href

            if full_link in seen_links:
                continue

            seen_links.add(full_link)

            title = "Не указано"
            price = "Не указана"
            memory = "Не указана"
            city = "Не указан"

            try:
                ad = requests.get(
                    full_link,
                    headers=headers,
                    timeout=10
                )

                html = ad.text

                ad_soup = BeautifulSoup(html, "html.parser")

                if ad_soup.title:
                    title = ad_soup.title.get_text(strip=True)

                price_match = re.search(
                    r"Cena\s*([\d\s]+€)",
                    html
                )

                if price_match:
                    price = price_match.group(1)

                memory_match = re.search(
                    r"(\d+)\s?GB",
                    html,
                    re.I
                )

                if memory_match:
                    memory = memory_match.group(1) + " GB"

                city_match = re.search(
                    r"Rīga|Jūrmala|Liepāja|Daugavpils|Jelgava|Ventspils",
                    html,
                    re.I
                )

                if city_match:
                    city = city_match.group(0)

            except Exception as error:
                print("Ошибка объявления:", error)

            message = (
                f"📱 {title}\n\n"
                f"💰 {price}\n"
                f"💾 {memory}\n"
                f"📍 {city}\n\n"
                f"🔗 {full_link}"
            )

            send_message(message)

            print(message)

        time.sleep(10)

    except Exception as error:
        print("Ошибка:", error)
        time.sleep(10)
