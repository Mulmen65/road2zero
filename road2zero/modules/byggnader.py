"""Modul 1 Byggnader: byggskede, grundläggning, energi i drift, inbyggt virke och invånare.

Byggbeståndet anges som andelar. Varje andel har en byggnadstyp, en stomme och egna energival
(energiklass, uppvärmning och solceller), så att byggpåverkan och energi alltid hör till samma BTA.
"""
from __future__ import annotations

from ..kontext import Kontext
from ..konstanter import BYGGNADSTYPER, OUPPVARMDA_KLASSER, REDUKTIONSKURVA_FOR_STOMME, STOMMAR, UPPVARMNING, VIRKESPRODUKTER
from ..scenario import ar_tra, etikett, takt, virke_m3_m2

MODUL = "1 Byggnader"


def i_drift(t: dict[int, float], y: int) -> float:
    """BTA i drift år y. Halvårsregel: hälften det år BTA:n blir klar, därefter helt."""
    return sum(a * (0.5 if ar == y else 1.0) for ar, a in t.items() if ar <= y)


def bygg_kg_m2(fb, b: dict, ar: int) -> float:
    """Byggskedets klimatpåverkan, kg CO2e per m² BTA, för BTA som blir klar år ar."""
    manuell = b.get("manuellt_kg_m2")
    if manuell not in (None, "") and float(manuell) > 0:
        return float(manuell)
    st = b.get("stomme") or "generisk"
    grupp = BYGGNADSTYPER[b["typ"]][2]
    return fb.byggschablon(b["typ"], st) * fb.reduktionskurva(grupp, REDUKTIONSKURVA_FOR_STOMME.get(st, st))(ar)


def energi_kwh_m2(fb, b: dict) -> dict:
    """Köpt fjärrvärme och el per m² Atemp för andelens energiklass och uppvärmning."""
    ek = fb.energiklass(b["typ"], b.get("energiklass") or "C")
    fjv_uppv = b.get("uppvarmning", "fjärrvärme") == "fjärrvärme" and ek["klass"] not in OUPPVARMDA_KLASSER
    if fjv_uppv:
        fjv = ek["kopt_fjarrvarme"]
        el = ek["fastighetsel_fjv"]
    else:
        fjv = 0.0
        el = ek["el_eluppvarmd"]
    if b.get("egen_fjv_kwh") not in (None, "") and fjv_uppv:
        fjv = float(b["egen_fjv_kwh"])
    if b.get("egen_el_kwh") not in (None, ""):
        el = float(b["egen_el_kwh"])
    return {"fjv": fjv, "el": el, "klass": ek["klass"], "kategori": ek["typ"], "uppvarmning": "fjärrvärme" if fjv_uppv else "el",
            "kalla": ek["kalla"]}


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
        produkt = VIRKESPRODUKTER.get(b.get("virkesprodukt") or "Stomvirke", "bygg.virke.stomvirke")
        v_m3_m2 = virke_m3_m2(b, fb)
        virke_kg_m3 = k.p(produkt) if v_m3_m2 else 0.0
        if v_m3_m2:
            k.anvanda.add("bygg.virke_m3_m2")
        ccf = max(0.0, min(100.0, float(b.get("ccf_andel") or 0))) / 100

        summa = {"bygg": 0.0, "paln": 0.0, "spont": 0.0, "virke": 0.0, "virke_m3": 0.0}
        for ar, a in sorted(t.items()):
            bygg = a * bygg_kg_m2(fb, b, ar) / 1000
            paln = a * paln_f * float(b.get("paln_andel", 100) or 0) / 100 if b.get("palning") else 0.0
            spont = float(b.get("spont_m2") or 0) * spont_f * a / bta
            vm3 = a * v_m3_m2
            virke = vm3 * virke_kg_m3 / 1000 * ccf
            k.add("Byggnad", BYGGNADSTYPER[typ][0], MODUL, ar, bygg)
            k.add("Anläggning", "Pålning", MODUL, ar, paln)
            k.add("Anläggning", "Spontning", MODUL, ar, spont)
            k.add("Negativa utsläpp", "Inbyggt virke", MODUL, ar, -virke)
            summa["bygg"] += bygg; summa["paln"] += paln; summa["spont"] += spont; summa["virke"] += virke; summa["virke_m3"] += vm3

        # energi i drift, med andelens egna energival
        e = energi_kwh_m2(fb, b)
        sol_m2 = float(b.get("sol_m2") or 0)
        energi_tot = 0.0
        undvikna = 0.0
        for y in k.ar:
            u = i_drift(t, y)
            if u <= 0:
                continue
            atemp = atemp_andel * u
            fjv = atemp * e["fjv"]
            el = atemp * e["el"]
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
               "manuellt värde" if manuell else f"schablon {fb.byggschablon(typ, b.get('stomme') or 'generisk'):.0f} kg CO2e/m² år 2025, reduktionsgrupp {grupp}")
        k.steg(MODUL, f"{namn}: byggskede", round(summa["bygg"], 1), "t CO2e", f"i snitt {summa['bygg']*1000/bta:.1f} kg CO2e/m² BTA")
        k.steg(MODUL, f"{namn}: pålning och spont", round(summa["paln"] + summa["spont"], 1), "t CO2e")
        k.steg(MODUL, f"{namn}: energi i drift", round(energi_tot, 1), "t CO2e",
               f"klass {e['klass']}, {UPPVARMNING[e['uppvarmning']].lower()}: {e['fjv']:g} kWh fjärrvärme och {e['el']:g} kWh el per m² Atemp")
        if summa["virke"] or (v_m3_m2 and ar_tra(b)):
            k.steg(MODUL, f"{namn}: inbyggt virke", round(-summa["virke"], 1), "t CO2", f"{summa['virke_m3']:,.0f} m³, CCF {ccf*100:.0f} %".replace(",", " "))
        if undvikna:
            k.steg(MODUL, f"{namn}: undvikna utsläpp, separat", round(undvikna, 1), "t CO2e")
    return invanare
