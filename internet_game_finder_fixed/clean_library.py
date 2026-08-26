import csv
from pathlib import Path

BASE = Path(__file__).parent
SRC = BASE / "game_library.csv"
OUT = BASE / "game_library_clean.csv"

# Слова, по которым строка точно НЕ игра
BAD_NAMES = {
    "dlc",
    "д онаты",
    "донаты",
    "гайды",
    "гайд",
    "стримеры",
    "стример",
    "карта сайта",
    "политика конфиденциальности",
    "пользовательское соглашение",
    "о нас",
    "контакты",
    "реклама",
    "регистрация",
    "вход",
    "login",
    "sign up",
    "subscribe",
    "подписка",
    "блог",
    "новости",
    "статьи",
    "forum",
    "форум",
}


def is_good_game(name: str) -> bool:
    n = (name or "").strip().lower()
    if not n:
        return False
    if n in BAD_NAMES:
        return False
    # Отбрасываем очень короткие названия
    if len(n) < 3:
        return False
    # Отбрасываем типичные «служебные» штуки
    if any(b in n for b in ["карта сайта", "политика", "соглашение", "о нас", "контакты", "реклама"]):
        return False
    return True


def main():
    with SRC.open("r", encoding="utf-8", newline="") as f_in, \
         OUT.open("w", encoding="utf-8", newline="") as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
        writer.writeheader()

        total = 0
        kept = 0

        for row in reader:
            total += 1
            name = row.get("name", "")
            if not is_good_game(name):
                continue
            kept += 1
            writer.writerow(row)

    print(f"Total rows: {total}")
    print(f"Kept games: {kept}")
    print(f"Saved to: {OUT}")


if __name__ == "__main__":
    main()