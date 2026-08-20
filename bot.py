import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin
from html import unescape


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = "8935933040:AAEfLk_llaTbsuUfse57oekzvi0vS-_E7Tg"
CHAT_ID = "5309553879"


# ============================================================
# НАСТРОЙКИ
# ============================================================

CHECK_INTERVAL = 10

SSLV_URL = "https://www.ss.lv/lv/electronics/phones/mobile-phones/apple/"

ANDELE_URLS = [
    "https://www.andelemandele.lv/perles/tehnika/telefoni/?setlang=lv",
    "https://www.andelemandele.lv/perles/home/tehnika/?setlang=lv",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ============================================================
# ХРАНИМ УЖЕ ОТПРАВЛЕННЫЕ ОБЪЯВЛЕНИЯ
# ============================================================

seen_sslv = set()
seen_andele = set()


# ============================================================
# SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# TELEGRAM FUNCTIONS
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

        try:
            result = response.json()
        except Exception:
            result = {
                "ok": False,
                "description": response.text
            }

        print(f"Telegram {method}: {response.status_code} -> {result}")

        return result

    except Exception as error:
        print(f"Telegram error ({method}): {error}")
        return None


def send_message(text):
    return telegram_request(
        "sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False
        }
    )


def send_photo_from_url(photo_url, caption):
    """
    Скачиваем картинку сами и отправляем файл Telegram.
    Это надёжнее, чем передавать Telegram ссылку на картинку.
    """

    if not photo_url:
        return False

    try:
        print(f"Загрузка фотографии: {photo_url}")

        response = session.get(
            photo_url,
            timeout=30
        )

        if response.status_code != 200:
            print(
                f"Фото не загрузилось: "
                f"HTTP {response.status_code}"
            )
            return False

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        if not content_type.startswith("image/"):
            print(
                f"URL не является изображением: "
                f"{content_type}"
            )
            return False

        result = telegram_request(
            "sendPhoto",
            data={
                "chat_id": CHAT_ID,
                "caption": caption
            },
            files={
                "photo": (
                    "photo.jpg",
                    response.content,
                    content_type
                )
            }
        )

        if result and result.get("ok"):
            return True

        return False

    except Exception as error:
        print(f"Ошибка отправки фотографии: {error}")
        return False


def send_photo_or_message(photo_url, message):
    """
    Если картинка работает — отправляем картинку.
    Если картинка не работает — обычное сообщение.
    """

    if photo_url:
        success = send_photo_from_url(
            photo_url,
            message
        )

        if success:
            return

    send_message(message)


# ============================================================
# ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def absolute_url(url, base_url):
    if not url:
        return None

    return urljoin(
        base_url,
        url
    )


def normalize_link(url):
    if not url:
        return ""

    url = url.split("#")[0]

    return url.rstrip("/")


def extract_price(text):
    if not text:
        return "Не указана"

    patterns = [
        r"(\d[\d\s,.]*)\s*€",
        r"€\s*(\d[\d\s,.]*)",
        r"(\d[\d\s,.]*)\s*EUR",
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
                .replace(",", ".")
                .strip()
                + " €"
            )

    return "Не указана"


def extract_memory(text):
    if not text:
        return "Не указана"

    patterns = [
        r"(\d+)\s*GB",
        r"(\d+)\s*Gb",
        r"(\d+)\s*gb",
        r"(\d+)\s*ГБ",
    ]

    values = []

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for value in matches:
            number = int(value)

            if number in [
                16,
                32,
                64,
                128,
                256,
                512,
                1024,
                2048
            ]:
                values.append(number)

    if values:
        return str(values[0]) + " GB"

    return "Не указана"


def extract_battery(text):
    if not text:
        return "Не указана"

    patterns = [
        r"Battery\s*Health[^\d]{0,20}(\d{2,3})\s*%",
        r"battery[^\d]{0,20}(\d{2,3})\s*%",
        r"baterija[^\d]{0,20}(\d{2,3})\s*%",
        r"akumulator[^\d]{0,20}(\d{2,3})\s*%",
        r"(\d{2,3})\s*%\s*(?:baterija|battery)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1) + "%"

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
        "Salaspils",
        "Ulbroka",
    ]

    for city in cities:
        if re.search(
            re.escape(city),
            text,
            re.IGNORECASE
        ):
            if city.lower() == "riga":
                return "Rīga"

            if city.lower() == "jurmala":
                return "Jūrmala"

            if city.lower() == "liepaja":
                return "Liepāja"

            return city

    return "Не указан"


def get_title(soup):
    if not soup:
        return "Не указано"

    og_title = soup.find(
        "meta",
        property="og:title"
    )

    if og_title and og_title.get("content"):
        return clean_text(
            og_title["content"]
        )

    if soup.title:
        return clean_text(
            soup.title.get_text()
        )

    h1 = soup.find("h1")

    if h1:
        return clean_text(
            h1.get_text()
        )

    return "Не указано"


