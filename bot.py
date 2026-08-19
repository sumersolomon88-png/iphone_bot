import requests
from bs4 import BeautifulSoup
import time
import re

URL = "https://www.ss.lv/lv/electronics/phones/mobile-phones/apple/"

BOT_TOKEN = "ВСТАВЬ_СВОЙ_ТОКЕН"
CHAT_ID = "5309553879"

seen_links = set()

headers = {
    "User-Agent": "Mozilla/5.0"
}


def send_message(text):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text
            }
        )

        print("sendMessage:", response.status_code)
        print(response.text)

    except Exception as error:
        print("Ошибка отправки сообщения:", error)


def send_photo(photo, caption):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": CHAT_ID,
                "photo": photo,
                "caption": caption
            }
        )

        print("sendPhoto:", response.status_code)
        print(response.text)

    except Exception as error:
        print("Ошибка отправки фотографии:", error)


while True:
    try:
        print("Проверка новых объявлений...")

        response = requests.get(URL, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):

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
            photo = None

            try:
                ad = requests.get(full_link, headers=headers)

                html = ad.text

                ad_soup = BeautifulSoup(html, "html.parser")

                if ad_soup.title:
                    title = ad_soup.title.get_text(strip=True)

                price_match = re.search(r"Cena\s*([\d\s]+€)", html)

                if price_match:
                    price = price_match.group(1)

                memory_match = re.search(r"(\d+)\s?GB", html, re.I)

                if memory_match:
                    memory = memory_match.group(1) + " GB"

                city_match = re.search(
                    r"Rīga|Jūrmala|Liepāja|Daugavpils|Jelgava|Ventspils",
                    html,
                    re.I
                )

                if city_match:
                    city = city_match.group(0)

                image_match = re.search(
                    r'msg_img_dir\s*=\s*"([^"]+)"',
                    html
                )

                if image_match:
                    photo = image_match.group(1) + "800.jpg"

            except Exception as error:
                print("Ошибка объявления:", error)
                continue

            message = (
                f"📱 {title}\n\n"
                f"💰 {price}\n"
                f"💾 {memory}\n"
                f"📍 {city}\n\n"
                f"🔗 {full_link}"
            )

            print(message)

            if photo:
                send_photo(photo, message)
            else:
                send_message(message)

        time.sleep(10)

    except Exception as error:
        print("Общая ошибка:", error)
        time.sleep(10)
