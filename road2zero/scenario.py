"""Scenario: alla indata för ett projekt, som ett JSON-vänligt lexikon.

Ett scenario sparas och läses som JSON med modellversion. Standardvärden hämtas ur
faktabiblioteket, så att ett tomt fält alltid betyder schablon med källa.
"""
from __future__ import annotations

import copy
import json

from . import __version__
from .factlib import Faktabibliotek, ladda
from .konstanter import (BYGGNADSTYPER, MARKTYPER, OUPPVARMDA_KLASSER, SCHABLON_PRODUKT, STANDARD_VIRKESPRODUKT, STANDARDKLASS,
                         STOMME_MIGRERING, STOMMAR, TILL_MARK, TRASTOMMAR, VIRKESPRODUKTER)
from .utveckling import standard as utveckling_standard


def standard_mat(fb: Faktabibliotek) -> dict:
    kp = fb.kostprofiler
    return {
        "andelar": {r.profil: float(r.andel_standard) for r in kp.itertuples()},
        "avtryck": {r.profil: float(r.kg_co2e_per_dag) for r in kp.itertuples()},
        "kalibrering": False,
        "omstallning": False,
        "mal_andelar": {r.profil: float(r.andel_standard) for r in kp.itertuples()},
        "malar": 2045,
    }


def standard_ovrig(fb: Faktabibliotek) -> dict:
    tot = fb.param("ovr.hushall_total")
    return {"varden": {r.kategori: round(float(r.andel_av_hushall) * tot, 4) for r in fb.ovrig.itertuples()}}


def standard_mobilitet(fb: Faktabibliotek, kommun: str) -> dict:
    k = fb.kommuner[fb.kommuner["kommun"] == kommun]
    if k.empty:
        k = fb.kommuner[fb.kommuner["kommun"] == "Annan kommun"]
    k = k.iloc[0]
    return {
        "kommunvarden": True,
        "bilar_per_hushall": float(k["bilar_per_hushall"]),
        "km_per_bil": float(k["km_per_bil"]),
        "mix": {d: fb.param(f"mob.mix.{d}") for d in ["petrol", "diesel", "hev", "bev", "phev", "biogas"]},
        "phev_eldrift": fb.param("mob.phev_eldrift"),
        "bensin_fossil": fb.param("mob.bensin.fossil"),
        "diesel_fossil": fb.param("mob.diesel.fossil"),
    }


def standardklass(typ: str) -> str:
    return STANDARDKLASS.get(typ, "C")


def standard_fjv_andel(klass: str) -> float:
    """Förvald andel fjärrvärme (%) för fastighetsvärmen: 100 % för uppvärmda klasser A–G, 0 % för garage och liknande."""
    return 0.0 if klass in OUPPVARMDA_KLASSER else 100.0


def ny_andel(typ: str = "flerbostadshus", stomme: str = "generisk", bta: float = 10000.0, ar: int = 2028, **kw) -> dict:
    """En andel av byggbeståndet: en byggnadstyp med en stomme och egna energival."""
    klass = kw.pop("energiklass", None) or standardklass(typ)
    b = {
        "namn": "", "typ": typ, "stomme": stomme, "bta": float(bta),
        "forsta_ar": int(ar), "sista_ar": int(ar), "fordelning": "jämn", "takt": {},
        "manuellt_kg_m2": None,
        "energiklass": klass, "fjv_andel": standard_fjv_andel(klass), "egen_fjv_kwh": None, "egen_el_kwh": None,
        "sol_m2": 0.0,
        "palning": False, "paln_andel": 100.0, "spont_m2": 0.0,
        "virke_m3_m2": None, "virkesprodukt": SCHABLON_PRODUKT,
    }
    b.update(kw)
    return b


def etikett(b: dict) -> str:
    """Visningsnamn för en andel: eget namn eller typ och stomme."""
    if b.get("namn"):
        return str(b["namn"])
    return f"{BYGGNADSTYPER.get(b['typ'], (b['typ'],))[0]}, {STOMMAR.get(b.get('stomme') or 'generisk', b.get('stomme'))}"


def ar_tra(b: dict) -> bool:
    return (b.get("stomme") or "generisk") in TRASTOMMAR