def get_og_image(soup, base_url):
    if not soup:
        return None

    # Основной вариант
    image = soup.find(
        "meta",
        property="og:image"
    )

    if image and image.get("content"):
        return absolute_url(
            image["content"],
            base_url
        )

    # Другие варианты
    for meta in soup.find_all("meta"):
        prop = (
            meta.get("property")
            or meta.get("name")
            or ""
        ).lower()

        if prop in [
            "twitter:image",
            "twitter:image:src"
        ]:
            content = meta.get("content")

            if content:
                return absolute_url(
                    content,
                    base_url
                )

    return None


# ============================================================
# ============================================================
#                       SS.LV
# ============================================================
# ============================================================
#
# ЭТУ ЧАСТЬ МЫ СОХРАНЯЕМ МАКСИМАЛЬНО БЛИЗКО
# К ТВОЕЙ РАБОЧЕЙ ВЕРСИИ.
# ============================================================

def process_sslv():

    print("🟢 SS.LV: проверяю сайт...")

    try:

        response = session.get(
            SSLV_URL,
            timeout=30
        )

        print(
            f"SS.LV HTTP: {response.status_code}"
        )

        if response.status_code != 200:
            return

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

            full_link = normalize_link(
                full_link
            )

            if full_link not in links:
                links.append(
                    full_link
                )

        print(
            f"SS.LV: найдено ссылок: {len(links)}"
        )

        for full_link in links:

            if full_link in seen_sslv:
                continue

            try:

                ad_response = session.get(
                    full_link,
                    timeout=30
                )

                if ad_response.status_code != 200:
                    print(
                        f"SS.LV карточка HTTP: "
                        f"{ad_response.status_code}"
                    )
                    continue

                html = ad_response.text

                ad_soup = BeautifulSoup(
                    html,
                    "html.parser"
                )

                title = get_title(
                    ad_soup
                )

                # Цена
                price = "Не указана"

                price_match = re.search(
                    r"Cena\s*[:\-]?\s*([\d\s,.]+€)",
                    html,
                    re.IGNORECASE
                )

                if price_match:
                    price = clean_text(
                        price_match.group(1)
                    )

                if price == "Не указана":
                    price = extract_price(
                        ad_soup.get_text(" ", strip=True)
                    )

                # Память
                memory = extract_memory(
                    ad_soup.get_text(
                        " ",
                        strip=True
                    )
                )

                # Город
                city = extract_city(
                    ad_soup.get_text(
                        " ",
                        strip=True
                    )
                )

                # Батарея
                battery = extract_battery(
                    ad_soup.get_text(
                        " ",
                        strip=True
                    )
                )

                # ------------------------------------------------
                # ФОТО SS.LV
                # ------------------------------------------------

                photo = None

                image_match = re.search(
                    r'msg_img_dir\s*=\s*"([^"]+)"',
                    html
                )

                if image_match:

                    image_dir = image_match.group(1)

                    if image_dir.startswith(
                        "http://"
                    ) or image_dir.startswith(
                        "https://"
                    ):
                        photo = (
                            image_dir.rstrip("/")
                            + "/800.jpg"
                        )

                    else:
                        photo = (
                            "https://www.ss.lv"
                            + image_dir
                            + "800.jpg"
                        )

                if not photo:

                    photo = get_og_image(
                        ad_soup,
                        full_link
                    )

                message = (
                    "📱 Новое объявление iPhone\n\n"
                    f"📱 {title}\n"
                    f"💰 Цена: {price}\n"
                    f"💾 Память: {memory}\n"
                    f"🔋 Батарея: {battery}\n"
                    f"📍 Город: {city}\n\n"
                    f"🔗 {full_link}"
                )

                send_photo_or_message(
                    photo,
                    message
                )

                print(message)

                # Добавляем только ПОСЛЕ успешной обработки
                seen_sslv.add(full_link)

            except Exception as error:

                print(
                    f"SS.LV ошибка карточки: {error}"
                )

    except Exception as error:

        print(
            f"SS.LV ошибка: {error}"
        )


# ============================================================
# ============================================================
#                     ANDELE MANDELE
# ============================================================
# ============================================================

def find_andele_links(soup, base_url):

    found = []

    if not soup:
        return found

    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a.get("href")

        if not href:
            continue

        full_url = absolute_url(
            href,
            base_url
        )

        if not full_url:
            continue

        full_url = normalize_link(
            full_url
        )

        # Нам нужны именно карточки:
        #
        # /perle/12345678/...
        #
        if not re.search(
            r"/perle/\d+/",
            full_url,
            re.IGNORECASE
        ):
            continue

        if "andelemandele.lv" not in full_url:
            continue

        if full_url not in found:
            found.append(
                full_url
            )

    return found


