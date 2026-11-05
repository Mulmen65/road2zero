"""Rättvis jämförelse av scenarier eller stadsdelar.

1. Funktion. Varje andel får en funktion efter byggnadstyp: bostäder (flerbostadshus, småhus) och närservice (skola) bildar
   boendefunktionen; kontor, lokaler, handel, vård, industri och övriga byggnader är verksamheter; mobilitetshus och garage är
   parkering. Parkering, anläggning, markanvändning och stadsträd är gemensamma och fördelas på boende och verksamheter efter BTA.
   Boendefunktionen redovisas per invånare och verksamheterna per arbetsplats (BTA delat med BTA per arbetsplats).
2. Lika förutsättningar. Alla emissionsfaktorer hålls på startvärdena 2026 (årlig förändring 0 %), så att skillnaderna bara beror
   på utformningen: program, täthet, stommar, energiklasser, parkering, gator och mark, inte på när det byggs.
3. Livscykel per år. Engångsutsläpp (byggskede, grundläggning, anläggning, mark, kolinlagring och stadsträd) fördelas på
   referensstudieperioden och läggs till ett års drift vid full utbyggnad.
4. Standardiserad blandning. Intensiteten per m² BTA för boende och verksamheter vägs med en gemensam fördelning mellan boende
   och verksamheter, så att olika andelar kontor och bostäder inte avgör jämförelsen.
5. Faktisk tidpunkt. Samma uppdelning med emissionsfaktorerna över tid och de faktiska utbyggnadsåren.
"""
from __future__ import annotations

import copy

import pandas as pd

from .engine import berakna
from .factlib import Faktabibliotek, ladda
from .konstanter import BYGGNADSTYPER
from .scenario import takt

NARSERVICE_TYPER = {"skola"}                               # närservice räknas till boendefunktionen
PARKERING_TYPER = {"mobilitetshus", "underjordisk_parkering"}
ENGANG = ("Byggnad", "Anläggning", "Förändrad markanvändning", "Negativa utsläpp")
NIVA1 = ["Byggnad", "Energi", "Anläggning", "Förändrad markanvändning", "Negativa utsläpp"]
KONSUMTION = ["Matkonsumtion", "Övrig konsumtion", "Flygresor"]
KOMPONENTER = {"byggskede": "Byggskede och kolinlagring", "parkering": "Parkering",
               "anlaggning_mark": "Anläggning, mark och stadsträd", "drift": "Drift (energi)"}


def funktion(b: dict) -> str:
    """bostad, narservice, verksamhet eller parkering."""
    if b["typ"] in PARKERING_TYPER:
        return "parkering"
    if BYGGNADSTYPER[b["typ"]][1]:
        return "bostad"
    if b["typ"] in NARSERVICE_TYPER:
        return "narservice"
    return "verksamhet"


def lika_forutsattningar(s: dict) -> dict:
    """Alla emissionsfaktorer på startvärdet 2026 under hela perioden."""
    s = copy.deepcopy(s)
    for f, v in s["utveckling"]["takt"].items():
        s["utveckling"]["takt"][f] = [0.0] * len(v)
    return s


def _delmangd(s: dict, funktioner: set[str] | None, gemensamt: bool) -> dict:
    d = copy.deepcopy(s)
    d["byggnader"] = [b for b in s["byggnader"] if funktioner and funktion(b) in funktioner]
    if not gemensamt:
        d["anlaggning"] = {k: [] for k in s["anlaggning"]}
        d["mark"]["overgangar"] = []
        d["negativa"] = {"biokol": [], "trad": []}
    return d


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


