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

ANDELE_URL = (
    "https://www.andelemandele.lv/"
    "perles/tehnika/telefoni/?setlang=lv"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,"
              "application/xml;q=0.9,image/avif,image/webp,"
              "image/apng,*/*;q=0.8"
}


# ============================================================
# ПАМЯТЬ
# ============================================================

seen_sslv = set()
seen_andele = set()

first_scan_sslv = True
first_scan_andele = True

# Для первого запуска отправляем один существующий
# iPhone с Andele для проверки.
ANDELE_TEST_MODE = True


# ============================================================
# TELEGRAM
# ============================================================

def telegram_request(method, data=None, files=None):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    try:

        response = requests.post(
            url,
            data=data,
            files=files,
            timeout=30
        )

        print(
            f"Telegram {method}: "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            print(response.text)

        return response

    except Exception as error:

        print(
            "Ошибка Telegram:",
            error
        )

        return None


def send_message(text):

    telegram_request(
        "sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False
        }
    )


def send_photo(image_bytes, caption):

    if not image_bytes:

        send_message(caption)

        return


    try:

        files = {
            "photo": (
                "iphone.jpg",
                image_bytes,
                "image/jpeg"
            )
        }

        data = {
            "chat_id": CHAT_ID,
            "caption": caption
        }

        response = telegram_request(
            "sendPhoto",
            data=data,
            files=files
        )

        if (
            response is None
            or response.status_code != 200
        ):

            print(
                "⚠️ Telegram не принял фотографию."
            )

            send_message(caption)

    except Exception as error:

        print(
            "Ошибка отправки фото:",
            error
        )

        send_message(caption)


# ============================================================
# СКАЧИВАНИЕ ФОТО
# ============================================================

def download_image(image_url):

    if not image_url:
        return None

    try:

        print(
            "📸 Загружаю фотографию:",
            image_url
        )

        response = requests.get(
            image_url,
            headers=HEADERS,
            timeout=30
        )

        print(
            "📸 Фото HTTP:",
            response.status_code
        )

        if response.status_code != 200:
            return None

        content = response.content

        if len(content) < 1000:
            return None

        return content

    except Exception as error:

        print(
            "Ошибка загрузки фото:",
            error
        )

        return None


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_price(text):

    if not text:
        return "Не указана"

    patterns = [

        r"(\d[\d\s.,]*)\s*€",

        r"€\s*(\d[\d\s.,]*)",

        r"Cena[:\s]*([0-9\s.,]+)\s*€",

        r"Цена[:\s]*([0-9\s.,]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            return value + " €"

    return "Не указана"


def extract_memory(text):

    if not text:
        return "Не указана"

    patterns = [

        r"\b(\d{2,4})\s*GB\b",

        r"\b(\d{2,4})\s*Gb\b",

        r"\b(\d{2,4})\s*gb\b",

        r"\b(\d{2,4})\s*ГБ\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return (
                match.group(1)
                + " GB"
            )

    return "Не указана"


def extract_battery(text):

    if not text:
        return "Не указана"

    patterns = [

        r"(\d{2,3})\s*%",

        r"battery.{0,30}?(\d{2,3})",

        r"baterij.{0,30}?(\d{2,3})",

        r"akumulator.{0,30}?(\d{2,3})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                value = int(
                    match.group(1)
                )

                if 1 <= value <= 100:

                    return (
                        str(value)
                        + "%"
                    )

            except:
                pass

    return "Не указана"


def extract_city(text):

    if not text:
        return "Не указан"

    cities = [

        "Rīga",
        "Riga",
        "Jūrmala",
        "Jurmala",
        "Liepāja",
        "Liepaja",
        "Daugavpils",
        "Jelgava",
        "Ventspils",
        "Valmiera",
        "Ogre",
        "Rēzekne",
        "Rezekne"
    ]

    for city in cities:

        if re.search(
            re.escape(city),
            text,
            re.IGNORECASE
        ):

            if city.lower() == "riga":

                return "Rīga"

            return city

    return "Не указан"


# ============================================================
# ПОИСК ФОТО
# ============================================================

def find_image(
    soup,
    html,
    base_url
):

    # --------------------------------------------------------
    # OpenGraph
    # --------------------------------------------------------

    og = soup.find(
        "meta",
        property="og:image"
    )

    if og:

        url = og.get("content")

        if url:

            return urljoin(
                base_url,
                url
            )


    # --------------------------------------------------------
    # Twitter image
    # --------------------------------------------------------

    twitter = soup.find(
        "meta",
        attrs={
            "name": "twitter:image"
        }
    )

    if twitter:

        url = twitter.get("content")

        if url:

            return urljoin(
                base_url,
                url
            )


    # --------------------------------------------------------
    # IMG
    # --------------------------------------------------------

    for img in soup.find_all("img"):

        for attribute in [
            "src",
            "data-src",
            "data-original",
            "data-lazy-src"
        ]:

            url = img.get(
                attribute
            )

            if not url:
                continue

            url = urljoin(
                base_url,
                url
            )

            lower = url.lower()

            if any(
                x in lower
                for x in [
                    "logo",
                    "icon",
                    "sprite",
                    "avatar"
                ]
            ):

                continue

            return url


    # --------------------------------------------------------
    # URL изображения в HTML
    # --------------------------------------------------------

    patterns = [

        r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)',

        r'//[^"\']+\.(?:jpg|jpeg|png|webp)'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:

            url = match.group(0)

            if url.startswith("//"):

                url = "https:" + url

            return url

    return None


# ============================================================
# SS.LV
# ============================================================

def get_sslv_list():

    print(
        "🟢 SS.LV: проверяю сайт..."
    )

    try:

        response = requests.get(
            SSLV_URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            "🟢 SS.LV HTTP:",
            response.status_code
        )

        if response.status_code != 200:

            return []


        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            )

            if "/msg/" not in href:

                continue

            full_link = urljoin(
                "https://www.ss.lv",
                href
            )

            if full_link not in links:

                links.append(
                    full_link
                )


        print(
            "🟢 SS.LV: найдено:",
            len(links)
        )

        return links


    except Exception as error:

        print(
            "❌ SS.LV ошибка:",
            error
        )

        return []


