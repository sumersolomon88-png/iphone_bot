import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = "8935933040:AAEfLk_llaTbsuUfse57oekzvi0vS-_E7Tg"
CHAT_ID = "5309553879"


# ============================================================
# НАСТРОЙКИ
# ============================================================

CHECK_INTERVAL = 10

SS_URL = (
    "https://www.ss.lv/lv/electronics/phones/"
    "mobile-phones/apple/"
)

ANDELE_URL = (
    "https://www.andelemandele.lv/"
    "perles/tehnika/telefoni/?setlang=lv"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive"
}


# ============================================================
# ПАМЯТЬ
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

def send_message(text):

    try:

        response = session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": False
            },
            timeout=15
        )

        if response.status_code == 200:

            print("Telegram: сообщение отправлено")

            return True

        print(
            "Telegram ошибка:",
            response.status_code,
            response.text
        )

        return False

    except Exception as error:

        print(
            "Ошибка Telegram:",
            error
        )

        return False


# ============================================================
# ЗАГРУЗКА СТРАНИЦЫ
# ============================================================

def get_html(url):

    try:

        response = session.get(
            url,
            timeout=20
        )

        print(
            f"HTTP {response.status_code} -> {url}"
        )

        if response.status_code != 200:

            return None

        return response.text

    except Exception as error:

        print(
            "Ошибка загрузки:",
            url
        )

        print(error)

        return None


# ============================================================
# НОРМАЛИЗАЦИЯ ТЕКСТА
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = text.replace(
        "\xa0",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# SS.LV
# ПОЛУЧЕНИЕ ОБЪЯВЛЕНИЙ ИЗ СПИСКА
# ============================================================

def get_ss_ads():

    ads = []

    html = get_html(
        SS_URL
    )

    if not html:

        print(
            "SS.LV: страницу получить не удалось"
        )

        return ads

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    # --------------------------------------------------------
    # Ищем все ссылки объявлений
    # --------------------------------------------------------

    links = soup.find_all(
        "a",
        href=True
    )


    for link in links:

        href = link.get(
            "href",
            ""
        )

        if "/msg/" not in href:

            continue


        full_url = urljoin(
            "https://www.ss.lv",
            href
        )


        if full_url in {
            ad["url"]
            for ad in ads
        }:

            continue


        # ----------------------------------------------------
        # Пытаемся найти строку таблицы
        # ----------------------------------------------------

        row = link.find_parent(
            "tr"
        )


        row_text = ""

        cells = []

        if row:

            row_text = clean_text(
                row.get_text(
                    " ",
                    strip=True
                )
            )

            cells = [
                clean_text(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                )
                for cell in row.find_all(
                    ["td", "th"]
                )
            ]


        # ----------------------------------------------------
        # Название
        # ----------------------------------------------------

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )


        # Иногда текст ссылки пустой.
        # Тогда берём весь текст строки.

        if not title:

            title = row_text


        if not title:

            title = "iPhone"


        # ----------------------------------------------------
        # Цена
        # ----------------------------------------------------

        price = "Не указана"


        for cell in cells:

            if "€" in cell:

                price_match = re.search(
                    r"[\d\s,.]+€",
                    cell
                )

                if price_match:

                    price = clean_text(
                        price_match.group(0)
                    )

                    break


        if price == "Не указана":

            price_match = re.search(
                r"[\d\s,.]+€",
                row_text
            )

            if price_match:

                price = clean_text(
                    price_match.group(0)
                )


        # ----------------------------------------------------
        # Память
        # ----------------------------------------------------

        memory = "Не указана"


        memory_match = re.search(
            r"\b(\d{1,4})\s*(GB|Gb|gb)\b",
            row_text,
            re.IGNORECASE
        )


        if memory_match:

            memory = (
                memory_match.group(1)
                + " GB"
            )


        # ----------------------------------------------------
        # Город
        # ----------------------------------------------------

        city = "Не указан"


        cities = [
            "Rīga",
            "Riga",
            "Jūrmala",
            "Liepāja",
            "Daugavpils",
            "Jelgava",
            "Ventspils",
            "Rēzekne",
            "Valmiera",
            "Ogre"
        ]


        for city_name in cities:

            if re.search(
                r"\b"
                + re.escape(city_name)
                + r"\b",
                row_text,
                re.IGNORECASE
            ):

                city = city_name

                break


        # ----------------------------------------------------
        # Состояние
        # ----------------------------------------------------

        condition = "Не указано"

        condition_words = [
            "jaun",
            "lietota",
            "lietots",
            "pērku",
            "pārdodu"
        ]


        for word in condition_words:

            if word.lower() in row_text.lower():

                if (
                    "jaun"
                    in word.lower()
                ):

                    condition = "Новое"

                elif (
                    "lietot"
                    in word.lower()
                ):

                    condition = "Б/у"

                break


        # ----------------------------------------------------
        # Сохраняем
        # ----------------------------------------------------

        ads.append({

            "url": full_url,

            "title": title,

            "price": price,

            "memory": memory,

            "city": city,

            "condition": condition

        })


    return ads


