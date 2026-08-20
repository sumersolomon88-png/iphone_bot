import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin


# ============================================================
# НАСТРОЙКИ
# ============================================================

SS_URL = "https://www.ss.lv/lv/electronics/phones/mobile-phones/apple/"
ANDELE_URL = "https://www.andelemandele.lv/perles/tehnika/telefoni/?setlang=lv"

# Токен берём из переменной Railway.
# В Railway нужно создать переменную:
# BOT_TOKEN = твой Telegram Bot Token
BOT_TOKEN = "8935933040:AAEfLk_llaTbsuUfse57oekzvi0vS-_E7Tg"

# Твой chat ID
CHAT_ID = "5309553879"

CHECK_INTERVAL = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7"
}


# ============================================================
# ПАМЯТЬ УЖЕ ОТПРАВЛЕННЫХ ОБЪЯВЛЕНИЙ
# ============================================================

seen_ss = set()
seen_andele = set()


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# TELEGRAM
# ============================================================

def telegram_request(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    try:
        response = requests.post(
            url,
            data=data,
            timeout=20
        )

        print(f"Telegram {method}: {response.status_code}")

        try:
            result = response.json()
            print(result)
            return result
        except Exception:
            print(response.text)
            return None

    except Exception as error:
        print("Telegram error:", error)
        return None


def send_message(text):
    return telegram_request(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False
        }
    )


def send_photo(photo_url, caption):
    if not photo_url:
        return send_message(caption)

    result = telegram_request(
        "sendPhoto",
        {
            "chat_id": CHAT_ID,
            "photo": photo_url,
            "caption": caption
        }
    )

    # Если фотографию Telegram не смог загрузить,
    # отправляем обычное сообщение.
    if not result or result.get("ok") is not True:
        print("Фото не отправилось, отправляю обычное сообщение.")
        return send_message(caption)

    return result


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url(url, base_url):
    if not url:
        return None

    return urljoin(base_url, url)


def get_soup(url):
    try:
        response = session.get(
            url,
            timeout=25
        )

        print(f"HTTP {response.status_code} -> {url}")

        if response.status_code != 200:
            return None

        return BeautifulSoup(
            response.text,
            "html.parser"
        )

    except Exception as error:
        print("Ошибка запроса:", error)
        return None


def get_page_text(soup):
    if not soup:
        return ""

    return clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )


def extract_price(text):
    if not text:
        return "Не указана"

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*€",
        r"€\s*(\d+(?:[.,]\d+)?)"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).replace(",", ".") + " €"

    return "Не указана"


def extract_memory(text):
    if not text:
        return "Не указана"

    patterns = [
        r"\b(32|64|128|256|512|1024)\s*GB\b",
        r"\b(32|64|128|256|512|1024)\s*Gb\b",
        r"\b(32|64|128|256|512|1024)\s*gb\b"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1) + " GB"

    return "Не указана"


def extract_battery(text):
    if not text:
        return "Не указана"

    patterns = [
        r"battery.{0,30}?(\d{2,3})\s*%",
        r"bater(?:ijas|ijas veselība|ijas maksimālā kapacitāte).{0,50}?(\d{2,3})\s*%",
        r"baterija.{0,50}?(\d{2,3})\s*%",
        r"(\d{2,3})\s*%\s*(?:battery|baterija)"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = int(match.group(1))

            if 1 <= value <= 100:
                return str(value) + "%"

    return "Не указана"


def extract_city(text):
    if not text:
        return "Не указан"

    cities = [
        "Rīga",
        "Riga",
        "Jūrmala",
        "Jelgava",
        "Liepāja",
        "Daugavpils",
        "Ventspils",
        "Valmiera",
        "Ogre",
        "Rēzekne"
    ]

    for city in cities:
        if re.search(
            r"\b" + re.escape(city) + r"\b",
            text,
            re.IGNORECASE
        ):
            return city

    return "Не указан"


def extract_image(soup, base_url):
    if not soup:
        return None

    # 1. og:image — самый надёжный вариант
    meta = soup.find(
        "meta",
        property="og:image"
    )

    if meta and meta.get("content"):
        return normalize_url(
            meta["content"],
            base_url
        )

    # 2. twitter:image
    meta = soup.find(
        "meta",
        attrs={"name": "twitter:image"}
    )

    if meta and meta.get("content"):
        return normalize_url(
            meta["content"],
            base_url
        )

    # 3. Старый способ Andele / SS.LV
    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
        )

        if not src:
            continue

        src_lower = src.lower()

        if (
            "logo" not in src_lower
            and "icon" not in src_lower
            and "avatar" not in src_lower
        ):
            return normalize_url(
                src,
                base_url
            )

    return None


