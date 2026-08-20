import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
from io import BytesIO


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = "8935933040:AAEfLk_llaTbsuUfse57oekzvi0vS-_E7Tg"
CHAT_ID = "5309553879"

CHECK_INTERVAL = 10

SSLV_URL = "https://www.ss.lv/lv/electronics/phones/mobile-phones/apple/"
ANDELE_URL = "https://www.andelemandele.lv/perles/tehnika/telefoni/?setlang=lv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7"
}


# ============================================================
# ПАМЯТЬ БОТА
# ============================================================

seen_sslv = set()
seen_andele = set()

first_scan_sslv = True
first_scan_andele = True


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

        print(f"Telegram {method}: {response.status_code}")

        if response.status_code != 200:
            print(response.text)

        return response

    except Exception as error:
        print("Ошибка Telegram:", error)
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
                "photo.jpg",
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

        if response is None or response.status_code != 200:
            print("Не удалось отправить фотографию.")

            # Если фотография не отправилась —
            # хотя бы отправляем текст.
            send_message(caption)

    except Exception as error:

        print("Ошибка отправки фотографии:", error)
        send_message(caption)


# ============================================================
# СКАЧИВАНИЕ ФОТОГРАФИИ
# ============================================================

def download_image(image_url):

    if not image_url:
        return None

    try:

        print("📸 Скачиваю:", image_url)

        response = requests.get(
            image_url,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code != 200:
            print(
                "Фото не скачалось:",
                response.status_code
            )
            return None

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        if "image" not in content_type:

            # Иногда сервер неправильно указывает Content-Type.
            # Поэтому проверяем и размер.
            if len(response.content) < 1000:
                print("Ответ не похож на изображение.")
                return None

        return response.content

    except Exception as error:

        print("Ошибка загрузки изображения:", error)
        return None


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def absolute_url(url, base):

    if not url:
        return None

    return urljoin(base, url)


def extract_price(text):

    if not text:
        return "Не указана"

    patterns = [

        r"(\d[\d\s.,]*)\s*€",

        r"€\s*(\d[\d\s.,]*)",

        r"Цена[:\s]*([0-9\s.,]+)",

        r"Cena[:\s]*([0-9\s.,]+)\s*€"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
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
            re.I
        )

        if match:

            return match.group(1) + " GB"

    return "Не указана"


def extract_battery(text):

    if not text:
        return "Не указана"

    patterns = [

        r"(\d{2,3})\s*%",

        r"battery\s*(?:health)?\s*[:\-]?\s*(\d{2,3})",

        r"baterij[as]*\s*(?:veselība)?\s*[:\-]?\s*(\d{2,3})",

        r"akumulators\s*[:\-]?\s*(\d{2,3})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
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
            re.I
        ):

            if city.lower() == "riga":
                return "Rīga"

            return city

    return "Не указан"


# ============================================================
# ПОИСК ФОТО В HTML
# ============================================================

def find_image(soup, html, base_url):

    # --------------------------------------------------------
    # 1. OpenGraph image
    # --------------------------------------------------------

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:

        url = og_image.get("content")

        if url:

            return absolute_url(
                url,
                base_url
            )


    # --------------------------------------------------------
    # 2. Twitter image
    # --------------------------------------------------------

    twitter_image = soup.find(
        "meta",
        attrs={
            "name": "twitter:image"
        }
    )

    if twitter_image:

        url = twitter_image.get("content")

        if url:

            return absolute_url(
                url,
                base_url
            )


    # --------------------------------------------------------
    # 3. img src
    # --------------------------------------------------------

    for img in soup.find_all("img"):

        for attribute in [
            "src",
            "data-src",
            "data-original",
            "data-lazy-src"
        ]:

            url = img.get(attribute)

            if not url:
                continue

            url = absolute_url(
                url,
                base_url
            )

            if not url:
                continue

            # Не берём маленькие UI-иконки.
            lower = url.lower()

            if any(
                word in lower
                for word in [
                    "logo",
                    "icon",
                    "avatar",
                    "sprite"
                ]
            ):

                continue

            return url


    # --------------------------------------------------------
    # 4. Поиск URL изображения в HTML
    # --------------------------------------------------------

    image_patterns = [

        r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)',

        r'//[^"\']+\.(?:jpg|jpeg|png|webp)'
    ]

    for pattern in image_patterns:

        match = re.search(
            pattern,
            html,
            re.I
        )

        if match:

            url = match.group(0)

            if url.startswith("//"):
                url = "https:" + url

            return url


    return None


