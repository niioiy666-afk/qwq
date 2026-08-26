import re

EXACT_EXCLUDE = [
    "stalker 2",
    "s.t.a.l.k.e.r. 2",
]

STRONG_COOP = [
    "co-op",
    "coop",
    "cooperative",
    "online co-op",
    "local co-op",
    "couch co-op",
    "split-screen",
    "split screen",
    "shared screen",
    "shared-screen",
    "campaign co-op",
    "story co-op",
    "lan co-op",
    "drop-in/drop-out",
    "drop-in",
    "drop out",
    "play together",
    "team up",
    "кооператив",
    "совместное прохождение",
]

MEDIUM_COOP = [
    "multiplayer co-op",
    "co-op mode",
    "co-op campaign",
    "co-op adventure",
    "online multiplayer",
    "local multiplayer",
    "lan multiplayer",
    "party game",
    "мультиплеер",
]

PLAYER_HINTS = [
    "2 player", "3 player", "4 player", "5 player", "6 player", "7 player", "8 player",
    "up to 2", "up to 3", "up to 4", "up to 5", "up to 6", "up to 7", "up to 8",
    "2-4 players", "2-8 players", "supports 2", "supports 3", "supports 4",
    "supports 5", "supports 6", "supports 7", "supports 8",
    "для 2", "для 3", "для 4", "для 5", "для 6", "для 7", "для 8",
    "кооператив для 2", "кооператив для 3", "кооператив для 4",
    "кооп для 2", "кооп для 3", "кооп для 4",
]

LOCAL_HINTS = [
    "local co-op", "couch co-op", "split-screen", "split screen",
    "shared screen", "shared-screen", "lan co-op", "lan multiplayer",
    "local multiplayer",
]

ONLINE_HINTS = [
    "online co-op", "online multiplayer", "internet co-op",
]

NEGATIVE = [
    "pvp",
    "player vs player",
    "versus",
    "competitive",
    "ranked",
    "deathmatch",
    "team deathmatch",
    "battle royale",
    "solo only",
    "singleplayer only",
    "single-player only",
    "single player only",
    "соревновательный мультиплеер",
]

def _norm(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def _contains(text, terms):
    return any(term in text for term in terms)

def _text(item):
    parts = [
        item.get("name", ""),
        item.get("title", ""),
        item.get("text", ""),
        item.get("description", ""),
        item.get("url", ""),
    ]
    return _norm(" ".join(str(p) for p in parts if p))

def _score(item):
    text = _text(item)
    score = 0
    reasons = []

    if _contains(text, EXACT_EXCLUDE):
        return -999, ["excluded title"]

    if _contains(text, STRONG_COOP):
        score += 6
        reasons.append("strong co-op signal")

    if _contains(text, LOCAL_HINTS):
        score += 4
        reasons.append("local co-op signal")

    if _contains(text, ONLINE_HINTS):
        score += 3
        reasons.append("online co-op signal")

    if _contains(text, MEDIUM_COOP):
        score += 2
        reasons.append("co-op/multiplayer signal")

    if _contains(text, PLAYER_HINTS):
        score += 1
        reasons.append("player count signal")

    if "campaign" in text and ("co-op" in text or "coop" in text or "кооператив" in text):
        score += 2
        reasons.append("campaign co-op")

    if "story" in text and ("co-op" in text or "coop" in text or "кооператив" in text):
        score += 2
        reasons.append("story co-op")

    if _contains(text, NEGATIVE):
        score -= 5
        reasons.append("competitive/PvP signal")

    if "multiplayer" in text and not _contains(text, STRONG_COOP + LOCAL_HINTS + ONLINE_HINTS):
        score -= 1
        reasons.append("generic multiplayer only")

    return score, reasons

def pick_games(links, cfg=None):
    if not isinstance(links, list):
        return []

    max_results = 25
    if isinstance(cfg, dict):
        try:
            max_results = int(cfg.get("max_results", max_results))
        except Exception:
            pass

    results = []
    seen = set()

    for item in links:
        if not isinstance(item, dict):
            continue

        name = (item.get("name") or item.get("title") or item.get("text") or "").strip()
        url = (item.get("url") or item.get("href") or "").strip()
        if not name and not url:
            continue

        key = (name or url).lower()
        if key in seen:
            continue
        seen.add(key)

        text = _text(item)
        score, reasons = _score(item)

        # Жёсткое правило: если есть PvP и нет коопа — отбрасываем
        has_pvp = _contains(text, NEGATIVE)
        has_coop = _contains(text, STRONG_COOP)
        if has_pvp and not has_coop:
            continue

        if score < 3:
            continue

        has_strong = _contains(text, STRONG_COOP)
        has_local = _contains(text, LOCAL_HINTS)
        has_online = _contains(text, ONLINE_HINTS)

        if score >= 8:
            confidence = "high"
        elif score >= 5:
            confidence = "medium"
        else:
            confidence = "low"

        out = dict(item)
        out["name"] = name or url
        out["url"] = url
        out["confidence"] = confidence
        out["reason"] = ", ".join(reasons) if reasons else "possible co-op match"
        results.append(out)

    results.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("confidence", "low"), 2))
    return results[:max_results]