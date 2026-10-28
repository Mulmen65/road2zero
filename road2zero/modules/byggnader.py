"""Modul 1 Byggnader: byggskede, grundläggning, energi i drift, kolinlagring i trästomme och invånare.

Byggbeståndet anges som andelar. Varje andel har en byggnadstyp, en stomme och egna energival
(energiklass, andel fjärrvärme och värmepump, egen köpt el och fjärrvärme per m² BTA, solceller),
så att byggpåverkan och energi alltid hör till samma BTA.
"""
from __future__ import annotations

from ..kontext import Kontext
from ..konstanter import BYGGNADSTYPER, OUPPVARMDA_KLASSER, STOMMAR, VIRKESPRODUKTER
from ..scenario import ar_tra, etikett, takt, virkesprodukt

MODUL = "1 Byggnader"


def i_drift(t: dict[int, float], y: int) -> float:
    """BTA i drift år y. Halvårsregel: hälften det år BTA:n blir klar, därefter helt."""
    return sum(a * (0.5 if ar == y else 1.0) for ar, a in t.items() if ar <= y)


def bygg_kg_m2(fb, utv, b: dict, ar: int) -> float:
    """Byggskedets klimatpåverkan, kg CO2e per m² BTA, för BTA som blir klar år ar.
    Startvärdet (nivå 2026) för typ och stomme gånger stommens index i fliken Emissionsfaktorer över tid."""
    manuell = b.get("manuellt_kg_m2")
    if manuell not in (None, "") and float(manuell) > 0:
        return float(manuell)
    st = b.get("stomme") or "generisk"
    return fb.byggschablon(b["typ"], st) * utv.index(f"bygg.{st}", ar)


def fjv_andel(b: dict, klass: str) -> float:
    """Andel av fastighetsvärmen från fjärrvärme (0–1); resten är eluppvärmning med värmepump."""
    if klass in OUPPVARMDA_KLASSER:
        return 0.0
    v = b.get("fjv_andel", 100)
    try:
        return max(0.0, min(100.0, float(v))) / 100
    except (TypeError, ValueError):
        return 1.0


def energi_kwh_m2(fb, b: dict, atemp_andel: float | None = None) -> dict:
    """Köpt fjärrvärme och el per m² BTA för andelens energiklass och fördelning mellan fjärrvärme och värmepump.
    Energiklassen anger kWh per m² Atemp; egna värden anges per m² BTA och ersätter klassens värde."""
    atemp = fb.param("allm.atemp_andel") if atemp_andel is None else atemp_andel
    ek = fb.energiklass(b["typ"], b.get("energiklass") or "C")
    s = fjv_andel(b, ek["klass"])
    fjv_atemp = s * ek["kopt_fjarrvarme"]
    el_atemp = s * ek["fastighetsel_fjv"] + (1 - s) * ek["el_eluppvarmd"]
    fjv, el = fjv_atemp * atemp, el_atemp * atemp
    egen_fjv = b.get("egen_fjv_kwh") not in (None, "")
    egen_el = b.get("egen_el_kwh") not in (None, "")
    if egen_fjv:
        fjv = float(b["egen_fjv_kwh"])
    if egen_el:
        el = float(b["egen_el_kwh"])
    return {"fjv": fjv, "el": el, "fjv_atemp": fjv_atemp, "el_atemp": el_atemp, "klass": ek["klass"], "kategori": ek["typ"],
            "fjv_andel": s, "kalla": ek["kalla"], "eget": egen_fjv or egen_el}