# ============================================================
# SS.LV — ПОЛУЧЕНИЕ ОБЪЯВЛЕНИЙ
# ============================================================

def get_sslv_list():

    print("🔎 SS.LV: проверяю сайт...")

    try:

        response = requests.get(
            SSLV_URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            "SS.LV HTTP:",
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

            href = link["href"]

            if "/msg/" not in href:
                continue

            full_link = absolute_url(
                href,
                "https://www.ss.lv"
            )

            if full_link:

                if full_link not in links:

                    links.append(full_link)


        print(
            "SS.LV: найдено:",
            len(links)
        )

        return links


    except Exception as error:

        print(
            "SS.LV ошибка:",
            error
        )

        return []


# ============================================================
# SS.LV — ПОЛУЧЕНИЕ ДАННЫХ ОБЪЯВЛЕНИЯ
# ============================================================

def parse_sslv_ad(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:

            print(
                "SS.LV объявление HTTP:",
                response.status_code
            )

            return None


        html = response.text

        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = "Не указано"

        if soup.title:

            title = clean_text(
                soup.title.get_text(
                    " ",
                    strip=True
                )
            )


        # ----------------------------------------------------
        # Весь текст страницы
        # ----------------------------------------------------

        page_text = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )


        # ----------------------------------------------------
        # PRICE
        # ----------------------------------------------------

        price = extract_price(
            page_text
        )


        # ----------------------------------------------------
        # MEMORY
        # ----------------------------------------------------

        memory = extract_memory(
            page_text
        )


        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        battery = extract_battery(
            page_text
        )


        # ----------------------------------------------------
        # CITY
        # ----------------------------------------------------

        city = extract_city(
            page_text
        )


        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

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
            "Ошибка SS.LV объявления:",
            error
        )

        return None


# ============================================================
# SS.LV — ФОРМИРОВАНИЕ СООБЩЕНИЯ
# ============================================================

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


# ============================================================
# ANDELE — ПОЛУЧЕНИЕ СПИСКА
# ============================================================

def get_andele_list():

    print("🔎 ANDELE: проверяю сайт...")

    try:

        response = requests.get(
            ANDELE_URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            "ANDELE HTTP:",
            response.status_code
        )

        if response.status_code != 200:

            return []


        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        links = []


        # ----------------------------------------------------
        # Ищем реальные ссылки /perle/XXXXXXXX/
        # ----------------------------------------------------

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link["href"]

            if not re.search(
                r"/perle/\d+",
                href
            ):
                continue


            full_link = absolute_url(
                href,
                "https://www.andelemandele.lv"
            )


            if not full_link:
                continue


            # Убираем query-параметры,
            # чтобы ссылка была стабильной.

            full_link = full_link.split("?")[0]


            if full_link not in links:

                links.append(full_link)


        print(
            "ANDELE: найдено ссылок:",
            len(links)
        )


        return links


    except Exception as error:

        print(
            "ANDELE ошибка:",
            error
        )

        return []


# ============================================================
# ANDELE — ПОЛУЧЕНИЕ ДАННЫХ КАРТОЧКИ
# ============================================================