def virke_m3_m2(b: dict, fb: Faktabibliotek) -> float:
    """Virke per m² BTA: eget värde, annars schablonen för trästommar och noll för andra stommar."""
    v = b.get("virke_m3_m2")
    if v not in (None, "") and not (isinstance(v, float) and v != v):
        return float(v)
    return fb.param("bygg.virke_m3_m2") if ar_tra(b) else 0.0


def virkesprodukt(b: dict) -> str:
    """Träprodukt för kolinlagringen: valt värde, annars schablonen för stommen (stomvirke för Trä BAU, limträ för Trä BÄST)."""
    p = b.get("virkesprodukt") or SCHABLON_PRODUKT
    if p == "Limträ":
        p = "Limträ/glulam"
    if p in VIRKESPRODUKTER:
        return p
    return STANDARD_VIRKESPRODUKT.get(b.get("stomme"), "Stomvirke")


def migrera_byggnad(b: dict) -> list[dict]:
    """Läser en byggnadsrad i det äldre formatet (två stommar med andelar och fjärrvärmeandel) som andelar."""
    if "stomme" in b:
        return [b]
    a1 = max(0.0, min(100.0, float(b.get("andel1", 100) or 0))) / 100
    delar = [(b.get("stomme1") or "generisk", a1)]
    if a1 < 1:
        delar.append((b.get("stomme2") or "generisk", 1 - a1))
    out = []
    for st, andel in delar:
        n = {k: v for k, v in b.items() if k not in ("stomme1", "stomme2", "andel1", "fjv_andel")}
        n.update(stomme=st, bta=float(b.get("bta", 0)) * andel, sol_m2=float(b.get("sol_m2") or 0) * andel,
                 spont_m2=float(b.get("spont_m2") or 0) * andel,
                 takt={a: float(v) * andel for a, v in (b.get("takt") or {}).items()},
                 fjv_andel=float(b.get("fjv_andel", 1.0)) * 100,
                 namn="" if len(delar) > 1 else b.get("namn", ""))
        if STOMME_MIGRERING.get(st, st) not in TRASTOMMAR:
            n["virke_m3_m2"] = None
        out.append(ny_andel(**{**n}))
    return out


def tomt(fb: Faktabibliotek | None = None) -> dict:
    """Ett nytt projekt: inga byggnader, ingen anläggning och ingen mark, men alla schabloner förifyllda med källa."""
    fb = fb or ladda()
    return {
        "modellversion": __version__,
        "projekt": {"namn": "Nytt projekt", "kommun": "Annan kommun", "fas": "Detaljplan, samråd", "startar": 2026, "slutar": 2076},
        "fjarrvarme": {"startvarde": fb.param("fjv.startvarde")},
        "utveckling": utveckling_standard(fb),
        "hushall": {"personer_per_hushall": fb.param("allm.personer_per_hushall"),
                    "bta_per_hushall": fb.param("allm.bta_per_hushall")},
        "byggnader": [],
        "anlaggning": {"ytor": [], "massor": [], "betong": [], "ledningar": [], "engangsvarden": []},
        "mark": {"overgangar": [], "pooler": {}, "bevarande": {}},
        "mobilitet": standard_mobilitet(fb, "Annan kommun"),
        "mat": standard_mat(fb),
        "ovrig": standard_ovrig(fb),
        "flyg": {"per_inv": fb.param("flyg.per_inv")},
        "offentlig": {"konsumtion": fb.param("off.konsumtion"), "investeringar": fb.param("off.investeringar"),
                      "andel": fb.param("off.andel")},
        "negativa": {"biokol": [], "trad": []},
        "budget": {"temperatur": "1,5", "sannolikhet": 50, "niva": 3},
        "parametrar": {},
    }


