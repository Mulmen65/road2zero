"""Bygger tre Road2Zero-fall i Malmö: Västra hamnen (från 2000), Varvsstaden (från 2020) och Jägersro SMT (från 2030), alla till 2050.
Alla tre använder samma schabloner för arbetsplatser, närservice, mobilitetshus, gator och fjärrvärme, så att de kan jämföras.

Kör från repots rot:  python verktyg/bygg_malmofall.py            # skriver fall/vastra_hamnen.json, fall/varvsstaden.json och fall/jagersro_smt.json
Varje byggnadsrad, yta och massa har en rad i "dokumentation" med underlag och status (Uppgift, Kalibrerat eller Antagande).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT))
from road2zero.factlib import ladda  # noqa: E402
from road2zero.scenario import ny_andel, standard_mobilitet, tomt  # noqa: E402

UT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROT / "fall"
fb = ladda()

FJV_2024 = 55.3
# Närservice (förskolor och grundskola) med samma schablon per bostad i alla fall som jämförs:
# en förskola på 1 300 m² per 800 bostäder och en grundskola på 9 000 m² per 4 000 bostäder = 3,875 m² BTA per bostad (antagande).
NARSERVICE_M2_PER_BOSTAD = (5 * 1300 + 9000) / 4000
NARSERVICE_TEXT = ("Samma schablon per bostad i alla jämförda fall: en förskola på 1 300 m² per 800 bostäder och en grundskola på 9 000 m² "
                   "per 4 000 bostäder, 3,9 m² BTA per bostad (antagande). Skolgård 1 m² per m² BTA.")   # g CO2e/kWh, Energiföretagen, medelvärde för levererad fjärrvärme 2024 (riksgenomsnitt)

# ---------------------------------------------------------------- källor
K = {
    "MALMO_VH": ("Malmö stad: Västra Hamnen (stadsutvecklingsområde)", "https://malmo.se/Stadsutveckling/Stadsutvecklingsomraden/Vastra-Hamnen.html"),
    "MALMO_VH_HIST": ("Malmö stad: Västra hamnen, platser och byggnader", "https://malmo.se/Uppleva-och-gora/Arkitektur-och-kulturarv/Malmos-historia/Platser-och-byggnader/Stadsdelar-och-omraden/Vastra-hamnen.html"),
    "WIKI_VH": ("Wikipedia: Västra hamnen", "https://en.wikipedia.org/wiki/V%C3%A4stra_hamnen"),
    "WIKI_BO01": ("Wikipedia: Bo01", "https://en.wikipedia.org/wiki/Bo01"),
    "WIKI_UNIHOLMEN": ("Wikipedia: Universitetsholmen", "https://en.wikipedia.org/wiki/Universitetsholmen"),
    "CTCN_VH": ("CTCN: Western Harbour, Malmö (energisystemet i Bo01)", "https://www.ctc-n.org/"),
    "MMO_DELOMR_2006": ("Malmö stad: Områdesfakta delområden 2006", "https://mmostatfiler.malmo.se/delomraden/delomraden_2006.pdf"),
    "MMO_DELOMR_2001": ("Malmö stad: Områdesfakta delområden 2001", "https://mmostatfiler.malmo.se/delomraden/delomraden_2001.pdf"),
    "MMO_PROGNOS_2023": ("Malmö stad: Befolkningsprognos 2023–2033", "https://motenmedborgarportal.malmo.se/"),
    "NEWSWORTHY_REGSO": ("Newsworthy: befolkning per RegSO, Västra hamnen", "https://newsworthy.se/"),
    "FOJAB_ORKANEN": ("Fojab: Lärarhögskolan Orkanen", "https://fojab.se/en/project/lararhogskolan-orkanen/"),
    "FT_NIAGARA": ("Fastighetstidningen: Byggstart för Malmö högskolas nya profilbyggnad Niagara (2012)", "https://fastighetstidningen.se/nyhet/byggstart-for-malmo-hogskolas-nya-profilbyggnad-niagara/"),
    "WIKI_MALMOLIVE": ("Wikipedia: Malmö Live", "https://en.wikipedia.org/wiki/Malm%C3%B6_Live"),
    "SKANDIA_GYMN": ("Skandia Fastigheter: hyr ut 9 000 kvadratmeter till Malmö stads nya gymnasium", "https://skandiafastigheter.mynewsdesk.com/pressreleases/skandia-fastigheter-hyr-ut-9-000-kvadratmeter-till-malmoe-stads-nya-gymnasium-3278723.pdf"),
    "SKANDIA_TAMPEN": ("Skandia Fastigheter: kvarteret Tampen i Västra hamnen", "https://skandiafastigheter.mynewsdesk.com/"),
    "REJLERS_CITADELLSFOGEN": ("Rejlers: Malmö stad anlitar Rejlers för infrastrukturen i Västra Hamnen (Citadellsfogen, 2024)", "https://www.rejlers.com/newsroom/news/2024/07/the-city-of-malmo-appoints-rejlers-for-the-reconstruction-and-expansion-of-infrastructure-in-vastra-hamnen/"),
    "NORD_VARVSSTADEN": ("NORD Architects: Varvsstaden school district", "https://www.nordarchitects.dk/projects/varvsstaden-school-district/"),
    "PEAB_HALL259_SV": ("Peab: pressmeddelande om Hall 259 (Stora Varvsgatan, nordvästra hörnet av Varvsstaden)", "https://peab.se/globalassets/cision/documents/swedish/pressmeddelande__-_peab_bygger_i_varvsstaden_i_malmo.pdf"),
    "MALMO_JAGERSRO_2024": ("Malmö stad: Nya Jägersro blir en hållbar stadsdel i absoluta framkant (pressmeddelande)",
                            "https://www.mynewsdesk.com/se/malmo/pressreleases/nya-jaegersro-blir-en-haallbar-stadsdel-i-absoluta-framkant-3325882"),
    "FOP_JAGERSRO": ("Malmö stad: Översiktsplan för Jägersro, granskningshandling (s. 14–15: 4 300 bostäder, 440 000 m² bostads-BTA, 8 900 invånare, park > 5 ha)",
                     "https://malmo.se/Stadsutveckling/Det-har-ar-pa-gang-i-Malmo/Fordjupad-oversiktsplan-for-Jagersro.html"),
    "SBN_JAGERSRO_2025": ("Malmö stad: Tjänsteskrivelse SBN 2025-06-19, Översiktsplan för Jägersro (fem förskolor, en grundskola; travbanan flyttar 2028)",
                          "https://motenmedborgarportal.malmo.se/welcome-sv/namnder-styrelser/stadsbyggnadsnamnden/mote-2025-06-19/agenda/g-tjansteskrivelse-sbn-2025-06-19-oversiktsplan-for-jagersropdf?downloadMode=open"),
    "SMT_AVGRANSNING": ("Användarens avgränsning av SMT: 4 000 bostäder och 41 ha", ""),
    "CISION_VARV": ("Varvsstaden: underlag till Planpriset", "https://mb.cision.com/Main/20015/4130926/3367853.pdf"),
    "EHH_VARV": ("European Heritage Hub: Varvsstaden, Malmö", "https://europeanheritagehub.eu/"),
    "AFFV_PEAB": ("Affärsvärlden: Peab säljer i Malmö (Varvsstaden, 350 000 m² byggrätter)", "https://www.affarsvarlden.se/artikel/peab-saljer-i-malmo-6773366"),
    "BJURFORS_FYRSKEPPET": ("Bjurfors: Brf Fyrskeppet, objektbeskrivning (2021)", "https://www.bjurfors.se/contentassets/b7fe9b3f03f24fe09eec7689cb124873/brf-fyrskeppet.pdf"),
    "DPS_VARVSPORTEN": ("Dagens PS: Peabs nya betongbostäder i Malmös industriområde (Varvsporten)", "https://www.dagensps.se/teknik/peabs-nya-betongbostader-i-malmos-industriomrade/"),
    "SWEDISHWOOD_GJUTERIET": ("Swedish Wood: Gjuteriet, Malmö", "https://www.swedishwood.com/"),
    "PEAB_BRO": ("Peab: Peab bygger bro till Varvsstaden i Malmö (2022)", "https://peab.com/press/pressreleases/2022/may/peab-builds-bridge-to-varvstaden-in-malmo"),
    "PEAB_HALL259": ("Peab: Peab bygger kontor, butiker och parkeringshus i Malmö (Hall 259, 2024)", "https://www.peab.com/press/pressreleases/2024/august/peab-builds-offices-stores-and-parking-garage-in-malmo/"),
    "IPE_HALL259": ("PropertyEU: Peab to develop €40m mixed-use complex in Malmö", "https://realassets.ipe.com/propertyeu/peab-to-develop-40m-mixed-use-complex-in-malm%C3%B6/10089239.article"),
    "MALMO_HOGTHUS": ("Malmö stad: Arkitekttävling Högt hus i Västra Varvsstaden", "https://malmo.se/Arkitekttavlingar/Hogt-hus-i-Vastra-Varvsstaden.html"),
    "MALMO_PARKERING": ("Malmö stad: Policy och norm för mobilitet och parkering", "https://malmo.se/Stadsutveckling/Sa-utvecklar-vi-staden/Resande-och-infrastruktur/Policy-och-norm-for-mobilitet-och-parkering.html"),
    "MALMO_POLICY_2026": ("Malmö stad: Ny policy ska göra det enklare att leva, röra sig och trivas i Malmö (2026)", "https://www.mynewsdesk.com/se/malmo/pressreleases/ny-policy-ska-goera-det-enklare-att-leva-roera-sig-och-trivas-i-malmoe-3429463"),
    "EF_HIST_2024": ("Energiföretagen: Miljövärden, historiska medelvärden (fjärrvärme 2024)", "https://www.energiforetagen.se/49dccf/globalassets/energiforetagen/statistik/fjarrvarme/miljovardering-av-fjarrvarme/2024/miljovarden-historiska-medelvarden.pdf"),
    "EF_LOKALA": ("Energiföretagen: Fjärrvärmens lokala miljövärden", "https://www.energiforetagen.se/statistik/fjarrvarmestatistik/miljovardering-av-fjarrvarme/"),
    "SCB_TRAFA_MALMO": ("Road2Zero faktabibliotek: Malmö, bilar per hushåll och körsträcka (SCB, Trafikanalys)", ""),
}


def kalla(*ids):
    return [k for k in ids]


DOK_ANDELAR: list[dict] = []


def andel(namn, typ, stomme, bta, a0, a1=None, *, status, underlag, kallor, takt=None, fordelning="jämn", **kw):
    b = ny_andel(typ, stomme, round(bta), a0, sista_ar=a1 or a0, namn=namn, fordelning=fordelning, **kw)
    if takt:
        b["fordelning"] = "egen"
        b["takt"] = {str(a): round(v) for a, v in takt.items()}
        b["bta"] = float(sum(round(v) for v in takt.values()))
        b["forsta_ar"], b["sista_ar"] = min(takt), max(takt)
    DOK_ANDELAR.append({"namn": namn, "bta_m2": b["bta"], "ar": f"{b['forsta_ar']}–{b['sista_ar']}" if b["sista_ar"] != b["forsta_ar"] else str(b["forsta_ar"]),
                        "status": status, "underlag": underlag, "kallor": list(kallor)})
    return b


def bostader(namn, lgh, bta_lgh, a0, a1=None, takt_lgh=None, **kw):
    takt = {a: n * bta_lgh for a, n in takt_lgh.items()} if takt_lgh else None
    kw["underlag"] = f"{lgh:,} bostäder × {bta_lgh} m² BTA. ".replace(",", " ") + kw["underlag"]
    return andel(namn, "flerbostadshus", kw.pop("stomme", "generisk"), lgh * bta_lgh, a0, a1, takt=takt, **kw)


def yta(typ, m2, a0, a1, underlag, status="Antagande", kallor=()):
    return {"typ": typ, "utforande": "standard", "yta_m2": float(m2), "forsta_ar": a0, "sista_ar": a1,
            "_dok": {"underlag": underlag, "status": status, "kallor": list(kallor)}}


def strip_dok(rader):
    dok = []
    for r in rader:
        d = r.pop("_dok", None)
        if d:
            dok.append({"post": r.get("typ") or r.get("namn") or r.get("fran", ""), **{k: v for k, v in r.items() if k in ("yta_m2", "volym_m3", "meter", "t_co2e", "forsta_ar", "sista_ar", "ar", "ha", "till", "antal", "planteringsar")}, **d})
    return dok


def kallista(dok_anl):
    """Källorna som fallet använder: andelarnas och anläggningens källor plus de gemensamma för energi och mobilitet."""
    ids = []
    for d in DOK_ANDELAR + dok_anl:
        ids += [i for i in d.get("kallor", []) if i not in ids]
    ids += [i for i in ("EF_HIST_2024", "EF_LOKALA", "SCB_TRAFA_MALMO", "MALMO_PARKERING") if i not in ids]
    return [{"id": i, "titel": K[i][0], "url": K[i][1]} for i in ids]


def gemensam_dok():
    return {
        "Energi": [
            f"Fjärrvärmens klimatfaktor {FJV_2024} g CO2e/kWh: Energiföretagens medelvärde för levererad fjärrvärme 2024 (riksgenomsnitt). "
            "E.ON:s lokala miljövärde för Malmönätet kunde inte läsas (tabellen finns som Excel hos Energiföretagen). Byt till ortens värde och använd samma värde i alla fall som jämförs.",
            "Elens klimatfaktor: modellens standard (Boverket 37 g CO2e/kWh) och utveckling enligt fliken Emissionsfaktorer över tid.",
            "Andel fjärrvärme 100 % för uppvärmda byggnader: i princip alla bostäder i området är anslutna till fjärrvärme (Bo01:s lokala system med akviferlager, värmepump och solfångare levererar till nätet).",
            "Energiklass efter byggår (antagande): D för 2001–2015 (byggregler före BBR 2015/2020 och uppföljda avvikelser mot Bo01:s mål), C från 2016 (nybyggnadskrav), B för Svanenmärkta hus i Varvsstaden.",
        ],
        "Tid": [
            "Modellen räknar inte bakåt: startvärdena 2026 gäller för alla år före 2026 (byggpåverkan, el, fjärrvärme, drivlinemix, konsumtion). "
            "Faktiska utsläpp före 2026 var högre (äldre byggmetoder, mer fossil el och fjärrvärme, nästan inga elbilar), så resultaten före 2026 är en undre skattning.",
            "Klimatbudgeten (Forster m.fl. 2026) börjar 2026. År före 2026 har ingen budgetandel men deras utsläpp räknas in i den kumulativa summan. Jämför därför också perioden 2026–2050 eller 2030–2050.",
        ],
        "Konsumtion": [
            "Mat, övrig konsumtion, flyg och offentlig sektor: modellens standardvärden per invånare (Sverige). Ingen justering för inkomstnivå, så att fallen kan jämföras med samma antaganden.",
        ],
    }


# ================================================================ VÄSTRA HAMNEN
def vastra_hamnen():
    s = tomt(fb)
    s["projekt"].update(namn="Västra hamnen väster om Stora Varvsgatan, Malmö", kommun="Malmö", fas="Genomförande", startar=2000, slutar=2050)
    s["fjarrvarme"]["startvarde"] = FJV_2024
    s["hushall"] = {"personer_per_hushall": 1.70, "bta_per_hushall": 110.0}
    mob = standard_mobilitet(fb, "Malmö")
    mob.update(kommunvarden=False, bilar_per_hushall=0.50)
    s["mobilitet"] = mob
    BTA = 110
    U = dict(status="Uppgift")
    A = dict(status="Antagande")
    C = dict(status="Kalibrerat")
    b = []
    # --- bostäder
    b.append(bostader("Bo01, bomässan och första etappen", 1024, BTA, 2001, 2005, takt_lgh={2001: 400, 2002: 150, 2003: 150, 2004: 150, 2005: 174},
                      energiklass="D", palning=True, sol_m2=120.0, **U,
                      underlag="Bo01 (22 ha) byggdes från 2000 med bomässan 2001. Antalet bostäder t.o.m. 2005 är 1 171 (delområdesstatistik 2006) minus Turning Torsos 147. "
                               "Fördelningen per år är ett antagande. 120 m² solceller på Bo01; solfångarna (1 400 m²) levererar till fjärrvärmenätet och räknas inte här.",
                      kallor=kalla("WIKI_BO01", "MMO_DELOMR_2006", "CTCN_VH")))
    b.append(bostader("Turning Torso, bostäder", 147, BTA, 2005, stomme="betong_bau", energiklass="D", **U,
                      underlag="147 lägenheter, invigt 2005. Betongstomme. Grundlagt på berg (ingen pålning). BTA per lägenhet som för området.",
                      kallor=kalla("WIKI_VH", "MMO_DELOMR_2006")))
    b.append(bostader("Bo01-området, kompletteringar", 401, BTA, 2007, 2010, energiklass="D", palning=True, **C,
                      underlag="Bo01-området har totalt 1 425 bostäder; resterande 401 efter 2006. År är ett antagande.",
                      kallor=kalla("WIKI_BO01")))
    b.append(bostader("Flagghusen", 650, BTA, 2007, 2008, takt_lgh={2007: 300, 2008: 350}, energiklass="D", palning=True, **U,
                      underlag="Cirka 650 lägenheter, inflyttning till och med 2008.", kallor=kalla("MALMO_VH_HIST", "WIKI_VH")))
    b.append(bostader("Fullriggaren", 645, BTA, 2010, 2013, energiklass="C", palning=True, **U,
                      underlag="645 bostäder 2010–2013.", kallor=kalla("MALMO_VH_HIST", "WIKI_VH")))
    b.append(bostader("Dockan m.fl. 2010–2013", 1167, BTA, 2010, 2013, takt_lgh={2010: 40, 2011: 70, 2012: 500, 2013: 557},
                      energiklass="D", palning=True, **C,
                      underlag="Kalibrerad rest: antalet bostäder som behövs för att modellens invånare ska träffa statistiken 2011 (4 512) och 2013 (6 857) med 1,70 personer per hushåll.",
                      kallor=kalla("NEWSWORTHY_REGSO", "MMO_PROGNOS_2023")))
    b.append(bostader("Kvarter 2014–2022 (kalibrerat mot befolkningen)", 3260, BTA, 2014, 2022, energiklass="C", palning=True, **C,
                      underlag="Kalibrerad rest mot 12 909 invånare 2022, efter Masthusens första 300 bostäder.",
                      kallor=kalla("NEWSWORTHY_REGSO", "MMO_PROGNOS_2023")))
    mt = {2021: 100, 2022: 200, **{a: 160 for a in range(2023, 2033)}}
    b.append(bostader("Masthusen, bostäder", 1900, BTA, 2021, 2032, takt_lgh=mt, energiklass="C", palning=True, **U,
                      underlag="Masthusen: 1 900 bostäder och 590 studentbostäder. Fördelningen per år är ett antagande (sista etappen omkring 2032).",
                      kallor=kalla("MALMO_VH", "WIKI_VH")))
    b.append(andel("Masthusen, studentbostäder", "flerbostadshus", "generisk", 590 * 40, 2025, 2026, energiklass="C", palning=True, **U,
                   underlag="590 studentbostäder × 40 m² BTA (antagande om storlek). Modellen räknar invånare med samma BTA per hushåll som övriga bostäder, så studenterna blir färre i modellen än i verkligheten.",
                   kallor=kalla("MALMO_VH")))
    b.append(bostader("Hamnporten", 170, BTA, 2026, 2027, energiklass="C", palning=True, **U, underlag="Cirka 170 bostäder; år är ett antagande.", kallor=kalla("MALMO_VH")))
    b.append(bostader("Tampen", 220, BTA, 2029, 2030, energiklass="C", palning=True, **U, underlag="Cirka 220 bostäder, byggstart 2027.", kallor=kalla("SKANDIA_TAMPEN")))
    b.append(bostader("Citadellsfogen, Galeonen och sista kvarteren", 1000, BTA, 2031, 2037, energiklass="C", palning=True, **C,
                      underlag="Kalibrerat mot prognosen 2033 och en färdig stadsdel omkring 2035–2037 (Galeonen sist). Prognosens invånare minus Varvsstadens. "
                               "Citadellsfogen (cirka 7 ha) är Västra hamnens sydvästra entré med bostäder, kontor, förskola och parkeringshus.",
                      kallor=kalla("MALMO_VH", "MMO_PROGNOS_2023", "REJLERS_CITADELLSFOGEN")))
    # --- lokaler
    b.append(andel("Turning Torso, kontor", "kontor", "betong_bau", 4200, 2005, energiklass="D", **A,
                   underlag="De nedre kuberna är kontor; ytan cirka 4 200 m² är en uppskattning.", kallor=kalla("WIKI_VH")))
    b.append(andel("Kontor 2002–2010", "kontor", "generisk", 70000, 2002, 2010, energiklass="D", palning=True, **C,
                   underlag="Kalibrerat mot cirka 16 000 arbetsplatser i dag: arbetsplatser i nya kontor × 20 m² BTA per arbetsplats (antagande). "
                            "Avdrag för arbetsplatser öster om Stora Varvsgatan (universitetet, Malmö Live och kontor på Universitetsholmen), skolor, handel och cirka 2 500 arbetsplatser i äldre byggnader.",
                   kallor=kalla("MALMO_VH")))
    b.append(andel("Kontor 2011–2024 (Dockan m.fl.)", "kontor", "generisk", 111800, 2011, 2024, energiklass="C", palning=True, **C,
                   underlag="Som ovan, minus cirka 1 500 arbetsplatser (30 000 m²) i nya kontor på Universitetsholmen; totalt cirka 186 000 m² nya kontor 2002–2024 väster om Stora Varvsgatan inklusive Turning Torso.", kallor=kalla("MALMO_VH")))
    b.append(andel("Masthusen, kontor (1 200 arbetsplatser)", "kontor", "generisk", 24000, 2023, 2032, energiklass="C", palning=True, **A,
                   underlag="1 200 arbetsplatser × 20 m² BTA (antagande).", kallor=kalla("MALMO_VH")))
    b.append(andel("Kontor 2026–2037 (Citadellsfogen, Hamnporten, Galeonen)", "kontor", "generisk", 76000, 2026, 2037, energiklass="C", palning=True, **C,
                   underlag="Visionen 25 000 arbetsplatser minus 16 000 i dag, minus Varvsstadens 4 000 och Masthusens 1 200, × 20 m² BTA.", kallor=kalla("MALMO_VH", "CISION_VARV", "REJLERS_CITADELLSFOGEN")))
    b.append(andel("Förskolor och grundskolor 2006–2015", "skola", "generisk", 4758 * NARSERVICE_M2_PER_BOSTAD, 2006, 2015, energiklass="D", palning=True, **A,
                   underlag="Cirka 4 760 bostäder byggda till 2015. " + NARSERVICE_TEXT, kallor=()))
    b.append(andel("Förskolor och grundskolor 2016–2037", "skola", "generisk", 5826 * NARSERVICE_M2_PER_BOSTAD, 2016, 2037, energiklass="C", palning=True, **A,
                   underlag="Cirka 5 830 bostäder från 2016 (utan studentbostäder). " + NARSERVICE_TEXT, kallor=("REJLERS_CITADELLSFOGEN",)))
    b.append(andel("Lokaler i bottenvåningar 2001–2015", "lokaler", "generisk", 20000, 2001, 2015, energiklass="D", palning=True, **A,
                   underlag="Handel och service, cirka 4 % av bostadsytan.", kallor=()))
    b.append(andel("Lokaler i bottenvåningar 2016–2037", "lokaler", "generisk", 25000, 2016, 2037, energiklass="C", palning=True, **A,
                   underlag="Som ovan.", kallor=()))
    # --- parkering
    b.append(andel("Garage under kvarter 2002–2015", "underjordisk_parkering", "generisk", 71400, 2002, 2015, **A,
                   underlag="0,5 bilplatser per bostad × 30 m² BTA per plats för bostäder byggda till 2015 (cirka 4 760).", kallor=()))
    b.append(andel("Mobilitetshus 2017–2036", "mobilitetshus", "generisk", 58300, 2017, 2036, **A,
                   underlag="0,4 bilplatser per bostad × 25 m² BTA per plats för bostäder från 2016 (cirka 5 830, utan studentbostäder). Malmös parkeringspolicy styr mot färre platser och gemensamma mobilitetshus.",
                   kallor=kalla("MALMO_PARKERING", "MALMO_POLICY_2026")))
    s["byggnader"] = b

    # --- anläggning
    ytor = [
        yta("huvudgata", 44000, 2001, 2035, "Huvudgator, cirka 2,7 % av 165 ha."),
        yta("lokalgata", 159000, 2001, 2037, "Lokalgator, cirka 10 % av 165 ha."),
        yta("gc_vag", 44000, 2001, 2037, "Gång- och cykelvägar."),
        yta("torg", 35000, 2001, 2037, "Torg och kajpromenader (bland annat Sundspromenaden)."),
        yta("park", 150000, 2001, 2037, "Parker cirka 15 ha (bland annat Ankarparken, Daniaparken, Scaniaparken, Stapelbäddsparken)."),
        yta("bostadsgard", 120000, 2001, 2037, "Bostadsgårdar."),
        yta("lekplats", 6000, 2001, 2037, "Lekplatser."),
        yta("skolgard", round(10584 * NARSERVICE_M2_PER_BOSTAD), 2006, 2037, "Skol- och förskolegårdar, 1 m² per m² BTA närservice (antagande, samma i alla fall)."),
        yta("markparkering", 15000, 2001, 2015, "Markparkering under utbyggnaden."),
    ]
    betong = [{"namn": "Kajer och strandpromenader", "utforande": "standard", "volym_m3": 24000.0, "forsta_ar": 2001, "sista_ar": 2035,
               "_dok": {"underlag": "Cirka 3 km kajkant × 8 m³ betong per meter. Kajernas yta har ingen schablon i modellen (0 kg/m²), därför räknas betongen.", "status": "Antagande", "kallor": []}}]
    massor = [
        {"typ": "Sanering", "volym_m3": 130000.0, "transport_km": 10.0, "forsta_ar": 2000, "sista_ar": 2035,
         "_dok": {"underlag": "Förorenad hamn- och varvsmark; volymen är ett antagande.", "status": "Antagande", "kallor": []}},
        {"typ": "Schakt", "volym_m3": 350000.0, "transport_km": 10.0, "forsta_ar": 2000, "sista_ar": 2037,
         "_dok": {"underlag": "Schakt för grundläggning, garage och ledningar; antagande.", "status": "Antagande", "kallor": []}},
    ]
    ledningar = [{"meter": 53000.0, "forsta_ar": 2000, "sista_ar": 2037,
                  "_dok": {"underlag": "Vatten, avlopp, dagvatten, fjärrvärme, el och fiber; cirka 53 km. Faktorn för ledningar ska verifieras i faktabiblioteket.", "status": "Antagande", "kallor": []}}]
    dok_anl = strip_dok(ytor) + strip_dok(betong) + strip_dok(massor) + strip_dok(ledningar)
    s["anlaggning"] = {"ytor": ytor, "massor": massor, "betong": betong, "ledningar": ledningar, "engangsvarden": []}

    # --- mark
    over = []
    for ar, f in ((2001, 0.25), (2010, 0.30), (2020, 0.30), (2030, 0.15)):
        for till, ha in (("Bebyggd kvartersmark", 72), ("Gata och torg", 27), ("Park", 15), ("Kvartersmark gård", 12)):
            over.append({"fran": "Hårdgjord mark", "till": till, "ha": round(ha * f, 2), "ar": ar,
                         "tradslag": "Blandskog (gran/bok)", "skotsel": "Fri utveckling", "skogsalder": 40})
    s["mark"] = {"overgangar": over, "pooler": {}, "bevarande": {}}
    # --- negativa
    s["negativa"] = {"biokol": [], "trad": [{"antal": n, "planteringsar": a} for a, n in ((2001, 400), (2008, 400), (2013, 500), (2020, 600), (2030, 600))]}

    s["dokumentation"] = {
        "beskrivning": "Västra hamnen i Malmö väster om Stora Varvsgatan, från första spadtaget för Bo01 (2000) till 2050. Varvsstaden och Universitetsholmen ligger öster om gatan och ingår inte.",
        "avgransning": "Allt väster om Stora Varvsgatan, cirka 165 ha (antagande: Malmö stads 187 ha för Västra hamnen minus Varvsstaden och Universitetsholmens del): Bo01, Dockan, Flagghusen, "
                       "Fullriggaren, Masthusen, Hamnporten, Tampen, Citadellsfogen och Galeonen. Universitetsholmen (Orkanen, Niagara, Malmö Live, Neptunigymnasiet) och Varvsstaden ingår inte. Befintliga äldre byggnader (Kockums kontor m.m.) ingår inte; deras arbetsplatser dras av vid kalibreringen.",
        "kalibrering": {
            "invanare_statistik": {"2006": 1555, "2011": 4512, "2013": 6857, "2022": 12909},
            "invanare_prognos": {"2028": 16380, "2033": 19161,
                                 "kommentar": "Prognosen antas omfatta även Varvsstaden; Varvsstadens beräknade invånare (cirka 800 år 2028 och 1 900 år 2033) är avdragna i kalibreringen."},
            "hushall_2006": 988, "bostader_2006": 1171, "bilar_2006": 496,
            "personer_per_hushall": "1,70 (antagande mellan 1,57 år 2006 och Malmös 2,11)",
            "bilar_per_hushall": "0,50 (496 bilar på 988 hushåll år 2006)",
            "bta_per_hushall": "110 m² (modellens schablon)",
            "arbetsplatser": "cirka 16 000 i dag och 25 000 enligt visionen för hela Västra hamnen; arbetsplatser öster om Stora Varvsgatan dras av; 20 m² BTA per arbetsplats (antagande)",
        },
        "kategorier": {
            **gemensam_dok(),
            "Byggnad": ["Stomme Generisk (= Betong BAU) där stomval saknas; Turning Torso Betong BAU. Pålning för alla byggnader på utfylld hamnmark utom Turning Torso (berggrundläggning).",
                        "Parkering: garage under kvarter till 2015 och mobilitetshus därefter (antaganden om platser per bostad)."],
            "Anläggning": ["Ytor uppskattade som andelar av 165 ha. Kajernas betong räknas separat. Sanering och schakt är antaganden.", *[f"{d['post']}: {d['underlag']}" for d in dok_anl]],
            "Förändrad markanvändning": ["Före: hamn- och industrimark, räknad som hårdgjord mark utan kolförråd. Efter: bebyggd kvartersmark 72 ha, gator och torg 27 ha, parker 15 ha, gårdar 12 ha. "
                                         "Förgröning av parker och gårdar ger ett litet upptag."],
            "Mobilitet och transport": ["Bilar per hushåll 0,50 (2006) och Malmös körsträcka 11 892 km per bil. Drivlinemix enligt modellens standard 2025, ökning enligt fliken Emissionsfaktorer över tid."],
            "Negativa utsläpp": ["Cirka 2 500 stadsträd planterade i fem omgångar (antagande)."],
        },
        "andelar": DOK_ANDELAR.copy(),
        "kallor": kallista(dok_anl),
    }
    return s


# ================================================================ VARVSSTADEN
def varvsstaden():
    DOK_ANDELAR.clear()
    s = tomt(fb)
    s["projekt"].update(namn="Varvsstaden, Malmö", kommun="Malmö", fas="Genomförande", startar=2020, slutar=2050)
    s["fjarrvarme"]["startvarde"] = FJV_2024
    s["hushall"] = {"personer_per_hushall": 1.70, "bta_per_hushall": 105.0}
    mob = standard_mobilitet(fb, "Malmö")
    mob.update(kommunvarden=False, bilar_per_hushall=0.35)
    s["mobilitet"] = mob
    BTA = 105
    U = dict(status="Uppgift"); A = dict(status="Antagande")
    b = []
    b.append(andel("Gjuteriet (kontor i KL-trä och limträ, återbrukat stål)", "kontor", "tra_bast", 4900, 2022, energiklass="C", palning=True, **U,
                   underlag="4 900 m², byggt 2020–2022 med stomme av KL-trä och limträ och återbrukat stål. Kolinlagring med schablonen 0,15 m³ limträ per m² BTA.",
                   kallor=kalla("SWEDISHWOOD_GJUTERIET")))
    b.append(bostader("Fyrskeppet", 103, BTA, 2022, stomme="betong_bast", energiklass="B", palning=True, **U,
                      underlag="103 lägenheter, prefabricerad stomme i ECO-Betong (klimatförbättrad betong), fjärrvärme och FTX, Svanenmärkt. Bilpool och parkering i garage 350–500 m bort.",
                      kallor=kalla("BJURFORS_FYRSKEPPET")))
    b.append(bostader("Varvsporten", 116, BTA, 2023, energiklass="B", palning=True, **U,
                      underlag="116 lägenheter, inflyttning 2023, Svanenmärkt, bil- och cykelpool.", kallor=kalla("DPS_VARVSPORTEN")))
    for namn, n, a0, a1 in (("Bostäder 2025–2029", 600, 2025, 2029), ("Bostäder 2030–2035 (bland annat högt hus i Västra Varvsstaden)", 900, 2030, 2035),
                            ("Bostäder 2036–2041", 781, 2036, 2041)):
        for st, txt in (("generisk", "Generisk"), ("betong_bast", "Betong BÄST")):
            b.append(bostader(f"{namn}, {txt}", n // 2 + (n % 2 if st == "generisk" else 0), BTA, a0, a1, stomme=st, energiklass="C", palning=True, **A,
                              underlag="Resten av 2 500 bostäder till 2041, jämnt fördelat per etapp. Hälften klimatförbättrad betong som i Fyrskeppet (antagande).",
                              kallor=kalla("CISION_VARV", "MALMO_HOGTHUS")))
    b.append(andel("Hall 259, kontor och handel (ombyggnad och tillbyggnad)", "kontor", "generisk", 16500, 2027, energiklass="C", palning=True,
                   manuellt_kg_m2=192.5, **A,
                   underlag="Hall 259 totalt cirka 29 000 m², klart sommaren 2027, varav parkeringshuset cirka 12 500 m². Ombyggnaden räknas med 50 % av Generisk för kontor (192,5 kg CO2e/m²; antagande).",
                   kallor=kalla("PEAB_HALL259", "PEAB_HALL259_SV", "IPE_HALL259")))
    b.append(andel("Hall 259, parkeringshus 500 platser", "mobilitetshus", "generisk", 12500, 2027, **U,
                   underlag="Cirka 500 bilplatser i fem plan × 25 m² BTA per plats (antagande om yta).", kallor=kalla("PEAB_HALL259")))
    b.append(andel("Kontor och verksamheter 2028–2041", "kontor", "generisk", 58600, 2028, 2041, energiklass="C", palning=True, **A,
                   underlag="4 000 arbetsplatser × 20 m² BTA minus Gjuteriet och Hall 259. Byggrätterna är totalt cirka 350 000 m².", kallor=kalla("CISION_VARV", "AFFV_PEAB")))
    b.append(andel("Förskolor och grundskola", "skola", "generisk", 2500 * NARSERVICE_M2_PER_BOSTAD, 2028, 2036, energiklass="C", palning=True, **A,
                   underlag="2 500 bostäder. " + NARSERVICE_TEXT + " Masterplanen för Varvsstaden (2014) har en grundskola med förskola i södra delen.",
                   kallor=kalla("NORD_VARVSSTADEN")))
    b.append(andel("Lokaler i bottenvåningar", "lokaler", "generisk", 10500, 2025, 2041, energiklass="C", palning=True, **A, underlag="Cirka 4 % av bostadsytan.", kallor=()))
    b.append(andel("Mobilitetshus, senare etapper", "mobilitetshus", "generisk", 7500, 2034, **A,
                   underlag="Cirka 300 platser; tillsammans med Hall 259 cirka 0,32 platser per bostad.", kallor=kalla("MALMO_PARKERING")))
    s["byggnader"] = b

    ytor = [
        yta("lokalgata", 36000, 2021, 2041, "Cirka 20 % av 18 ha."),
        yta("gc_vag", 10000, 2021, 2041, "Gång- och cykelvägar."),
        yta("torg", 23000, 2023, 2041, "Torg 8 000 m² och kajpromenad 1 km × 15 m.", status="Antagande", kallor=("CISION_VARV",)),
        yta("park", 15000, 2025, 2041, "Parker cirka 1,5 ha."),
        yta("bostadsgard", 20000, 2022, 2041, "Bostadsgårdar."),
        yta("lekplats", 1500, 2025, 2041, "Lekplatser."),
        yta("skolgard", round(2500 * NARSERVICE_M2_PER_BOSTAD), 2028, 2036, "Skol- och förskolegårdar, 1 m² per m² BTA närservice (antagande, samma i alla fall)."),
    ]
    betong = [{"namn": "Kajer, 1 km kajpromenad", "utforande": "standard", "volym_m3": 6000.0, "forsta_ar": 2023, "sista_ar": 2041,
               "_dok": {"underlag": "1 km kaj × 6 m³ betong per meter (antagande).", "status": "Antagande", "kallor": ["CISION_VARV"]}}]
    massor = [
        {"typ": "Schakt", "volym_m3": 125000.0, "transport_km": 5.0, "forsta_ar": 2022, "sista_ar": 2024,
         "_dok": {"underlag": "Södra Varvsbassängen grundas upp: cirka 50 000 m² från 6,5 till 4 m djup med schaktmassor (cirka 125 000 m³).", "status": "Uppgift", "kallor": ["PEAB_BRO"]}},
        {"typ": "Sanering", "volym_m3": 80000.0, "transport_km": 15.0, "forsta_ar": 2020, "sista_ar": 2035,
         "_dok": {"underlag": "Förorenad varvsmark; volymen är ett antagande.", "status": "Antagande", "kallor": []}},
        {"typ": "Schakt", "volym_m3": 150000.0, "transport_km": 10.0, "forsta_ar": 2020, "sista_ar": 2041,
         "_dok": {"underlag": "Schakt för grundläggning, garage och ledningar; antagande.", "status": "Antagande", "kallor": []}},
    ]
    ledningar = [{"meter": 10000.0, "forsta_ar": 2020, "sista_ar": 2041,
                  "_dok": {"underlag": "Cirka 10 km ledningar (antagande).", "status": "Antagande", "kallor": []}}]
    eng = [
        {"namn": "Bro från Styrmansgatan till Varvsstaden", "t_co2e": 3000.0, "ar": 2024,
         "_dok": {"underlag": "Bro för gång, cykel och kollektivtrafik med två stöd, 206 miljoner kr, klar november 2024. Klimatpåverkan grovt uppskattad: cirka 1 700 m² brodäck × 1,8 t CO2e/m². Byt mot projektets klimatkalkyl.",
                  "status": "Antagande", "kallor": ["PEAB_BRO"]}},
        {"namn": "Gång- och cykelbro 2", "t_co2e": 500.0, "ar": 2030,
         "_dok": {"underlag": "Varvsstaden får tre broar; de två mindre är uppskattade till 500 t var.", "status": "Antagande", "kallor": ["CISION_VARV"]}},
        {"namn": "Gång- och cykelbro 3", "t_co2e": 500.0, "ar": 2036,
         "_dok": {"underlag": "Som ovan.", "status": "Antagande", "kallor": ["CISION_VARV"]}},
    ]
    dok_anl = strip_dok(ytor) + strip_dok(betong) + strip_dok(massor) + strip_dok(ledningar) + strip_dok(eng)
    s["anlaggning"] = {"ytor": ytor, "massor": massor, "betong": betong, "ledningar": ledningar, "engangsvarden": eng}
    over = []
    for ar, f in ((2022, 0.25), (2030, 0.45), (2038, 0.30)):
        for till, ha in (("Bebyggd kvartersmark", 9.0), ("Gata och torg", 4.5), ("Park", 1.5), ("Kvartersmark gård", 2.0)):
            over.append({"fran": "Hårdgjord mark", "till": till, "ha": round(ha * f, 2), "ar": ar,
                         "tradslag": "Blandskog (gran/bok)", "skotsel": "Fri utveckling", "skogsalder": 40})
    s["mark"] = {"overgangar": over, "pooler": {}, "bevarande": {}}
    s["negativa"] = {"biokol": [], "trad": [{"antal": n, "planteringsar": a} for a, n in ((2024, 150), (2030, 250), (2037, 200))]}
    s["dokumentation"] = {
        "beskrivning": "Varvsstaden i Malmö (Kockums tidigare varvsområde) från första byggstart 2020 (Gjuteriet) till 2050.",
        "avgransning": "Öster om Stora Varvsgatan (Hall 259 ligger i nordvästra hörnet längs gatan). Cirka 18 ha med 2 500 bostäder, 4 000 arbetsplatser och cirka 350 000 m² byggrätter, färdigt omkring 2041. Tre broar och 1 km kajpromenad.",
        "kalibrering": {
            "personer_per_hushall": "1,70 (som Västra hamnen; antagande)",
            "bilar_per_hushall": "0,35 (antagande: bilfria kvarter med bilpool och parkering i mobilitetshus, cirka 0,32 platser per bostad)",
            "bta_per_hushall": "105 m² (antagande; 2 500 bostäder och 4 000 arbetsplatser ryms då i 350 000 m²)",
            "arbetsplatser": "4 000 × 20 m² BTA (antagande)",
        },
        "kategorier": {
            **gemensam_dok(),
            "Byggnad": ["Fyrskeppet i ECO-Betong räknas som Betong BÄST, Gjuteriet som Trä BÄST. Senare etapper: hälften Generisk och hälften Betong BÄST (antagande).",
                        "Hall 259 är en ombyggnad av en kulturhistorisk svets- och pannverkstad; ombyggnadsdelen har ett manuellt värde (50 % av Generisk)."],
            "Anläggning": [f"{d['post']}: {d['underlag']}" for d in dok_anl],
            "Förändrad markanvändning": ["Före: hårdgjord varvsmark. Efter: kvartersmark 9 ha, gator och torg 4,5 ha, park 1,5 ha, gårdar 2 ha."],
            "Mobilitet och transport": ["Bilar per hushåll 0,35 och Malmös körsträcka 11 892 km per bil."],
            "Negativa utsläpp": ["600 stadsträd (antagande). Kolinlagring i Gjuteriets trästomme."],
        },
        "andelar": DOK_ANDELAR.copy(),
        "kallor": kallista(dok_anl),
    }
    return s


# ================================================================ JÄGERSRO SMT
JAG_HA = 41.0
JAG_BOST = 4000
JAG_BTA = 102.3
JAG_ARB = 2000


def jagersro():
    DOK_ANDELAR.clear()
    s = tomt(fb)
    s["projekt"].update(namn="Jägersro SMT, Malmö", kommun="Malmö", fas="Planprogram", startar=2030, slutar=2050)
    s["fjarrvarme"]["startvarde"] = FJV_2024
    s["hushall"] = {"personer_per_hushall": 2.07, "bta_per_hushall": JAG_BTA}
    s["mobilitet"] = standard_mobilitet(fb, "Malmö")
    U = dict(status="Uppgift"); A = dict(status="Antagande")
    b = []
    for i, (a0, a1) in enumerate(((2032, 2035), (2036, 2040), (2041, 2045), (2046, 2050)), 1):
        b.append(bostader(f"Bostäder etapp {i}", JAG_BOST // 4, JAG_BTA, a0, a1, energiklass="C", **U,
                             underlag="4 000 bostäder i fyra lika etapper; första spadtag 2030 och första inflyttning 2032 (antagande om tidplan). "
                                      "102,3 m² BTA per bostad enligt FÖP:s genomsnitt. Stomme ej vald (Generisk). Ingen pålning (lermorän, antagande).",
                             kallor=kalla("SMT_AVGRANSNING", "FOP_JAGERSRO", "MALMO_JAGERSRO_2024")))
    b.append(andel("Verksamheter och stadsdelscentrum (2 000 arbetsplatser)", "kontor", "generisk", JAG_ARB * 20, 2034, 2050, energiklass="C", **A,
                      underlag="2 000 arbetsplatser × 20 m² BTA per arbetsplats (samma antagande som i de andra fallen).", kallor=kalla("MALMO_JAGERSRO_2024")))
    for nr, ar in enumerate((2033, 2037, 2041, 2045, 2049), 1):
        b.append(andel(f"Förskola {nr}", "skola", "generisk", 1300, ar, energiklass="C", **A,
                          underlag="Fem förskolor enligt planen; 1 300 m² per förskola (antagande, samma schablon som i de andra fallen).",
                          kallor=kalla("MALMO_JAGERSRO_2024", "SBN_JAGERSRO_2025")))
    b.append(andel("Grundskola", "skola", "generisk", 9000, 2038, energiklass="C", **A,
                      underlag="En grundskola enligt planen; 9 000 m² (antagande, samma schablon som i de andra fallen).", kallor=kalla("MALMO_JAGERSRO_2024", "SBN_JAGERSRO_2025")))
    platser = 0.4 * JAG_BOST + 0.1 * JAG_ARB
    for nr, ar in enumerate((2032, 2035, 2038, 2041, 2044, 2047, 2050), 1):
        b.append(andel(f"Mobilitetshus {nr}", "mobilitetshus", "generisk", platser * 25 / 7, ar, **A,
                          underlag=f"Sju mobilitetshus enligt planen; 0,4 platser per bostad och 0,1 per arbetsplats, {platser:,.0f} platser × 25 m² (samma regel som i Västra hamnen efter 2016).".replace(",", " "),
                          kallor=kalla("MALMO_JAGERSRO_2024")))
    s["byggnader"] = b
    ytor = [
        yta("huvudgata", round(JAG_HA * 10000 * 0.027), 2030, 2048, "Huvudgator, 2,7 % av 41 ha (samma andel som i Västra hamnen)."),
        yta("lokalgata", round(JAG_HA * 10000 * 0.10), 2030, 2050, "Lokalgator, 10 % av 41 ha."),
        yta("gc_vag", round(JAG_HA * 10000 * 0.027), 2030, 2050, "Gång- och cykelvägar, 2,7 % av ytan."),
        yta("torg", round(JAG_HA * 10000 * 0.021), 2034, 2045, "Torg vid stadsdelscentrum och kollektivtrafiknod, 2,1 % av ytan."),
        yta("park", 50000, 2030, 2034, "Stadsdelspark på travbanans innerplan, minst 5 ha enligt planen; 5 ha används.", status="Uppgift", kallor=("FOP_JAGERSRO", "MALMO_JAGERSRO_2024")),
        yta("bostadsgard", JAG_BOST * 10, 2032, 2050, "Bostadsgårdar, 10 m² per bostad (Västra hamnen 11, Varvsstaden 8)."),
        yta("lekplats", 2000, 2032, 2050, "Lekplatser."),
        yta("skolgard", 15500, 2033, 2049, "Skol- och förskolegårdar, 1 m² per m² BTA närservice (samma i alla fall)."),
    ]
    massor = [
        {"typ": "Schakt", "volym_m3": JAG_HA * 3000, "transport_km": 10.0, "forsta_ar": 2030, "sista_ar": 2050,
         "_dok": {"underlag": "3 000 m³ per ha för grundläggning och ledningar (antagande; Västra hamnen cirka 2 100, Varvsstaden 8 300 med garage och utfyllnad).", "status": "Antagande", "kallor": []}},
        {"typ": "Sanering", "volym_m3": 10000.0, "transport_km": 15.0, "forsta_ar": 2030, "sista_ar": 2035,
         "_dok": {"underlag": "Begränsad sanering av travbana, stall och parkeringar (antagande).", "status": "Antagande", "kallor": []}},
    ]
    ledningar = [{"meter": JAG_HA * 400, "forsta_ar": 2030, "sista_ar": 2050,
                  "_dok": {"underlag": "0,4 km ledningar per ha (Västra hamnen 0,32, Varvsstaden 0,56); antagande.", "status": "Antagande", "kallor": []}}]
    dok_anl = strip_dok(ytor) + strip_dok(massor) + strip_dok(ledningar)
    s["anlaggning"] = {"ytor": ytor, "massor": massor, "betong": [], "ledningar": ledningar, "engangsvarden": []}
    over = [{"fran": "Urban grönyta", "till": "Park", "ha": 5.0, "ar": 2030}]
    for ar in (2030, 2035, 2040, 2045):
        over += [{"fran": "Urban grönyta", "till": "Bebyggd kvartersmark", "ha": 1.25, "ar": ar},
                 {"fran": "Urban grönyta", "till": "Kvartersmark gård", "ha": 0.5, "ar": ar},
                 {"fran": "Hårdgjord mark", "till": "Bebyggd kvartersmark", "ha": 3.75, "ar": ar},
                 {"fran": "Hårdgjord mark", "till": "Gata och torg", "ha": 1.75, "ar": ar},
                 {"fran": "Hårdgjord mark", "till": "Kvartersmark gård", "ha": 0.5, "ar": ar}]
    for o in over:
        o.update(tradslag="Blandskog (gran/bok)", skotsel="Fri utveckling", skogsalder=40)
    s["mark"] = {"overgangar": over, "pooler": {}, "bevarande": {}}
    s["negativa"] = {"biokol": [], "trad": [{"antal": 250, "planteringsar": a} for a in (2032, 2037, 2042, 2047)]}
    s["dokumentation"] = {
        "beskrivning": "Jägersro SMT från första spadtaget 2030 till 2050, med samma schabloner som fallen för Västra hamnen och Varvsstaden.",
        "avgransning": "SMT:s del av Jägersro, 41 ha, 4 000 bostäder och 2 000 arbetsplatser. Tidplanen (inflyttning 2032–2050 i fyra etapper) är ett antagande.",
        "kalibrering": {"personer_per_hushall": "2,07 (FÖP: 8 900 invånare på 4 300 bostäder)", "bta_per_hushall": "102,3 m² (FÖP: 440 000 m² på 4 300 bostäder)",
                        "bilar_per_hushall": "Malmös 0,581 (SCB). Byt gärna mot ett värde för området när ett sådant finns.",
                        "arbetsplatser": "2 000 × 20 m² BTA"},
        "kategorier": {
            **gemensam_dok(),
            "Byggnad": ["Stomme Generisk och energiklass C (inga beslut ännu). Ingen pålning (antagande om lermorän)."],
            "Anläggning": [f"{d['post']}: {d['underlag']}" for d in dok_anl],
            "Förändrad markanvändning": ["Före (antagande): 12 ha gräs på travbanornas innerplan och kringytor (urban grönyta), 24 ha banor, stall och parkering (hårdgjord), 5 ha oförändrat. "
                                         "Parken behåller markkolet; grönyta som bebyggs förlorar markkol och biomassa."],
            "Negativa utsläpp": ["1 000 stadsträd, 25 per ha (antagande)."],
        },
        "andelar": DOK_ANDELAR.copy(),
        "kallor": kallista(dok_anl),
    }
    return s


if __name__ == "__main__":
    UT.mkdir(parents=True, exist_ok=True)
    from road2zero import __version__
    from road2zero.engine import berakna
    from road2zero.scenario import fran_json, till_json

    def nyckeltal(s):
        r = berakna(fran_json(till_json(s), fb), fb)
        p = r.per_ar_och_kategori(); n = r.netto_per_niva(); inv = r.invanare

        def fonster(a0):
            d = n[n.ar >= a0]; pa = sum(v for y, v in inv.items() if y >= a0)
            return {"netto_t": {f"niva{L}": round(float(d[f"niva{L}"].sum())) for L in (1, 2, 3)},
                    "personar": round(pa), "t_per_personar": {f"niva{L}": round(float(d[f"niva{L}"].sum()) / pa, 2) for L in (1, 2, 3)},
                    "per_kategori_t": {k: round(float(v)) for k, v in p.loc[a0:].sum().items()}}
        a0 = int(s["projekt"]["startar"])
        return {"modellversion": __version__, "kommentar": "Beräknat när filen skapades; ändras när indata eller faktabibliotek ändras.",
                "bta_m2": round(r.bta_totalt()), "invanare_2050": round(inv[2050]),
                "byggnad_kg_per_m2_bta": round(float(p["Byggnad"].sum()) * 1000 / r.bta_totalt()),
                f"{a0}_2050": fonster(a0), **({"2030_2050": fonster(2030)} if a0 < 2030 else {})}

    alla = {}
    for bokstav, namn, f in (("A", "vastra_hamnen.json", vastra_hamnen), ("B", "varvsstaden.json", varvsstaden), ("C", "jagersro_smt.json", jagersro)):
        s = f()
        s["dokumentation"]["nyckeltal"] = nyckeltal(s)
        (UT / namn).write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        alla[bokstav] = s
        print("skrev", UT / namn, len(s["byggnader"]), "andelar")
    from road2zero.scenario import SCENARIOSET
    paket = {"typ": SCENARIOSET, "namn": "Malmöfallen: Västra hamnen, Varvsstaden och Jägersro SMT", "modellversion": __version__,
             "aktiv": "A", "scenarier": alla}
    (UT / "malmofallen.json").write_text(json.dumps(paket, ensure_ascii=False, indent=2), encoding="utf-8")
    print("skrev", UT / "malmofallen.json", "(alla tre som A, B och C)")
