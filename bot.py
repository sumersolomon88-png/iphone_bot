import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin


# =========================
# TELEGRAM
# =========================

# ОСТАВЬ ЗДЕСЬ СВОЙ СУЩЕСТВУЮЩИЙ BOT_TOKEN
BOT_TOKEN = "8935933040:AAEfLk_llaTbsuUfse57oekzvi0vS-_E7Tg"

CHAT_ID = "5309553879"


# =========================
# SS.LV
# =========================

SS_URL = "https://www.ss.lv/lv/electronics/phones/mobile-phones/apple/"


# =========================
# ANDELE MANDELE
# =========================

ANDELE_URL = (
    "https://www.andelemandele.lv/"
    "perles/tehnika/telefoni/?setlang=lv"
)


headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )
}


seen_ss_links = set()
seen_andele_links = set()


# =========================
# TELEGRAM
# =========================

def send_message(text):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": False
            },
            timeout=10
        )

        print("Telegram:", response.text)

    except Exception as error:
        print("Ошибка Telegram:", error)


# =========================
# SS.LV
# =========================

def check_ss():
    try:
        response = requests.get(
            SS_URL,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link["href"]

            if "/msg/" not in href:
                continue

            full_link = urljoin(
                "https://www.ss.lv",
                href
            )

            if full_link in seen_ss_links:
                continue

            seen_ss_links.add(full_link)

            title = link.get_text(
                " ",
                strip=True
            )

            if not title:
                title = "Новое объявление iPhone"

            message = (
                "🟢 SS.LV\n\n"
                f"📱 {title}\n\n"
                f"🔗 {full_link}"
            )

            send_message(message)

            print(
                "SS.LV:",
                full_link
            )

    except Exception as error:
        print(
            "Ошибка SS.LV:",
            error
        )


# =========================
# ANDELE MANDELE
# =========================

def check_andele():
    try:
        response = requests.get(
            ANDELE_URL,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link["href"]

            if "/perle/" not in href:
                continue

            full_link = urljoin(
                "https://www.andelemandele.lv",
                href
            )

            title = link.get_text(
                " ",
                strip=True
            )

            text_for_check = (
                title + " " + href
            ).lower()

            # Только iPhone
            if "iphone" not in text_for_check:
                continue

            if full_link in seen_andele_links:
                continue

            seen_andele_links.add(
                full_link
            )

            message = (
                "🔵 ANDELE MANDELE\n\n"
                f"📱 {title}\n\n"
                f"🔗 {full_link}"
            )

            send_message(message)

            print(
                "ANDELE:",
                full_link
            )

    except Exception as error:
        print(
            "Ошибка Andele Mandele:",
            error
        )

print(
    "Загрузка существующих объявлений SS.LV..."
)

try:
    response = requests.get(
        SS_URL,
        headers=headers,
        timeout=10
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if "/msg/" not in href:
            continue

        full_link = urljoin(
            "https://www.ss.lv",
            href
        )

        seen_ss_links.add(
            full_link
        )

except Exception as error:
    print(
        "Ошибка загрузки SS.LV:",
        error
    )


# =========================
# ЗАПОМИНАЕМ СУЩЕСТВУЮЩИЕ
# ОБЪЯВЛЕНИЯ ANDELE
# =========================

print(
    "Загрузка существующих объявлений "
    "Andele Mandele..."
)

try:
    response = requests.get(
        ANDELE_URL,
        headers=headers,
        timeout=10
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if "/perle/" not in href:
            continue

        full_link = urljoin(
            "https://www.andelemandele.lv",
            href
        )

        title = link.get_text(
            " ",
            strip=True
        )

        text_for_check = (
            title + " " + href
        ).lower()

        if "iphone" not in text_for_check:
            continue

        seen_andele_links.add(
            full_link
        )

except Exception as error:
    print(
        "Ошибка загрузки Andele:",
        error
    )


# =========================
# ЗАПУСК
# =========================

print("==============================")
print("Бот запущен!")
print("🟢 SS.LV: включён")
print("🔵 Andele Mandele: включён")
print("📱 Поиск: только iPhone")
print("⏱ Интервал: 10 секунд")
print("==============================")


# =========================
# ОСНОВНОЙ ЦИКЛ
# =========================

while True:

    try:

        print("\nПроверяю сайты...")

        check_ss()
        check_andele()

        time.sleep(10)

    except Exception as error:

        print(
            "Общая ошибка:",
            error
        )

        time.sleep(10)
# =========================
# ЗАПОМИНАЕМ СУЩЕСТВУЮЩИЕ
# ОБЪЯВЛЕНИЯ SS.LV
# =========================
