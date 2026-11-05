"""Road2Zero-CityScenario – tre scenarier (samma eller olika stadsdelar) med alla indata, beräknade med Road2Zero och jämförda
med varandra, rättvist och med karta.

Starta lokalt från repots rot:   python -m streamlit run cityscenario/streamlit_app.py
Streamlit Community Cloud:       repo Mulmen65/road2zero, huvudfil cityscenario/streamlit_app.py
"""
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
if str(ROT) not in sys.path:
    sys.path.insert(0, str(ROT))

import streamlit as st  # noqa: E402

from gemensamt import varumarke  # noqa: E402

varumarke.sidinstallning("cityscenario")

from cityscenario import scenarier, ui_jamforelse  # noqa: E402
from gemensamt import forklaring, geodata, karta, ui_indata, ui_resultat  # noqa: E402
from gemensamt.common import _berakna, fmt, kor_senare, ny_version, senare, ss  # noqa: E402
from road2zero.scenario import till_json  # noqa: E402

MODELL = "cityscenario"
SIDOR = {
    "oversikt": "Översikt",
    "indata": "Indata",
    "jamforelse": "Jämförelse",
    "rattvis": "Rättvis jämförelse",
    "resultat": "Resultat per scenario",
    "karta": "Karta & områden",
    "rakna": "Så räknas resultatet",
    "antaganden": "Antaganden & scenario",
    "trafik": "Trafik & geodata",
    "metod": "Metod & källor",
}


def _ga(sida: str):
    varumarke.ga_till(sida, ny_version)


def _valjare():
    scenarier.valjare()


def _lager(utom: str | None = None) -> list[dict]:
    return [{"namn": f"Scenario {n} · {ss.scenarier[n]['projekt']['namn']}", "farg": scenarier.FARG[n],
             "koder": ss.scenarier[n].get("geografi", {}).get("deso", [])} for n in scenarier.NAMN if n != utom]


# ---------- sidor som läser indata (före beräkningen) ----------
def indata():
    varumarke.sidrubrik(forklaring.stig(), "Indata", "Ett scenario i taget.", "Alla indata i Road2Zero.",
                        "Välj vilket scenario du ändrar. Jämförelsesidorna visar alla tre. Emissionsfaktorernas utveckling över tid "
                        "anges under Antaganden & scenario.")
    _valjare()
    rubrik = st.empty()                       # fylls när indata är lästa, så att ett nytt namn syns direkt
    ui_indata.visa()
    senare(lambda res: rubrik.markdown(scenarier.markering(ss.aktiv, " · här ändrar du det valda scenariot"), unsafe_allow_html=True))


def resultatsida():
    varumarke.sidrubrik(forklaring.stig(), "Resultat per scenario", "Ett scenario i detalj.", "Samma resultat som i Road2Zero-Plan.",
                        "Välj redovisningsnivå och klimatkategorier. Urvalet styr alla diagram och tabeller på sidan.")
    _valjare()
    senare(lambda res: (st.markdown(scenarier.markering(ss.aktiv), unsafe_allow_html=True), ui_resultat.visa(res)))


def kartsida():
    forklaring.karta_sida(_lager(utom=ss.aktiv), f"Scenario {ss.aktiv}", scenarier.FARG[ss.aktiv], fore=_valjare)


FORE = {
    "indata": indata,
    "resultat": resultatsida,
    "karta": kartsida,
    "rakna": lambda: forklaring.sa_raknas(fore=_valjare),
    "antaganden": lambda: forklaring.antaganden(fore=_valjare),
    "trafik": lambda: forklaring.trafik_geodata([(f"{n} · {ss.scenarier[n]['projekt']['namn']}", ss.scenarier[n]) for n in scenarier.NAMN],
                                                fore=_valjare),
    "metod": lambda: forklaring.metod_kallor("Road2Zero-CityScenario"),
}


