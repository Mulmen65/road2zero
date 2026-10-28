"""Modul 3 Förändrad markanvändning: kolförlust per pool, förlorat skogsupptag, ny skog och förgröning.

Skog räknas med Skogskolmodellen 10.4 (förberäknat kurvbibliotek). Öppen mark kompletteras med
kolförråd per pool (SOC, DOM, biomassa) där riksgenomsnittet är standard och användaren kan ange egna värden.
"""
from __future__ import annotations

from ..kontext import Kontext
from ..konstanter import (FORGRONING_FRAN, FORGRONING_TILL, SKOGSTYPER, SKOTSEL, TIDIGARE_MARK_FOR_SKOG, TRADSLAG)

MODUL = "3 Förändrad markanvändning"


def pooler(k: Kontext, marktyp: str, alder: int = 40) -> dict:
    """Kolförråd i t C/ha per pool för en marktyp."""
    egna = k.scen["mark"].get("pooler", {}).get(marktyp)
    if egna:
        return {p: float(egna[p]) for p in ("soc", "dom", "bio")}
    if marktyp in SKOGSTYPER:
        k.tabell("skogskol_kurvbibliotek")
        alder = 80 if int(alder or 40) >= 60 else 40
        d = k.fb.skogskurva(f"befintlig_skog|forest|{SKOGSTYPER[marktyp]}|natural|{alder}")
        tot = float(d.loc[d["ar"] == 0, "projekt_ekosystem_tC_ha"].iloc[0])
        return {"soc": tot * k.p("mark.skog_andel_soc"), "dom": tot * k.p("mark.skog_andel_dom"),
                "bio": tot * k.p("mark.skog_andel_bio")}
    k.tabell("markpooler")
    r = k.fb.markpooler[k.fb.markpooler["marktyp"] == marktyp].iloc[0]
    return {"soc": float(r["soc_tc_ha"]), "dom": float(r["dom_tc_ha"]), "bio": float(r["bio_tc_ha"])}


def bevarat(k: Kontext, o: dict) -> dict:
    if all(o.get(f"bevarat_{p}") not in (None, "") for p in ("soc", "dom", "bio")):
        return {p: float(o[f"bevarat_{p}"]) / 100 for p in ("soc", "dom", "bio")}
    egna = k.scen["mark"].get("bevarande", {}).get(o["till"])
    if egna:
        return {p: float(egna[p]) / 100 for p in ("soc", "dom", "bio")}
    k.tabell("bevarande")
    r = k.fb.bevarande[k.fb.bevarande["till_markanvandning"] == o["till"]].iloc[0]
    return {p: float(r[p]) / 100 for p in ("soc", "dom", "bio")}


def berakna(k: Kontext):
    c2co2 = k.p("allm.c_till_co2")
    for o in k.scen["mark"]["overgangar"]:
        ha = float(o.get("ha") or 0)
        ar = int(o.get("ar") or k.ar[0])
        if ha <= 0:
            continue
        rubrik = f"{o['fran']} → {o['till']}"
        if o["till"] == "Bevarad":
            k.steg(MODUL, rubrik, 0, "t CO2e", f"{ha:g} ha bevaras, ingen förändring")
            continue
        pl = pooler(k, o["fran"], o.get("skogsalder", 40))
        bv = bevarat(k, o)
        forlust = ha * sum(pl[p] * (1 - bv[p]) for p in pl) * c2co2
        k.add("Förändrad markanvändning", "Kolförlust", MODUL, ar, forlust)
        k.steg(MODUL, f"{rubrik}: kolförlust", round(forlust, 1), "t CO2",
               f"{ha:g} ha × (SOC {pl['soc']:.0f}·{1-bv['soc']:.0%} + DOM {pl['dom']:.0f}·{1-bv['dom']:.0%} + bio {pl['bio']:.0f}·{1-bv['bio']:.0%}) t C/ha × 44/12")
        # förlorat framtida upptag när skog avverkas
        if o["fran"] in SKOGSTYPER and bv["bio"] < 1:
            h = int(k.p("mark.horisont"))
            alder = 80 if int(o.get("skogsalder") or 40) >= 60 else 40
            d = k.fb.skogskurva(f"befintlig_skog|forest|{SKOGSTYPER[o['fran']]}|natural|{alder}")
            kum = float(d.loc[d["ar"] == h, "netto_kumulativt_tCO2_ha"].iloc[0])
            v = kum * ha * (1 - bv["bio"])
            k.add("Förändrad markanvändning", "Förlorat skogsupptag", MODUL, ar, v)
            k.steg(MODUL, f"{rubrik}: förlorat upptag {h} år", round(v, 1), "t CO2", f"{kum:.1f} t CO2/ha ur Skogskolmodellen")
        # ny skog
        if o["till"] == "Nyplanterad skog":
            k.tabell("skogskol_kurvbibliotek")
            sp = TRADSLAG.get(o.get("tradslag") or "Blandskog (gran/bok)", "mixed")
            mg = SKOTSEL.get(o.get("skotsel") or "Fri utveckling", "natural")
            prior = TIDIGARE_MARK_FOR_SKOG.get(o["fran"], "grassland")
            d = k.fb.skogskurva(f"nybeskogning|{prior}|{sp}|{mg}|")
            serie = dict(zip(d["ar"].astype(int), d["netto_arligt_tCO2_ha"].astype(float)))
            tot = 0.0
            for y in k.ar:
                kk = y - ar + 1
                if kk >= 1 and kk in serie:
                    v = serie[kk] * ha
                    k.add("Negativa utsläpp", "Ny skog", MODUL, y, -v)
                    tot += v
            k.steg(MODUL, f"{rubrik}: upptag i ny skog", round(-tot, 1), "t CO2",
                   f"kurva {prior}, {o.get('tradslag')}, {o.get('skotsel')}, från {ar}")
        # förgröning av hårdgjord mark
        if o["fran"] in FORGRONING_FRAN and o["till"] in FORGRONING_TILL:
            g0 = k.p("mark.forgroning_start"); m = k.p("mark.forgroning_mattnad"); n = int(k.p("mark.forgroning_ar"))
            tot = 0.0
            for y in k.ar:
                t = y - ar
                if t < 0:
                    continue
                f = 1 - (1 - m) * min(t, n) / n
                v = ha * 10000 * g0 * f / 1000
                k.add("Negativa utsläpp", "Förgröning", MODUL, y, -v)
                tot += v
            k.steg(MODUL, f"{rubrik}: förgröning", round(-tot, 1), "t CO2")