# ============================================================
# SS.LV
# ДОПОЛНИТЕЛЬНО ПОЛУЧАЕМ ДАННЫЕ СО СТРАНИЦЫ ОБЪЯВЛЕНИЯ
# ============================================================

def improve_ss_ad(ad):

    html = get_html(
        ad["url"]
    )

    if not html:

        return ad


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


    # --------------------------------------------------------
    # Название
    # --------------------------------------------------------

    if (
        not ad["title"]
        or ad["title"] == "iPhone"
        or len(ad["title"]) < 5
    ):

        if soup.title:

            title = clean_text(
                soup.title.get_text(
                    " ",
                    strip=True
                )
            )

            if title:

                ad["title"] = title


    # --------------------------------------------------------
    # Цена
    # --------------------------------------------------------

    if ad["price"] == "Не указана":

        patterns = [

            r"Cena\s*:?\s*([\d\s,.]+€)",

            r"Цена\s*:?\s*([\d\s,.]+€)",

            r"([\d\s,.]+€)"

        ]


        for pattern in patterns:

            match = re.search(
                pattern,
                page_text,
                re.IGNORECASE
            )

            if match:

                ad["price"] = clean_text(
                    match.group(1)
                )

                break


    # --------------------------------------------------------
    # Память
    # --------------------------------------------------------

    if ad["memory"] == "Не указана":

        memory_match = re.search(
            r"\b(\d{1,4})\s*(GB|Gb|gb)\b",
            page_text,
            re.IGNORECASE
        )


        if memory_match:

            ad["memory"] = (
                memory_match.group(1)
                + " GB"
            )


    # --------------------------------------------------------
    # Город
    # --------------------------------------------------------

    if ad["city"] == "Не указан":

        cities = [
            "Rīga",
            "Riga",
            "Jūrmala",
            "Liepāja",
            "Daugavpils",
            "Jelgava",
            "Ventspils",
            "Rēzekne",
            "Valmiera",
            "Ogre"
        ]


        for city_name in cities:

            if re.search(
                r"\b"
                + re.escape(city_name)
                + r"\b",
                page_text,
                re.IGNORECASE
            ):

                ad["city"] = city_name

                break


    return ad


# ============================================================
# ANDELE MANDELE
# ПОИСК IPHONE
# ============================================================

