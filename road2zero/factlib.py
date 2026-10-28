"""Faktabiblioteket: alla parametrar, tabeller, tidskurvor och källor som motorn använder.

Varje skalär parameter har id, värde, enhet, statusklass och källa. Tabeller (byggschabloner,
energiklasser, ytschabloner, kolförråd, kostprofiler m.fl.) bär en källkolumn. Källorna finns i
referenser.csv. Användaren kan skriva över skalära parametrar per scenario; motorn registrerar
vilka parametrar som faktiskt används.
"""
from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name, sep=";", dtype=str, keep_default_na=False)


class Kurva:
    """Styckvis linjär tidskurva med konstant förlängning före första och efter sista punkten."""

    def __init__(self, punkter: dict[float, float]):
        self.x = sorted(punkter)
        self.y = [punkter[k] for k in self.x]

    def __call__(self, t: float) -> float:
        x, y = self.x, self.y
        if t <= x[0]:
            return y[0]
        if t >= x[-1]:
            return y[-1]
        i = bisect_right(x, t)
        x0, x1, y0, y1 = x[i - 1], x[i], y[i - 1], y[i]
        return y0 + (y1 - y0) * (t - x0) / (x1 - x0)


@dataclass
class Faktabibliotek:
    parametrar: pd.DataFrame
    referenser: pd.DataFrame
    byggschabloner: pd.DataFrame
    reduktion: pd.DataFrame
    kurvor: pd.DataFrame
    energiklasser: pd.DataFrame
    ytschabloner: pd.DataFrame
    markpooler: pd.DataFrame
    bevarande: pd.DataFrame
    kostprofiler: pd.DataFrame
    ovrig: pd.DataFrame
    budget: pd.DataFrame
    befolkning: pd.DataFrame
    kommuner: pd.DataFrame
    skog: pd.DataFrame
    personbil: dict
    utveckling: pd.DataFrame
    _kurvcache: dict = field(default_factory=dict, repr=False)

    # ---------- skalära parametrar ----------
    def param(self, pid: str) -> float:
        if "_p" not in self._kurvcache:
            self._kurvcache["_p"] = dict(zip(self.parametrar["id"], self.parametrar["varde"]))
        try:
            return float(self._kurvcache["_p"][pid])
        except KeyError:
            raise KeyError(f"Okänd parameter: {pid}") from None

    def param_rad(self, pid: str) -> dict:
        return self.parametrar.loc[self.parametrar["id"] == pid].iloc[0].to_dict()

    # ---------- tidskurvor ----------
    def kurva(self, namn: str) -> Kurva:
        if namn not in self._kurvcache:
            d = self.kurvor[self.kurvor["kurva"] == namn]
            if d.empty:
                raise KeyError(f"Okänd kurva: {namn}")
            self._kurvcache[namn] = Kurva({float(a): float(v) for a, v in zip(d["ar"], d["varde"])})
        return self._kurvcache[namn]

    def reduktionskurva(self, kategori: str, stomme: str) -> Kurva:
        """Tabell A utökad: faktor relativt 2025 per byggnadskategori och stomme (för redovisning)."""
        key = ("red", kategori, stomme)
        if key not in self._kurvcache:
            d = self.reduktion[(self.reduktion["kategori"] == kategori) & (self.reduktion["stomme"] == stomme)]
            self._kurvcache[key] = Kurva({float(a): float(v) for a, v in zip(d["ar"], d["faktor"])}) if not d.empty else Kurva({2025.0: 1.0})
        return self._kurvcache[key]

    def skogskurva(self, namn: str) -> pd.DataFrame:
        d = self.skog[self.skog["kurva"] == namn]
        if d.empty:
            raise KeyError(f"Kurvan {namn} saknas i Skogskolmodellens bibliotek")
        return d

    # ---------- tabeller ----------
    def byggschablon(self, typ: str, stomme: str) -> float:
        d = self.byggschabloner[(self.byggschabloner["byggnadstyp"] == typ) & (self.byggschabloner["stomme"] == stomme)]
        if d.empty:
            d = self.byggschabloner[(self.byggschabloner["byggnadstyp"] == typ) & (self.byggschabloner["stomme"] == "generisk")]
        return float(d.iloc[0]["kg_co2e_m2"])

    def energikategori(self, typ: str) -> str:
        from .konstanter import ENERGIKATEGORI
        kat = ENERGIKATEGORI.get(typ, typ)
        return kat if (self.energiklasser["byggnadstyp"] == kat).any() else "övrig_byggnation"

    def energiklass(self, typ: str, klass: str) -> dict:
        typ_e = self.energikategori(typ)
        d = self.energiklasser[(self.energiklasser["byggnadstyp"] == typ_e) & (self.energiklasser["klass"] == klass)]
        if d.empty:
            d = self.energiklasser[self.energiklasser["byggnadstyp"] == typ_e].iloc[[0]]
        r = d.iloc[0]
        return {"kopt_fjarrvarme": float(r["kopt_fjarrvarme"]), "fastighetsel_fjv": float(r["fastighetsel_fjv"]),
                "el_eluppvarmd": float(r["el_eluppvarmd"]), "klass": r["klass"], "typ": typ_e, "kalla": r["kalla"]}

    def energiklasser_for(self, typ: str) -> list[str]:
        typ_e = self.energikategori(typ)
        return list(self.energiklasser.loc[self.energiklasser["byggnadstyp"] == typ_e, "klass"])

    def byggschablon_rad(self, typ: str, stomme: str) -> dict:
        d = self.byggschabloner[(self.byggschabloner["byggnadstyp"] == typ) & (self.byggschabloner["stomme"] == stomme)]
        if d.empty:
            d = self.byggschabloner[(self.byggschabloner["byggnadstyp"] == typ) & (self.byggschabloner["stomme"] == "generisk")]
        r = d.iloc[0].to_dict()
        r["kg_co2e_m2"] = float(r["kg_co2e_m2"])
        return r

    def ytschablon(self, typ: str, utforande: str) -> float:
        d = self.ytschabloner[(self.ytschabloner["anlaggningstyp"] == typ) & (self.ytschabloner["utforande"] == utforande)]
        return float(d.iloc[0]["t_co2e_m2"]) if not d.empty else 0.0

    def referens(self, rid: str) -> dict:
        d = self.referenser[self.referenser["id"] == rid]
        return d.iloc[0].to_dict() if not d.empty else {"id": rid, "kortnamn": rid, "titel": rid, "url": ""}


@lru_cache(maxsize=1)
def ladda() -> Faktabibliotek:
    return Faktabibliotek(
        parametrar=_csv("parametrar.csv"),
        referenser=_csv("referenser.csv"),
        byggschabloner=_csv("byggschabloner.csv"),
        reduktion=_csv("reduktionskurvor.csv"),
        kurvor=_csv("kurvor.csv"),
        energiklasser=_csv("energiklasser.csv"),
        ytschabloner=_csv("ytschabloner.csv"),
        markpooler=_csv("markpooler.csv"),
        bevarande=_csv("bevarande.csv"),
        kostprofiler=_csv("kostprofiler.csv"),
        ovrig=_csv("ovrig_konsumtion.csv"),
        budget=_csv("budget_forster2026.csv"),
        befolkning=_csv("befolkning_unwpp2024.csv"),
        kommuner=_csv("kommuner.csv"),
        skog=pd.read_csv(DATA / "skogskol_kurvbibliotek.csv", sep=";"),
        personbil=json.loads((DATA / "personbil_livscykel.json").read_text(encoding="utf-8")),
        utveckling=_csv("utveckling.csv"),
    )