def is_iphone_ad(text):

    text_lower = text.lower()

    # --------------------------------------------------------
    # ОБЯЗАТЕЛЬНО должно быть Apple
    # --------------------------------------------------------

    has_apple = (
        "zīmols apple" in text_lower
        or "brand apple" in text_lower
        or re.search(
            r"\bapple\b",
            text_lower
        )
    )

    # --------------------------------------------------------
    # ОБЯЗАТЕЛЬНО телефон IOS
    # --------------------------------------------------------

    has_ios_phone = (
        "mob.telefoni ios" in text_lower
        or "mob. telefoni ios" in text_lower
        or "telefoni ios" in text_lower
        or "iphone" in text_lower
    )

    # --------------------------------------------------------
    # Защита от чехлов / аксессуаров
    # --------------------------------------------------------

    bad_words = [
        "vāciņš",
        "vaciņš",
        "vāciņi",
        "vaciņi",
        "case",
        "cover",
        "aizsargstikliņš",
        "aizsargstikls",
        "lādētājs",
        "lādētāji",
        "charger",
        "kabelis",
        "kabeli",
        "stikls",
    ]

    # Если есть поле Mob.telefoni IOS,
    # доверяем ему больше, чем словам в описании.
    if (
        "mob.telefoni ios" in text_lower
        or "mob. telefoni ios" in text_lower
    ):
        return bool(has_apple)

    # Для запасного варианта нужно явно видеть iPhone
    # и Apple.
    if has_apple and has_ios_phone:

        # Если заголовок/описание явно говорит,
        # что продаётся чехол — исключаем.
        for word in bad_words:

            if (
                word in text_lower
                and "iphone" not in text_lower
            ):
                return False

        return True

    return False


def extract_andele_image(
    soup,
    html,
    base_url
):

    # --------------------------------------------------------
    # 1. og:image
    # --------------------------------------------------------

    image = get_og_image(
        soup,
        base_url
    )

    if image:
        return image

    # --------------------------------------------------------
    # 2. meta image
    # --------------------------------------------------------

    for meta in soup.find_all("meta"):

        content = meta.get("content")

        if not content:
            continue

        if not (
            "image" in content.lower()
            or content.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            )
        ):
            continue

        image = absolute_url(
            content,
            base_url
        )

        if image:
            return image

    # --------------------------------------------------------
    # 3. img src
    # --------------------------------------------------------

    for img in soup.find_all("img"):

        for attr in [
            "src",
            "data-src",
            "data-original",
            "data-lazy-src"
        ]:

            src = img.get(attr)

            if not src:
                continue

            src = absolute_url(
                src,
                base_url
            )

            if not src:
                continue

            low = src.lower()

            if any(
                extension in low
                for extension in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp"
                ]
            ):
                return src

    # --------------------------------------------------------
    # 4. Поиск URL изображения в HTML
    # --------------------------------------------------------

    image_patterns = [

        r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)',

        r'["\']([^"\']+\.(?:jpg|jpeg|png|webp))["\']',

    ]

    for pattern in image_patterns:

        matches = re.findall(
            pattern,
            html,
            re.IGNORECASE
        )

        for match in matches:

            if isinstance(
                match,
                tuple
            ):
                match = match[0]

            image = absolute_url(
                match,
                base_url
            )

            if image:
                return image

    return None


