"""Modul 8 Negativa utsläpp: biokol och stadsträd. Kolinlagring i trästomme kommer från Byggnader och ny skog och förgröning från Markanvändning."""
from __future__ import annotations

from ..kontext import Kontext

MODUL = "8 Negativa utsläpp"


def berakna(k: Kontext):
    n = k.scen["negativa"]
    for r in n.get("biokol", []):
        gropar = float(r.get("gropar") or 0)
        if not r.get("certifierat", True):
            k.steg(MODUL, "Biokol", 0, "t CO2e", f"{gropar:.0f} gropar räknas inte: EBC C-sink-certifikat saknas")
            continue
        v = gropar * k.p("neg.biokol_per_grop")
        k.add("Negativa utsläpp", "Biokol", MODUL, int(r["ar"]), -v)
        k.steg(MODUL, "Biokol", round(-v, 1), "t CO2e", f"{gropar:.0f} gropar år {r['ar']}")
    tillv = k.fb.kurva("tradtillvaxt")
    k.tabell("kurvor")
    for r in n.get("trad", []):
        antal = float(r.get("antal") or 0); p0 = int(r.get("planteringsar") or k.ar[0])
        up = k.p("neg.trad_upptag")
        tot = 0.0
        for y in k.ar:
            if y >= p0:
                v = antal * up * tillv(y - p0) / 1000
                k.add("Negativa utsläpp", "Stadsträd", MODUL, y, -v)
                tot += v
        k.steg(MODUL, "Stadsträd", round(-tot, 1), "t CO2", f"{antal:.0f} träd från {p0}")
