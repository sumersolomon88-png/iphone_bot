import re
import time
import os
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

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

# Facebook
FACEBOOK_ENABLED = True

FACEBOOK_SEARCH_URL = (
    "https://www.facebook.com/marketplace/search/"
    "?query=iphone"
)

# Файл сохранённой Facebook-сессии.
# Пароль сюда НЕ записываем.
FACEBOOK_SESSION_FILE = "facebook_session.json"


# ============================================================
# SS.LV
# ============================================================

SSLV_URL = (
    "https://www.ss.lv/lv/electronics/"
    "phones/mobile-phones/apple/"
)


# ============================================================
# ANDELE
# ============================================================

ANDELE_URL = (
    "https://www.andelemandele.lv/"
    "perles/elektronika/telefoni/?setlang=lv"
)


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),

    "Accept-Language": (
        "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7"
    ),

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "*/*;q=0.8"
    ),
}


# ============================================================
# УЖЕ ОТПРАВЛЕННЫЕ
# ============================================================

seen_sslv = set()

seen_andele = set()

seen_facebook = set()


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ============================================================
# TELEGRAM API
# ============================================================

def telegram_call(
    method,
    data=None,
    files=None
):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

    try:

        response = requests.post(
            url,
            data=data,
            files=files,
            timeout=40
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


# ============================================================
# ФОТО
# ============================================================

def is_probably_image(
    response
):

    if not response:
        return False

    if response.status_code != 200:
        return False

    content_type = (
        response.headers
        .get("Content-Type", "")
        .lower()
    )

    if not content_type.startswith(
        "image/"
    ):
        return False

    if len(
        response.content
    ) < 8000:
        return False

    return True


def download_image(
    photo_url
):

    if not photo_url:
        return None

    try:

        response = session.get(
            photo_url,
            timeout=30,
            allow_redirects=True
        )

        if not is_probably_image(
            response
        ):
            return None

        return {
            "content": response.content,
            "content_type": (
                response.headers
                .get(
                    "Content-Type",
                    "image/jpeg"
                )
            )
        }

    except Exception as error:

        print(
            f"Фото не загрузилось: "
            f"{error}"
        )

        return None


def send_photo(
    photo_url,
    caption
):

    if not photo_url:
        return False

    print(
        f"📷 Загружаю фото: "
        f"{photo_url}"
    )

    image = download_image(
        photo_url
    )

    if not image:

        print(
            "❌ Фото не удалось загрузить."
        )

        return False

    try:

        result = telegram_call(
            "sendPhoto",
            data={
                "chat_id": CHAT_ID,
                "caption": caption
            },

            files={
                "photo": (
                    "photo.jpg",
                    image["content"],
                    image["content_type"]
                )
            }
        )

        if (
            result
            and result.get("ok")
        ):

            print(
                "✅ Фото отправлено"
            )

            return True

        print(
            f"❌ Telegram не принял фото: "
            f"{result}"
        )

        return False

    except Exception as error:

        print(
            f"❌ Ошибка отправки фото: "
            f"{error}"
        )

        return False


def send_photo_or_message(
    photo_url,
    text
):

    if photo_url:

        if send_photo(
            photo_url,
            text
        ):

            return

    send_message(
        text
    )


# ============================================================
# ОБЩИЕ ФУНКЦИИ
# ============================================================

def clean_text(
    text
):

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def absolute_url(
    url,
    base
):

    if not url:
        return None

    url = url.strip()

    if url.startswith(
        "//"
    ):

        parsed = urlparse(
            base
        )

        return (
            parsed.scheme
            + ":"
            + url
        )

    return urljoin(
        base,
        url
    )


def normalize_url(
    url
):

    if not url:
        return ""

    return (
        url
        .split("#")[0]
        .rstrip("/")
    )


# ============================================================
# PRICE
# ============================================================

def extract_price(
    text
):

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

            value = (
                match.group(1)
                .replace(",", ".")
                .strip()
            )

            return (
                value
                + " €"
            )

    return "Не указана"


# ============================================================
# MEMORY
# ============================================================

def extract_memory(
    text
):

    if not text:
        return "Не указана"

    patterns = [

        r"(\d+)\s*GB",

        r"(\d+)\s*Gb",

        r"(\d+)\s*gb",

        r"(\d+)\s*ГБ",

    ]

    valid_sizes = {
        16,
        32,
        64,
        128,
        256,
        512,
        1024,
        2048
    }

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for value in matches:

            try:

                number = int(
                    value
                )

            except Exception:

                continue

            if number in valid_sizes:

                return (
                    f"{number} GB"
                )

    return "Не указана"


# ============================================================
# BATTERY
# ============================================================

def extract_battery(
    text
):

    if not text:
        return "Не указана"

    patterns = [

        r"(\d{2,3})\s*%\s*"
        r"(?:battery|baterija)",

        r"(?:battery|baterija)"
        r"[^\d]{0,40}"
        r"(\d{2,3})\s*%",

        r"(?:akumulators|akumulator)"
        r"[^\d]{0,40}"
        r"(\d{2,3})\s*%",

        r"(\d{2,3})\s*%\s*"
        r"(?:akumulators|akumulator)",

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
# CITY
# ============================================================

def extract_city(
    text
):

    cities = [

        (
            "Rīga",
            ["rīga", "riga"]
        ),

        (
            "Jūrmala",
            ["jūrmala", "jurmala"]
        ),

        (
            "Liepāja",
            ["liepāja", "liepaja"]
        ),

        (
            "Daugavpils",
            ["daugavpils"]
        ),

        (
            "Jelgava",
            ["jelgava"]
        ),

        (
            "Ventspils",
            ["ventspils"]
        ),

        (
            "Valmiera",
            ["valmiera"]
        ),

        (
            "Ogre",
            ["ogre"]
        ),

        (
            "Salaspils",
            ["salaspils"]
        ),

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

def get_title_from_soup(
    soup
):

    h1 = soup.find(
        "h1"
    )

    if h1:

        value = clean_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

        if value:

            return value

    og = soup.find(
        "meta",
        property="og:title"
    )

    if og and og.get(
        "content"
    ):

        return clean_text(
            og["content"]
        )

    if soup.title:

        return clean_text(
            soup.title.get_text()
        )

    return "Не указано"


# ============================================================
# SS.LV MODEL
# ============================================================

def extract_sslv_model(
    soup,
    full_text,
    fallback_title
):

    labels = [
        "Marka:",
        "Modelis:",
        "Modelis",
        "Marka"
    ]

    for label in labels:

        match = re.search(
            rf"{re.escape(label)}\s*"
            r"([^\n|]+)",
            full_text,
            re.IGNORECASE
        )

        if match:

            value = clean_text(
                match.group(1)
            )

            if (
                "iphone"
                in value.lower()
            ):

                return value

    iphone_pattern = re.compile(
        r"\b("
        r"iPhone"
        r"(?:\s+"
        r"(?:Air|SE|X|XR|XS|XS Max|"
        r"11|11 Pro|11 Pro Max|"
        r"12|12 Mini|12 Pro|12 Pro Max|"
        r"13|13 Mini|13 Pro|13 Pro Max|"
        r"14|14 Plus|14 Pro|14 Pro Max|"
        r"15|15 Plus|15 Pro|15 Pro Max|"
        r"16|16 Plus|16e|16 Pro|16 Pro Max|"
        r"17|17 Plus|17 Pro|17 Pro Max)"
        r")?"
        r")\b",
        re.IGNORECASE
    )

    match = iphone_pattern.search(
        full_text
    )

    if match:

        return clean_text(
            match.group(1)
        )

    match = iphone_pattern.search(
        fallback_title
    )

    if match:

        return clean_text(
            match.group(1)
        )

    return fallback_title


# ============================================================
# SS.LV PHOTO SEARCH
# ============================================================

def add_photo_candidate(
    candidates,
    url,
    base_url
):

    if not url:
        return

    url = (
        url
        .strip()
        .strip("\"'")
        .replace(
            "\\/",
            "/"
        )
    )

    url = absolute_url(
        url,
        base_url
    )

    if not url:
        return

    low = url.lower()

    bad_words = [
        "logo",
        "icon",
        "sprite",
        "avatar",
        "placeholder",
        "noimage",
        "no-image",
        "blank",
        "loading",
        "loader"
    ]

    for word in bad_words:

        if word in low:

            return

    extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".avif"
    ]

    looks_like_image = any(
        ext in low
        for ext in extensions
    )

    looks_like_ss_image = (
        "ss.lv" in low
        and (
            "/images/" in low
            or "/img/" in low
        )
    )

    if (
        not looks_like_image
        and not looks_like_ss_image
    ):

        return

    if url not in candidates:

        candidates.append(
            url
        )


def extract_sslv_photo_candidates(
    soup,
    html,
    page_url
):

    candidates = []

    # IMG
    for img in soup.find_all(
        "img"
    ):

        attributes = [
            "src",
            "data-src",
            "data-original",
            "data-lazy-src",
            "data-image",
            "data-url",
            "data-full",
            "data-large",
            "data-original-src"
        ]

        for attr in attributes:

            value = img.get(
                attr
            )

            if value:

                add_photo_candidate(
                    candidates,
                    value,
                    page_url
                )

        srcset = img.get(
            "srcset"
        )

        if srcset:

            for part in srcset.split(","):

                part = part.strip()

                if not part:
                    continue

                image_url = (
                    part.split(" ")[0]
                )

                add_photo_candidate(
                    candidates,
                    image_url,
                    page_url
                )

    # Links
    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a.get(
            "href"
        )

        if not href:
            continue

        low = href.lower()

        if any(
            ext in low
            for ext in (
                ".jpg",
                ".jpeg",
                ".png",
                ".webp"
            )
        ):

            add_photo_candidate(
                candidates,
                href,
                page_url
            )

    # msg_img_dir
    dirs = re.findall(
        r'msg_img_dir\s*=\s*["\']([^"\']+)',
        html,
        re.IGNORECASE
    )

    for image_dir in dirs:

        image_dir = (
            image_dir
            .replace(
                "\\/",
                "/"
            )
            .rstrip("/")
            + "/"
        )

        for filename in [
            "800.jpg",
            "600.jpg",
            "400.jpg",
            "300.jpg",
            "200.jpg"
        ]:

            add_photo_candidate(
                candidates,
                image_dir + filename,
                page_url
            )

    # Absolute URLs in HTML
    url_pattern = re.compile(
        r'https?://[^"\']+?\.(?:jpg|jpeg|png|webp)(?:\?[^"\']*)?',
        re.IGNORECASE
    )

    for match in url_pattern.finditer(
        html
    ):

        add_photo_candidate(
            candidates,
            match.group(0),
            page_url
        )

    return candidates


def find_working_sslv_photo(
    soup,
    html,
    page_url
):

    candidates = (
        extract_sslv_photo_candidates(
            soup,
            html,
            page_url
        )
    )

    print(
        "📷 SS.LV: найдено кандидатов "
        f"на фото: {len(candidates)}"
    )

    for index, photo_url in enumerate(
        candidates[:20],
        start=1
    ):

        print(
            f"📷 SS.LV: проверяю "
            f"фото {index}/"
            f"{min(len(candidates), 20)}"
        )

        image = download_image(
            photo_url
        )

        if image:

            print(
                "✅ SS.LV: рабочая "
                f"фотография: {photo_url}"
            )

            return photo_url

    print(
        "❌ SS.LV: фотография не найдена."
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

                page_title = (
                    get_title_from_soup(
                        ad_soup
                    )
                )

                model = extract_sslv_model(
                    ad_soup,
                    all_text,
                    page_title
                )

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

                photo = find_working_sslv_photo(
                    ad_soup,
                    html,
                    link
                )

                message = (
                    "🟢 Новое объявление iPhone\n\n"
                    f"📱 {model}\n"
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

                seen_sslv.add(
                    link
                )

            except Exception as error:

                print(
                    "SS.LV ошибка карточки: "
                    f"{error}"
                )

    except Exception as error:

        print(
            f"SS.LV ошибка: {error}"
        )


# ============================================================
# ANDELE IPHONE CHECK
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
        "🔎 ANDELE: ищу карточки..."
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
        f"ANDELE: найдено ссылок: "
        f"{count}"
    )

    for i in range(
        count
    ):

        try:

            href = (
                anchors
                .nth(i)
                .get_attribute(
                    "href"
                )
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

            links.add(
                full_url
            )

        except Exception:

            continue

    return list(links)


# ============================================================
# ANDELE IMAGE
# ============================================================

def get_image_from_soup(
    soup,
    base_url
):

    meta = soup.find(
        "meta",
        property="og:image"
    )

    if meta and meta.get(
        "content"
    ):

        url = absolute_url(
            meta["content"],
            base_url
        )

        if download_image(
            url
        ):

            return url

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

                url = absolute_url(
                    meta["content"],
                    base_url
                )

                if download_image(
                    url
                ):

                    return url

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

            if download_image(
                src
            ):

                return src

    return None


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

            return None

        html = page.content()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        real_title = (
            get_title_from_soup(
                soup
            )
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
            f"❌ ANDELE ошибка: "
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
        "🔵 ANDELE: проверяю сайт..."
    )

    page = None

    try:

        page = browser.new_page()

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
            f"🔵 ANDELE: карточек: "
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
            f"❌ ANDELE ошибка: "
            f"{error}"
        )

    finally:

        if page:

            try:
                page.close()

            except Exception:
                pass


# ============================================================
# ============================================================
#                  FACEBOOK MARKETPLACE
# ============================================================
# ============================================================

def facebook_is_login_page(
    page
):

    try:

        current_url = page.url.lower()

        if (
            "login" in current_url
            or "checkpoint" in current_url
        ):

            return True

        text = (
            page.locator(
                "body"
            )
            .inner_text()
            .lower()
        )

        login_words = [
            "log in",
            "login",
            "войти",
            "увійти",
            "pieteikties"
        ]

        for word in login_words:

            if word in text:

                # Не считаем обычное слово
                # login в ссылке достаточным.
                if (
                    "marketplace"
                    not in current_url
                ):

                    return True

        return False

    except Exception:

        return False


def facebook_extract_image(
    card,
    page_url
):

    try:

        images = card.locator(
            "img"
        )

        count = images.count()

        for i in range(
            min(count, 10)
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
                page_url
            )

            if not src:

                continue

            low = src.lower()

            if (
                "profile" in low
                or "avatar" in low
                or "icon" in low
            ):

                continue

            # Facebook CDN обычно отдаёт
            # нормальную фотографию.
            return src

    except Exception:

        pass

    return None


def facebook_is_iphone(
    text
):

    low = text.lower()

    if "iphone" not in low:

        return False

    bad_words = [

        "case",
        "cover",
        "чехол",
        "чехла",

        "стекло",
        "защитное стекло",

        "cable",
        "charger",
        "кабель",
        "зарядка",

        "adapter",
        "адаптер",

        "airpods",
        "watch",

    ]

    for word in bad_words:

        if word in low:

            # Если одновременно есть
            # явное описание телефона,
            # не отбрасываем сразу.
            phone_words = [
                "gb",
                "battery",
                "батар",
                "телефон",
                "phone",
                "pro",
                "plus",
                "mini"
            ]

            if not any(
                p in low
                for p in phone_words
            ):

                return False

    return True


def facebook_extract_model(
    text
):

    patterns = [

        r"(iPhone\s+"
        r"(?:SE|X|XR|XS|"
        r"11|12|13|14|15|16|17)"
        r"(?:\s+(?:Pro|Pro Max|"
        r"Plus|Mini|Max|e))*)",

        r"(iPhone\s+[A-Za-z0-9+ -]{1,25})",

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

            return value

    return "iPhone"


def facebook_parse_card(
    card,
    browser
):

    try:

        text = clean_text(
            card.inner_text()
        )

        if not text:

            return None

        if not facebook_is_iphone(
            text
        ):

            return None

        # ----------------------------------------------------
        # LINK
        # ----------------------------------------------------

        links = card.locator(
            "a"
        )

        href = None

        for i in range(
            min(links.count(), 10)
        ):

            candidate = (
                links
                .nth(i)
                .get_attribute(
                    "href"
                )
            )

            if not candidate:

                continue

            if (
                "/marketplace/item/"
                in candidate
            ):

                href = candidate

                break

        if not href:

            return None

        url = normalize_url(
            absolute_url(
                href,
                "https://www.facebook.com"
            )
        )

        if not url:

            return None

        # ----------------------------------------------------
        # MODEL
        # ----------------------------------------------------

        model = facebook_extract_model(
            text
        )

        # ----------------------------------------------------
        # PRICE
        # ----------------------------------------------------

        price = extract_price(
            text
        )

        # ----------------------------------------------------
        # MEMORY
        # ----------------------------------------------------

        memory = extract_memory(
            text
        )

        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        battery = extract_battery(
            text
        )

        # ----------------------------------------------------
        # CITY
        # ----------------------------------------------------

        city = extract_city(
            text
        )

        # ----------------------------------------------------
        # PHOTO
        # ----------------------------------------------------

        photo = (
            facebook_extract_image(
                card,
                url
            )
        )

        # ----------------------------------------------------
        # MESSAGE
        # ----------------------------------------------------

        message = (
            "🔴 Новое объявление iPhone\n\n"
            f"📱 {model}\n"
            f"💰 Цена: {price}\n"
            f"💾 Память: {memory}\n"
            f"🔋 Батарея: {battery}\n"
            f"📍 Город: {city}\n\n"
            f"🔗 {url}"
        )

        return {
            "url": url,
            "title": model,
            "price": price,
            "memory": memory,
            "battery": battery,
            "city": city,
            "photo": photo,
            "message": message
        }

    except Exception as error:

        print(
            f"🔴 Facebook ошибка карточки: "
            f"{error}"
        )

        return None


def process_facebook(
    context
):

    if not FACEBOOK_ENABLED:

        return

    print(
        "🔴 FACEBOOK: проверяю Marketplace..."
    )

    page = None

    try:

        page = context.new_page()

        print(
            "🔴 FACEBOOK: открываю Marketplace..."
        )

        response = page.goto(
            FACEBOOK_SEARCH_URL,
            wait_until="domcontentloaded",
            timeout=45000
        )

        if response:

            print(
                f"FACEBOOK HTTP: "
                f"{response.status}"
            )

        page.wait_for_timeout(
            5000
        )

        # ----------------------------------------------------
        # Проверяем авторизацию
        # ----------------------------------------------------

        if facebook_is_login_page(
            page
        ):

            print(
                "⚠️ FACEBOOK: нужна авторизация."
            )

            print(
                "⚠️ Facebook Marketplace "
                "не отдаёт объявления "
                "без входа в аккаунт."
            )

            return

        # ----------------------------------------------------
        # Прокрутка
        # ----------------------------------------------------

        for _ in range(4):

            page.mouse.wheel(
                0,
                1800
            )

            page.wait_for_timeout(
                1500
            )

        # ----------------------------------------------------
        # Ищем Marketplace item links
        # ----------------------------------------------------

        item_links = page.locator(
            'a[href*="/marketplace/item/"]'
        )

        count = item_links.count()

        print(
            f"🔴 FACEBOOK: найдено "
            f"ссылок: {count}"
        )

        cards = []

        # ----------------------------------------------------
        # Берём родительские контейнеры
        # ----------------------------------------------------

        for i in range(
            min(count, 100)
        ):

            try:

                link = (
                    item_links
                    .nth(i)
                )

                href = link.get_attribute(
                    "href"
                )

                if not href:

                    continue

                url = normalize_url(
                    absolute_url(
                        href,
                        "https://www.facebook.com"
                    )
                )

                if not url:

                    continue

                # Ищем ближайший контейнер.
                card = link.locator(
                    "xpath=ancestor::div[.//a[contains(@href,'/marketplace/item/')]][1]"
                )

                if card.count() == 0:

                    card = link.locator(
                        "xpath=.."
                    )

                cards.append(
                    (
                        card,
                        url
                    )
                )

            except Exception:

                continue

        sent = 0

        # ----------------------------------------------------
        # Обрабатываем карточки
        # ----------------------------------------------------

        checked_urls = set()

        for card, url in cards:

            if url in checked_urls:

                continue

            checked_urls.add(
                url
            )

            if url in seen_facebook:

                continue

            try:

                ad = facebook_parse_card(
                    card,
                    context
                )

                if not ad:

                    continue

                print(
                    "🎯 FACEBOOK: НАЙДЕН IPHONE!"
                )

                print(
                    ad["message"]
                )

                send_photo_or_message(
                    ad["photo"],
                    ad["message"]
                )

                seen_facebook.add(
                    url
                )

                sent += 1

            except Exception as error:

                print(
                    "🔴 Facebook ошибка "
                    f"объявления: {error}"
                )

        print(
            f"🔴 FACEBOOK: новых "
            f"iPhone отправлено: {sent}"
        )

    except Exception as error:

        print(
            f"❌ FACEBOOK главная ошибка: "
            f"{error}"
        )

    finally:

        if page:

            try:

                page.close()

            except Exception:

                pass


# ============================================================
# START MESSAGE
# ============================================================

def send_start_message():

    text = (
        "🤖 Бот запущен!\n\n"

        "🟢 SS.LV — поиск iPhone\n"

        "🔵 Andele Mandele — поиск iPhone\n"

        "🔴 Facebook Marketplace — поиск iPhone\n\n"

        "📷 Фото включены\n\n"

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

    print(
        "=" * 70
    )

    print(
        "🤖 IPHONE BOT ЗАПУЩЕН"
    )

    print(
        "🟢 SS.LV"
    )

    print(
        "🔵 Andele Mandele"
    )

    print(
        "🔴 Facebook Marketplace"
    )

    print(
        f"⏱ Интервал: "
        f"{CHECK_INTERVAL} секунд"
    )

    print(
        "=" * 70
    )

    send_start_message()

    with sync_playwright() as p:

        # ====================================================
        # CHROMIUM
        # ====================================================

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

        # ====================================================
        # ANDELE CONTEXT
        # ====================================================

        andele_context = browser.new_context(
            user_agent=HEADERS[
                "User-Agent"
            ],
            locale="lv-LV"
        )

        # ====================================================
        # FACEBOOK CONTEXT
        # ====================================================

        facebook_context = None

        if FACEBOOK_ENABLED:

            if os.path.exists(
                FACEBOOK_SESSION_FILE
            ):

                print(
                    "🔴 FACEBOOK: "
                    "найдена сохранённая сессия."
                )

                try:

                    facebook_context = (
                        browser.new_context(
                            storage_state=(
                                FACEBOOK_SESSION_FILE
                            ),

                            user_agent=HEADERS[
                                "User-Agent"
                            ],

                            locale="lv-LV"
                        )
                    )

                except Exception as error:

                    print(
                        "❌ Facebook session "
                        f"ошибка: {error}"
                    )

            else:

                print(
                    "⚠️ FACEBOOK: "
                    "facebook_session.json "
                    "не найден."
                )

                print(
                    "⚠️ Facebook модуль "
                    "пока не сможет войти."
                )

        # ====================================================
        # LOOP
        # ====================================================

        while True:

            try:

                print()
                print(
                    "=" * 70
                )

                print(
                    "🔎 ПРОВЕРЯЮ САЙТЫ..."
                )

                print(
                    "=" * 70
                )

                # =================================================
                # SS.LV
                # =================================================

                process_sslv()

                # =================================================
                # ANDELE
                # =================================================

                process_andele(
                    andele_context
                )

                # =================================================
                # FACEBOOK
                # =================================================

                if facebook_context:

                    process_facebook(
                        facebook_context
                    )

                else:

                    print(
                        "🔴 FACEBOOK: "
                        "сессия ещё не настроена."
                    )

                # =================================================
                # WAIT
                # =================================================

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

        # ====================================================
        # CLOSE
        # ====================================================

        if facebook_context:

            try:

                facebook_context.close()

            except Exception:

                pass

        try:

            andele_context.close()

        except Exception:

            pass

        browser.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