# ============================================================
# SS.LV
# ============================================================

def get_ss_links():
    soup = get_soup(SS_URL)

    if not soup:
        print("SS.LV: страница не загрузилась.")
        return []

    links = []

    for a in soup.find_all("a", href=True):

        href = a.get("href", "")

        if "/msg/" not in href:
            continue

        full_link = normalize_url(
            href,
            "https://www.ss.lv"
        )

        if full_link and full_link not in links:
            links.append(full_link)

    print(f"SS.LV: найдено ссылок: {len(links)}")

    return links


def parse_ss_ad(url):
    soup = get_soup(url)

    if not soup:
        return None

    text = get_page_text(soup)

    title = "iPhone"

    if soup.title:
        title = clean_text(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

    # Убираем лишнюю часть заголовка сайта
    title = re.sub(
        r"\s*-\s*Sludinājumi.*$",
        "",
        title,
        flags=re.IGNORECASE
    )

    price = extract_price(text)
    memory = extract_memory(text)
    battery = extract_battery(text)
    city = extract_city(text)
    photo = extract_image(
        soup,
        "https://www.ss.lv"
    )

    return {
        "title": title,
        "price": price,
        "memory": memory,
        "battery": battery,
        "city": city,
        "photo": photo,
        "link": url
    }


def send_ss_ad(ad):
    message = (
        "📱 Новое объявление iPhone\n\n"
        f"📱 {ad['title']}\n"
        f"💰 Цена: {ad['price']}\n"
        f"💾 Память: {ad['memory']}\n"
        f"🔋 Батарея: {ad['battery']}\n"
        f"📍 Город: {ad['city']}\n\n"
        f"🔗 {ad['link']}"
    )

    print("\n" + "=" * 50)
    print("SS.LV")
    print(message)
    print("=" * 50)

    if ad["photo"]:
        send_photo(
            ad["photo"],
            message
        )
    else:
        send_message(message)


# ============================================================
# ANDELE MANDELE
# ============================================================

def get_andele_links():
    soup = get_soup(ANDELE_URL)

    if not soup:
        print("ANDELE: страница не загрузилась.")
        return []

    links = []

    for a in soup.find_all("a", href=True):

        href = a.get("href", "")

        # Нас интересуют именно карточки товаров
        if "/perle/" not in href:
            continue

        full_link = normalize_url(
            href,
            "https://www.andelemandele.lv"
        )

        if not full_link:
            continue

        if full_link in links:
            continue

        links.append(full_link)

    print(
        f"ANDELE: найдено ссылок /perle/: {len(links)}"
    )

    return links


def is_iphone_andele(soup):
    """
    Проверяем всю страницу объявления.

    Andele может указывать:
    - Apple
    - iPhone
    - Mob.telefoni IOS

    Поэтому НЕ ищем iPhone только в одном HTML-элементе.
    """

    if not soup:
        return False

    title = ""

    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True
        )

    text = get_page_text(soup)

    combined = (
        title + " " + text
    ).lower()

    # Прямое упоминание iPhone
    if re.search(
        r"\biphone\b|\biphone\s*\d+",
        combined,
        re.IGNORECASE
    ):
        return True

    # Apple + категория iOS-телефонов
    has_apple = re.search(
        r"\bapple\b",
        combined,
        re.IGNORECASE
    )

    has_ios_category = (
        "mob.telefoni ios" in combined
        or "mob. telefoni ios" in combined
        or "mobile phones ios" in combined
    )

    if has_apple and has_ios_category:
        return True

    # Иногда карточка имеет Apple, но название
    # модели может быть написано иначе.
    if has_apple:
        apple_models = [
            "iphone",
            "apple phone",
            "apple telefon",
            "apple tālrun"
        ]

        for model in apple_models:
            if model in combined:
                return True

    return False