def exempel(fb: Faktabibliotek | None = None) -> dict:
    """Testfall med påhittade indata. Används bara av testerna, inte av gränssnittet."""
    fb = fb or ladda()
    s = tomt(fb)
    s["projekt"].update(namn="Testfall", kommun="Helsingborg")
    s["mobilitet"] = standard_mobilitet(fb, "Helsingborg")
    s["byggnader"] = [
        ny_andel("flerbostadshus", "tra_bau", 36000, 2027, sista_ar=2031, energiklass="B", sol_m2=1200, palning=True),
        ny_andel("flerbostadshus", "betong_bast", 24000, 2027, sista_ar=2031, energiklass="B", sol_m2=800, palning=True),
        ny_andel("kontor", "generisk", 15000, 2030, energiklass="C", palning=True),
        ny_andel("skola", "tra_bau", 6000, 2029, energiklass="B", sol_m2=600),
    ]
    s["anlaggning"]["ytor"] = [
        {"typ": t, "utforande": "standard", "yta_m2": a, "forsta_ar": 2027, "sista_ar": 2031}
        for t, a in [("lokalgata", 18000), ("gc_vag", 6000), ("torg", 4000), ("park", 12000), ("bostadsgard", 14000)]]
    s["anlaggning"]["massor"] = [{"typ": "Schakt", "volym_m3": 20000, "transport_km": 15, "forsta_ar": 2027, "sista_ar": 2031}]
    s["mark"]["overgangar"] = [
        {"fran": "Åkermark", "till": "Bebyggd kvartersmark", "ha": 8.0, "ar": 2027,
         "tradslag": "Blandskog (gran/bok)", "skotsel": "Fri utveckling", "skogsalder": 40},
        {"fran": "Blandskog", "till": "Bevarad", "ha": 3.0, "ar": 2027,
         "tradslag": "Blandskog (gran/bok)", "skotsel": "Fri utveckling", "skogsalder": 80},
        {"fran": "Betes- och gräsmark", "till": "Nyplanterad skog", "ha": 1.5, "ar": 2028,
         "tradslag": "Blandskog (gran/bok)", "skotsel": "Fri utveckling", "skogsalder": 40},
    ]
    s["negativa"] = {"biokol": [{"gropar": 150, "ar": 2028, "certifierat": True}],
                     "trad": [{"antal": 400, "planteringsar": 2031}]}
    return s


def takt(b: dict) -> dict[int, float]:
    """Färdigställd BTA per år för en byggnadsrad."""
    if b.get("fordelning") == "egen" and b.get("takt"):
        return {int(k): float(v) for k, v in b["takt"].items() if float(v or 0) > 0}
    a0, a1 = int(b["forsta_ar"]), int(b["sista_ar"])
    if a1 < a0:
        a1 = a0
    ar = list(range(a0, a1 + 1))
    n = len(ar)
    if b.get("fordelning") == "framtung":
        vikt = [n - i for i in range(n)]
    elif b.get("fordelning") == "baktung":
        vikt = [i + 1 for i in range(n)]
    else:
        vikt = [1] * n
    s = sum(vikt)
    return {a: float(b["bta"]) * v / s for a, v in zip(ar, vikt)}