def analys(s: dict, fb: Faktabibliotek | None = None, livslangd: float | None = None, m2_per_arbetsplats: float | None = None,
           lika: bool = True) -> dict:
    """Jämförelsemått för ett scenario. lika=True håller alla emissionsfaktorer på 2026 års nivå."""
    fb = fb or ladda()
    livslangd = float(livslangd or fb.param("jmf.livslangd"))
    m2_arb = float(m2_per_arbetsplats or fb.param("jmf.m2_per_arbetsplats"))
    s = lika_forutsattningar(s) if lika else copy.deepcopy(s)
    slut = int(s["projekt"]["slutar"])
    klar = [max(t) for t in (takt(b) for b in s["byggnader"]) if t]
    full = max([slut] + klar) + 1                        # första året med hela beståndet i drift
    s["projekt"]["slutar"] = full
    bta = {f: 0.0 for f in ("bostad", "narservice", "verksamhet", "parkering")}
    for b in s["byggnader"]:
        bta[funktion(b)] += sum(takt(b).values())
    bta_boende = bta["bostad"] + bta["narservice"]
    bta_verks = bta["verksamhet"]
    andel_b = _div(bta_boende, bta_boende + bta_verks) if bta_boende + bta_verks else 1.0
    r = berakna(s, fb)
    p = r.per_ar_och_kategori()
    inv = r.invanare[full]
    arb = _div(bta_verks, m2_arb)
    hush = _div(bta["bostad"], float(s["hushall"]["bta_per_hushall"]))
    delar = {}
    for namn, (fset, gem) in {"boende": ({"bostad", "narservice"}, False), "verksamhet": ({"verksamhet"}, False),
                              "parkering": ({"parkering"}, False), "gemensamt": (None, True)}.items():
        pd_ = berakna(_delmangd(s, fset, gem), fb).per_ar_och_kategori()
        delar[namn] = {"engang": float(sum(pd_.loc[:full - 1, k].sum() for k in ENGANG)), "drift": float(pd_.loc[full, "Energi"]),
                       "byggnad": float(pd_["Byggnad"].sum()), "grund": float(pd_["Anläggning"].sum()) if namn != "gemensamt" else 0.0,
                       "kolinlagring": float(pd_["Negativa utsläpp"].sum()) if namn != "gemensamt" else 0.0}
    gem = [delar["parkering"], delar["gemensamt"]]

    def per_ar(funk: str, andel: float) -> float:
        d = delar[funk]
        return (d["engang"] + andel * sum(g["engang"] for g in gem)) / livslangd + d["drift"] + andel * sum(g["drift"] for g in gem)
    lc_b = per_ar("boende", andel_b); lc_v = per_ar("verksamhet", 1 - andel_b)
    ut = {
        "namn": s["projekt"]["namn"], "startar": int(s["projekt"]["startar"]), "slutar": slut, "full_ar": full, "lika": lika,
        "livslangd": livslangd, "m2_per_arbetsplats": m2_arb,
        "bta": bta, "bta_boende": bta_boende, "bta_verksamhet": bta_verks, "andel_boende": andel_b,
        "invanare": inv, "arbetsplatser": arb, "bostader": hush, "personer_per_hushall": float(s["hushall"]["personer_per_hushall"]),
        "bta_bostad_per_inv": _div(bta["bostad"], inv), "bta_boende_per_inv": _div(bta_boende, inv),
        "parkering_m2_per_bostad": _div(bta["parkering"], hush),
        "delar": delar,
        "bygg_kg_m2_boende": _div((delar["boende"]["byggnad"] + delar["boende"]["grund"]) * 1000, bta_boende),
        "bygg_kg_m2_verks": _div((delar["verksamhet"]["byggnad"] + delar["verksamhet"]["grund"]) * 1000, bta_verks),
        "kolinlagring_kg_m2": _div((delar["boende"]["kolinlagring"] + delar["verksamhet"]["kolinlagring"]) * 1000, bta_boende + bta_verks),
        "parkering_kg_per_bostad": _div(delar["parkering"]["engang"] * 1000, hush),
        "gemensamt_kg_m2": _div(delar["gemensamt"]["engang"] * 1000, bta_boende + bta_verks),
        "drift_kg_m2_ar_boende": _div(delar["boende"]["drift"] * 1000, bta_boende),
        "drift_kg_m2_ar_verks": _div(delar["verksamhet"]["drift"] * 1000, bta_verks),
        "lc_kg_m2_ar_boende": _div(lc_b * 1000, bta_boende),
        "lc_kg_m2_ar_verks": _div(lc_v * 1000, bta_verks),
        "lc_delar_boende": {
            "byggskede": _div(delar["boende"]["engang"] / livslangd * 1000, bta_boende),
            "parkering": _div(andel_b * (gem[0]["engang"] / livslangd + gem[0]["drift"]) * 1000, bta_boende),
            "anlaggning_mark": _div(andel_b * (gem[1]["engang"] / livslangd + gem[1]["drift"]) * 1000, bta_boende),
            "drift": _div(delar["boende"]["drift"] * 1000, bta_boende)},
        "niva1_boende_t_per_inv": _div(lc_b, inv),
        "naiv_t_per_inv": _div(lc_b + lc_v, inv),
        "verks_t_per_arb": _div(lc_v, arb),
        "mobilitet_t_per_inv": _div(float(p.loc[full, "Mobilitet och transport"]), inv),
        "konsumtion_t_per_inv": _div(float(p.loc[full, KONSUMTION].sum()), inv),
        "offentlig_t_per_inv": _div(float(p.loc[full, "Offentliga investeringar"]), inv),
        "per_kategori_t": {k: float(v) for k, v in p.loc[:slut].sum().items()},
        "personar": float(sum(v for y, v in r.invanare.items() if y <= slut)),
    }
    ut["egen_mix_kg_m2_ar"] = andel_b * ut["lc_kg_m2_ar_boende"] + (1 - andel_b) * ut["lc_kg_m2_ar_verks"]
    ut["niva2_t_per_inv"] = ut["niva1_boende_t_per_inv"] + ut["mobilitet_t_per_inv"] + ut["konsumtion_t_per_inv"]
    ut["niva3_t_per_inv"] = ut["niva2_t_per_inv"] + ut["offentlig_t_per_inv"]
    ut["niva1_t_per_personar"] = _div(sum(ut["per_kategori_t"][k] for k in NIVA1), ut["personar"])
    return ut