def parse_andele_ad(url):
    soup = get_soup(url)

    if not soup:
        return None

    if not is_iphone_andele(soup):
        print(
            f"ANDELE: не iPhone -> {url}"
        )
        return None

    text = get_page_text(soup)

    title = "iPhone"

    # h1 обычно содержит название объявления
    h1 = soup.find("h1")

    if h1:
        title = clean_text(
            h1.get_text(
                " ",
                strip=True
            )
        )
    elif soup.title:
        title = clean_text(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

    price = extract_price(text)
    memory = extract_memory(text)
    battery = extract_battery(text)
    city = extract_city(text)
    photo = extract_image(
        soup,
        "https://www.andelemandele.lv"
    )

    return {
        "title": title,
        "price": price,
        "memory": memory,
        "battery": battery,
        "city": city,
        "photo": photo,
        "link": url
    }


def send_andele_ad(ad):
    message = (
        "🔵 Новое объявление iPhone — Andele Mandele\n\n"
        f"📱 {ad['title']}\n"
        f"💰 Цена: {ad['price']}\n"
        f"💾 Память: {ad['memory']}\n"
        f"🔋 Батарея: {ad['battery']}\n"
        f"📍 Город: {ad['city']}\n\n"
        f"🔗 {ad['link']}"
    )

    print("\n" + "=" * 50)
    print("ANDELE MANDELE")
    print(message)
    print("=" * 50)

    if ad["photo"]:
        send_photo(
            ad["photo"],
            message
        )
    else:
        send_message(message)


# ============================================================
# ПРОВЕРКА SS.LV
# ============================================================

def check_ss():
    print("\n🟢 Проверяю SS.LV...")

    links = get_ss_links()

    for link in links:

        if link in seen_ss:
            continue

        print(
            f"SS.LV: новое объявление -> {link}"
        )

        ad = parse_ss_ad(link)

        # Запоминаем только после успешного разбора
        if ad:
            seen_ss.add(link)
            send_ss_ad(ad)

        time.sleep(0.5)


# ============================================================
# ПРОВЕРКА ANDELE
# ============================================================

def check_andele():
    print("\n🔵 Проверяю Andele Mandele...")

    links = get_andele_links()

    iphone_count = 0

    for link in links:

        if link in seen_andele:
            continue

        print(
            f"ANDELE: проверяю -> {link}"
        )

        ad = parse_andele_ad(link)

        if ad:

            iphone_count += 1

            seen_andele.add(link)

            send_andele_ad(ad)

        time.sleep(0.5)

    print(
        f"ANDELE: найдено iPhone: {iphone_count}"
    )


# ============================================================
# СТАРТОВОЕ СООБЩЕНИЕ
# ============================================================

def send_start_message():

    message = (
        "🤖 Бот запущен!\n\n"
        "🟢 SS.LV — поиск iPhone\n"
        "🔵 Andele Mandele — поиск iPhone\n\n"
        "📱 Отслеживаются новые объявления\n"
        "⏱ Проверка каждые 10 секунд"
    )

    send_message(message)


# ============================================================
# ОСНОВНОЙ ЦИКЛ
# ============================================================

def main():

    print("=" * 60)
    print("🤖 IPHONE BOT")
    print("=" * 60)

    print(
        f"SS.LV: {SS_URL}"
    )

    print(
        f"Andele: {ANDELE_URL}"
    )

    print(
        f"Интервал: {CHECK_INTERVAL} секунд"
    )

    print("=" * 60)

    # Проверяем Telegram
    print("Проверяю Telegram...")

    test = telegram_request(
        "getMe",
        {}
    )

    if not test or not test.get("ok"):
        print(
            "❌ Telegram не отвечает. "
            "Проверь BOT_TOKEN."
        )
        return

    print("✅ Telegram подключён.")

    send_start_message()

    while True:

        try:

            print("\n" + "#" * 60)
            print("🔎 ПРОВЕРКА САЙТОВ...")
            print("#" * 60)

            check_ss()

            check_andele()

            print(
                f"\n⏱ Следующая проверка "
                f"через {CHECK_INTERVAL} секунд..."
            )

            time.sleep(
                CHECK_INTERVAL
            )

        except KeyboardInterrupt:

            print(
                "\n🛑 Бот остановлен."
            )

            break

        except Exception as error:

            print(
                "\n❌ ГЛОБАЛЬНАЯ ОШИБКА:"
            )

            print(error)

            print(
                f"Повтор через "
                f"{CHECK_INTERVAL} секунд..."
            )

            time.sleep(
                CHECK_INTERVAL
            )


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    main()