def validera(s: dict, fb: Faktabibliotek | None = None) -> list[tuple[str, str, str]]:
    """Kontroller före beräkning. Returnerar (allvar, modul, text)."""
    fb = fb or ladda()
    fel = []
    p = s["projekt"]
    if p["slutar"] <= p["startar"]:
        fel.append(("fel", "Projekt", "Slutåret måste vara senare än startåret."))
    for i, b in enumerate(s["byggnader"], 1):
        namn = f"Andel {i} ({etikett(b)})"
        t = takt(b)
        if b["typ"] not in BYGGNADSTYPER:
            fel.append(("fel", "Byggnader", f"{namn}: okänd byggnadstyp {b['typ']}."))
            continue
        if b.get("stomme") not in STOMMAR:
            fel.append(("fel", "Byggnader", f"{namn}: okänd stomme {b.get('stomme')}."))
        if not t:
            fel.append(("varning", "Byggnader", f"{namn}: ingen BTA blir klar."))
        elif min(t) < p["startar"] or max(t) > p["slutar"]:
            fel.append(("varning", "Byggnader", f"{namn}: BTA blir klar utanför tidsperioden och räknas inte det året."))
        if b.get("fordelning") == "egen" and abs(sum(t.values()) - float(b["bta"])) > 1:
            fel.append(("varning", "Byggnader", f"{namn}: utbyggnadstakten summerar till {sum(t.values()):,.0f} m², inte {float(b['bta']):,.0f} m².".replace(",", " ")))
        klasser = fb.energiklasser_for(b["typ"])
        if b.get("energiklass") not in klasser:
            fel.append(("fel", "Byggnader", f"{namn}: energiklass {b.get('energiklass')} finns inte för typen; välj bland {', '.join(klasser)}."))
        try:
            fa = float(b.get("fjv_andel", 100))
        except (TypeError, ValueError):
            fa = -1
        if not 0 <= fa <= 100:
            fel.append(("fel", "Byggnader", f"{namn}: andelen fjärrvärme ska ligga mellan 0 och 100 %."))
        elif b.get("energiklass") in OUPPVARMDA_KLASSER and fa > 0:
            fel.append(("varning", "Byggnader", f"{namn}: klassen {b['energiklass']} har ingen fjärrvärme; all värme räknas som el."))
        for falt, text in (("egen_el_kwh", "köpt el"), ("egen_fjv_kwh", "köpt fjärrvärme")):
            if b.get(falt) not in (None, "") and float(b[falt]) < 0:
                fel.append(("fel", "Byggnader", f"{namn}: egen {text} per m² BTA kan inte vara negativ."))
        if float(b.get("virke_m3_m2") or 0) > 0 and not ar_tra(b):
            fel.append(("varning", "Byggnader", f"{namn}: virke anges men stommen är inte Trä BAU eller Trä BÄST; kolinlagringen räknas inte."))
    for o in s["mark"]["overgangar"]:
        if o["fran"] not in MARKTYPER or o["till"] not in TILL_MARK:
            fel.append(("fel", "Markanvändning", f"Okänd övergång {o['fran']} → {o['till']}."))
        if o["till"] == "Nyplanterad skog" and o["fran"] in ("Barrskog", "Lövskog", "Blandskog"):
            fel.append(("varning", "Markanvändning", "Nyplantering på befintlig skog räknas som plantering på gräsmark."))
    andelar = s["mat"]["andelar"]
    if abs(sum(andelar.values()) - 1) > 0.005:
        fel.append(("fel", "Matkonsumtion", f"Kostprofilernas andelar summerar till {sum(andelar.values())*100:.1f} %, inte 100 %."))
    mix = s["mobilitet"]["mix"]
    if abs(sum(mix.values()) - 1) > 0.005:
        fel.append(("fel", "Mobilitet", f"Drivlinemixen summerar till {sum(mix.values())*100:.1f} %, inte 100 %."))
    if not s["byggnader"]:
        fel.append(("info", "Byggnader", "Inga byggnader ännu: invånare och invånarnas utsläpp blir noll."))
    return fel


def till_json(s: dict) -> str:
    return json.dumps(s, ensure_ascii=False, indent=2)


def fran_json(text: str, fb: Faktabibliotek | None = None) -> dict:
    """Läser sparade indata och fyller på nycklar som saknas med standardvärden.
    Byggnadsrader i det äldre formatet delas upp i andelar med en stomme var."""
    data = json.loads(text)
    bas = tomt(fb)

    def fyll(d, b):
        for k, v in b.items():
            if k not in d:
                d[k] = copy.deepcopy(v)
            elif isinstance(v, dict) and isinstance(d[k], dict) and k not in ("takt", "pooler", "bevarande", "parametrar", "utveckling"):
                fyll(d[k], v)
    fyll(data, bas)
    data["projekt"].pop("scenario", None)
    data.pop("el", None)
    for nyckel in ("mat", "ovrig", "flyg", "offentlig"):
        data[nyckel].pop("forandring", None)
    for nyckel in ("elbilsandel", "effektivisering"):
        data["mobilitet"].pop(nyckel, None)
    data["fjarrvarme"].pop("kurva", None)
    andelar = []
    for b in data["byggnader"]:
        for a in migrera_byggnad(b):
            if "uppvarmning" in a:     # äldre: fjärrvärme eller el som val
                a["fjv_andel"] = 100.0 if a.pop("uppvarmning") == "fjärrvärme" else 0.0
            a["stomme"] = STOMME_MIGRERING.get(a.get("stomme"), a.get("stomme"))
            if a.get("stomme") not in STOMMAR:
                a["stomme"] = "generisk"
            a.pop("ccf_andel", None)               # kolinlagringen kräver inte längre CCF-certifikat
            if a.get("virkesprodukt") == "Limträ":
                a["virkesprodukt"] = "Limträ/glulam"
            andelar.append(ny_andel(**a))
    data["byggnader"] = andelar
    data["modellversion"] = __version__
    return data