def parse_sslv_ad(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:

            return None


        html = response.text

        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        title = "Не указано"

        if soup.title:

            title = clean_text(
                soup.title.get_text(
                    " ",
                    strip=True
                )
            )


        page_text = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )


        price = extract_price(
            page_text
        )

        memory = extract_memory(
            page_text
        )

        battery = extract_battery(
            page_text
        )

        city = extract_city(
            page_text
        )

        image_url = find_image(
            soup,
            html,
            "https://www.ss.lv"
        )


        return {

            "title": title,

            "price": price,

            "memory": memory,

            "battery": battery,

            "city": city,

            "url": url,

            "image": image_url
        }


    except Exception as error:

        print(
            "SS.LV карточка ошибка:",
            error
        )

        return None


def build_sslv_message(ad):

    return (
        "📱 Новое объявление iPhone\n\n"

        f"🟢 SS.LV\n"
        f"{ad['title']}\n\n"

        f"💰 Цена: {ad['price']}\n"
        f"💾 Память: {ad['memory']}\n"
        f"🔋 Батарея: {ad['battery']}\n"
        f"📍 Город: {ad['city']}\n\n"

        f"🔗 {ad['url']}"
    )


def check_sslv():

    global first_scan_sslv

    links = get_sslv_list()

    for link in links:

        if link in seen_sslv:

            continue

        seen_sslv.add(link)

        ad = parse_sslv_ad(
            link
        )

        if not ad:

            continue


        # Старые объявления
        # при первой синхронизации не отправляем.

        if first_scan_sslv:

            continue


        message = build_sslv_message(
            ad
        )

        image = download_image(
            ad["image"]
        )

        if image:

            send_photo(
                image,
                message
            )

        else:

            send_message(
                message
            )


# ============================================================
# ANDELE MANDELE
# ============================================================

