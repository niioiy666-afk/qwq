import json
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

BASE = Path(__file__).parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
SESSION_FILE = BASE / "session_cache.json"
LIB_FILE = BASE / "my_games.csv"
LIBRARY_FILE = BASE / "game_library.csv"
OUT_FILE = BASE / "recommendations.csv"


def load_session():
    if SESSION_FILE.exists():
        try:
            return set(json.loads(SESSION_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def save_session(s):
    SESSION_FILE.write_text(
        json.dumps(sorted(s), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_csv(path):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if len(lines) <= 1:
        return []
    out = []
    for line in lines[1:]:
        parts = line.split(",")
        if parts and parts[0].strip():
            out.append(
                {
                    "name": parts[0].strip(),
                    "url": parts[-1].strip() if len(parts) >= 2 else "",
                }
            )
    return out


def save_csv(path, games):
    lines = ["name,confidence,reason,url"]
    for g in games:
        lines.append(
            f"{g.get('name', '').replace(',', ' ')},"
            f"{g.get('confidence', '')},"
            f"{g.get('reason', '').replace(',', ' ')},"
            f"{g.get('url', '').replace(',', '%2C')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_library():
    games = []
    if not LIBRARY_FILE.exists():
        return games

    lines = LIBRARY_FILE.read_text(encoding="utf-8-sig").splitlines()
    if len(lines) <= 1:
        return games

    headers = [h.strip() for h in lines[0].split(",")]
    idx_map = {name: i for i, name in enumerate(headers)}

    def get(parts, key, default=""):
        idx = idx_map.get(key)
        if idx is None or idx >= len(parts):
            return default
        return parts[idx].strip()

    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(",")

        name = get(parts, "name")
        if not name:
            continue

        games.append(
            {
                "name": name,
                "platform": get(parts, "platform"),
                "coop_players": get(parts, "coop_players"),
                "has_pvp": get(parts, "has_pvp"),
                "year": get(parts, "year"),
                "genre": get(parts, "genre"),
                "free2play": get(parts, "free2play"),
                "url": get(parts, "url"),
            }
        )

    return games


def base_name(name: str) -> str:
    n = (name or "").strip()
    markers = [
        " Edition",
        " Remastered",
        " Remake",
        " Ultimate Edition",
        " Definitive Edition",
        " Enhanced Edition",
        " Complete Edition",
        " Anniversary Edition",
        " Special Edition",
        " Collector's Edition",
        " Game of the Year Edition",
        " Legendary Edition",
        " Deluxe Edition",
        " Premium Edition",
        " Physical Edition",
        " Digital Edition",
    ]
    for m in markers:
        idx = n.lower().find(m.lower())
        if idx != -1:
            n = n[:idx]
            break
    return n.strip()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Internet Game Finder AI (Library mode)")
        self.geometry("1050x720")
        self.minsize(1050, 720)

        self.session = {bn for bn in load_session()}
        self.results = []
        self.category = tk.StringVar(value="coop")
        self.mode = tk.StringVar(value="smart")
        self.status = tk.StringVar(value="Ready")
        self.searching = False

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Category:").pack(side="left")
        self.cat_box = ttk.Combobox(
            top,
            textvariable=self.category,
            values=list(CFG["sources"].keys()),
            state="readonly",
            width=14,
        )
        self.cat_box.pack(side="left", padx=6)

        ttk.Label(top, text="Mode:").pack(side="left", padx=(10, 0))
        self.mode_box = ttk.Combobox(
            top,
            textvariable=self.mode,
            values=["smart", "random"],
            state="readonly",
            width=10,
        )
        self.mode_box.pack(side="left", padx=6)

        self.search_btn = ttk.Button(top, text="Search", command=self.search)
        self.search_btn.pack(side="left", padx=6)
        self.reset_btn = ttk.Button(top, text="Reset session", command=self.reset_session)
        self.reset_btn.pack(side="left", padx=6)
        self.add_btn = ttk.Button(top, text="Add selected", command=self.add_selected)
        self.add_btn.pack(side="left", padx=6)

        body = ttk.Frame(self, padding=(10, 0, 10, 10))
        body.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(body, font=("Segoe UI", 11), selectmode="extended")
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status).pack(side="left")

    def set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.search_btn.config(state=state)
        self.reset_btn.config(state=state)
        self.add_btn.config(state=state)
        self.cat_box.config(state="disabled" if busy else "readonly")
        self.mode_box.config(state="disabled" if busy else "readonly")

    def search(self):
        if self.searching:
            return
        self.searching = True
        self.set_busy(True)
        self.status.set("Searching in local library...")
        threading.Thread(target=self._search_worker, daemon=True).start()

    def _search_worker(self):
        try:
            # Игры, которые уже в my_games.csv (по базовому имени)
            lib_names = {base_name(x["name"]).lower() for x in load_csv(LIB_FILE)}
            gathered = []

            all_games = load_library()
            total = len(all_games)
            self.after(
                0,
                lambda t=total: self.status.set(f"Searching in local library ({t} games)..."),
            )

            seen_base = set()

            for g in all_games:
                bn = base_name(g["name"]).lower()
                if bn in self.session or bn in lib_names or bn in seen_base:
                    continue
                seen_base.add(bn)

                # Простая уверенность и причина (без ai_filter)
                coop_players = (g.get("coop_players") or "").strip()
                has_pvp = (g.get("has_pvp") or "").strip().lower()
                genre = (g.get("genre") or "").strip()

                if coop_players and has_pvp != "yes":
                    confidence = "high"
                elif coop_players and has_pvp == "yes":
                    confidence = "medium"
                else:
                    confidence = "low"

                reason_parts = []
                if coop_players:
                    reason_parts.append(f"coop for {coop_players} players")
                if has_pvp == "yes":
                    reason_parts.append("has PvP modes")
                if genre:
                    reason_parts.append(f"genre: {genre}")
                if not reason_parts:
                    reason_parts.append("from local library")

                reason = ", ".join(reason_parts)

                gathered.append(
                    {
                        "name": g["name"],
                        "confidence": confidence,
                        "reason": reason,
                        "url": g.get("url", ""),
                    }
                )

            if self.mode.get() == "random":
                random.shuffle(gathered)

            gathered = gathered[:CFG.get("max_results", 25)]

            def finish():
                self.results = gathered
                self.listbox.delete(0, tk.END)
                for i, g in enumerate(gathered, 1):
                    self.listbox.insert(
                        tk.END, f"{i}. {g['name']}  [{g['confidence']}]  {g['url']}"
                    )
                save_csv(OUT_FILE, gathered)
                self.session.update(base_name(g["name"]).lower() for g in gathered)
                save_session(self.session)
                self.status.set(
                    f"Found {len(gathered)} games from local library. Saved to recommendations.csv"
                )
                self.set_busy(False)
                self.searching = False

            self.after(0, finish)

        except Exception as e:
            def fail():
                messagebox.showerror("Search error", str(e))
                self.status.set(f"Fatal error: {e}")
                self.set_busy(False)
                self.searching = False

            self.after(0, fail)

    def reset_session(self):
        self.session.clear()
        save_session(self.session)
        self.listbox.delete(0, tk.END)
        self.status.set("Session cleared")

    def add_selected(self):
        idxs = self.listbox.curselection()
        if not idxs:
            return messagebox.showinfo("Add", "Select games first")

        existing = load_csv(LIB_FILE)
        known = {base_name(x["name"]).lower() for x in existing}
        added = 0

        for idx in idxs:
            g = self.results[idx]
            bn = base_name(g["name"]).lower()
            if bn in known:
                continue
            existing.append(g)
            known.add(bn)
            added += 1

        LIB_FILE.write_text(
            "name,url\n"
            + "\n".join(
                f"{x['name'].replace(',', ' ')},{x.get('url', '').replace(',', '%2C')}"
                for x in existing
            )
            + "\n",
            encoding="utf-8",
        )
        self.status.set(f"Added {added} games to my_games.csv")
        messagebox.showinfo("Add", f"Added {added} games")


if __name__ == "__main__":
    App().mainloop()