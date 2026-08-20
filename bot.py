import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin


# ============================================================
# TELEGRAM
# ============================================================

# ОСТАВЬ ЗДЕСЬ СВОЙ УЖЕ РАБОТАЮЩИЙ BOT_TOKEN
BOT_TOKEN = "ТВОЙ_ТЕКУЩИЙ_ТОКЕН"

CHAT_ID = "5309553879"


# ============================================================
# НАСТРОЙКИ
# ============================================================

CHECK_INTERVAL = 10

# ТЕСТ:
# При первом запуске бот отправит уже существующие объявления.
SEND_OLD_ADS = True

# Сколько старых объявлений отправить с каждого сайта.
# Для первого теста ставим 10, чтобы Telegram не получил сотни сообщений.
OLD_ADS_LIMIT = 10


# ============================================================
# САЙТЫ
# ============================================================

SS_URL = (
    "https://www.ss.lv/lv/electronics/phones/"
    "mobile-phones/apple/"
)

ANDELE_URLS = [
    "https://www.andelemandele.lv/"
    "perles/tehnika/telefoni/?setlang=lv",

    "https://www.andelemandele.lv/"
    "perles/elektronika/telefoni/?setlang=lv"
]


# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7"
}


# ============================================================
# ПАМЯТЬ ОБЪЯВЛЕНИЙ
# ============================================================

seen_ss = set()
seen_andele = set()


# ============================================================
# TELEGRAM
# ============================================================

def send_message(text):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": False
            },
            timeout=15
        )

        print("Telegram:", response.status_code)

        if response.status_code != 200:
            print("Telegram error:", response.text)

        return response.status_code == 200

    except Exception as error:
        print("Ошибка отправки в Telegram:", error)
        return False


# ============================================================
# ПРОВЕРКА TELEGRAM
# ============================================================

def test_telegram():
    print("Проверяю Telegram...")

    message = (
        "🤖 ТЕСТ БОТА\n\n"
        "Бот запущен и готов искать объявления.\n"
        "Если ты видишь это сообщение — Telegram работает."
    )

    return send_message(message)


# ============================================================
# ПОЛУЧЕНИЕ СТРАНИЦЫ
# ============================================================