def berakna(k: Kontext) -> dict[int, float]:
    s = k.scen
    fb = k.fb
    k.tabell("byggschabloner"); k.tabell("reduktionskurvor"); k.tabell("energiklasser")
    atemp_andel = k.p("allm.atemp_andel")
    paln_f = k.p("bygg.paln")
    spont_f = k.p("bygg.spont")
    sol_kwh = k.p("sol.produktion")
    panel = k.p("sol.panel")
    pph = float(s["hushall"]["personer_per_hushall"])
    bta_hh = float(s["hushall"]["bta_per_hushall"])
    k.anvanda.update({"allm.personer_per_hushall", "allm.bta_per_hushall"})
    invanare = {y: 0.0 for y in k.ar}

    for i, b in enumerate(s["byggnader"], 1):
        typ = b["typ"]
        if typ not in BYGGNADSTYPER:
            continue
        _, bostad, grupp = BYGGNADSTYPER[typ]
        t = takt(b)
        if not t:
            continue
        bta = sum(t.values())
        namn = f"Andel {i}: {etikett(b)}"
        manuell = b.get("manuellt_kg_m2") not in (None, "") and float(b["manuellt_kg_m2"]) > 0
        # kolinlagring i trästomme: −(BTA × v × Fprodukt), bara för Trä BAU och Trä BÄST
        tra = ar_tra(b)
        produkt = virkesprodukt(b) if tra else None
        egen_v = b.get("virke_m3_m2")
        egen_v = None if egen_v in (None, "") or (isinstance(egen_v, float) and egen_v != egen_v) else float(egen_v)
        v_m3_m2 = (egen_v if egen_v is not None else k.p("bygg.virke_m3_m2")) if tra else 0.0
        f_produkt = k.p(VIRKESPRODUKTER[produkt]) if tra else 0.0
        if tra:
            k.anvanda.add("bygg.virke_m3_m2")

        summa = {"bygg": 0.0, "paln": 0.0, "spont": 0.0, "virke": 0.0, "virke_m3": 0.0}
        for ar, a in sorted(t.items()):
            bygg = a * bygg_kg_m2(fb, k.utv, b, ar) / 1000
            anl = k.index("anl", ar)
            paln = a * paln_f * float(b.get("paln_andel", 100) or 0) / 100 * anl if b.get("palning") else 0.0
            spont = float(b.get("spont_m2") or 0) * spont_f * a / bta * anl
            vm3 = a * v_m3_m2
            virke = vm3 * f_produkt / 1000
            k.add("Byggnad", BYGGNADSTYPER[typ][0], MODUL, ar, bygg)
            k.add("Anläggning", "Pålning", MODUL, ar, paln)
            k.add("Anläggning", "Spontning", MODUL, ar, spont)
            k.add("Negativa utsläpp", "Kolinlagring i trästomme", MODUL, ar, -virke)
            summa["bygg"] += bygg; summa["paln"] += paln; summa["spont"] += spont; summa["virke"] += virke; summa["virke_m3"] += vm3

        # energi i drift, med andelens egna energival (kWh per m² BTA)
        e = energi_kwh_m2(fb, b, atemp_andel)
        sol_m2 = float(b.get("sol_m2") or 0)
        energi_tot = 0.0
        undvikna = 0.0
        for y in k.ar:
            u = i_drift(t, y)
            if u <= 0:
                continue
            fjv = u * e["fjv"]
            el = u * e["el"]
            sol = sol_m2 * sol_kwh * u / bta
            egen = min(sol, el)
            over = sol - egen
            t_fjv = fjv * k.fjv(y) / 1e6
            t_el = (el - egen) * k.el(y) / 1e6
            k.add("Energi", "Fjärrvärme", MODUL, y, t_fjv)
            k.add("Energi", "El", MODUL, y, t_el)
            energi_tot += t_fjv + t_el
            if over > 0:
                v = -over * (k.el(y) - panel) / 1e6
                k.add_utanfor("Exporterad solel", MODUL, y, v)
                undvikna += v
            if bostad:
                invanare[y] += u / bta_hh * pph

        k.steg(MODUL, f"{namn}: BTA", bta, "m²", ", ".join(f"{a}: {v:,.0f}".replace(",", " ") for a, v in sorted(t.items())))
        k.steg(MODUL, f"{namn}: stomme", STOMMAR.get(b.get("stomme"), b.get("stomme")), "",
               "manuellt värde" if manuell else f"schablon {fb.byggschablon(typ, b.get('stomme') or 'generisk'):.1f} kg CO2e/m² nivå 2026, "
               f"index för stommen när BTA:n blir klar")
        k.steg(MODUL, f"{namn}: byggskede", round(summa["bygg"], 1), "t CO2e", f"i snitt {summa['bygg']*1000/bta:.1f} kg CO2e/m² BTA")
        k.steg(MODUL, f"{namn}: pålning och spont", round(summa["paln"] + summa["spont"], 1), "t CO2e")
        k.steg(MODUL, f"{namn}: energi i drift", round(energi_tot, 1), "t CO2e",
               f"klass {e['klass']}, fjärrvärme {e['fjv_andel']*100:.0f} % och värmepump {(1-e['fjv_andel'])*100:.0f} %: "
               f"{e['fjv']:.1f} kWh fjärrvärme och {e['el']:.1f} kWh el per m² BTA" + (" (eget värde)" if e["eget"] else ""))
        if tra:
            k.steg(MODUL, f"{namn}: kolinlagring i trästomme", round(-summa["virke"], 1), "t CO2",
                   f"{summa['virke_m3']:,.0f} m³ {produkt.lower()} ({v_m3_m2:g} m³/m² BTA) × {f_produkt:g} kg CO2/m³".replace(",", " "))
        if undvikna:
            k.steg(MODUL, f"{namn}: undvikna utsläpp, separat", round(undvikna, 1), "t CO2e")
    return invanare
