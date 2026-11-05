"""DeSO-underlag för kartorna och mobiliteten i alla Road2Zero-modeller.

Läser gemensamt/data/vagvis_deso.json, som verktyg/hamta_vagvis.py skriver ur Vägvis 2.3.1 (repot Mulmen65/vagvisa):
hushåll, invånare och personbilar per DeSO (SCB 2024), körsträcka per bil (Vägvis modell B) och DeSO-polygoner (SCB DeSO 2025).
Modulen använder inte Streamlit, så att den kan testas och användas av skript.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

FIL = Path(__file__).resolve().parent / "data" / "vagvis_deso.json"


@lru_cache(maxsize=1)
def data() -> dict:
    return json.loads(FIL.read_text(encoding="utf-8"))


def kalla() -> dict:
    """Versionsuppgifter och källa per fält."""
    return data()["kalla"]


def kommuner() -> dict[str, str]:
    """Kommunkod → kommunnamn för kommunerna med DeSO-underlag."""
    return dict(data()["kommuner"])


def kommunkod(namn: str) -> str | None:
    for kod, n in kommuner().items():
        if n.lower() == str(namn).strip().lower():
            return kod
    return None


@lru_cache(maxsize=1)
def per_kod() -> dict[str, dict]:
    return {d["kod"]: d for d in data()["deso"]}


def deso(kommun: str | None = None) -> list[dict]:
    """Alla DeSO, eller en kommuns, sorterade på RegSO-namn och kod."""
    rader = [d for d in data()["deso"] if kommun in (None, "", d["kommun"])]
    return sorted(rader, key=lambda d: (d["namn"] or "", d["kod"]))


def etikett(kod: str) -> str:
    """Fast etikett för en DeSO i rullistor: kod och RegSO-namn."""
    d = per_kod().get(kod)
    return f"{kod} · {d['namn']}" if d else kod


def regso(kommun: str) -> dict[str, list[str]]:
    """RegSO-namn → DeSO-koder i kommunen."""
    ut: dict[str, list[str]] = {}
    for d in deso(kommun):
        ut.setdefault(d["namn"] or d["regso"], []).append(d["kod"])
    return ut


def giltiga(koder) -> list[str]:
    """Bara koder som finns i underlaget, i samma ordning och utan dubbletter."""
    finns, ut = per_kod(), []
    for k in koder or []:
        if k in finns and k not in ut:
            ut.append(k)
    return ut


def summera(koder) -> dict | None:
    """Summa för valda DeSO: hushåll, invånare och bilar; bilar per hushåll = Σ bilar / Σ hushåll;
    körsträcka per bil viktad med antalet bilar. None om inga giltiga DeSO är valda."""
    rader = [per_kod()[k] for k in giltiga(koder)]
    if not rader:
        return None
    hh = sum(r["hushall"] for r in rader)
    bilar = sum(r["bilar"] for r in rader)
    inv = sum(r["invanare"] for r in rader)
    km = sum(r["bilar"] * r["km_per_bil"] for r in rader) / bilar if bilar else 0.0
    return {"antal": len(rader), "hushall": hh, "invanare": inv, "bilar": bilar,
            "bilar_per_hushall": bilar / hh if hh else 0.0, "km_per_bil": km,
            "personer_per_hushall": inv / hh if hh else 0.0}


def kommun_for(koder) -> str | None:
    k = giltiga(koder)
    return per_kod()[k[0]]["kommun"] if k else None


def mitt(koder) -> tuple[float, float] | None:
    rader = [per_kod()[k] for k in giltiga(koder)]
    if not rader:
        return None
    return sum(r["lat"] for r in rader) / len(rader), sum(r["lon"] for r in rader) / len(rader)


def _i_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inne = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inne = not inne
        j = i
    return inne


def hitta(lat: float, lon: float, kommun: str | None = None) -> str | None:
    """DeSO som en punkt ligger i (jämnt–udda-regeln över alla ringar, så att hål räknas rätt)."""
    for d in deso(kommun):
        if sum(_i_ring(lon, lat, r) for r in d["ringar"]) % 2 == 1:
            return d["kod"]
    return None
