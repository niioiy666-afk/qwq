import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).parent
OUT = BASE / "game_library.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

SOURCES = [
    # Кооперативные подборки / каталоги
    "https://iwant.games/kooperativ/",           # кооп-игры 2026 [web:26]
    "https://gglevel.com/ru/games-list?platform=pc&player_mode=co-op",  # кооп на ПК [web:43]
    "https://1lag.com/ru/igry/50-luchshih-kooperativnyh-igr/",          # большой список кооп-игр [web:46]
]

# Можно позже добавить ещё источников вручную:
# - общие каталоги игр;
# - другие подборки.


def get_html(url, sleep=0.5):
    """Простой GET с заголовком и задержкой, чтобы не душить сайты."""
    time.sleep(sleep)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def clean_text(text: str) -> str:
    return " ".join((text or "").split())


def guess_year(text: str) -> str:
    m = re.search(r"(19|20)\d{2}", text)
    return m.group(0) if m else ""


def guess_free2play(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["free-to-play", "free2play", "условно-бесплатн", "бесплатная игра", "free to play"]):
        return "Yes"
    return "No"


def guess_platforms(text: str) -> str:
    t = text.lower()
    platforms = []
    if "pc" in t or "windows" in t:
        platforms.append("PC")
    if "ps5" in t or "playstation 5" in t:
        platforms.append("PS5")
    if "ps4" in t or "playstation 4" in t:
        platforms.append("PS4")
    if "xbox series" in t or "series x" in t or "series s" in t:
        platforms.append("Xbox Series")
    if "xbox one" in t:
        platforms.append("Xbox One")
    if "switch" in t or "nintendo switch" in t:
        platforms.append("Switch")
    return ";".join(platforms)


def guess_genre(text: str) -> str:
    t = text.lower()
    genres = []
    if "шутер" in t or "shooter" in t:
        genres.append("Shooter")
    if "rpg" in t or "role-playing" in t or "рпг" in t:
        genres.append("RPG")
    if "strategy" in t or "стратегия" in t:
        genres.append("Strategy")
    if "survival" in t or "выживание" in t:
        genres.append("Survival")
    if "sandbox" in t or "песочница" in t:
        genres.append("Sandbox")
    if "horror" in t or "ужасы" in t:
        genres.append("Horror")
    if "platformer" in t or "платформер" in t:
        genres.append("Platformer")
    if "simulation" in t or "симулятор" in t:
        genres.append("Simulator")
    if "action" in t or "экшен" in t:
        genres.append("Action")
    if "adventure" in t or "приключение" in t:
        genres.append("Adventure")
    return ";".join(genres)


def guess_coop_players(text: str) -> str:
    t = text.lower()
    # Ищем "кооператив для 4х", "2-4 players", "up to 4 players" и т.п.
    m = re.search(r"кооператив для (\d+)", t)
    if m:
        return m.group(1)

    m = re.search(r"(\d+)[–-](\d+)\s*players", t)
    if m:
        return m.group(2)

    m = re.search(r"up to (\d+)\s*players", t)
    if m:
        return m.group(1)

    m = re.search(r"(\d+)\s*players", t)
    if m:
        return m.group(1)

    return ""


def guess_has_pvp(text: str) -> str:
    t = text.lower()
    if any(x in t for x in [
        "pvp",
        "competitive",
        "versus",
        "ranked",
        "соревновательный",  # соревновательный мультиплеер
        "deathmatch",
        "team deathmatch",
        "battle royale",
    ]):
        return "Yes"
    return "No"


def collect_from_iwant_games(url: str):
    """Парсер кооп-списка iwant.games. [web:26]"""
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")

    items = []

    # На iwant.games игры обычно лежат в списке карточек.
    # Используем простое правило: ссылки внутри блока с названием, годом и платформами.
    for card in soup.select("article, .game-item, .game-card"):
        text = clean_text(card.get_text(" ", strip=True))
        a = card.find("a", href=True)
        if not a:
            continue
        name = clean_text(a.get_text(" ", strip=True))
        href = urljoin(url, a["href"].strip())
        if not name:
            continue

        item_text = text.lower()

        items.append({
            "name": name,
            "platform": guess_platforms(text),
            "coop_players": guess_coop_players(text),
            "has_pvp": guess_has_pvp(text),
            "year": guess_year(text),
            "genre": guess_genre(text),
            "free2play": guess_free2play(text),
            "url": href,
            "source": "iwant.games",
        })

    return items


def collect_from_gglevel(url: str):
    """Парсер кооп-списка gglevel / igroPad. [web:43]"""
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")

    items = []

    # Игры обычно лежат в блоках с классами типа .game-card / .card / .item
    for card in soup.select(".game-card, .card, .item, article"):
        text = clean_text(card.get_text(" ", strip=True))
        a = card.find("a", href=True)
        if not a:
            continue
        name = clean_text(a.get_text(" ", strip=True))
        href = urljoin(url, a["href"].strip())
        if not name:
            continue

        items.append({
            "name": name,
            "platform": guess_platforms(text),
            "coop_players": guess_coop_players(text),
            "has_pvp": guess_has_pvp(text),
            "year": guess_year(text),
            "genre": guess_genre(text),
            "free2play": guess_free2play(text),
            "url": href,
            "source": "gglevel",
        })

    return items


def collect_from_1lag(url: str):
    """Парсер списка 'ТОП 50 кооп-игр'. [web:46]"""
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")

    items = []

    # Там игры обычно перечислены в списках <li> или блоках с <strong>/<b> названием
    for li in soup.select("li"):
        text = clean_text(li.get_text(" ", strip=True))
        if len(text) < 5:
            continue

        # Пытаемся вытащить название как первую часть строки
        # Простой хак: всё до тире / дефиса считаем названием
        name = text.split("—", 1)[0].split("-", 1)[0].strip()
        if len(name) < 3:
            continue

        items.append({
            "name": name,
            "platform": guess_platforms(text),
            "coop_players": guess_coop_players(text),
            "has_pvp": guess_has_pvp(text),
            "year": guess_year(text),
            "genre": guess_genre(text),
            "free2play": guess_free2play(text),
            "url": url,
            "source": "1lag.com",
        })

    return items


def collect_all():
    all_items = []

    for src in SOURCES:
        try:
            print(f"[*] Collecting from {src}")
            if "iwant.games" in src:
                items = collect_from_iwant_games(src)
            elif "gglevel.com" in src or "igropad" in src:
                items = collect_from_gglevel(src)
            elif "1lag.com" in src:
                items = collect_from_1lag(src)
            else:
                items = []
            print(f"    -> got {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            print(f"[!] Error on {src}: {e}", file=sys.stderr)
            continue

    # Убираем дубликаты по name+url
    uniq = []
    seen = set()
    for g in all_items:
        key = (g["name"].lower(), g["url"].lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(g)

    return uniq


def save_csv(items):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "platform", "coop_players", "has_pvp",
                         "year", "genre", "free2play", "url", "source"])
        for g in items:
            writer.writerow([
                g.get("name", ""),
                g.get("platform", ""),
                g.get("coop_players", ""),
                g.get("has_pvp", ""),
                g.get("year", ""),
                g.get("genre", ""),
                g.get("free2play", ""),
                g.get("url", ""),
                g.get("source", ""),
            ])


def main():
    print("[*] Building game_library.csv ...")
    items = collect_all()
    print(f"[*] Total unique games: {len(items)}")
    save_csv(items)
    print(f"[+] Saved to {OUT}")


if __name__ == "__main__":
    main()