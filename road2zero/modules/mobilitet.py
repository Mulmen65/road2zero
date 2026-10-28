"""Modul 4 Mobilitet och transport: de boendes bilar (hushållsmodell) med livscykelfaktor per drivlina.

Livscykelfaktorn per drivlina (g CO2e per fordonskm) består av förbränning, bränslets tidigare led,
el till laddning, fordons- och batteritillverkning fördelad på livslängden samt underhåll (ICCT 2025,
direktiv 2015/652). Biogen CO2 och möjlig återvinningskredit ingår inte i totalen. Elens klimatfaktor
är modellens gemensamma kurva.
"""
from __future__ import annotations

from ..kontext import Kontext
from ..konstanter import DRIVLINOR

MODUL = "4 Mobilitet och transport"
BASAR = 2024  # basår för drivlinemix och körsträcka (Trafikanalys)


def mix_for_ar(k: Kontext, y: int) -> dict:
    m = dict(k.scen["mobilitet"]["mix"])
    if k.scen["mobilitet"].get("elbilsandel", "kurva") != "kurva":
        return m
    k.tabell("kurvor")
    mal = k.fb.kurva("elbilsandel_trafikverket")(y) / 100
    bev = m.get("bev", 0.0)
    flytt = max(0.0, mal - bev)
    icke = 1 - bev
    out = {d: (v * (1 - flytt / icke) if icke else v) for d, v in m.items() if d != "bev"}
    out["bev"] = bev + flytt
    return out


def faktorer(k: Kontext, y: int) -> dict[str, dict[str, float]]:
    """Livscykelfaktor per drivlina, g CO2e per fordonskm, år y."""
    vv = k.fb.personbil
    r = vv["profil"]["rules"]
    mob = k.scen["mobilitet"]
    bransle = {
        "petrol": {"fossil": float(mob["bensin_fossil"]), "ttw": k.p("mob.bensin.ttw"), "wtt": k.p("mob.bensin.wtt"), "bio": k.p("mob.bensin.bio")},
        "diesel": {"fossil": float(mob["diesel_fossil"]), "ttw": k.p("mob.diesel.ttw"), "wtt": k.p("mob.diesel.wtt"), "bio": k.p("mob.diesel.bio")},
        "biogas": {"fossil": 0.0, "ttw": k.p("mob.biogas.ttw"), "wtt": 0.0, "bio": k.p("mob.biogas.bio")},
    }
    k.anvanda.update({"mob.bensin.fossil", "mob.diesel.fossil", "mob.phev_eldrift"})
    mj0, kwh0 = k.p("mob.mj_per_km"), k.p("mob.kwh_per_km")
    eta, ovr = k.p("mob.laddverkningsgrad"), k.p("mob.ovrigt")
    liv, kaross = k.p("mob.livslangd"), k.p("mob.kaross")
    bat_kwh, bat_ef, underhall = k.p("mob.batteri_kwh"), k.p("mob.batteri_ef"), k.p("mob.underhall")
    eff = float(mob.get("effektivisering", 0))
    k.anvanda.add("mob.effektivisering")
    eff_f = (1 - eff) ** max(0, y - BASAR)
    phev_el = float(mob["phev_eldrift"])
    ut = {}
    for d in DRIVLINOR:
        el_andel = 1.0 if d == "bev" else phev_el if d == "phev" else 0.0
        termisk = 1 - el_andel
        mj = mj0 * r["energy"].get(d, 1.0) * termisk
        ttw = up = 0.0
        if termisk:
            f = bransle["petrol" if d in ("phev", "hev") else d]
            ttw = (mj * f["fossil"] * f["ttw"] + ovr * termisk) * eff_f
            up = mj * (f["fossil"] * f["wtt"] + (1 - f["fossil"]) * f["bio"]) * eff_f
        el = el_andel * kwh0 * r["kwh"].get(d, 1.0) / eta * k.el(y)
        kropp = kaross * r["body"].get(d, 1.0)
        fordon = kropp * 1000 / liv
        kap = r["battery"].get(d, bat_kwh if d == "bev" else 0.0)
        batteri = kap * bat_ef * 1000 / liv
        uh = underhall * r["maint"].get(d, 1.0)
        ut[d] = {"bransle": ttw + up, "el": el, "fordon": fordon + batteri, "underhall": uh}
        ut[d]["total"] = sum(ut[d].values())
    return ut


def berakna(k: Kontext, invanare: dict[int, float]):
    mob = k.scen["mobilitet"]
    pph = float(k.scen["hushall"]["personer_per_hushall"])
    bph = float(mob["bilar_per_hushall"]); km = float(mob["km_per_bil"])
    k.tabell("kommuner")
    tot = 0.0
    for y in k.ar:
        n = invanare.get(y, 0.0)
        if n <= 0:
            continue
        fkm = n / pph * bph * km
        mix = mix_for_ar(k, y)
        f = faktorer(k, y)
        for delpost, nyckel in (("Bränsle och avgaser", "bransle"), ("El till laddning", "el"),
                                ("Fordon och batteri", "fordon"), ("Underhåll", "underhall")):
            v = fkm * sum(mix[d] * f[d][nyckel] for d in mix) / 1e6
            k.add("Mobilitet och transport", delpost, MODUL, y, v)
            tot += v
    f0 = faktorer(k, k.ar[0])
    for d, namn in DRIVLINOR.items():
        k.steg(MODUL, f"Livscykelfaktor {namn} {k.ar[0]}", round(f0[d]["total"], 1), "g CO2e/fkm",
               f"bränsle {f0[d]['bransle']:.1f}, el {f0[d]['el']:.1f}, fordon {f0[d]['fordon']:.1f}, underhåll {f0[d]['underhall']:.1f}")
    k.steg(MODUL, "Bilar per hushåll och körsträcka", f"{bph:.3f} · {km:,.0f}".replace(",", " "), "bilar · km/år")
    k.steg(MODUL, "Elbilsandel 2030 / 2050", f"{mix_for_ar(k, 2030)['bev']:.0%} / {mix_for_ar(k, 2050)['bev']:.0%}", "av körsträckan")
    k.steg(MODUL, "Mobilitet och transport totalt", round(tot, 1), "t CO2e")