def get_andele_list():

    print(
        "🔵 ANDELE: проверяю сайт..."
    )

    try:

        response = requests.get(
            ANDELE_URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            "🔵 ANDELE HTTP:",
            response.status_code
        )

        if response.status_code != 200:

            return []


        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []


        # Ищем реальные карточки /perle/ID/
        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            ).strip()

            if not href:

                continue


            match = re.search(
                r"/perle/(\d+)",
                href
            )

            if not match:

                continue


            full_link = urljoin(
                "https://www.andelemandele.lv",
                href
            )

            full_link = full_link.split(
                "?"
            )[0]


            if full_link not in links:

                links.append(
                    full_link
                )


        print(
            "🔵 ANDELE: найдено ссылок:",
            len(links)
        )


        for link in links:

            print(
                "🔵 ANDELE LINK:",
                link
            )


        return links


    except Exception as error:

        print(
            "❌ ANDELE ошибка:",
            error
        )

        return []


def parse_andele_ad(url):

    try:

        print()
        print(
            "🔵 ANDELE: открываю:"
        )

        print(url)


        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        print(
            "🔵 ANDELE карточка HTTP:",
            response.status_code
        )


        if response.status_code != 200:

            return None


        html = response.text

        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        page_text = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )


        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = ""

        h1 = soup.find("h1")

        if h1:

            title = clean_text(
                h1.get_text(
                    " ",
                    strip=True
                )
            )


        if not title and soup.title:

            title = clean_text(
                soup.title.get_text(
                    " ",
                    strip=True
                )
            )


        print(
            "🔵 ANDELE TITLE:",
            title
        )


        # ----------------------------------------------------
        # ПРИЗНАКИ iPHONE
        # ----------------------------------------------------

        title_is_iphone = bool(
            re.search(
                r"\bi[\s\-]?phone\b",
                title,
                re.IGNORECASE
            )
        )


        page_is_iphone = bool(
            re.search(
                r"\bi[\s\-]?phone\b",
                page_text,
                re.IGNORECASE
            )
        )


        is_apple = bool(
            re.search(
                r"\bApple\b",
                page_text,
                re.IGNORECASE
            )
        )


        is_ios = bool(
            re.search(
                r"Mob\.?\s*telefoni\s*IOS",
                page_text,
                re.IGNORECASE
            )
        )


        print(
            "🔵 iPhone в названии:",
            title_is_iphone
        )

        print(
            "🔵 iPhone на странице:",
            page_is_iphone
        )

        print(
            "🔵 Apple:",
            is_apple
        )

        print(
            "🔵 Mob.telefoni IOS:",
            is_ios
        )


        # ----------------------------------------------------
        # РЕШЕНИЕ
        # ----------------------------------------------------

        is_iphone = (

            title_is_iphone

            or

            (
                is_apple
                and
                is_ios
            )

            or

            (
                is_apple
                and
                page_is_iphone
            )
        )


        if not is_iphone:

            print(
                "🔵 ANDELE: ❌ не iPhone"
            )

            return None


        print(
            "🔵 ANDELE: ✅ НАЙДЕН IPHONE!"
        )


        # ----------------------------------------------------
        # ДАННЫЕ
        # ----------------------------------------------------

        price = extract_price(
            page_text
        )

        memory = extract_memory(
            page_text
        )

        battery = extract_battery(
            page_text
        )

        city = extract_city(
            page_text
        )


        # ----------------------------------------------------
        # ФОТО
        # ----------------------------------------------------

        image_url = find_image(
            soup,
            html,
            "https://www.andelemandele.lv"
        )


        print(
            "🔵 ANDELE PHOTO:",
            image_url
        )


        return {

            "title": title or "iPhone",

            "price": price,

            "memory": memory,

            "battery": battery,

            "city": city,

            "url": url,

            "image": image_url
        }


    except Exception as error:

        print(
            "❌ ANDELE карточка ошибка:",
            error
        )

        return None


def build_andele_message(ad):

    return (
        "📱 Новое объявление iPhone\n\n"

        f"🔵 Andele Mandele\n"
        f"{ad['title']}\n\n"

        f"💰 Цена: {ad['price']}\n"
        f"💾 Память: {ad['memory']}\n"
        f"🔋 Батарея: {ad['battery']}\n"
        f"📍 Город: {ad['city']}\n\n"

        f"🔗 {ad['url']}"
    )