def parse_andele_ad(
    url
):

    try:

        response = session.get(
            url,
            timeout=30
        )

        print(
            f"ANDELE HTTP: "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            return None

        html = response.text

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        text = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )

        # ----------------------------------------------------
        # Проверяем, что это действительно iPhone
        # ----------------------------------------------------

        if not is_iphone_ad(text):

            print(
                f"ANDELE: не iPhone -> {url}"
            )

            return None

        title = get_title(
            soup
        )

        # Если title выглядит как общий заголовок,
        # всё равно оставляем его.
        # Основная проверка уже прошла.

        price = extract_price(
            text
        )

        memory = extract_memory(
            text
        )

        battery = extract_battery(
            text
        )

        city = extract_city(
            text
        )

        photo = extract_andele_image(
            soup,
            html,
            url
        )

        # ----------------------------------------------------
        # Описание
        # ----------------------------------------------------

        description = ""

        # Ищем наиболее подходящий текстовый блок
        candidates = []

        for tag in soup.find_all(
            [
                "p",
                "div",
                "section"
            ]
        ):

            value = clean_text(
                tag.get_text(
                    " ",
                    strip=True
                )
            )

            if not value:
                continue

            if len(value) < 50:
                continue

            if len(value) > 1500:
                continue

            candidates.append(
                value
            )

        # Берём наиболее содержательный блок
        if candidates:

            candidates.sort(
                key=len,
                reverse=True
            )

            for candidate in candidates:

                candidate_lower = (
                    candidate.lower()
                )

                if (
                    "bater" in candidate_lower
                    or "battery" in candidate_lower
                    or "gb" in candidate_lower
                    or "iphone" in candidate_lower
                ):

                    description = candidate
                    break

        message = (
            "🔵 Новое объявление iPhone\n\n"
            f"📱 {title}\n"
            f"💰 Цена: {price}\n"
            f"💾 Память: {memory}\n"
            f"🔋 Батарея: {battery}\n"
            f"📍 Город: {city}\n"
        )

        if description:

            # Ограничиваем описание,
            # чтобы Telegram не получил слишком длинное сообщение.
            if len(description) > 800:
                description = (
                    description[:800]
                    + "..."
                )

            message += (
                "\n📝 Описание:\n"
                f"{description}\n"
            )

        message += (
            "\n🔗 "
            f"{url}"
        )

        return {
            "url": url,
            "title": title,
            "price": price,
            "memory": memory,
            "battery": battery,
            "city": city,
            "photo": photo,
            "message": message,
        }

    except Exception as error:

        print(
            f"ANDELE ошибка карточки: {error}"
        )

        return None


def process_andele():

    print(
        "🔵 ANDELE: проверяю сайт..."
    )

    all_links = []

    for category_url in ANDELE_URLS:

        try:

            response = session.get(
                category_url,
                timeout=30
            )

            print(
                f"ANDELE HTTP: "
                f"{response.status_code}"
            )

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            links = find_andele_links(
                soup,
                category_url
            )

            print(
                f"ANDELE: найдено карточек "
                f"на странице: {len(links)}"
            )

            for link in links:

                if link not in all_links:
                    all_links.append(
                        link
                    )

        except Exception as error:

            print(
                f"ANDELE ошибка страницы: {error}"
            )

    print(
        f"ANDELE: всего найдено карточек: "
        f"{len(all_links)}"
    )

    iphone_count = 0

    for url in all_links:

        if url in seen_andele:
            continue

        print(
            f"ANDELE: проверяю карточку -> "
            f"{url}"
        )

        ad = parse_andele_ad(
            url
        )

        if not ad:

            # ВАЖНО:
            # неправильную карточку помечаем просмотренной,
            # чтобы не проверять одну и ту же швейную машинку
            # каждые 10 секунд.
            seen_andele.add(url)

            continue

        iphone_count += 1

        print(
            "ANDELE: НАЙДЕН IPHONE!"
        )

        print(
            ad["message"]
        )

        send_photo_or_message(
            ad["photo"],
            ad["message"]
        )

        seen_andele.add(url)

    print(
        f"ANDELE: iPhone найдено: "
        f"{iphone_count}"
    )


# ============================================================
# СТАРТОВОЕ СООБЩЕНИЕ
# ============================================================

def send_start_message():

    message = (
        "🤖 Бот запущен!\n\n"
        "🟢 SS.LV — поиск iPhone\n"
        "🔵 Andele Mandele — поиск iPhone\n\n"
        f"⏱ Проверка каждые "
        f"{CHECK_INTERVAL} секунд."
    )

    send_message(
        message
    )


# ============================================================
# ОСНОВНОЙ ЦИКЛ
# ============================================================

def main():

    print("=" * 70)

    print(
        "🤖 IPHONE BOT ЗАПУЩЕН"
    )

    print(
        "🟢 SS.LV — поиск iPhone"
    )

    print(
        "🔵 Andele Mandele — поиск iPhone"
    )

    print(
        f"⏱ Интервал: "
        f"{CHECK_INTERVAL} секунд"
    )

    print("=" * 70)

    send_start_message()

    while True:

        try:

            print()
            print("=" * 70)

            print(
                "🔎 ПРОВЕРЯЮ САЙТЫ..."
            )

            print("=" * 70)

            # ------------------------------------------------
            # SS.LV
            # ------------------------------------------------

            process_sslv()

            # ------------------------------------------------
            # ANDELE MANDELE
            # ------------------------------------------------

            process_andele()

            print(
                f"⏱ Следующая проверка "
                f"через {CHECK_INTERVAL} секунд..."
            )

            time.sleep(
                CHECK_INTERVAL
            )

        except KeyboardInterrupt:

            print(
                "Бот остановлен."
            )

            break

        except Exception as error:

            print(
                f"❌ Главная ошибка: "
                f"{error}"
            )

            time.sleep(
                CHECK_INTERVAL
            )


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    main()
