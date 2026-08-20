import re
import time
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = "8935933040:AAEfLk_llaTbsuUfse57oekzvi0vS-_E7Tg"

CHAT_ID = "5309553879"


# ============================================================
# НАСТРОЙКИ
# ============================================================

CHECK_INTERVAL = 10

SSLV_URL = (
    "https://www.ss.lv/lv/electronics/"
    "phones/mobile-phones/apple/"
)

ANDELE_URL = (
    "https://www.andelemandele.lv/"
    "perles/elektronika/telefoni/?setlang=lv"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": (
        "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
}


# ============================================================
# УЖЕ ОТПРАВЛЕННЫЕ
# ============================================================

seen_sslv = set()
seen_andele = set()


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# TELEGRAM
# ============================================================

def telegram_call(method, data=None, files=None):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

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

        print(
            f"Telegram {method}: "
            f"HTTP {response.status_code}"
        )

        return result

    except Exception as error:

        print(
            f"Telegram ошибка: {error}"
        )

        return None


def send_message(text):

    return telegram_call(
        "sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False
        }
    )


def send_photo(photo_url, caption):

    if not photo_url:
        return False

    try:

        print(
            f"📷 Загружаю фотографию: "
            f"{photo_url}"
        )

        response = session.get(
            photo_url,
            timeout=30
        )

        if response.status_code != 200:

            print(
                "❌ Фото не загрузилось: "
                f"HTTP {response.status_code}"
            )

            return False

        content_type = (
            response.headers
            .get("Content-Type", "")
            .lower()
        )

        if not content_type.startswith("image/"):

            print(
                "❌ URL не является изображением: "
                f"{content_type}"
            )

            return False

        if len(response.content) < 1000:

            print(
                "❌ Изображение подозрительно маленькое."
            )

            return False

        result = telegram_call(
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

            print(
                "✅ Фотография отправлена"
            )

            return True

        print(
            f"❌ Telegram не принял фото: "
            f"{result}"
        )

        return False

    except Exception as error:

        print(
            f"❌ Ошибка фотографии: {error}"
        )

        return False


def send_photo_or_message(photo_url, text):

    if photo_url:

        if send_photo(
            photo_url,
            text
        ):
            return

    send_message(text)


# ============================================================
# ОБЩИЕ ФУНКЦИИ
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


def absolute_url(url, base):

    if not url:
        return None

    return urljoin(
        base,
        url
    )


def normalize_url(url):

    if not url:
        return ""

    return url.split("#")[0].rstrip("/")


# ============================================================
# ЦЕНА
# ============================================================

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


# ============================================================
# ПАМЯТЬ
# ============================================================

def extract_memory(text):

    if not text:
        return "Не указана"

    patterns = [
        r"(\d+)\s*GB",
        r"(\d+)\s*Gb",
        r"(\d+)\s*gb",
        r"(\d+)\s*ГБ",
        r"(\d+)\s*Gbайт",
    ]

    valid_values = (
        16,
        32,
        64,
        128,
        256,
        512,
        1024,
        2048
    )

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for value in matches:

            try:
                number = int(value)

            except Exception:
                continue

            if number in valid_values:

                return (
                    f"{number} GB"
                )

    return "Не указана"


# ============================================================
# БАТАРЕЯ
# ============================================================

def extract_battery(text):

    if not text:
        return "Не указана"

    patterns = [
        r"(\d{2,3})\s*%\s*(?:battery|baterija)",
        r"(?:battery|baterija)[^\d]{0,40}(\d{2,3})\s*%",
        r"(?:akumulators|akumulator)[^\d]{0,40}(\d{2,3})\s*%",
        r"(?:health)[^\d]{0,40}(\d{2,3})\s*%",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = int(
                match.group(1)
            )

            if 1 <= value <= 100:

                return (
                    f"{value}%"
                )

    return "Не указана"


# ============================================================
# ГОРОД
# ============================================================

def extract_city(text):

    cities = [
        ("Rīga", ["rīga", "riga"]),
        ("Jūrmala", ["jūrmala", "jurmala"]),
        ("Liepāja", ["liepāja", "liepaja"]),
        ("Daugavpils", ["daugavpils"]),
        ("Jelgava", ["jelgava"]),
        ("Ventspils", ["ventspils"]),
        ("Valmiera", ["valmiera"]),
        ("Ogre", ["ogre"]),
        ("Salaspils", ["salaspils"]),
    ]

    low = text.lower()

    for city, variants in cities:

        for variant in variants:

            if variant in low:

                return city

    return "Не указан"


# ============================================================
# TITLE
# ============================================================

def get_title_from_soup(soup):

    # --------------------------------------------------------
    # Сначала ищем H1
    # --------------------------------------------------------

    h1 = soup.find("h1")

    if h1:

        text = clean_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

        if text:

            return text

    # --------------------------------------------------------
    # Затем OG TITLE
    # --------------------------------------------------------

    og = soup.find(
        "meta",
        property="og:title"
    )

    if og and og.get("content"):

        text = clean_text(
            og["content"]
        )

        if text:

            return text

    # --------------------------------------------------------
    # Затем title страницы
    # --------------------------------------------------------

    if soup.title:

        return clean_text(
            soup.title.get_text()
        )

    return "Не указано"


# ============================================================
# НОРМАЛИЗАЦИЯ НАЗВАНИЯ
# ============================================================

def is_bad_sslv_title(title):

    if not title:
        return True

    low = clean_text(
        title
    ).lower()

    bad_words = [
        "sludinājumi",
        "sludinajumi",
        "ss.lv",
        "ss.lv -",
        "mobilie telefoni - apple",
    ]

    # Если это просто название сайта,
    # а не модель телефона.

    if low in (
        "sludinājumi",
        "sludinajumi",
        "ss.lv",
        "не указано",
    ):

        return True

    # Если в заголовке нет iPhone
    # и он похож на служебный заголовок.

    if (
        "iphone" not in low
        and any(
            word in low
            for word in bad_words
        )
    ):

        return True

    return False


# ============================================================
# ПОИСК МОДЕЛИ В URL
# ============================================================

def extract_iphone_model_from_url(url):

    if not url:
        return None

    low = url.lower()

    # Пример:
    # /iphone-17/
    # /iphone-14-pro-max/
    # /iphone-13-mini/

    match = re.search(
        r"/(iphone-[^/?#]+)/?",
        low
    )

    if not match:
        return None

    slug = match.group(1)

    slug = slug.replace(
        "iphone-",
        "",
        1
    )

    slug = re.sub(
        r"-+",
        " ",
        slug
    )

    slug = slug.strip()

    if not slug:
        return None

    # --------------------------------------------------------
    # Известные специальные модели
    # --------------------------------------------------------

    replacements = {
        "xs": "XS",
        "xs max": "XS Max",
        "xr": "XR",
        "se": "SE",
        "se 2": "SE 2",
        "se 3": "SE 3",
        "mini": "Mini",
        "pro": "Pro",
        "pro max": "Pro Max",
        "plus": "Plus",
    }

    words = slug.split()

    result = []

    for word in words:

        if word.lower() in replacements:

            result.append(
                replacements[
                    word.lower()
                ]
            )

        elif word.isdigit():

            result.append(
                word
            )

        else:

            result.append(
                word.capitalize()
            )

    if not result:
        return None

    return (
        "iPhone "
        + " ".join(result)
    )


# ============================================================
# ПОИСК МОДЕЛИ В ТЕКСТЕ
# ============================================================

def extract_iphone_model_from_text(text):

    if not text:
        return None

    patterns = [

        r"\biPhone\s+"
        r"(17|16|15|14|13|12|11|XR|XS|X|8|7|6S|6|SE)"
        r"(?:\s+(Pro\s+Max|Pro|Plus|Mini|Max))?",

        r"\bIPhone\s+"
        r"(17|16|15|14|13|12|11|XR|XS|X|8|7|6S|6|SE)"
        r"(?:\s+(Pro\s+Max|Pro|Plus|Mini|Max))?",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        number = match.group(1)

        suffix = (
            match.group(2)
            if len(match.groups()) >= 2
            else None
        )

        if number.upper() in (
            "XR",
            "XS",
            "X",
            "SE"
        ):

            number_out = (
                number.upper()
            )

        else:

            number_out = number

        result = (
            "iPhone "
            + number_out
        )

        if suffix:

            suffix_clean = (
                suffix.strip()
            )

            if suffix_clean.lower() == "pro max":
                suffix_clean = "Pro Max"

            elif suffix_clean.lower() == "pro":
                suffix_clean = "Pro"

            elif suffix_clean.lower() == "plus":
                suffix_clean = "Plus"

            elif suffix_clean.lower() == "mini":
                suffix_clean = "Mini"

            elif suffix_clean.lower() == "max":
                suffix_clean = "Max"

            result += (
                " "
                + suffix_clean
            )

        return result

    return None


# ============================================================
# ПОИСК МОДЕЛИ В ТАБЛИЦЕ SS.LV
# ============================================================

def extract_sslv_model_from_table(soup):

    # SS.LV обычно имеет отдельное поле Modelis.
    # Ищем его максимально гибко.

    for row in soup.find_all("tr"):

        cells = row.find_all(
            ["td", "th"]
        )

        if not cells:
            continue

        texts = [
            clean_text(
                cell.get_text(
                    " ",
                    strip=True
                )
            )
            for cell in cells
        ]

        for index, cell_text in enumerate(texts):

            low = cell_text.lower()

            if low in (
                "modelis",
                "model",
            ):

                # Следующая ячейка.
                if index + 1 < len(texts):

                    value = texts[
                        index + 1
                    ]

                    if value:

                        model = (
                            extract_iphone_model_from_text(
                                value
                            )
                        )

                        if model:
                            return model

                        # Если значение само
                        # является моделью.

                        if "iphone" in value.lower():

                            return value

    return None


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ НАЗВАНИЯ SS.LV
# ============================================================

def get_sslv_phone_title(
    soup,
    html,
    link,
    all_text
):

    # --------------------------------------------------------
    # 1. Отдельное поле Modelis
    # --------------------------------------------------------

    model = extract_sslv_model_from_table(
        soup
    )

    if model:

        print(
            f"📱 SS.LV модель из Modelis: "
            f"{model}"
        )

        return model

    # --------------------------------------------------------
    # 2. URL
    # --------------------------------------------------------

    model = extract_iphone_model_from_url(
        link
    )

    if model:

        print(
            f"📱 SS.LV модель из URL: "
            f"{model}"
        )

        return model

    # --------------------------------------------------------
    # 3. H1 / OG title
    # --------------------------------------------------------

    title = get_title_from_soup(
        soup
    )

    if not is_bad_sslv_title(
        title
    ):

        model = extract_iphone_model_from_text(
            title
        )

        if model:

            print(
                f"📱 SS.LV модель из title: "
                f"{model}"
            )

            return model

    # --------------------------------------------------------
    # 4. Весь текст
    # --------------------------------------------------------

    model = extract_iphone_model_from_text(
        all_text
    )

    if model:

        print(
            f"📱 SS.LV модель из текста: "
            f"{model}"
        )

        return model

    # --------------------------------------------------------
    # 5. Последний fallback
    # --------------------------------------------------------

    if (
        title
        and not is_bad_sslv_title(
            title
        )
    ):

        return title

    return "iPhone"


# ============================================================
# ПОИСК КАРТИНКИ SS.LV
# ============================================================

def add_image_candidate(
    candidates,
    url,
    base_url
):

    if not url:
        return

    url = url.strip()

    if not url:
        return

    # Убираем кавычки.
    url = url.strip(
        "\"'"
    )

    url = absolute_url(
        url,
        base_url
    )

    if not url:
        return

    # Не принимаем data:image.
    if url.startswith(
        "data:"
    ):
        return

    if url not in candidates:

        candidates.append(
            url
        )


def get_sslv_image_candidates(
    soup,
    html,
    base_url
):

    candidates = []

    # --------------------------------------------------------
    # OG IMAGE
    # --------------------------------------------------------

    for meta in soup.find_all(
        "meta"
    ):

        prop = (
            meta.get("property")
            or meta.get("name")
            or ""
        ).lower()

        if prop in (
            "og:image",
            "og:image:url",
            "twitter:image",
            "twitter:image:src",
        ):

            add_image_candidate(
                candidates,
                meta.get("content"),
                base_url
            )

    # --------------------------------------------------------
    # LINK PRELOAD
    # --------------------------------------------------------

    for link in soup.find_all(
        "link"
    ):

        href = link.get(
            "href"
        )

        rel = " ".join(
            link.get(
                "rel",
                []
            )
        ).lower()

        as_value = (
            link.get(
                "as",
                ""
            )
            .lower()
        )

        if (
            "preload" in rel
            and as_value == "image"
        ):

            add_image_candidate(
                candidates,
                href,
                base_url
            )

    # --------------------------------------------------------
    # msg_img_dir
    # --------------------------------------------------------

    patterns = [

        r'msg_img_dir\s*=\s*"([^"]+)"',

        r"msg_img_dir\s*=\s*'([^']+)'",

        r'msg_img_dir\s*:\s*"([^"]+)"',

        r"msg_img_dir\s*:\s*'([^']+)'",

    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            html,
            re.IGNORECASE
        )

        for image_dir in matches:

            image_dir = image_dir.strip()

            image_dir = image_dir.rstrip(
                "/"
            )

            # ------------------------------------------------
            # Возможные размеры SS.LV
            # ------------------------------------------------

            for filename in (
                "800.jpg",
                "600.jpg",
                "400.jpg",
                "300.jpg",
                "big.jpg",
            ):

                if (
                    image_dir.startswith(
                        "http://"
                    )
                    or image_dir.startswith(
                        "https://"
                    )
                ):

                    candidate = (
                        image_dir
                        + "/"
                        + filename
                    )

                else:

                    # Сначала пробуем ss.lv.
                    candidate = (
                        "https://www.ss.lv"
                        + "/"
                        + image_dir.lstrip("/")
                        + "/"
                        + filename
                    )

                add_image_candidate(
                    candidates,
                    candidate,
                    base_url
                )

                # Также пробуем i.ss.lv.
                if not image_dir.startswith(
                    "http"
                ):

                    candidate_i = (
                        "https://i.ss.lv"
                        + "/"
                        + image_dir.lstrip("/")
                        + "/"
                        + filename
                    )

                    add_image_candidate(
                        candidates,
                        candidate_i,
                        base_url
                    )

    # --------------------------------------------------------
    # IMG src / data-src / srcset
    # --------------------------------------------------------

    for img in soup.find_all(
        "img"
    ):

        for attr in (
            "src",
            "data-src",
            "data-original",
            "data-lazy-src",
            "data-image",
        ):

            value = img.get(
                attr
            )

            if value:

                add_image_candidate(
                    candidates,
                    value,
                    base_url
                )

        srcset = img.get(
            "srcset"
        )

        if srcset:

            parts = srcset.split(",")

            for part in parts:

                part = part.strip()

                if not part:
                    continue

                image_url = (
                    part.split()[0]
                )

                add_image_candidate(
                    candidates,
                    image_url,
                    base_url
                )

    # --------------------------------------------------------
    # Абсолютные ссылки на картинки
    # --------------------------------------------------------

    absolute_patterns = [

        r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)(?:\?[^"\']*)?',

        r'https?://[^"\']+/images/[^"\']+',

    ]

    for pattern in absolute_patterns:

        matches = re.findall(
            pattern,
            html,
            re.IGNORECASE
        )

        for match in matches:

            add_image_candidate(
                candidates,
                match,
                base_url
            )

    return candidates


# ============================================================
# ПРОВЕРКА КАРТИНКИ
# ============================================================

def find_working_sslv_photo(
    soup,
    html,
    link
):

    candidates = get_sslv_image_candidates(
        soup,
        html,
        link
    )

    print(
        f"📷 SS.LV: кандидатов фото: "
        f"{len(candidates)}"
    )

    for candidate in candidates:

        try:

            response = session.get(
                candidate,
                timeout=15,
                stream=True
            )

            if response.status_code != 200:

                continue

            content_type = (
                response.headers
                .get(
                    "Content-Type",
                    ""
                )
                .lower()
            )

            if not content_type.startswith(
                "image/"
            ):

                continue

            content_length = (
                response.headers
                .get(
                    "Content-Length"
                )
            )

            if content_length:

                try:

                    if int(
                        content_length
                    ) < 1000:

                        continue

                except Exception:
                    pass

            print(
                f"✅ SS.LV: рабочая фотография: "
                f"{candidate}"
            )

            response.close()

            return candidate

        except Exception:

            continue

    print(
        "⚠️ SS.LV: фотография не найдена"
    )

    return None


# ============================================================
# SS.LV
# ============================================================

def process_sslv():

    print(
        "🟢 SS.LV: проверяю сайт..."
    )

    try:

        response = session.get(
            SSLV_URL,
            timeout=30
        )

        print(
            f"SS.LV HTTP: "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            return

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        for a in soup.find_all(
            "a",
            href=True
        ):

            href = a["href"]

            if "/msg/" not in href:

                continue

            link = absolute_url(
                href,
                "https://www.ss.lv"
            )

            link = normalize_url(
                link
            )

            if link not in links:

                links.append(
                    link
                )

        print(
            f"SS.LV: найдено ссылок: "
            f"{len(links)}"
        )

        for link in links:

            if link in seen_sslv:

                continue

            try:

                print(
                    f"🟢 SS.LV: открываю -> "
                    f"{link}"
                )

                ad_response = session.get(
                    link,
                    timeout=30
                )

                if (
                    ad_response.status_code
                    != 200
                ):

                    continue

                html = ad_response.text

                ad_soup = BeautifulSoup(
                    html,
                    "html.parser"
                )

                all_text = clean_text(
                    ad_soup.get_text(
                        " ",
                        strip=True
                    )
                )

                # ------------------------------------------------
                # НАЗВАНИЕ — НОВАЯ ЛОГИКА
                # ------------------------------------------------

                title = get_sslv_phone_title(
                    ad_soup,
                    html,
                    link,
                    all_text
                )

                # ------------------------------------------------
                # ДАННЫЕ
                # ------------------------------------------------

                price = extract_price(
                    all_text
                )

                memory = extract_memory(
                    all_text
                )

                battery = extract_battery(
                    all_text
                )

                city = extract_city(
                    all_text
                )

                # ------------------------------------------------
                # ФОТО — НОВАЯ ЛОГИКА
                # ------------------------------------------------

                photo = find_working_sslv_photo(
                    ad_soup,
                    html,
                    link
                )

                # ------------------------------------------------
                # TELEGRAM
                # ------------------------------------------------

                message = (
                    "🟢 Новое объявление iPhone\n\n"
                    f"📱 {title}\n"
                    f"💰 Цена: {price}\n"
                    f"💾 Память: {memory}\n"
                    f"🔋 Батарея: {battery}\n"
                    f"📍 Город: {city}\n\n"
                    f"🔗 {link}"
                )

                send_photo_or_message(
                    photo,
                    message
                )

                print(
                    message
                )

                seen_sslv.add(
                    link
                )

            except Exception as error:

                print(
                    f"SS.LV ошибка карточки: "
                    f"{error}"
                )

    except Exception as error:

        print(
            f"SS.LV ошибка: "
            f"{error}"
        )


# ============================================================
# ANDELE
# ============================================================

def is_real_iphone(
    title,
    text
):

    combined = (
        f"{title} {text}"
    ).lower()

    has_iphone = (
        "iphone" in combined
        or "apple" in combined
    )

    if not has_iphone:

        return False

    accessory_words = [
        "vāciņš",
        "vaciņš",
        "vāciņi",
        "vaciņi",
        "case",
        "cover",
        "aizsargstikls",
        "aizsargstikliņš",
        "kabelis",
        "lādētājs",
        "charger",
        "adapteris",
        "austiņas",
        "earphones",
        "airpods case",
    ]

    title_low = title.lower()

    if "iphone" in title_low:

        for word in accessory_words:

            if word in title_low:

                return False

        return True

    if (
        "zīmols: apple" in combined
        or "zīmols apple" in combined
        or "brand: apple" in combined
        or "brand apple" in combined
    ):

        for word in accessory_words:

            if word in title_low:

                return False

        return True

    return False


# ============================================================
# ANDELE LINKS
# ============================================================

def get_andele_links(
    page
):

    print(
        "🔎 ANDELE: ищу реальные карточки..."
    )

    links = set()

    page.wait_for_timeout(
        3000
    )

    for _ in range(4):

        page.mouse.wheel(
            0,
            1800
        )

        page.wait_for_timeout(
            1000
        )

    anchors = page.locator(
        'a[href*="/perle/"]'
    )

    count = anchors.count()

    print(
        f"ANDELE: найдено ссылок "
        f"на карточки: {count}"
    )

    for i in range(count):

        try:

            href = anchors.nth(
                i
            ).get_attribute(
                "href"
            )

            if not href:

                continue

            if not re.search(
                r"/perle/\d+",
                href,
                re.IGNORECASE
            ):

                continue

            full_url = normalize_url(
                absolute_url(
                    href,
                    "https://www.andelemandele.lv"
                )
            )

            if (
                "andelemandele.lv"
                not in full_url
            ):

                continue

            links.add(
                full_url
            )

        except Exception:

            continue

    return list(
        links
    )


# ============================================================
# ANDELE CARD
# ============================================================

def parse_andele_card(
    browser,
    url
):

    page = None

    try:

        page = browser.new_page()

        print(
            f"🔵 ANDELE: открываю -> "
            f"{url}"
        )

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(
            1500
        )

        title = clean_text(
            page.title()
        )

        body_text = clean_text(
            page.locator(
                "body"
            ).inner_text()
        )

        if not is_real_iphone(
            title,
            body_text
        ):

            print(
                f"🔵 ANDELE: НЕ iPhone -> "
                f"{title[:100]}"
            )

            return None

        print(
            f"📱 ANDELE: IPHONE -> "
            f"{title}"
        )

        html = page.content()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        real_title = get_title_from_soup(
            soup
        )

        if (
            not real_title
            or real_title == "Не указано"
        ):

            real_title = title

        price = extract_price(
            body_text
        )

        memory = extract_memory(
            body_text
        )

        battery = extract_battery(
            body_text
        )

        city = extract_city(
            body_text
        )

        photo = get_image_from_soup(
            soup,
            url
        )

        if not photo:

            try:

                images = page.locator(
                    "img"
                )

                image_count = images.count()

                for i in range(
                    min(
                        image_count,
                        20
                    )
                ):

                    src = (
                        images
                        .nth(i)
                        .get_attribute(
                            "src"
                        )
                    )

                    if not src:

                        continue

                    src = absolute_url(
                        src,
                        url
                    )

                    if src:

                        low = src.lower()

                        if any(
                            ext in low
                            for ext in (
                                ".jpg",
                                ".jpeg",
                                ".png",
                                ".webp"
                            )
                        ):

                            photo = src

                            break

            except Exception:

                pass

        message = (
            "🔵 Новое объявление iPhone\n\n"
            f"📱 {real_title}\n"
            f"💰 Цена: {price}\n"
            f"💾 Память: {memory}\n"
            f"🔋 Батарея: {battery}\n"
            f"📍 Город: {city}\n\n"
            f"🔗 {url}"
        )

        return {
            "url": url,
            "title": real_title,
            "price": price,
            "memory": memory,
            "battery": battery,
            "city": city,
            "photo": photo,
            "message": message
        }

    except Exception as error:

        print(
            f"❌ ANDELE ошибка карточки: "
            f"{error}"
        )

        return None

    finally:

        if page:

            try:

                page.close()

            except Exception:

                pass


# ============================================================
# ANDELE
# ============================================================

def process_andele(
    browser
):

    print(
        "🔵 ANDELE: запускаю Chromium..."
    )

    page = None

    try:

        page = browser.new_page()

        print(
            f"🔵 ANDELE: открываю "
            f"{ANDELE_URL}"
        )

        response = page.goto(
            ANDELE_URL,
            wait_until="domcontentloaded",
            timeout=30000
        )

        if response:

            print(
                f"ANDELE HTTP: "
                f"{response.status}"
            )

        page.wait_for_timeout(
            3000
        )

        links = get_andele_links(
            page
        )

        print(
            f"🔵 ANDELE: всего карточек: "
            f"{len(links)}"
        )

        iphone_count = 0

        for link in links:

            if link in seen_andele:

                continue

            ad = parse_andele_card(
                browser,
                link
            )

            if not ad:

                seen_andele.add(
                    link
                )

                continue

            iphone_count += 1

            print(
                "🎯 ANDELE: НАЙДЕН IPHONE!"
            )

            print(
                ad["message"]
            )

            send_photo_or_message(
                ad["photo"],
                ad["message"]
            )

            seen_andele.add(
                link
            )

        print(
            f"🔵 ANDELE: iPhone найдено: "
            f"{iphone_count}"
        )

    except Exception as error:

        print(
            f"❌ ANDELE главная ошибка: "
            f"{error}"
        )

    finally:

        if page:

            try:

                page.close()

            except Exception:

                pass


# ============================================================
# GET IMAGE FOR ANDELE
# ============================================================

def get_image_from_soup(
    soup,
    base_url
):

    # OG IMAGE
    meta = soup.find(
        "meta",
        property="og:image"
    )

    if meta and meta.get(
        "content"
    ):

        return absolute_url(
            meta["content"],
            base_url
        )

    # TWITTER IMAGE
    for meta in soup.find_all(
        "meta"
    ):

        name = (
            meta.get("name")
            or meta.get("property")
            or ""
        ).lower()

        if name in (
            "twitter:image",
            "twitter:image:src"
        ):

            if meta.get(
                "content"
            ):

                return absolute_url(
                    meta["content"],
                    base_url
                )

    # IMG
    for img in soup.find_all(
        "img"
    ):

        for attr in (
            "src",
            "data-src",
            "data-original",
            "data-lazy-src"
        ):

            src = img.get(
                attr
            )

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
                ext in low
                for ext in (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp"
                )
            ):

                return src

    return None


# ============================================================
# START MESSAGE
# ============================================================

def send_start_message():

    text = (
        "🤖 Бот запущен!\n\n"
        "🟢 SS.LV — поиск iPhone\n"
        "🔵 Andele Mandele — поиск iPhone\n\n"
        "📸 SS.LV — поиск фотографий включён\n"
        "📱 SS.LV — определение модели включено\n"
        "🌐 Andele работает через Chromium\n\n"
        f"⏱ Проверка каждые "
        f"{CHECK_INTERVAL} секунд."
    )

    send_message(
        text
    )


# ============================================================
# MAIN
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
        "📸 SS.LV — поиск фотографий"
    )

    print(
        "📱 SS.LV — определение модели"
    )

    print(
        "🌐 Andele: Playwright + Chromium"
    )

    print(
        f"⏱ Интервал: "
        f"{CHECK_INTERVAL} секунд"
    )

    print("=" * 70)

    send_start_message()

    # ========================================================
    # CHROMIUM
    # ========================================================

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
            ]
        )

        print(
            "🌐 Chromium запущен."
        )

        while True:

            try:

                print()
                print("=" * 70)

                print(
                    "🔎 ПРОВЕРЯЮ САЙТЫ..."
                )

                print("=" * 70)

                # =================================================
                # SS.LV
                # =================================================

                process_sslv()

                # =================================================
                # ANDELE
                # =================================================

                process_andele(
                    browser
                )

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
                    f"❌ Ошибка основного цикла: "
                    f"{error}"
                )

                time.sleep(
                    CHECK_INTERVAL
                )

        browser.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
