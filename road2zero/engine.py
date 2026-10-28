"""Road2Zeros beräkningsmotor: berakna(scenario) -> Resultat.

Ordningen är fast: Byggnader ger invånare per år, som driver mobilitet, konsumtion och budget.
Resultatet är en lång tabell med en rad per år, klimatkategori, delpost och modul i ton CO2e.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .factlib import Faktabibliotek, ladda
from .kontext import Kontext
from .konstanter import KATEGORI_NAMN, NIVA
from .modules import anlaggning, budget, byggnader, konsumtion, mark, mobilitet, negativa
from .scenario import validera


@dataclass
class Resultat:
    scen: dict
    lang: pd.DataFrame                 # ar, kategori, delpost, modul, niva, t
    utanfor: pd.DataFrame              # undvikna utsläpp, separat
    invanare: dict
    budget: dict
    spar: pd.DataFrame
    anvanda: set
    anvanda_tabeller: set
    kontroller: list = field(default_factory=list)

    # ---------- sammanställningar ----------
    def per_ar_och_kategori(self) -> pd.DataFrame:
        if self.lang.empty:
            return pd.DataFrame(0.0, index=pd.Index(self.ar(), name="ar"), columns=KATEGORI_NAMN)
        p = self.lang.pivot_table(index="ar", columns="kategori", values="t", aggfunc="sum").reindex(index=self.ar(), columns=KATEGORI_NAMN).fillna(0.0)
        return p

    def ar(self) -> list[int]:
        return list(range(int(self.scen["projekt"]["startar"]), int(self.scen["projekt"]["slutar"]) + 1))

    def netto_per_niva(self) -> pd.DataFrame:
        p = self.per_ar_och_kategori()
        out = pd.DataFrame({"ar": p.index})
        for L in (1, 2, 3):
            cols = [c for c in KATEGORI_NAMN if NIVA[c] <= L]
            out[f"niva{L}"] = p[cols].sum(axis=1).values
        return out

    def totalt_per_kategori(self) -> pd.Series:
        return self.per_ar_och_kategori().sum(axis=0)

    def netto(self, niva: int) -> float:
        return float(self.netto_per_niva()[f"niva{niva}"].sum())

    def brutto_niva1(self) -> float:
        t = self.totalt_per_kategori()
        return float(sum(t[c] for c in KATEGORI_NAMN if NIVA[c] == 1 and c != "Negativa utsläpp"))

    def bta_totalt(self) -> float:
        from .scenario import takt
        return float(sum(sum(takt(b).values()) for b in self.scen["byggnader"]))

    def personar(self) -> float:
        return float(sum(self.invanare.values()))

    def nyckeltal(self) -> dict:
        t = self.totalt_per_kategori()
        bta = self.bta_totalt()
        ar = self.ar()
        n = self.netto_per_niva()
        full = max(self.invanare.values()) if self.invanare else 0.0
        ref = 2040 if 2040 in ar else ar[min(len(ar) - 1, 14)]
        rad = n[n["ar"] == ref]
        brutto = self.brutto_niva1()
        return {
            "netto": {L: self.netto(L) for L in (1, 2, 3)},
            "per_m2_niva1": self.netto(1) * 1000 / bta if bta else 0.0,
            "invanare_full": full,
            "ref_ar": ref,
            "per_inv_ref": {L: (float(rad[f"niva{L}"].iloc[0]) / self.invanare.get(ref, 0) if self.invanare.get(ref, 0) else 0.0) for L in (1, 2, 3)},
            "negativa": float(t["Negativa utsläpp"]),
            "negativ_andel": -float(t["Negativa utsläpp"]) / brutto if brutto else 0.0,
            "brutto_niva1": brutto,
            "bta": bta,
            "personar": self.personar(),
            "undvikna": float(self.utanfor["t"].sum()) if not self.utanfor.empty else 0.0,
        }


def berakna(scen: dict, fb: Faktabibliotek | None = None) -> Resultat:
    fb = fb or ladda()
    k = Kontext(fb=fb, scen=scen)
    inv = byggnader.berakna(k)
    anlaggning.berakna(k)
    mark.berakna(k)
    negativa.berakna(k)
    mobilitet.berakna(k, inv)
    konsumtion.berakna(k, inv)
    lang = pd.DataFrame(k.rader, columns=["ar", "kategori", "delpost", "modul", "t"])
    if not lang.empty:
        lang = lang.groupby(["ar", "kategori", "delpost", "modul"], as_index=False)["t"].sum()
        lang["niva"] = lang["kategori"].map(NIVA)
    else:
        lang["niva"] = []
    res = Resultat(scen=scen, lang=lang, utanfor=pd.DataFrame(k.utanfor, columns=["ar", "delpost", "modul", "t"]),
                   invanare=inv, budget={}, spar=pd.DataFrame(), anvanda=k.anvanda, anvanda_tabeller=k.anvanda_tabeller,
                   kontroller=validera(scen, fb))
    res.budget = budget.berakna(k, inv, res.netto_per_niva())
    res.spar = pd.DataFrame(k.spar, columns=["modul", "rubrik", "varde", "enhet", "kommentar"])
    res.anvanda = k.anvanda
    res.anvanda_tabeller = k.anvanda_tabeller
    return res
