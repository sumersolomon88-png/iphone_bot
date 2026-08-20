import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin

# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = "8935933040:AAEfLk_llaTbsuUfse57oekzvi0vS-_E7Tg"
CHAT_ID = "5309553879"

CHECK_INTERVAL = 10

SSLV_URL = "https://www.ss.lv/lv/electronics/phones/mobile-phones/apple/"

ANDELE_URL = "https://www.andelemandele.lv/perles/home/tehnika/telefoni/?setlang=lv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8"
}


# ============================================================
# ПАМЯТЬ ОБ УЖЕ ОТПРАВЛЕННЫХ ОБЪЯВЛЕНИЯХ
# ============================================================

seen_sslv = set()
seen_andele = set()


# ============================================================
# TELEGRAM
# ============================================================

def telegram_request(method, data=None, files=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

        response = requests.post(
            url,
            data=data,
            files=files,
            timeout=30
        )

        print(
            f"Telegram {method}: "
            f"{response.status_code} -> {response.text[:500]}"
        )

        return response

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
    return telegram_request(
        "sendPhoto",
        {
            "chat_id": CHAT_ID,
            "photo": photo_url,
            "caption": caption
        }
    )


# ============================================================
# ОБЩИЕ ФУНКЦИИ
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_soup(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        print(f"HTTP {response.status_code} -> {url}")

        if response.status_code != 200:
            return None

        return BeautifulSoup(
            response.text,
            "html.parser"
        )

    except Exception as error:
        print("Ошибка загрузки:", error)
        return None


def absolute_url(url, base_url):
    if not url:
        return None

    return urljoin(base_url, url)


def is_image_url(url):
    if not url:
        return False

    url = url.lower()

    return any(
        extension in url
        for extension in [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        ]
    )


# ============================================================
# SS.LV
# ============================================================

def parse_sslv_ad(url):
    print("SS.LV: открываю объявление...")

    soup = get_soup(url)

    if not soup:
        return None

    title = "Не указано"
    price = "Не указана"
    memory = "Не указана"
    battery = "Не указана"
    city = "Не указан"
    photo = None

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    if soup.title:
        title = clean_text(
            soup.title.get_text(" ", strip=True)
        )

    # --------------------------------------------------------
    # ВЕСЬ ТЕКСТ СТРАНИЦЫ
    # --------------------------------------------------------

    page_text = clean_text(
        soup.get_text(" ", strip=True)
    )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    price_patterns = [
        r"Cena\s*:?\s*([\d\s]+)\s*€",
        r"Цена\s*:?\s*([\d\s]+)\s*€",
        r"([\d\s]+)\s*€"
    ]

    for pattern in price_patterns:

        match = re.search(
            pattern,
            page_text,
            re.I
        )

        if match:
            price = clean_text(
                match.group(1)
            ) + " €"
            break

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    memory_patterns = [
        r"(\d+)\s*GB",
        r"(\d+)\s*Gb",
        r"(\d+)\s*gb"
    ]

    for pattern in memory_patterns:

        match = re.search(
            pattern,
            page_text
        )

        if match:
            memory = match.group(1) + " GB"
            break

    # --------------------------------------------------------
    # BATTERY
    # --------------------------------------------------------

    battery_patterns = [
        r"[Bb]aterija[^0-9]{0,30}(\d{1,3})\s*%",
        r"[Bb]attery[^0-9]{0,30}(\d{1,3})\s*%",
        r"(\d{1,3})\s*%\s*[Bb]ater"
    ]

    for pattern in battery_patterns:

        match = re.search(
            pattern,
            page_text,
            re.I
        )

        if match:
            battery = match.group(1) + "%"
            break

    # --------------------------------------------------------
    # CITY
    # --------------------------------------------------------

    cities = [
        "Rīga",
        "Riga",
        "Jūrmala",
        "Liepāja",
        "Daugavpils",
        "Jelgava",
        "Ventspils",
        "Valmiera",
        "Ogre"
    ]

    for city_name in cities:

        if re.search(
            r"\b" + re.escape(city_name) + r"\b",
            page_text,
            re.I
        ):
            city = city_name
            break

    # --------------------------------------------------------
    # PHOTO
    # --------------------------------------------------------

    # Сначала пробуем старый способ SS.LV
    html = str(soup)

    image_match = re.search(
        r'msg_img_dir\s*=\s*"([^"]+)"',
        html
    )

    if image_match:

        photo = image_match.group(1)

        if not photo.endswith("800.jpg"):
            photo = photo.rstrip("/") + "800.jpg"

        photo = absolute_url(
            photo,
            "https://www.ss.lv"
        )

    # Если старый способ не сработал,
    # ищем og:image
    if not photo:

        og_image = soup.find(
            "meta",
            property="og:image"
        )

        if og_image:

            photo = og_image.get("content")

            photo = absolute_url(
                photo,
                url
            )

    # --------------------------------------------------------
    # РЕЗУЛЬТАТ
    # --------------------------------------------------------

    message = (
        "📱 Новое объявление iPhone\n\n"
        f"🟢 SS.LV\n"
        f"📱 {title}\n\n"
        f"💰 Цена: {price}\n"
        f"💾 Память: {memory}\n"
        f"🔋 Батарея: {battery}\n"
        f"📍 Город: {city}\n\n"
        f"🔗 {url}"
    )

    return {
        "message": message,
        "photo": photo
    }


def check_sslv():

    print("🟢 SS.LV: проверяю сайт...")

    soup = get_soup(SSLV_URL)

    if not soup:
        print("SS.LV: сайт не загрузился")
        return

    links = []

    for link in soup.find_all("a", href=True):

        href = link.get("href")

        if not href:
            continue

        if "/msg/" not in href:
            continue

        full_link = absolute_url(
            href,
            "https://www.ss.lv"
        )

        if full_link not in links:
            links.append(full_link)

    print(
        f"🟢 SS.LV: найдено ссылок: {len(links)}"
    )

    for full_link in links:

        if full_link in seen_sslv:
            continue

        print(
            "🟢 SS.LV: новое объявление ->",
            full_link
        )

        data = parse_sslv_ad(
            full_link
        )

        if not data:
            continue

        seen_sslv.add(full_link)

        if data["photo"]:

            result = send_photo(
                data["photo"],
                data["message"]
            )

            # Если Telegram не смог отправить фото,
            # отправляем обычное сообщение
            if (
                result is None
                or result.status_code != 200
            ):
                send_message(
                    data["message"]
                )

        else:

            send_message(
                data["message"]
            )


# ============================================================
# ANDELE MANDELE
# ============================================================

def looks_like_iphone(text):

    text = text.lower()

    iphone_words = [
        "iphone",
        "i phone",
        "айфон"
    ]

    for word in iphone_words:

        if word in text:
            return True

    return False


def is_apple_ios_phone(text):

    text_lower = text.lower()

    apple = (
        "apple" in text_lower
        or "iphone" in text_lower
        or "ābol" in text_lower
    )

    ios_phone = (
        "mob.telefoni ios" in text_lower
        or "mob telefoni ios" in text_lower
        or "telefoni ios" in text_lower
    )

    return apple and ios_phone


def extract_andele_photo(soup, url):

    # --------------------------------------------------------
    # 1. og:image — самый надёжный вариант
    # --------------------------------------------------------

    og = soup.find(
        "meta",
        property="og:image"
    )

    if og:

        image = og.get("content")

        if image:

            image = absolute_url(
                image,
                url
            )

            if image:
                return image

    # --------------------------------------------------------
    # 2. twitter:image
    # --------------------------------------------------------

    twitter = soup.find(
        "meta",
        attrs={
            "name": "twitter:image"
        }
    )

    if twitter:

        image = twitter.get("content")

        if image:

            image = absolute_url(
                image,
                url
            )

            if image:
                return image

    # --------------------------------------------------------
    # 3. обычные img
    # --------------------------------------------------------

    for img in soup.find_all("img"):

        for attribute in [
            "src",
            "data-src",
            "data-original",
            "data-lazy-src"
        ]:

            image = img.get(attribute)

            if not image:
                continue

            image = absolute_url(
                image,
                url
            )

            if is_image_url(image):
                return image

    return None


def extract_andele_field(
    text,
    labels
):

    for label in labels:

        pattern = (
            re.escape(label)
            + r"\s*:?\s*"
            + r"(.{1,100})"
        )

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            value = re.split(
                r"\s+(?:Zīmols|Krāsa|Stāvoklis|"
                r"Tehnikas veids|Pievienots)\b",
                value,
                flags=re.I
            )[0]

            return value.strip()

    return None


def parse_andele_ad(url):

    print(
        "🔵 ANDELE: проверяю карточку...",
        url
    )

    soup = get_soup(url)

    if not soup:
        return None

    # --------------------------------------------------------
    # ВЕСЬ ТЕКСТ
    # --------------------------------------------------------

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    # --------------------------------------------------------
    # ПРОВЕРКА: ДЕЙСТВИТЕЛЬНО ЛИ ЭТО IPHONE
    # --------------------------------------------------------

    if not is_apple_ios_phone(text):

        print(
            "🔵 ANDELE: не Apple/iOS ->",
            url
        )

        return None

    if not looks_like_iphone(text):

        print(
            "🔵 ANDELE: нет слова iPhone ->",
            url
        )

        return None

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title = "iPhone"

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

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    price = "Не указана"

    price_patterns = [
        r"(\d[\d\s]*(?:[.,]\d+)?)\s*€",
        r"€\s*(\d[\d\s]*(?:[.,]\d+)?)"
    ]

    for pattern in price_patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            price = (
                clean_text(
                    match.group(1)
                )
                + " €"
            )

            break

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    memory = "Не указана"

    memory_patterns = [
        r"(\d+)\s*GB",
        r"(\d+)\s*Gb",
        r"(\d+)\s*gb",
        r"(\d+)\s*GB\s*atmiņa"
    ]

    for pattern in memory_patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            memory = (
                match.group(1)
                + " GB"
            )

            break

    # --------------------------------------------------------
    # BATTERY
    # --------------------------------------------------------

    battery = "Не указана"

    battery_patterns = [
        r"[Bb]ater(?:ija|ijas)[^0-9]{0,50}(\d{1,3})\s*%",
        r"[Bb]attery[^0-9]{0,50}(\d{1,3})\s*%",
        r"(\d{1,3})\s*%\s*[Bb]ater"
    ]

    for pattern in battery_patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            battery = (
                match.group(1)
                + "%"
            )

            break

    # --------------------------------------------------------
    # CITY
    # --------------------------------------------------------

    city = "Не указан"

    cities = [
        "Rīga",
        "Riga",
        "Jūrmala",
        "Liepāja",
        "Daugavpils",
        "Jelgava",
        "Ventspils",
        "Valmiera",
        "Ogre"
    ]

    for city_name in cities:

        if re.search(
            r"\b"
            + re.escape(city_name)
            + r"\b",
            text,
            re.I
        ):

            city = city_name
            break

    # --------------------------------------------------------
    # PHOTO
    # --------------------------------------------------------

    photo = extract_andele_photo(
        soup,
        url
    )

    # --------------------------------------------------------
    # СООБЩЕНИЕ
    # --------------------------------------------------------

    message = (
        "📱 Новое объявление iPhone\n\n"
        "🔵 ANDELE MANDELE\n"
        f"📱 {title}\n\n"
        f"💰 Цена: {price}\n"
        f"💾 Память: {memory}\n"
        f"🔋 Батарея: {battery}\n"
        f"📍 Город: {city}\n\n"
        f"🔗 {url}"
    )

    return {
        "message": message,
        "photo": photo
    }


def check_andele():

    print(
        "🔵 ANDELE: проверяю сайт..."
    )

    soup = get_soup(
        ANDELE_URL
    )

    if not soup:

        print(
            "🔵 ANDELE: сайт не загрузился"
        )

        return

    links = []

    # --------------------------------------------------------
    # ИЩЕМ ВСЕ КАРТОЧКИ /perle/
    # --------------------------------------------------------

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get("href")

        if not href:
            continue

        if "/perle/" not in href:
            continue

        full_link = absolute_url(
            href,
            "https://www.andelemandele.lv"
        )

        if not full_link:
            continue

        # Убираем параметры после ссылки
        full_link = full_link.split("?")[0]

        if full_link not in links:
            links.append(full_link)

    print(
        f"🔵 ANDELE: найдено карточек: {len(links)}"
    )

    # --------------------------------------------------------
    # ПРОВЕРЯЕМ КАЖДУЮ КАРТОЧКУ
    # --------------------------------------------------------

    found_iphone = 0

    for link in links:

        if link in seen_andele:
            continue

        data = parse_andele_ad(
            link
        )

        if not data:
            continue

        found_iphone += 1

        seen_andele.add(link)

        print(
            "🔵 ANDELE: НАЙДЕН IPHONE ->",
            link
        )

        photo = data["photo"]

        if photo:

            print(
                "🔵 ANDELE: фотография ->",
                photo
            )

            result = send_photo(
                photo,
                data["message"]
            )

            if (
                result is None
                or result.status_code != 200
            ):

                print(
                    "🔵 ANDELE: фото не отправилось, "
                    "отправляю текст"
                )

                send_message(
                    data["message"]
                )

        else:

            print(
                "🔵 ANDELE: фото не найдено"
            )

            send_message(
                data["message"]
            )

    print(
        f"🔵 ANDELE: iPhone найдено: "
        f"{found_iphone}"
    )


# ============================================================
# СТАРТОВОЕ СООБЩЕНИЕ
# ============================================================

print("=" * 60)
print("🤖 БОТ ЗАПУЩЕН")
print("=" * 60)

send_message(
    "🤖 Бот запущен!\n\n"
    "🟢 SS.LV — поиск iPhone\n"
    "🔵 Andele Mandele — поиск iPhone\n\n"
    "📸 Фотографии включены\n"
    "🔎 Andele проверяет каждую карточку\n"
    f"⏱ Проверка каждые {CHECK_INTERVAL} секунд."
)

# ============================================================
# ГЛАВНЫЙ ЦИКЛ
# ============================================================

while True:

    try:

        print()
        print("=" * 60)
        print("🔎 ПРОВЕРЯЮ САЙТЫ...")
        print("=" * 60)

        # SS.LV
        check_sslv()

        # ANDELE
        check_andele()

        print()
        print(
            f"⏱ Следующая проверка "
            f"через {CHECK_INTERVAL} секунд..."
        )

        time.sleep(
            CHECK_INTERVAL
        )

    except KeyboardInterrupt:

        print(
            "🛑 Бот остановлен."
        )

        break

    except Exception as error:

        print(
            "❌ ГЛОБАЛЬНАЯ ОШИБКА:",
            error
        )

        time.sleep(
            CHECK_INTERVAL
        )