def standardisera(analyser: list[dict], andel_boende: float) -> None:
    """Lägger till intensiteten per m² BTA och år vägd med en gemensam fördelning mellan boende och verksamheter."""
    for a in analyser:
        verks = a["lc_kg_m2_ar_verks"] if a["bta_verksamhet"] else a["lc_kg_m2_ar_boende"]
        a["standardiserad_kg_m2_ar"] = andel_boende * a["lc_kg_m2_ar_boende"] + (1 - andel_boende) * verks


# Måtten i jämförelsetabellen: (grupp, namn, nyckel eller funktion, decimaler)
MATT = [
    ("Program", "Bostäder", "bostader", 0),
    ("Program", "Invånare vid full utbyggnad", "invanare", 0),
    ("Program", "Arbetsplatser", "arbetsplatser", 0),
    ("Program", "BTA bostäder (m²)", lambda a: a["bta"]["bostad"], 0),
    ("Program", "BTA närservice (m²)", lambda a: a["bta"]["narservice"], 0),
    ("Program", "BTA verksamheter (m²)", "bta_verksamhet", 0),
    ("Program", "BTA parkering (m²)", lambda a: a["bta"]["parkering"], 0),
    ("Program", "Boendefunktionens andel av BTA utan parkering (%)", lambda a: a["andel_boende"] * 100, 1),
    ("Program", "Personer per hushåll", "personer_per_hushall", 2),
    ("Program", "BTA boendefunktion per invånare (m²)", "bta_boende_per_inv", 1),
    ("Program", "Parkering, m² BTA per bostad", "parkering_m2_per_bostad", 1),
    ("Per m² BTA", "Byggskede inkl. grundläggning, boende (kg/m²)", "bygg_kg_m2_boende", 0),
    ("Per m² BTA", "Byggskede inkl. grundläggning, verksamheter (kg/m²)", "bygg_kg_m2_verks", 0),
    ("Per m² BTA", "Kolinlagring i trästomme (kg/m²)", "kolinlagring_kg_m2", 1),
    ("Per m² BTA", "Anläggning, mark och stadsträd (kg/m²)", "gemensamt_kg_m2", 0),
    ("Per m² BTA", "Parkering (kg per bostad)", "parkering_kg_per_bostad", 0),
    ("Per m² BTA", "Drift, boende (kg/m² och år)", "drift_kg_m2_ar_boende", 2),
    ("Per m² BTA", "Drift, verksamheter (kg/m² och år)", "drift_kg_m2_ar_verks", 2),
    ("Livscykel per år", "Boende (kg/m² BTA och år)", "lc_kg_m2_ar_boende", 2),
    ("Livscykel per år", "  därav byggskede och kolinlagring", lambda a: a["lc_delar_boende"]["byggskede"], 2),
    ("Livscykel per år", "  därav parkering", lambda a: a["lc_delar_boende"]["parkering"], 2),
    ("Livscykel per år", "  därav anläggning, mark och stadsträd", lambda a: a["lc_delar_boende"]["anlaggning_mark"], 2),
    ("Livscykel per år", "  därav drift", lambda a: a["lc_delar_boende"]["drift"], 2),
    ("Livscykel per år", "Verksamheter (kg/m² BTA och år)", "lc_kg_m2_ar_verks", 2),
    ("Livscykel per år", "Egen blandning (kg/m² BTA och år)", "egen_mix_kg_m2_ar", 2),
    ("Livscykel per år", "Standardiserad blandning (kg/m² BTA och år)", "standardiserad_kg_m2_ar", 2),
    ("Per person", "Nivå 1 hela området per invånare, utan uppdelning (t/år)", "naiv_t_per_inv", 2),
    ("Per person", "Nivå 1 boende per invånare (t/år)", "niva1_boende_t_per_inv", 2),
    ("Per person", "Verksamheter per arbetsplats (t/år)", "verks_t_per_arb", 2),
    ("Per person", "Mobilitet per invånare (t/år)", "mobilitet_t_per_inv", 2),
    ("Per person", "Mat, flyg och övrig konsumtion per invånare (t/år)", "konsumtion_t_per_inv", 2),
    ("Per person", "Nivå 2 per invånare (t/år)", "niva2_t_per_inv", 2),
    ("Per person", "Nivå 3 per invånare (t/år)", "niva3_t_per_inv", 2),
    ("Hela perioden", "Nivå 1 från startår till slutår, t per personår", "niva1_t_per_personar", 2),
]


