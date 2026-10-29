"""Bygger standardprojektet Jägersro (Svensk Travsports del) ur underlaget och sparar det som JSON.

Läser:
  underlag/jagersro_underlag.xlsx  BTA och byggnadsarea (BYA) per objekt (bladet "Indata per objekt")
  underlag/jagersro_markyta.webp   planskissen "Markyta per kategori"; ytan per färg mäts pixelvis och skalas till markytan

Skriver:
  road2zero/data/standardprojekt_jagersro.json   (appen startar med det)
  och, om en mapp anges som argument, samma fil där

Användning (från repots rot):
  python verktyg/jagersro.py [utmapp]

Antaganden, som alla går att ändra i appen efteråt:
  - Utbyggnad 2030–2045, jämnt fördelad. Stadsträd planteras i jämn takt samma år.
  - Varje byggnadstyp: 50 % Trä BÄST klass A, 25 % Betong BAU klass C, 25 % Betong BÄST klass A, fjärrvärme 100 %.
    Mobilitetshus är ouppvärmda och har ingen fjärrvärme.
  - Kvartersmarkens ytor minskas med byggnadernas BYA, så att bara gård, förgård och skolgård räknas som anläggning.
Kör alltid testerna efteråt: python -m pytest -q
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl
from PIL import Image

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT))

from road2zero.factlib import ladda  # noqa: E402
from road2zero.scenario import ny_andel, standard_mobilitet, till_json, tomt  # noqa: E402

EXCEL = ROT / "underlag" / "jagersro_underlag.xlsx"
KARTA = ROT / "underlag" / "jagersro_markyta.webp"
UT = ROT / "road2zero" / "data" / "standardprojekt_jagersro.json"

AR0, AR1 = 2030, 2045
MARKYTA = 401_000          # m², planskissens totala markyta
TRAD = 3000

# Undertyp i underlaget -> byggnadstyp i modellen
TYPER = {"bostad": "flerbostadshus", "radhus": "småhus", "kontor": "kontor", "skolbyggnad": "skola", "p-hus": "mobilitetshus"}
# (stomme, energiklass, andel) per byggnadstyp
FORDELNING = [("tra_bast", "A", 0.50), ("betong_bau", "C", 0.25), ("betong_bast", "A", 0.25)]

# Legendens färger i planskissen (RGB) och kartans utsnitt (x0, y0, x1, y1)
LEGEND = {
    "tomt": (242, 237, 225), "lss": (248, 200, 118), "skola": (137, 167, 109), "forskola": (187, 204, 153),
    "mobilitetshus": (240, 178, 183), "gangfart": (255, 221, 160), "urban_gron": (156, 158, 73), "park": (74, 121, 69),
    "natur": (99, 160, 130), "gator": (145, 174, 177), "gron_gangfart": (132, 139, 95),
}
UTSNITT = (590, 40, 1440, 640)
TROSKEL = 22               # största färgavstånd till legendfärgen


def las_byggnader() -> tuple[dict[str, float], dict[str, float]]:
    """BTA och BYA (m²) per modellens byggnadstyp."""
    ws = openpyxl.load_workbook(EXCEL, data_only=True)["Indata per objekt"]
    obj = defaultdict(dict)
    for fid, _namn, _kat, undertyp, _dim, par, varde, _enh, _kalla in list(ws.iter_rows(values_only=True))[1:]:
        obj[fid]["undertyp"] = undertyp
        obj[fid][par] = varde
    bta, bya = defaultdict(float), defaultdict(float)
    for o in obj.values():
        typ = TYPER.get(o["undertyp"])
        if typ:
            bta[typ] += float(o.get("BTA") or 0)
            bya[typ] += float(o.get("Area (geometri)") or 0)
    return dict(bta), dict(bya)


def mat_markytor() -> dict[str, float]:
    """m² per legendkategori: andel pixlar i planskissen gånger markytan."""
    im = Image.open(KARTA).convert("RGB")
    n = defaultdict(int)
    x0, y0, x1, y1 = UTSNITT
    for y in range(y0, y1):
        for x in range(x0, x1):
            p = im.getpixel((x, y))
            namn = min(LEGEND, key=lambda c: sum((a - b) ** 2 for a, b in zip(p, LEGEND[c])))
            if namn == "tomt" and p[0] - p[2] < 11:     # bakgrundskartan är grå, tomtytan krämvit
                continue
            if sum((a - b) ** 2 for a, b in zip(p, LEGEND[namn])) ** 0.5 < TROSKEL:
                n[namn] += 1
    tot = sum(n.values())
    return {c: n[c] / tot * MARKYTA for c in LEGEND}


def anlaggningsytor(m: dict[str, float], bya: dict[str, float]) -> list[tuple[str, str, float]]:
    bya_bost = bya.get("flerbostadshus", 0) + bya.get("småhus", 0) + bya.get("kontor", 0)
    ytor = [
        ("bostadsgard", "Tomtyta bostäder, handel och kontor samt LSS, utan byggnader", m["tomt"] + m["lss"] - bya_bost),
        ("skolgard", "Tomtyta skola och förskola, utan byggnader", m["skola"] + m["forskola"] - bya.get("skola", 0)),
        ("markparkering", "Tomtyta mobilitetshus, utan byggnader", m["mobilitetshus"] - bya.get("mobilitetshus", 0)),
        ("lokalgata", "Gator, torg och övrigt", m["gator"]),
        ("gc_vag", "Gångfartsgator och gröna gångfartsgator", m["gangfart"] + m["gron_gangfart"]),
        ("park", "Park, natur med dammar och urbana gröningar", m["park"] + m["natur"] + m["urban_gron"]),
    ]
    return [(t, namn, max(0.0, round(a, -1))) for t, namn, a in ytor]


def bygg() -> dict:
    fb = ladda()
    s = tomt(fb)
    s["projekt"].update(namn="Jägersro, Svensk Travsports del", kommun="Malmö", fas="Planprogram", startar=2026, slutar=2076)
    s["mobilitet"] = standard_mobilitet(fb, "Malmö")
    bta, bya = las_byggnader()
    for typ in TYPER.values():
        for stomme, klass, andel in FORDELNING:
            if typ == "mobilitetshus":
                klass = "Ouppvärmt"
            b = ny_andel(typ, stomme, round(bta[typ] * andel, 1), AR0, sista_ar=AR1, energiklass=klass)
            s["byggnader"].append(b)
    ytor = anlaggningsytor(mat_markytor(), bya)
    s["anlaggning"]["ytor"] = [{"typ": t, "utforande": "standard", "yta_m2": a, "forsta_ar": AR0, "sista_ar": AR1, "namn": namn}
                               for t, namn, a in ytor]
    per_ar = TRAD / (AR1 - AR0 + 1)
    s["negativa"]["trad"] = [{"antal": per_ar, "planteringsar": y} for y in range(AR0, AR1 + 1)]
    return s


def main():
    s = bygg()
    text = till_json(s)
    UT.write_text(text + "\n", encoding="utf-8")
    print(f"Skrev {UT.relative_to(ROT)}")
    if len(sys.argv) > 1:
        ut = Path(sys.argv[1]) / "Jagersro_standardprojekt.json"
        ut.write_text(text + "\n", encoding="utf-8")
        print(f"Skrev {ut}")
    bta = sum(b["bta"] for b in s["byggnader"])
    print(f"{len(s['byggnader'])} andelar, {bta:,.0f} m² BTA".replace(",", " "))
    for r in s["anlaggning"]["ytor"]:
        print(f"  {r['typ']:<14}{format(r['yta_m2'], ',.0f').replace(',', ' '):>10} m²  {r['namn']}")


if __name__ == "__main__":
    main()
