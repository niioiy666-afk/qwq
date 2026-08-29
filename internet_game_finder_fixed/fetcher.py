import requests
import logging
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.exceptions import RequestException, HTTPError, Timeout

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

TEMPORARY_HTTP_ERRORS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
RETRY_DELAY = 2


def get_html(url, timeout=20):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.text
        except HTTPError as e:
            if e.response.status_code in TEMPORARY_HTTP_ERRORS and attempt < MAX_RETRIES - 1:
                logging.warning(f"Повторная попытка для {url} (попытка {attempt + 1}/{MAX_RETRIES}). Ошибка: HTTP {e.response.status_code}")
                time.sleep(RETRY_DELAY)
                continue
            logging.error(f"HTTP-ошибка для {url}: HTTP {e.response.status_code}")
            return None
        except (RequestException, Timeout) as e:
            logging.error(f"Ошибка запроса для {url}: {e}")
            return None
    return None


def extract_games(url):
    """
    Возвращает список ИГР с кооп-сайтов.
    Сейчас заточен под Coop-Land:
    - страницы вида https://coop-land.ru/allgames/.../...html
    - новости, теги, разделы и т.п. отбрасываются.
    Формат: {name, url, text}
    """
    html = get_html(url)
    if html is None:
        logging.warning(f"Не удалось получить HTML для {url}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    games = []

    # --- Coop-Land: страницы игр ---
    # Ссылки на конкретные игры имеют вид:
    # /allgames/<genre>/<id>-<slug>.html
    for a in soup.select("a[href]"):
        href = urljoin(url, a["href"].strip())
        if "/allgames/" not in href or not href.endswith(".html"):
            continue

        name = " ".join(a.get_text(" ", strip=True).split())
        if len(name) < 3:
            continue

        # Простая защита от дублей
        games.append({
            "name": name,
            "title": name,
            "text": name,
            "url": href,
            "href": href,
        })

    # --- Убираем дубликаты (name+url) ---
    uniq = []
    seen = set()
    for g in games:
        key = (g["name"].lower(), g["url"].lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(g)

    if not uniq:
        logging.warning(f"Не найдены ожидаемые элементы на странице {url}")

    return uniq
