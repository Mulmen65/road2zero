"""Rättvis jämförelse av sparade fall från kommandoraden. Samma beräkning som fliken Rättvis jämförelse i road2zero-scenario
(road2zero/jamforelse.py beskriver metoden).

Användning (från repots rot):
  python verktyg/jamfor_stadsdelar.py fall/a.json fall/b.json fall/c.json [--referens 3] [--livslangd 50] [--m2-per-arbetsplats 20] [--ut jamforelse.xlsx]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT))
from road2zero import jamforelse as jm  # noqa: E402
from road2zero.factlib import ladda  # noqa: E402
from road2zero.scenario import fran_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("filer", nargs="+")
    ap.add_argument("--referens", type=int, default=0, help="1-baserat nummer på fallet vars fördelning boende/verksamheter används (0 = medel)")
    ap.add_argument("--livslangd", type=float, default=None)
    ap.add_argument("--m2-per-arbetsplats", type=float, default=None)
    ap.add_argument("--ut", default="")
    a = ap.parse_args()
    fb = ladda()
    fall = [fran_json(Path(f).read_text(encoding="utf-8"), fb) for f in a.filer]
    delar = []
    for lika, rubrik in ((True, "Lika förutsättningar"), (False, "Faktisk tidpunkt")):
        an = {s["projekt"]["namn"]: jm.analys(s, fb, a.livslangd, a.m2_per_arbetsplats, lika=lika) for s in fall}
        lista = list(an.values())
        w = lista[a.referens - 1]["andel_boende"] if a.referens else sum(x["andel_boende"] for x in lista) / len(lista)
        jm.standardisera(lista, w)
        t = jm.tabell(an)
        t.insert(0, "Perspektiv", rubrik)
        delar.append(t)
    df = pd.concat(delar, ignore_index=True)
    with pd.option_context("display.max_rows", 200, "display.width", 250, "display.max_colwidth", 70):
        print(df.to_string(index=False))
    if a.ut:
        ut = Path(a.ut)
        if ut.suffix == ".xlsx":
            with pd.ExcelWriter(ut, engine="openpyxl") as wr:
                df.to_excel(wr, sheet_name="Jämförelse", index=False)
                pd.DataFrame({"Metod": [r for r in jm.__doc__.splitlines() if r.strip()]}).to_excel(wr, sheet_name="Metod", index=False)
        else:
            df.to_csv(ut, sep=";", index=False, encoding="utf-8-sig")
        print("skrev", ut)


if __name__ == "__main__":
    main()
