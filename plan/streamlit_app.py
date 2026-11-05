"""Road2Zero-Plan – klimatberäkning för en plan: tio klimatkategorier år för år mot en koldioxidbudget, med karta och
förklaringssidor.

Starta lokalt från repots rot:   python -m streamlit run plan/streamlit_app.py
Streamlit Community Cloud:       repo Mulmen65/road2zero, huvudfil plan/streamlit_app.py
"""
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
if str(ROT) not in sys.path:
    sys.path.insert(0, str(ROT))

import streamlit as st  # noqa: E402

from gemensamt import varumarke  # noqa: E402

varumarke.sidinstallning("plan")

from gemensamt import forklaring, karta, ui_indata, ui_resultat  # noqa: E402
from gemensamt.common import fmt, init, kor_senare, ny_version, resultat, senare, sidopanel, ss  # noqa: E402
from road2zero.konstanter import NIVA_INNEHALL, NIVA_NAMN  # noqa: E402

MODELL = "plan"
SIDOR = {
    "oversikt": "Översikt",
    "indata": "Indata",
    "resultat": "Resultat",
    "karta": "Karta & områden",
    "rakna": "Så räknas resultatet",
    "antaganden": "Antaganden & scenario",
    "trafik": "Trafik & geodata",
    "metod": "Metod & källor",
}


def _ga(sida: str):
    varumarke.ga_till(sida, ny_version)


def oversikt():
    p = ss.scen["projekt"]
    varumarke.sidrubrik(forklaring.stig(), f"Road2Zero-Plan · {p.get('fas', '')}", f"{p['namn']}.", "Klimatavtrycket år för år.",
                        "Planens utsläpp från byggande, drift, mark och invånarnas konsumtion räknas år för år och jämförs med en "
                        "koldioxidbudget enligt Forster m.fl. (2026), fördelad lika per person på dem som bor i området.")
    senare(_oversikt)


def _oversikt(res):
    s = ss.scen
    if not s["byggnader"]:
        st.info("Projektet har inga byggnader ännu. Börja under Indata → 1 Byggnader, eller ladda standardprojektet i sidopanelen.")
    niva = int(s["budget"]["niva"])
    u = ui_resultat.Urval(niva, ui_resultat.nivans_kategorier(niva), True, res.lang, False,
                          (min(max(ui_resultat.SNITT[0], res.ar()[0]), res.ar()[-1]), max(min(ui_resultat.SNITT[1], res.ar()[-1]), res.ar()[0])))
    m = ui_resultat.person_matt(res, u)
    nk = res.nyckeltal()
    c = st.columns(5)
    for i, L in enumerate((1, 2, 3)):
        c[i].metric(f"Nivå {L}, netto", f"{fmt(nk['netto'][L] / 1000, 1)} kt CO₂e", help=f"{NIVA_NAMN[L]}: {NIVA_INNEHALL[L]}, {res.ar()[0]}–{res.ar()[-1]}")
    c[3].metric(f"Per person {u.period[0]}–{u.period[1]}", f"{fmt(m['snitt'], 2)} t/år" if m["snitt"] is not None else "–",
                help=f"Nivå {niva}. Budgetandel samma år: {fmt(m['snitt_budget'], 2)} t per person och år.")
    slut = res.budget["slutar"].get(niva)
    c[4].metric("Budgeten förbrukad", str(slut) if slut else "Inte under perioden")
    c1, c2 = st.columns([5, 4])
    with c1:
        ui_resultat._visa(ui_resultat.mot_budget(res, u))
    with c2:
        ui_resultat._visa(ui_resultat.stapel_per_kategori(res, u))
    st.markdown("#### Kom igång")
    k = st.columns(4)
    steg = [("1 · Indata", "Byggbestånd, hushåll, anläggning, mark, mobilitet och konsumtion. Allt är förifyllt med källa.", "indata", "Öppna Indata"),
            ("2 · Karta & områden", "Välj de DeSO där planen ligger. Bilinnehavet i området kan föras över till mobiliteten.", "karta", "Utforska kartan"),
            ("3 · Resultat", "Välj redovisningsnivå och klimatkategorier. Diagram, klimatbudget, tabeller och export.", "resultat", "Visa resultatet"),
            ("4 · Bakgrund", "Så räknas resultatet, antaganden, trafik och geodata, metod och källor.", "rakna", "Så räknas det")]
    for col, (rubrik, text, sida, knapp) in zip(k, steg):
        with col:
            st.markdown(varumarke.kort(rubrik, text), unsafe_allow_html=True)
            st.button(knapp, key=f"ga_{sida}", on_click=_ga, args=(sida,), width="stretch")
    g = forklaring.geografi()
    if g["deso"]:
        st.markdown("#### Planområdet")
        karta.karta([g["kommunkod"]], [{"namn": "Planområdet", "farg": forklaring.PLANFARG, "koder": g["deso"]}], nyckel="karta_oversikt",
                    hojd=320, fokus=",".join(g["deso"]))
        if g.get("kommentar"):
            st.caption(g["kommentar"])


def indata():
    varumarke.sidrubrik(forklaring.stig(), "Indata", "Planen i siffror.", "Förifyllt med källa.",
                        "Alla indata som påverkar resultatet har ett förifyllt värde med källa som du kan ändra. Emissionsfaktorernas "
                        "utveckling över tid anges under Antaganden & scenario.")
    ui_indata.visa()


def resultatsida():
    varumarke.sidrubrik(forklaring.stig(), "Resultat", "Nettoutsläpp mot klimatbudgeten.", "Välj nivå och kategorier.",
                        "Urvalet styr alla diagram och tabeller på sidan. Klimatbudgeten jämförs med nettot för en redovisningsnivå.")
    senare(ui_resultat.visa)


varumarke.stil()
init()
sida = varumarke.meny(MODELL, SIDOR, vid_byte=ny_version)
{
    "oversikt": oversikt,
    "indata": indata,
    "resultat": resultatsida,
    "karta": forklaring.karta_sida,
    "rakna": forklaring.sa_raknas,
    "antaganden": forklaring.antaganden,
    "trafik": forklaring.trafik_geodata,
    "metod": lambda: forklaring.metod_kallor("Road2Zero-Plan"),
}[sida]()

res = resultat()              # indata på sidan är lästa: beräkna en gång ...
kor_senare(res)               # ... och fyll tabeller och diagram som väntar på resultatet
sidopanel(res)
varumarke.sidfot(MODELL)