def get_andele_ads():

    ads = {}

    html = get_html(
        ANDELE_URL
    )

    if not html:

        print(
            "ANDELE: страницу получить не удалось"
        )

        return []


    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    # --------------------------------------------------------
    # Ищем ВСЕ ссылки /perle/
    # --------------------------------------------------------

    links = soup.find_all(
        "a",
        href=re.compile(
            r"/perle/"
        )
    )


    print(
        "ANDELE: найдено ссылок /perle/:",
        len(links)
    )


    for link in links:

        href = link.get(
            "href",
            ""
        )


        if "/perle/" not in href:

            continue


        full_url = urljoin(
            "https://www.andelemandele.lv",
            href
        )


        # ----------------------------------------------------
        # Получаем текст ближайшего блока
        # ----------------------------------------------------

        text_parts = []


        current = link


        for _ in range(5):

            if not current:

                break


            text = clean_text(
                current.get_text(
                    " ",
                    strip=True
                )
            )


            if text:

                text_parts.append(
                    text
                )


            current = current.parent


        card_text = " ".join(
            text_parts
        )


        # ----------------------------------------------------
        # Название ссылки
        # ----------------------------------------------------

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )


        # ----------------------------------------------------
        # Проверяем iPhone
        # ----------------------------------------------------

        combined = (
            title
            + " "
            + card_text
            + " "
            + full_url
        ).lower()


        if "iphone" not in combined:

            continue


        # ----------------------------------------------------
        # Цена
        # ----------------------------------------------------

        price = "Не указана"


        price_match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*€",
            card_text
        )


        if price_match:

            price = (
                price_match.group(1)
                + " €"
            )


        # ----------------------------------------------------
        # Если название пустое
        # ----------------------------------------------------

        if not title:

            title = "iPhone"


        # ----------------------------------------------------
        # Сохраняем
        # ----------------------------------------------------

        ads[full_url] = {

            "url": full_url,

            "title": title,

            "price": price

        }


    return list(
        ads.values()
    )


# ============================================================
# ANDELE
# ПОЛУЧЕНИЕ ПОДРОБНОСТЕЙ
# ============================================================

def improve_andele_ad(ad):

    html = get_html(
        ad["url"]
    )

    if not html:

        return ad


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


    # --------------------------------------------------------
    # Название
    # --------------------------------------------------------

    h1 = soup.find(
        "h1"
    )


    if h1:

        title = clean_text(
            h1.get_text(
                " ",
                strip=True
            )
        )


        if title:

            ad["title"] = title


    # --------------------------------------------------------
    # Цена
    # --------------------------------------------------------

    price_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*€",
        page_text
    )


    if price_match:

        ad["price"] = (
            price_match.group(1)
            + " €"
        )


    # --------------------------------------------------------
    # Состояние
    # --------------------------------------------------------

    condition = "Не указано"


    if (
        "Lietots, lieliskā stāvoklī"
        in page_text
    ):

        condition = (
            "Б/у — отличное состояние"
        )

    elif (
        "Lietots, labā stāvoklī"
        in page_text
    ):

        condition = (
            "Б/у — хорошее состояние"
        )

    elif (
        "Lietots, iespējami trūkumi"
        in page_text
    ):

        condition = (
            "Б/у — есть недостатки"
        )

    elif "Jauns" in page_text:

        condition = "Новое"

    elif "Lietots" in page_text:

        condition = "Б/у"


    ad["condition"] = condition


    # --------------------------------------------------------
    # Память
    # --------------------------------------------------------

    memory = "Не указана"


    memory_match = re.search(
        r"\b(\d{1,4})\s*(GB|Gb|gb)\b",
        page_text,
        re.IGNORECASE
    )


    if memory_match:

        memory = (
            memory_match.group(1)
            + " GB"
        )


    ad["memory"] = memory


    # --------------------------------------------------------
    # Город
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
        "Rēzekne",
        "Valmiera",
        "Ogre"
    ]


    for city_name in cities:

        if re.search(
            r"\b"
            + re.escape(city_name)
            + r"\b",
            page_text,
            re.IGNORECASE
        ):

            city = city_name

            break


    ad["city"] = city


    return ad


# ============================================================
# ОТПРАВКА SS.LV
# ============================================================