def get_page(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        print(
            f"HTTP {response.status_code}: {url}"
        )

        if response.status_code != 200:
            return None

        return response.text

    except Exception as error:
        print(
            "Ошибка загрузки:",
            url,
            error
        )
        return None


# ============================================================
# SS.LV — ПОИСК ОБЪЯВЛЕНИЙ
# ============================================================

def get_ss_ads():
    ads = []

    html = get_page(SS_URL)

    if not html:
        return ads

    soup = BeautifulSoup(
        html,
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

        title = link.get_text(
            " ",
            strip=True
        )

        if not title:
            title = "iPhone"

        ads.append({
            "url": full_link,
            "title": title
        })

    # Убираем дубликаты
    unique = {}

    for ad in ads:
        unique[ad["url"]] = ad

    return list(unique.values())


# ============================================================
# SS.LV — ПОЛУЧЕНИЕ ДАННЫХ ОБЪЯВЛЕНИЯ
# ============================================================

def get_ss_details(url):
    title = "Не указано"
    price = "Не указана"
    memory = "Не указана"
    city = "Не указан"

    html = get_page(url)

    if not html:
        return title, price, memory, city

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Название
    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True
        )

    # Цена
    price_patterns = [
        r"Cena\s*([0-9\s]+€)",
        r"Цена\s*([0-9\s]+€)",
        r"([0-9\s]+€)"
    ]

    for pattern in price_patterns:
        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:
            price = match.group(1).strip()
            break

    # Память
    memory_match = re.search(
        r"(\d+)\s?(GB|gb)",
        html,
        re.IGNORECASE
    )

    if memory_match:
        memory = (
            memory_match.group(1)
            + " "
            + memory_match.group(2).upper()
        )

    # Город
    cities = [
        "Rīga",
        "Jūrmala",
        "Liepāja",
        "Daugavpils",
        "Jelgava",
        "Ventspils",
        "Riga"
    ]

    for city_name in cities:

        if re.search(
            city_name,
            html,
            re.IGNORECASE
        ):
            city = city_name
            break

    return title, price, memory, city


# ============================================================
# ANDELE MANDELE — ПОИСК ТЕЛЕФОНОВ
# ============================================================

def get_andele_ads():

    all_ads = {}

    for category_url in ANDELE_URLS:

        print(
            "Проверяю Andele:",
            category_url
        )

        html = get_page(
            category_url
        )

        if not html:
            continue

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link["href"]

            # Страница товара Andele
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

            # Проверяем название + ссылку
            check_text = (
                title
                + " "
                + full_link
            ).lower()

            # Только iPhone
            if "iphone" not in check_text:
                continue

            if full_link not in all_ads:

                if not title:
                    title = "iPhone"

                all_ads[full_link] = {
                    "url": full_link,
                    "title": title
                }

    return list(
        all_ads.values()
    )


# ============================================================
# ANDELE MANDELE — ДАННЫЕ ОБЪЯВЛЕНИЯ
# ============================================================

def get_andele_details(url, fallback_title):

    title = fallback_title
    price = "Не указана"
    condition = "Не указано"

    html = get_page(url)

    if not html:
        return title, price, condition

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Заголовок страницы
    h1 = soup.find("h1")

    if h1:
        text = h1.get_text(
            " ",
            strip=True
        )

        if text:
            title = text

    # Если H1 не найден
    if not title:

        if soup.title:

            title = soup.title.get_text(
                " ",
                strip=True
            )

    # Ищем цену
    price_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*€",
        soup.get_text(
            " ",
            strip=True
        )
    )

    if price_match:

        price = (
            price_match.group(1)
            + " €"
        )

    # Состояние
    page_text = soup.get_text(
        " ",
        strip=True
    )

    if "Jauns" in page_text:
        condition = "Новое"

    elif "Lietots, lieliskā stāvoklī" in page_text:
        condition = "Б/у, отличное состояние"

    elif "Lietots, labā stāvoklī" in page_text:
        condition = "Б/у, хорошее состояние"

    elif "Lietots" in page_text:
        condition = "Б/у"

    return title, price, condition


# ============================================================
# ОТПРАВКА SS.LV
# ============================================================

def send_ss_ad(ad, old=False):

    title, price, memory, city = get_ss_details(
        ad["url"]
    )

    if old:
        prefix = "🧪 ТЕСТ — СТАРОЕ SS.LV"
    else:
        prefix = "🟢 НОВОЕ SS.LV"

    message = (
        f"{prefix}\n\n"
        f"📱 {title}\n\n"
        f"💰 {price}\n"
        f"💾 {memory}\n"
        f"📍 {city}\n\n"
        f"🔗 {ad['url']}"
    )

    print("\n" + message)

    send_message(
        message
    )


# ============================================================
# ОТПРАВКА ANDELE
# ============================================================

def send_andele_ad(ad, old=False):

    title, price, condition = get_andele_details(
        ad["url"],
        ad["title"]
    )

    if old:
        prefix = "🧪 ТЕСТ — СТАРОЕ ANDELE"
    else:
        prefix = "🔵 НОВОЕ ANDELE"

    message = (
        f"{prefix}\n\n"
        f"📱 {title}\n\n"
        f"💰 {price}\n"
        f"📦 {condition}\n\n"
        f"🔗 {ad['url']}"
    )

    print("\n" + message)

    send_message(
        message
    )


# ============================================================
# ПЕРВЫЙ ЗАПУСК
# ============================================================

print("")
print("========================================")
print("        IPHONE BOT ЗАПУЩЕН")
print("========================================")
print("🟢 SS.LV")
print("🔵 ANDELE MANDELE")
print("📱 Только iPhone")
print(f"⏱ Проверка каждые {CHECK_INTERVAL} секунд")
print("========================================")
print("")


