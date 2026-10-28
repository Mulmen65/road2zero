"""Modul 2 Anläggning: ytor, betong, masshantering, ledningar och engångsvärden. Biokol och stadsträd redovisas under Negativa utsläpp.

Schablonerna gäller nivå 2026 och följer indexet för anläggning (som standard betongstommens kurva). Engångsvärden räknas som angivna."""
from __future__ import annotations

from ..kontext import Kontext
from ..konstanter import ANLAGGNINGSTYPER

MODUL = "2 Anläggning"


def _ar(r: dict) -> list[int]:
    a0 = int(r.get("forsta_ar") or r.get("ar") or 0)
    a1 = int(r.get("sista_ar") or a0)
    return list(range(a0, max(a0, a1) + 1))


def berakna(k: Kontext):
    a = k.scen["anlaggning"]
    k.tabell("ytschabloner")
    for r in a.get("ytor", []):
        f = k.fb.ytschablon(r["typ"], r.get("utforande", "standard"))
        tot = float(r["yta_m2"] or 0) * f
        ar = _ar(r)
        for y in ar:
            k.add("Anläggning", ANLAGGNINGSTYPER.get(r["typ"], r["typ"]), MODUL, y, tot / len(ar) * k.index("anl", y))
        k.steg(MODUL, f"Yta: {ANLAGGNINGSTYPER.get(r['typ'], r['typ'])}, nivå 2026", round(tot, 1), "t CO2e",
               f"{float(r['yta_m2']):,.0f} m² × {f*1000:g} kg/m² ({r.get('utforande', 'standard')})".replace(",", " "))
    for r in a.get("betong", []):
        pid = "anl.betong_klimatforbattrad" if r.get("utforande") == "klimatförbättrad" else "anl.betong_standard"
        tot = float(r["volym_m3"] or 0) * k.p(pid)
        ar = _ar(r)
        for y in ar:
            k.add("Anläggning", "Betong", MODUL, y, tot / len(ar) * k.index("anl", y))
        k.steg(MODUL, "Betong i anläggning", round(tot, 1), "t CO2e")
    for r in a.get("massor", []):
        vol = float(r["volym_m3"] or 0)
        f = k.p("anl.sanering") if r.get("typ") == "Sanering" else k.p("anl.schakt")
        trans = vol * k.p("anl.jorddensitet") * float(r.get("transport_km") or 0) * k.p("anl.transport")
        tot = vol * f + trans
        ar = _ar(r)
        for y in ar:
            k.add("Anläggning", "Masshantering", MODUL, y, tot / len(ar) * k.index("anl", y))
        k.steg(MODUL, f"Massor: {r.get('typ', 'Schakt')}", round(tot, 1), "t CO2e",
               f"{vol:,.0f} m³ × {f} t/m³ + transport {trans:.1f} t".replace(",", " "))
    for r in a.get("ledningar", []):
        tot = float(r["meter"] or 0) * k.p("anl.ledning")
        for y in _ar(r):
            k.add("Anläggning", "Ledningar", MODUL, y, tot / len(_ar(r)) * k.index("anl", y))
        k.steg(MODUL, "Ledningar", round(tot, 1), "t CO2e")
    for r in a.get("engangsvarden", []):
        k.add("Anläggning", r.get("namn") or "Engångsvärde", MODUL, int(r["ar"]), float(r["t_co2e"] or 0))
        k.steg(MODUL, f"Engångsvärde: {r.get('namn')}", float(r["t_co2e"] or 0), "t CO2e")
