"""Emissionsfaktorernas utveckling över tid: procentuell förändring per år och period, 2027–2100.

Varje faktor har en årlig förändring i procent per period (negativt = minskning). Index 2026 = 1, och
index(t) = index(t−1) · (1 + r(t)/100) från 2027. För el- och laddhybridbilarnas andel av körsträckan
anges förändringen i procentenheter per år. Standardvärdena står i data/utveckling.csv med källa.
"""
from __future__ import annotations

from .factlib import Faktabibliotek

BASAR = 2026
SLUTAR = 2100
PERIODER = [(2027, 2030), (2031, 2035), (2036, 2040), (2041, 2045), (2046, 2050), (2051, 2060), (2061, 2070), (2071, 2100)]
PERIODNAMN = [f"{a}–{b}" for a, b in PERIODER]
PERIODKOL = [f"p{a}_{b}" for a, b in PERIODER]
PROCENTENHETER = {"bev", "phev"}           # andelar som ändras i procentenheter per år
# Äldre faktornamn för stommar i sparade indata
MIGRERING = {"bygg.betong": "bygg.betong_bau", "bygg.klimatförbättrad_betong": "bygg.betong_bast", "bygg.stål": "bygg.stal_bau",
             "bygg.klimatförbättrat_stål": "bygg.stal_bast", "bygg.trä": "bygg.tra_bau", "bygg.klimatförbättrat_trä": "bygg.tra_bast"}
KOPPLINGAR = {"anl": ("anl_foljer_betong", "bygg.betong_bau"), "ovrig": ("ovrig_foljer_bilprod", "bilprod")}


def standard(fb: Faktabibliotek) -> dict:
    """Standardtakter ur faktabiblioteket."""
    return {
        "takt": {r["faktor"]: [float(r[c]) for c in PERIODKOL] for _, r in fb.utveckling.iterrows()},
        "anl_foljer_betong": True,
        "ovrig_foljer_bilprod": True,
    }


def period_for(y: int) -> int | None:
    for i, (a, b) in enumerate(PERIODER):
        if a <= y <= b:
            return i
    return None


class Utveckling:
    """Index per faktor och år, byggt ur indata (eller standard när en faktor saknas)."""

    def __init__(self, fb: Faktabibliotek, scen: dict):
        u = scen.get("utveckling") or {}
        std = standard(fb)
        self.takt: dict[str, list[float]] = {f: list(v) for f, v in std["takt"].items()}
        for f, v in (u.get("takt") or {}).items():
            f = MIGRERING.get(f, f)
            if f in self.takt and len(v) == len(PERIODER):
                self.takt[f] = [float(x or 0) for x in v]
        for f, (flagga, kalla) in KOPPLINGAR.items():
            if u.get(flagga, std[flagga]):
                self.takt[f] = list(self.takt[kalla])
        self.takt["bygg.generisk"] = list(self.takt["bygg.betong_bau"])   # Generisk = Betong BAU
        self._cache: dict[str, dict[int, float]] = {}

    def arstakt(self, faktor: str, y: int) -> float:
        i = period_for(y)
        return self.takt[faktor][i] if i is not None else 0.0

    def _serie(self, faktor: str) -> dict[int, float]:
        if faktor not in self._cache:
            s = {BASAR: 1.0 if faktor not in PROCENTENHETER else 0.0}
            v = s[BASAR]
            for y in range(BASAR + 1, SLUTAR + 1):
                r = self.arstakt(faktor, y)
                v = v + r / 100 if faktor in PROCENTENHETER else v * max(0.0, 1 + r / 100)
                s[y] = v
            self._cache[faktor] = s
        return self._cache[faktor]

    def index(self, faktor: str, y: int) -> float:
        """Index relativt 2026 (1 = startvärdet)."""
        s = self._serie(faktor)
        return s[min(max(int(y), BASAR), SLUTAR)]

    def tillskott(self, faktor: str, y: int) -> float:
        """Ackumulerad förändring i andel (0–1) sedan 2026, för faktorer i procentenheter."""
        return self.index(faktor, y)