# ---------- sidor som bara visar resultat (efter beräkningen) ----------
def oversikt(res: dict):
    varumarke.sidrubrik(["Road2Zero-CityScenario"], "Översikt", "Tre scenarier.", "Samma motor, rättvis jämförelse.",
                        "Testa olika planer mot varandra, i samma stadsdel eller i olika. Varje scenario har alla indata i Road2Zero "
                        "och kan läsas in från JSON eller Excel. Jämförelsen visar skillnaderna och förklarar dem.")
    c = st.columns(3)
    for col, n in zip(c, scenarier.NAMN):
        s = ss.scenarier[n]
        r = res.get(n)
        with col:
            if r:
                nk = r.nyckeltal()
                text = (f"{fmt(nk['bta'])} m² BTA · {fmt(nk['invanare_full'])} invånare<br>"
                        + "<br>".join(f"Nivå {L}: <b>{fmt(nk['netto'][L] / 1000, 1)} kt CO₂e</b>" for L in (1, 2, 3)))
            else:
                text = "Inga byggnader ännu. Öppna en fil eller hämta ett färdigt fall i sidopanelen."
            st.markdown(varumarke.kort(f"Scenario {n}", f"<span style='color:{scenarier.FARG[n]};font-weight:700'>■</span> "
                                                       f"<b>{s['projekt']['namn']}</b> · {s['projekt'].get('kommun', '')}<br>{text}"),
                        unsafe_allow_html=True)
    st.markdown("#### Kom igång")
    k = st.columns(4)
    steg = [("1 · Läs in", "Hämta Malmöfallen till A, B och C, eller öppna egna filer (JSON eller Excel) i sidopanelen.", "indata", "Öppna Indata"),
            ("2 · Jämför", "Nettoutsläpp per nivå och kategori, per person och per m² BTA, sida vid sida.", "jamforelse", "Visa jämförelsen"),
            ("3 · Rättvist", "Boende per invånare, verksamheter per arbetsplats, lika förutsättningar och livscykel per år.", "rattvis",
             "Rättvis jämförelse"),
            ("4 · På kartan", "Scenariernas DeSO på samma karta, och bilinnehavet i varje område.", "karta", "Utforska kartan")]
    for col, (rubrik, text, sida, knapp) in zip(k, steg):
        with col:
            st.markdown(varumarke.kort(rubrik, text), unsafe_allow_html=True)
            st.button(knapp, key=f"ga_{sida}", on_click=_ga, args=(sida,), width="stretch")
    lager = [x for x in _lager() if x["koder"]]
    if lager:
        st.markdown("#### Scenarierna på kartan")
        kommuner = [geodata.kommun_for(x["koder"]) for x in lager]
        karta.karta(kommuner, lager, nyckel="karta_oversikt", hojd=380, fokus="|".join(",".join(x["koder"]) for x in lager))


def jamforelse(res: dict):
    varumarke.sidrubrik(["Road2Zero-CityScenario"], "Jämförelse", "Scenarierna sida vid sida.", "Och varför de skiljer sig.",
                        "Nettoutsläpp per redovisningsnivå och kategori, per invånare och per m² BTA. Skillnaderna delas upp i "
                        "byggd yta och utsläpp per m².")
    ui_jamforelse.jamforelse(res)


def rattvis(res: dict):
    varumarke.sidrubrik(["Road2Zero-CityScenario"], "Rättvis jämförelse", "Lika villkor.", "Boende per invånare, verksamheter per arbetsplats.",
                        "Scenarier med olika blandning av bostäder och verksamheter, olika byggtakt och olika startår jämförs med samma "
                        "förutsättningar: faktorer på 2026 års nivå och livscykel per år.")
    ui_jamforelse.rattvis()


EFTER = {"oversikt": oversikt, "jamforelse": jamforelse, "rattvis": rattvis}

varumarke.stil()
scenarier.init()
sida = varumarke.meny(MODELL, SIDOR, vid_byte=ny_version)
if sida in FORE:
    FORE[sida]()              # indata för det valda scenariot läses först ...
scenarier.spara_aktiv()

res = {n: _berakna(till_json(ss.scenarier[n])) for n in scenarier.NAMN if ss.scenarier[n]["byggnader"]}
res_aktiv = res.get(ss.aktiv) or _berakna(till_json(ss.scen))
kor_senare(res_aktiv)         # ... sedan fylls tabeller och diagram som väntar på resultatet
if sida in EFTER:
    EFTER[sida](res)
scenarier.sidopanel(res)
varumarke.sidfot(MODELL)