def parse_andele_ad(url):

    try:

        print(
            "ANDELE: проверяю ->",
            url
        )


        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )


        print(
            "ANDELE HTTP:",
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
        # ПРОВЕРЯЕМ БРЕНД
        # ----------------------------------------------------

        is_apple = bool(
            re.search(
                r"\bApple\b",
                page_text,
                re.I
            )
        )


        # ----------------------------------------------------
        # ПРОВЕРЯЕМ ТИП
        #
        # Andele использует:
        # Mob.telefoni IOS
        # ----------------------------------------------------

        is_ios_phone = bool(
            re.search(
                r"Mob\.?\s*telefoni\s*IOS",
                page_text,
                re.I
            )
        )


        # ----------------------------------------------------
        # ДОПОЛНИТЕЛЬНО ПРОВЕРЯЕМ iPhone
        #
        # Это помогает, если структура страницы
        # немного изменится.
        # ----------------------------------------------------

        title_text = ""

        if soup.title:

            title_text = clean_text(
                soup.title.get_text(
                    " ",
                    strip=True
                )
            )


        iphone_in_text = bool(
            re.search(
                r"\bi[\s-]?phone\b",
                page_text,
                re.I
            )
        )


        iphone_in_title = bool(
            re.search(
                r"\bi[\s-]?phone\b",
                title_text,
                re.I
            )
        )


        # ----------------------------------------------------
        # ГЛАВНОЕ УСЛОВИЕ
        #
        # Apple + Mob.telefoni IOS
        #
        # ИЛИ
        #
        # Apple + iPhone
        # ----------------------------------------------------

        is_iphone = (

            (
                is_apple
                and
                is_ios_phone
            )

            or

            (
                is_apple
                and
                (
                    iphone_in_text
                    or
                    iphone_in_title
                )
            )
        )


        if not is_iphone:

            print(
                "ANDELE: не iPhone ->",
                url
            )

            return None


        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = title_text

        if not title:

            title = "iPhone"


        # ----------------------------------------------------
        # PRICE
        # ----------------------------------------------------

        price = extract_price(
            page_text
        )


        # ----------------------------------------------------
        # MEMORY
        # ----------------------------------------------------

        memory = extract_memory(
            page_text
        )


        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        battery = extract_battery(
            page_text
        )


        # ----------------------------------------------------
        # CITY
        # ----------------------------------------------------

        city = extract_city(
            page_text
        )


        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        image_url = find_image(
            soup,
            html,
            "https://www.andelemandele.lv"
        )


        print(
            "ANDELE: найден iPhone:",
            title
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
            "ANDELE ошибка объявления:",
            error
        )

        return None


# ============================================================
# ANDELE — СООБЩЕНИЕ
# ============================================================

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


# ============================================================
# ОБРАБОТКА SS.LV
# ============================================================

def check_sslv():

    global first_scan_sslv

    links = get_sslv_list()


    for link in links:

        # ----------------------------------------------------
        # Уже видели
        # ----------------------------------------------------

        if link in seen_sslv:

            continue


        # Добавляем сразу,
        # чтобы при ошибке не получить дубль
        # на следующем цикле.

        seen_sslv.add(link)


        ad = parse_sslv_ad(
            link
        )


        if not ad:

            continue


        message = build_sslv_message(
            ad
        )


        # ----------------------------------------------------
        # ПЕРВЫЙ ЗАПУСК
        #
        # Не отправляем старые объявления.
        # ----------------------------------------------------

        if first_scan_sslv:

            print(
                "SS.LV старое объявление:",
                link
            )

            continue


        print(
            "📱 SS.LV НОВОЕ ОБЪЯВЛЕНИЕ"
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
# ОБРАБОТКА ANDELE
# ============================================================

def check_andele():

    global first_scan_andele

    links = get_andele_list()


    for link in links:

        if link in seen_andele:

            continue


        seen_andele.add(link)


        ad = parse_andele_ad(
            link
        )


        # Если это не iPhone,
        # больше его не проверяем.

        if not ad:

            continue


        message = build_andele_message(
            ad
        )


        # ----------------------------------------------------
        # ПЕРВЫЙ ЗАПУСК
        # ----------------------------------------------------

        if first_scan_andele:

            print(
                "ANDELE старое объявление:",
                link
            )

            continue


        print(
            "📱 ANDELE НОВОЕ ОБЪЯВЛЕНИЕ"
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
# СТАРТОВОЕ СООБЩЕНИЕ
# ============================================================

send_message(
    "🤖 Бот запущен!\n\n"

    "🟢 SS.LV — поиск iPhone\n"
    "🔵 Andele Mandele — поиск iPhone\n\n"

    "📸 Фотографии загружаются напрямую\n"
    "💾 Старые объявления не отправляются\n"
    f"⏱ Проверка каждые {CHECK_INTERVAL} секунд."
)


# ============================================================
# ПЕРВАЯ СИНХРОНИЗАЦИЯ
# ============================================================

print()
print("=" * 60)
print("🚀 ПЕРВАЯ СИНХРОНИЗАЦИЯ")
print("=" * 60)
print()

print("Собираю существующие объявления...")
print("Старые объявления отправляться не будут.")
print()


# Первый проход

check_sslv()
check_andele()


# После первого прохода
# начинаем отправлять только новые.

first_scan_sslv = False
first_scan_andele = False


print()
print("=" * 60)
print("✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА")
print("Теперь бот ищет только НОВЫЕ объявления.")
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
                "Ошибка SS.LV:",
                error
            )


        # ----------------------------------------------------
        # ANDELE
        # ----------------------------------------------------

        try:

            check_andele()

        except Exception as error:

            print(
                "Ошибка ANDELE:",
                error
            )


        # ----------------------------------------------------
        # ОЖИДАНИЕ
        # ----------------------------------------------------

        print()
        print(
            f"⏱ Следующая проверка через "
            f"{CHECK_INTERVAL} секунд..."
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