# ============================================================
# TELEGRAM TEST
# ============================================================

telegram_ok = test_telegram()

if not telegram_ok:

    print(
        "❌ Telegram не отвечает."
    )

    while True:
        time.sleep(60)


# ============================================================
# ПОЛУЧАЕМ СТАРЫЕ ОБЪЯВЛЕНИЯ
# ============================================================

print("")
print("Ищу существующие объявления...")
print("")


ss_ads = get_ss_ads()

print(
    f"SS.LV: найдено {len(ss_ads)} объявлений"
)


andele_ads = get_andele_ads()

print(
    f"Andele: найдено {len(andele_ads)} iPhone"
)


# ============================================================
# ТЕСТ — ОТПРАВЛЯЕМ СТАРЫЕ ОБЪЯВЛЕНИЯ
# ============================================================

if SEND_OLD_ADS:

    print("")
    print(
        "🧪 ТЕСТОВЫЙ РЕЖИМ: "
        "отправляю старые объявления"
    )
    print("")

    # SS.LV
    ss_to_send = ss_ads[
        :OLD_ADS_LIMIT
    ]

    print(
        f"SS.LV: отправляю "
        f"{len(ss_to_send)} объявлений"
    )

    for ad in ss_to_send:

        send_ss_ad(
            ad,
            old=True
        )

        seen_ss.add(
            ad["url"]
        )

        time.sleep(1)


    # ANDELE
    andele_to_send = andele_ads[
        :OLD_ADS_LIMIT
    ]

    print(
        f"Andele: отправляю "
        f"{len(andele_to_send)} объявлений"
    )

    for ad in andele_to_send:

        send_andele_ad(
            ad,
            old=True
        )

        seen_andele.add(
            ad["url"]
        )

        time.sleep(1)


# ============================================================
# ПОСЛЕ ТЕСТА ЗАПОМИНАЕМ ВСЕ ТЕКУЩИЕ
# ============================================================

for ad in ss_ads:

    seen_ss.add(
        ad["url"]
    )


for ad in andele_ads:

    seen_andele.add(
        ad["url"]
    )


print("")
print("========================================")
print("ТЕСТ ЗАКОНЧЕН")
print(
    f"SS.LV в памяти: {len(seen_ss)}"
)
print(
    f"Andele в памяти: {len(andele_seen) if False else len(seen_andele)}"
)
print("========================================")
print("")


# ============================================================
# ОСНОВНОЙ ЦИКЛ
# ============================================================

while True:

    try:

        print("")
        print(
            "🔎 Проверяю сайты..."
        )


        # ====================================================
        # SS.LV
        # ====================================================

        current_ss = get_ss_ads()

        print(
            f"SS.LV найдено: "
            f"{len(current_ss)}"
        )

        for ad in current_ss:

            url = ad["url"]

            if url in seen_ss:
                continue

            print(
                "🆕 НОВОЕ SS.LV:",
                url
            )

            send_ss_ad(
                ad,
                old=False
            )

            seen_ss.add(
                url
            )


        # ====================================================
        # ANDELE MANDELE
        # ====================================================

        current_andele = get_andele_ads()

        print(
            f"Andele найдено iPhone: "
            f"{len(current_andele)}"
        )

        for ad in current_andele:

            url = ad["url"]

            if url in seen_andele:
                continue

            print(
                "🆕 НОВОЕ ANDELE:",
                url
            )

            send_andele_ad(
                ad,
                old=False
            )

            seen_andele.add(
                url
            )


        # ====================================================
        # ОЖИДАНИЕ
        # ====================================================

        print(
            f"⏱ Следующая проверка "
            f"через {CHECK_INTERVAL} секунд..."
        )

        time.sleep(
            CHECK_INTERVAL
        )


    except Exception as error:

        print("")
        print(
            "❌ ОШИБКА ОСНОВНОГО ЦИКЛА:"
        )

        print(error)

        print(
            "Повтор через 10 секунд..."
        )

        time.sleep(10)