def send_ss_ad(ad):

    print("")
    print(
        "🆕 НОВОЕ ОБЪЯВЛЕНИЕ SS.LV"
    )


    message = (

        "🟢 SS.LV\n\n"

        f"📱 {ad['title']}\n\n"

        f"💰 {ad['price']}\n"

        f"💾 {ad['memory']}\n"

        f"📍 {ad['city']}\n"

        f"📦 {ad['condition']}\n\n"

        f"🔗 {ad['url']}"

    )


    print(message)


    send_message(
        message
    )


# ============================================================
# ОТПРАВКА ANDELE
# ============================================================

def send_andele_ad(ad):

    print("")
    print(
        "🆕 НОВОЕ ОБЪЯВЛЕНИЕ ANDELE"
    )


    message = (

        "🔵 ANDELE MANDELE\n\n"

        f"📱 {ad['title']}\n\n"

        f"💰 {ad['price']}\n"

        f"💾 {ad.get('memory', 'Не указана')}\n"

        f"📍 {ad.get('city', 'Не указан')}\n"

        f"📦 {ad.get('condition', 'Не указано')}\n\n"

        f"🔗 {ad['url']}"

    )


    print(message)


    send_message(
        message
    )


# ============================================================
# СТАРТОВОЕ СООБЩЕНИЕ
# ============================================================

print("")
print("==============================================")
print("          IPHONE BOT ЗАПУЩЕН")
print("==============================================")
print("🟢 SS.LV — включён")
print("🔵 ANDELE MANDELE — включён")
print("📱 Только iPhone")
print(f"⏱ Проверка каждые {CHECK_INTERVAL} секунд")
print("==============================================")
print("")


send_message(
    "🤖 Бот запущен!\n\n"
    "🟢 SS.LV — поиск iPhone\n"
    "🔵 Andele Mandele — поиск iPhone\n\n"
    "⏱ Проверка каждые 10 секунд."
)


# ============================================================
# ПЕРВАЯ ЗАГРУЗКА SS.LV
# ============================================================

print("")
print(
    "Загружаю текущие объявления SS.LV..."
)


initial_ss = get_ss_ads()


print(
    "SS.LV: найдено:",
    len(initial_ss)
)


for ad in initial_ss:

    seen_ss.add(
        ad["url"]
    )


# ============================================================
# ПЕРВАЯ ЗАГРУЗКА ANDELE
# ============================================================

print("")
print(
    "Загружаю текущие объявления ANDELE..."
)


initial_andele = get_andele_ads()


print(
    "ANDELE: найдено iPhone:",
    len(initial_andele)
)


for ad in initial_andele:

    seen_andele.add(
        ad["url"]
    )


# ============================================================
# ГОТОВ
# ============================================================

print("")
print("==============================================")
print("           БОТ ГОТОВ К РАБОТЕ")
print("==============================================")
print(
    "SS.LV в памяти:",
    len(seen_ss)
)
print(
    "ANDELE в памяти:",
    len(seen_andele)
)
print("==============================================")
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
            "SS.LV: найдено:",
            len(current_ss)
        )


        for ad in current_ss:

            url = ad["url"]


            if url in seen_ss:

                continue


            print(
                "🆕 Обнаружено новое SS.LV:",
                url
            )


            # Дополняем информацию
            ad = improve_ss_ad(
                ad
            )


            send_ss_ad(
                ad
            )


            seen_ss.add(
                url
            )


        # ====================================================
        # ANDELE MANDELE
        # ====================================================

        current_andele = get_andele_ads()


        print(
            "ANDELE: найдено iPhone:",
            len(current_andele)
        )


        for ad in current_andele:

            url = ad["url"]


            if url in seen_andele:

                continue


            print(
                "🆕 Обнаружено новое ANDELE:",
                url
            )


            # Дополняем информацию
            ad = improve_andele_ad(
                ad
            )


            send_andele_ad(
                ad
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
        print("❌ ОШИБКА ОСНОВНОГО ЦИКЛА:")
        print(error)
        print("")
        print(
            "Бот продолжит работу "
            "через 10 секунд."
        )


        time.sleep(
            10
        )