def varde(a: dict, nyckel) -> float:
    return float(nyckel(a) if callable(nyckel) else a[nyckel])


def tabell(analyser: dict[str, dict]) -> pd.DataFrame:
    """Jämförelsetabell: en rad per mått och en kolumn per scenario."""
    rader = []
    for grupp, namn, nyckel, dec in MATT:
        if all("standardiserad_kg_m2_ar" not in a for a in analyser.values()) and nyckel == "standardiserad_kg_m2_ar":
            continue
        rader.append({"Grupp": grupp, "Mått": namn, **{n: round(varde(a, nyckel), dec) for n, a in analyser.items()}})
    return pd.DataFrame(rader)


def forklaring(bas: dict, x: dict) -> dict:
    """Skillnaden i nivå 1 boende per invånare (t/år) mellan x och bas, uppdelad på yta per invånare och utsläpp per m².
    Uppdelningen är exakt: medelvärdet av de två faktorerna används som vikt (två-faktor-Shapley)."""
    a0, a1 = bas["bta_boende_per_inv"], x["bta_boende_per_inv"]
    i0, i1 = bas["lc_kg_m2_ar_boende"], x["lc_kg_m2_ar_boende"]
    yta = (a1 - a0) * (i0 + i1) / 2 / 1000
    intens = (i1 - i0) * (a0 + a1) / 2 / 1000
    komp = {k: (x["lc_delar_boende"][k] - bas["lc_delar_boende"][k]) * (a0 + a1) / 2 / 1000 for k in KOMPONENTER}
    return {"totalt": x["niva1_boende_t_per_inv"] - bas["niva1_boende_t_per_inv"], "yta": yta, "intensitet": intens,
            "komponenter": komp, "mobilitet": x["mobilitet_t_per_inv"] - bas["mobilitet_t_per_inv"],
            "yta_per_inv": (a0, a1), "personer_per_hushall": (bas["personer_per_hushall"], x["personer_per_hushall"])}
