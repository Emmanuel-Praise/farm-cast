"""Offline gazetteer: normalise, alias expansion, fuzzy match (Levenshtein <= 2)."""
from __future__ import annotations
import csv
import os
import unicodedata
from dataclasses import dataclass


@dataclass
class GazetteerEntry:
    name: str
    division: str
    lat: float
    lon: float
    elevation_m: int
    aliases: list


def normalise(s: str) -> str:
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    # collapse spaces
    s = " ".join(s.split())
    # known alias expansions
    expansions = {
        "bamenda city": "bamenda",
        "ndop plain": "ndop",
        "baba 1": "baba i",
    }
    return expansions.get(s, s)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


class Gazetteer:
    def __init__(self):
        self.entries: list[GazetteerEntry] = []
        self._index: dict[str, GazetteerEntry] = {}  # normalised name/alias -> entry

    def load_csv(self, path: str) -> int:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aliases = [a.strip() for a in (row.get("aliases") or "").split(";") if a.strip()]
                e = GazetteerEntry(
                    name=row["name"].strip(),
                    division=(row.get("division") or "").strip(),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    elevation_m=int(float(row.get("elevation_m") or 0)),
                    aliases=aliases,
                )
                self.entries.append(e)
                self._index[normalise(e.name)] = e
                for a in aliases:
                    self._index.setdefault(normalise(a), e)
        return len(self.entries)

    def exact(self, query: str) -> GazetteerEntry | None:
        return self._index.get(normalise(query))

    def fuzzy(self, query: str, max_dist: int = 2) -> GazetteerEntry | None:
        q = normalise(query)
        best, best_d = None, max_dist + 1
        for key, entry in self._index.items():
            d = levenshtein(q, key)
            if d < best_d:
                best, best_d = entry, d
                if d == 0:
                    break
        return best if best_d <= max_dist else None


_default_gazetteer: Gazetteer | None = None


def get_default_gazetteer(seed_path: str | None = None) -> Gazetteer:
    global _default_gazetteer
    if _default_gazetteer is not None:
        return _default_gazetteer
    g = Gazetteer()
    candidates = []
    if seed_path:
        candidates.append(seed_path)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(base, "config", "localities_seed.csv"))
    candidates.append(os.path.join(os.getcwd(), "farmcast", "config", "localities_seed.csv"))
    candidates.append(os.path.join(os.getcwd(), "config", "localities_seed.csv"))
    for c in candidates:
        if c and os.path.exists(c):
            g.load_csv(c)
            break
    _default_gazetteer = g
    return g
