"""Läser Vägvis 2.3.1 (filen vagvis_data.json i repot Mulmen65/vagvisa) och skriver gemensamt/data/vagvis_deso.json.

Filen ger alla Road2Zero-modeller samma DeSO-underlag:
  - hushåll, invånare och personbilar per DeSO (SCB, 2024) och bilar per hushåll,
  - körsträcka per bil: kommunvärdet i Vägvis modell B (riksmedel 12 753 km × kommunens kvot mot riket enligt RUS/SCB
    körsträckedata), samma för alla DeSO i kommunen,
  - DeSO-polygoner (SCB DeSO 2025) förenklade till cirka 5 m, för kartorna,
  - RegSO-namn för att hitta områden.

Användning (från repots rot):
  python verktyg/hamta_vagvis.py sökväg/till/vagvis_data.json
Vägvis själv ändras inte. Kör om skriptet när Vägvis får nya data.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
UT = ROT / "gemensamt" / "data" / "vagvis_deso.json"
SKALA = 1_000_000            # Vägvis packar koordinater som heltal i miljondelar av grader
TOLERANS = 0.00005           # Douglas–Peucker i grader, cirka 5 m


def packa_upp(ring: list[int]) -> list[list[float]]:
    """Vägvis-pack-1: första paret är absolut, resten är skillnader."""
    x, y = ring[0], ring[1]
    ut = [[x / SKALA, y / SKALA]]
    for i in range(2, len(ring), 2):
        x += ring[i]; y += ring[i + 1]
        ut.append([x / SKALA, y / SKALA])
    return ut


def _avstand(p, a, b) -> float:
    if a == b:
        return math.dist(p, a)
    (x, y), (x1, y1), (x2, y2) = p, a, b
    return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / math.dist(a, b)


def forenkla(pts: list[list[float]], tol: float = TOLERANS) -> list[list[float]]:
    """Douglas–Peucker utan rekursion."""
    if len(pts) < 5:
        return pts
    behall = [False] * len(pts); behall[0] = behall[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        dmax, k = 0.0, None
        for m in range(i + 1, j):
            d = _avstand(pts[m], pts[i], pts[j])
            if d > dmax:
                dmax, k = d, m
        if k is not None and dmax > tol:
            behall[k] = True
            stack += [(i, k), (k, j)]
    ut = [[round(x, 5), round(y, 5)] for p, ok in zip(pts, behall) if ok for x, y in [p]]
    return ut if len(ut) >= 4 else [[round(x, 5), round(y, 5)] for x, y in pts]


def main():
    kalla = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not kalla or not kalla.exists():
        raise SystemExit("Ange sökvägen till vagvis_data.json (repot Mulmen65/vagvisa).")
    paket = json.loads(kalla.read_text(encoding="utf-8"))
    filer = paket["files"]
    hush = json.loads(filer["kallkod/data/household-project.json"])
    omr = json.loads(filer["kallkod/data/omraden.json"])
    geom = {}
    for props, (typ, ringar) in omr["deso"]:
        if typ != "P":
            continue
        geom[props["id"]] = [forenkla(packa_upp(r)) for r in ringar]
    kommuner = {c["id"]: c["name"] for c in hush["cities"]}
    deso = []
    for r in hush["d"]:
        if r["kod"] not in geom:
            continue
        deso.append({"kod": r["kod"], "kommun": r["kk"], "regso": r["rs"], "namn": r.get("regsoName") or r.get("name"),
                     "hushall": r["hh"], "invanare": r["bef"], "bilar": r["bil"], "bilar_per_hushall": round(r["bph"], 4),
                     "km_per_bil": r["km"], "lat": round(r["lat"], 5), "lon": round(r["lon"], 5), "ringar": geom[r["kod"]]})
    m = hush["metadata"]
    ut = {
        "kalla": {"modell": "Vägvis", "version": paket.get("modelVersion"), "paketerad": paket.get("packagedDate"),
                  "repo": "https://github.com/Mulmen65/vagvisa", "dataar": m.get("dataYear"), "deso_version": m.get("desoVersion"),
                  "falt": {"bilar": "SCB TAB6589, personbilar i trafik per DeSO 31 december", "hushall": "SCB TAB6568",
                           "invanare": "SCB TAB6574", "km_per_bil": "Vägvis modell B, kommunvärde: 12 753 km × kommunens kvot mot riket (RUS/SCB körsträckedata, tabell 2); "
                                         "samma värde för alla DeSO i kommunen",
                           "geometri": "SCB DeSO 2025, förenklad till cirka 5 m"}},
        "kommuner": kommuner,
        "deso": deso,
    }
    UT.parent.mkdir(parents=True, exist_ok=True)
    UT.write_text(json.dumps(ut, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    punkter = sum(len(r) for d in deso for r in d["ringar"])
    print(f"Skrev {UT.relative_to(ROT)}: {len(deso)} DeSO i {len(kommuner)} kommuner, {punkter} punkter, {UT.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
