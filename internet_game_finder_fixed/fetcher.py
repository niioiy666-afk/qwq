import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

def get_html(url, timeout=20):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text

def extract_games(url):
    """
    Возвращает список ИГР с кооп-сайтов.
    Сейчас заточен под Coop-Land:
    - страницы вида https://coop-land.ru/allgames/.../...html
    - новости, теги, разделы и т.п. отбрасываются.
    Формат: {name, url, text}
    """
    html = get_html(url)
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

    return uniq