def check_andele():

    global first_scan_andele
    global ANDELE_TEST_MODE

    links = get_andele_list()

    print(
        "🔵 ANDELE: проверяю карточки..."
    )


    found_iphones = 0


    for link in links:

        if link in seen_andele:

            continue


        seen_andele.add(link)


        ad = parse_andele_ad(
            link
        )


        if not ad:

            continue


        found_iphones += 1


        message = build_andele_message(
            ad
        )


        # ----------------------------------------------------
        # ТЕСТ ПЕРВОГО IPHONE
        # ----------------------------------------------------

        if ANDELE_TEST_MODE:

            print(
                "🧪 ANDELE TEST:"
                " отправляю найденный iPhone"
            )


            image = download_image(
                ad["image"]
            )


            if image:

                send_photo(
                    image,
                    message
                )

            else:

                send_message(
                    message
                )


            # Тест завершён.
            ANDELE_TEST_MODE = False


            print(
                "✅ ANDELE TEST ЗАВЕРШЁН"
            )

            print(
                "Теперь будут приходить "
                "только новые объявления."
            )

            break


        # ----------------------------------------------------
        # ОБЫЧНЫЙ РЕЖИМ
        # ----------------------------------------------------

        if first_scan_andele:

            continue


        image = download_image(
            ad["image"]
        )


        if image:

            send_photo(
                image,
                message
            )

        else:

            send_message(
                message
            )


    print(
        "🔵 ANDELE: iPhone найдено:",
        found_iphones
    )


# ============================================================
# ПРОВЕРКА ТОКЕНА
# ============================================================

if (
    BOT_TOKEN.startswith("ВСТАВЬ")
    or
    CHAT_ID.startswith("ВСТАВЬ")
):

    print()
    print(
        "❌ ОШИБКА:"
    )

    print(
        "Сначала вставь BOT_TOKEN и CHAT_ID "
        "в верхнюю часть файла."
    )

    raise SystemExit


# ============================================================
# СТАРТОВОЕ СООБЩЕНИЕ
# ============================================================

send_message(
    "🤖 Бот запущен!\n\n"

    "🟢 SS.LV — поиск iPhone\n"
    "🔵 Andele Mandele — поиск iPhone\n\n"

    "📸 Фотографии загружаются напрямую\n"
    "⏱ Проверка каждые 10 секунд\n\n"

    "🧪 Сейчас выполняется тест Andele."
)


# ============================================================
# ПЕРВАЯ СИНХРОНИЗАЦИЯ
# ============================================================

print()
print("=" * 60)
print("🚀 БОТ ЗАПУЩЕН")
print("=" * 60)
print()

print(
    "🟢 SS.LV — поиск iPhone"
)

print(
    "🔵 Andele Mandele — поиск iPhone"
)

print(
    "⏱ Интервал:",
    CHECK_INTERVAL,
    "секунд"
)

print()
print(
    "🧪 Andele: тестовый режим включён."
)

print()


# ============================================================
# ПЕРВЫЙ ПРОХОД
# ============================================================

check_sslv()

check_andele()


# Старые объявления SS.LV
# теперь считаются просмотренными.

first_scan_sslv = False

first_scan_andele = False


print()
print("=" * 60)
print(
    "✅ ПЕРВАЯ ПРОВЕРКА ЗАКОНЧЕНА"
)
print("=" * 60)
print()


# ============================================================
# ОСНОВНОЙ ЦИКЛ
# ============================================================

while True:

    try:

        print()
        print("=" * 60)
        print("🔎 ПРОВЕРЯЮ САЙТЫ...")
        print("=" * 60)


        # ----------------------------------------------------
        # SS.LV
        # ----------------------------------------------------

        try:

            check_sslv()

        except Exception as error:

            print(
                "❌ Ошибка SS.LV:",
                error
            )


        # ----------------------------------------------------
        # ANDELE
        # ----------------------------------------------------

        try:

            check_andele()

        except Exception as error:

            print(
                "❌ Ошибка ANDELE:",
                error
            )


        # ----------------------------------------------------
        # ОЖИДАНИЕ
        # ----------------------------------------------------

        print()

        print(
            "⏱ Следующая проверка через",
            CHECK_INTERVAL,
            "секунд..."
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
            "❌ Общая ошибка:",
            error
        )

        time.sleep(
            CHECK_INTERVAL
        )
