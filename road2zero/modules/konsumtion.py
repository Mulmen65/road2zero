"""Modul 5–7: matkonsumtion (kostprofiler), övrig konsumtion, flygresor och offentlig sektor, per invånare och år.

Alla värden är nivå 2026 och följer sina index i fliken Emissionsfaktorer över tid."""
from __future__ import annotations

from ..kontext import Kontext


def mat_per_profil(k: Kontext, y: int) -> dict[str, float]:
    """t CO2e per invånare och år per kostprofil: profilens andel gånger dess klimatavtryck (EPIC-Oxford), med omställning,
    kalibrering och matproduktionens index. Summan är kosten per invånare."""
    m = k.scen["mat"]
    dagar = k.p("mat.dagar")
    k.tabell("kostprofiler")
    andel = dict(m["andelar"])
    if m.get("omstallning"):
        y0, y1 = k.ar[0], int(m.get("malar", 2045))
        w = 1.0 if y >= y1 else max(0.0, (y - y0) / max(1, y1 - y0))
        andel = {p: (1 - w) * andel[p] + w * float(m["mal_andelar"].get(p, andel[p])) for p in andel}
    skala = k.index("mat", y)
    if m.get("kalibrering"):
        bas = sum(float(m["andelar"][p]) * float(m["avtryck"][p]) for p in andel) * dagar / 1000
        skala *= k.p("mat.kalibrering_mal") / bas if bas else 1
    return {p: andel[p] * float(m["avtryck"][p]) * dagar / 1000 * skala for p in andel}


def mat_per_inv(k: Kontext, y: int) -> float:
    return sum(mat_per_profil(k, y).values())


def berakna(k: Kontext, invanare: dict[int, float]):
    s = k.scen
    ovr = s["ovrig"]; fl = s["flyg"]; off = s["offentlig"]
    k.tabell("ovrig_konsumtion")
    k.anvanda.update({"ovr.hushall_total", "flyg.per_inv", "off.konsumtion", "off.investeringar", "off.andel"})
    namn = {r.kategori: r.namn for r in k.fb.ovrig.itertuples()}
    profilnamn = {r.profil: r.namn for r in k.fb.kostprofiler.itertuples()}
    summa = {"mat": 0.0, "ovrig": 0.0, "flyg": 0.0, "off": 0.0}
    hoghojd = k.p("flyg.hoghojd_faktor")
    bransle = 1 / hoghojd if hoghojd > 0 else 1.0     # andel av flygets klimatpåverkan som är koldioxid från bränslet
    for y in k.ar:
        n = invanare.get(y, 0.0)
        if n <= 0:
            continue
        for p, t in mat_per_profil(k, y).items():
            k.add("Matkonsumtion", profilnamn.get(p, p), "5 Matkonsumtion", y, n * t); summa["mat"] += n * t
        fo = k.index("ovrig", y)
        for kat, t in ovr["varden"].items():
            v = n * float(t) * fo
            k.add("Övrig konsumtion", namn.get(kat, kat), "6 Övrig konsumtion och flygresor", y, v); summa["ovrig"] += v
        v = n * float(fl["per_inv"]) * k.index("flyg", y)
        k.add("Flygresor", "Koldioxid från flygbränslet", "6 Övrig konsumtion och flygresor", y, v * bransle)
        k.add("Flygresor", "Höghöjdseffekt", "6 Övrig konsumtion och flygresor", y, v * (1 - bransle)); summa["flyg"] += v
        foff = k.index("offentlig", y)
        v1 = n * float(off["konsumtion"]) * foff
        v2 = n * float(off["investeringar"]) * float(off["andel"]) * foff
        k.add("Offentliga investeringar", "Offentlig konsumtion", "7 Offentlig sektor", y, v1)
        k.add("Offentliga investeringar", "Offentlig andel av investeringarna", "7 Offentlig sektor", y, v2)
        summa["off"] += v1 + v2
    personar = sum(invanare.values())
    for p, t in mat_per_profil(k, k.ar[0]).items():
        k.steg("5 Matkonsumtion", f"Kost per invånare första året: {profilnamn.get(p, p)}", round(t, 3), "t CO2e/år",
               f"andel {float(s['mat']['andelar'][p]):.1%} × {float(s['mat']['avtryck'][p])} kg CO2e per dag".replace(".", ","))
    k.steg("5 Matkonsumtion", "Kost per invånare första året", round(mat_per_inv(k, k.ar[0]), 3), "t CO2e/år",
           "kalibrerad" if s["mat"].get("kalibrering") else "okalibrerad")
    k.steg("5 Matkonsumtion", "Matkonsumtion totalt", round(summa["mat"], 1), "t CO2e", f"{personar:,.1f} personår".replace(",", " "))
    k.steg("6 Övrig konsumtion och flygresor", "Övrig konsumtion per invånare", round(sum(float(t) for t in ovr["varden"].values()), 3), "t CO2e/år")
    k.steg("6 Övrig konsumtion och flygresor", "Övrig konsumtion totalt", round(summa["ovrig"], 1), "t CO2e")
    k.steg("6 Övrig konsumtion och flygresor", "Flygresor per invånare", float(fl["per_inv"]), "t CO2e/år",
           "Kamb och Larsson 2018: svenska befolkningens flygresor år 2017, med höghöjdseffekt")
    k.steg("6 Övrig konsumtion och flygresor", "Flygresor, koldioxid från bränslet", round(summa["flyg"] * bransle, 1), "t CO2e",
           f"andel 1/{hoghojd:g} = {bransle:.0%}".replace(".", ","))
    k.steg("6 Övrig konsumtion och flygresor", "Flygresor, höghöjdseffekt", round(summa["flyg"] * (1 - bransle), 1), "t CO2e",
           f"andel 1 − 1/{hoghojd:g} = {1 - bransle:.0%}; vetenskapligt osäker".replace(".", ","))
    k.steg("6 Övrig konsumtion och flygresor", "Flygresor totalt", round(summa["flyg"], 1), "t CO2e", f"{float(fl['per_inv'])} t per invånare och år".replace(".", ","))
    k.steg("7 Offentlig sektor", "Offentlig sektor per invånare", round(float(off["konsumtion"]) + float(off["investeringar"]) * float(off["andel"]), 3),
           "t CO2e/år", f"{off['konsumtion']} + {off['investeringar']} × {float(off['andel']):.0%}")
    k.steg("7 Offentlig sektor", "Offentliga investeringar totalt", round(summa["off"], 1), "t CO2e")
