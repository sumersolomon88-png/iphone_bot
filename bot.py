import re
import time
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


# ============================================================
# TELEGRAM
# ============================================================

# НЕ вставляю секретный токен обратно в сообщение.
# Вставь сюда свой текущий BOT TOKEN.
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

# ВАЖНО:
# Это актуальная категория телефонов Andele.
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
    "Accept-Language": "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ============================================================
# УЖЕ ОТПРАВЛЕННЫЕ
# ============================================================

seen_sslv = set()
seen_andele = set()


# ============================================================
# HTTP SESSION ДЛЯ SS.LV
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

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for value in matches:

            number = int(value)

            if number in (
                16,
                32,
                64,
                128,
                256,
                512,
                1024,
                2048
            ):

                return (
                    f"{number} GB"
                )

    return "Не указана"


def extract_battery(text):

    if not text:
        return "Не указана"

    patterns = [
        r"(\d{2,3})\s*%\s*(?:battery|baterija)",
        r"(?:battery|baterija)[^\d]{0,30}(\d{2,3})\s*%",
        r"(?:akumulators|akumulator)[^\d]{0,30}(\d{2,3})\s*%",
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
                + "%"
            )

    return "Не указана"


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


def get_title_from_soup(
    soup
):

    og = soup.find(
        "meta",
        property="og:title"
    )

    if og and og.get("content"):

        return clean_text(
            og["content"]
        )

    h1 = soup.find("h1")

    if h1:

        return clean_text(
            h1.get_text(" ", strip=True)
        )

    if soup.title:

        return clean_text(
            soup.title.get_text()
        )

    return "Не указано"


def get_image_from_soup(
    soup,
    base_url
):

    # --------------------------------------------------------
    # OG IMAGE
    # --------------------------------------------------------

    meta = soup.find(
        "meta",
        property="og:image"
    )

    if meta and meta.get("content"):

        return absolute_url(
            meta["content"],
            base_url
        )

    # --------------------------------------------------------
    # TWITTER IMAGE
    # --------------------------------------------------------

    for meta in soup.find_all("meta"):

        name = (
            meta.get("name")
            or meta.get("property")
            or ""
        ).lower()

        if name in (
            "twitter:image",
            "twitter:image:src"
        ):

            if meta.get("content"):

                return absolute_url(
                    meta["content"],
                    base_url
                )

    # --------------------------------------------------------
    # IMG
    # --------------------------------------------------------

    for img in soup.find_all("img"):

        for attr in (
            "src",
            "data-src",
            "data-original",
            "data-lazy-src"
        ):

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
# ============================================================
#                       SS.LV
# ============================================================
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
                links.append(link)

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

                if ad_response.status_code != 200:
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

                title = get_title_from_soup(
                    ad_soup
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

                photo = None

                image_match = re.search(
                    r'msg_img_dir\s*=\s*"([^"]+)"',
                    html
                )

                if image_match:

                    image_dir = (
                        image_match.group(1)
                    )

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

                    photo = get_image_from_soup(
                        ad_soup,
                        link
                    )

                message = (
                    "📱 Новое объявление iPhone\n\n"
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
            f"SS.LV ошибка: {error}"
        )


# ============================================================
# ============================================================
#                    ANDELE + PLAYWRIGHT
# ============================================================
# ============================================================

def is_real_iphone(
    title,
    text
):

    combined = (
        f"{title} {text}"
    ).lower()

    # Должно присутствовать Apple/iPhone
    has_iphone = (
        "iphone" in combined
        or "apple" in combined
    )

    if not has_iphone:
        return False

    # Исключаем типичные аксессуары
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

    # Если прямо написано iPhone,
    # аксессуар всё равно может содержать слово iPhone.
    # Поэтому смотрим на title в первую очередь.

    title_low = title.lower()

    if "iphone" in title_low:

        # Явный iPhone в заголовке — хороший признак.
        # Но если заголовок явно начинается/содержит
        # чехол/cover — отбрасываем.

        for word in accessory_words:

            if word in title_low:
                return False

        return True

    # Если iPhone есть только в описании,
    # требуем более строгий признак.

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


def get_andele_links(
    page
):

    print(
        "🔎 ANDELE: ищу реальные карточки..."
    )

    links = set()

    # Ждём загрузки карточек.
    page.wait_for_timeout(
        3000
    )

    # Несколько раз прокручиваем страницу,
    # чтобы динамические карточки успели появиться.
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

            href = anchors.nth(i).get_attribute(
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

    return list(links)


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

        # Получаем весь видимый текст.
        body_text = clean_text(
            page.locator("body").inner_text()
        )

        # ----------------------------------------------------
        # Проверяем iPhone
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # HTML
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Данные
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Фото
        # ----------------------------------------------------

        photo = get_image_from_soup(
            soup,
            url
        )

        # ----------------------------------------------------
        # Дополнительный поиск картинки
        # через DOM
        # ----------------------------------------------------

        if not photo:

            try:

                images = page.locator(
                    "img"
                )

                image_count = images.count()

                for i in range(
                    min(image_count, 20)
                ):

                    src = (
                        images
                        .nth(i)
                        .get_attribute("src")
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

        # ----------------------------------------------------
        # Сообщение
        # ----------------------------------------------------

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

                # Это не iPhone.
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
# СТАРТОВОЕ СООБЩЕНИЕ
# ============================================================

def send_start_message():

    text = (
        "🤖 Бот запущен!\n\n"
        "🟢 SS.LV — поиск iPhone\n"
        "🔵 Andele Mandele — поиск iPhone\n\n"
        "🌐 Andele работает через Chromium\n"
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
        "🌐 Andele: Playwright + Chromium"
    )

    print(
        f"⏱ Интервал: "
        f"{CHECK_INTERVAL} секунд"
    )

    print("=" * 70)

    send_start_message()

    # --------------------------------------------------------
    # Запускаем настоящий Chromium
    # --------------------------------------------------------

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

                # ------------------------------------------------
                # SS.LV
                # ------------------------------------------------

                process_sslv()

                # ------------------------------------------------
                # ANDELE
                # ------------------------------------------------

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
