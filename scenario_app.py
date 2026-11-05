"""road2zero-scenario – tre scenarier med alla indata, beräknade med Road2Zero och jämförda med varandra.

Starta lokalt med:  streamlit run scenario_app.py
På Streamlit Community Cloud: samma repo, huvudfil scenario_app.py.
"""
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Road2Zero scenario", page_icon=str(Path(__file__).parent / "app" / "logo.svg"), layout="wide", initial_sidebar_state="expanded")

from app import scenarier, ui_faktorer, ui_indata, ui_jamforelse, ui_referenser, ui_resultat, ui_utveckling  # noqa: E402
from app.common import _berakna, kor_senare, ss  # noqa: E402
from road2zero.scenario import till_json  # noqa: E402

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1500px;}
h1, h2, h3, h4, h5 {letter-spacing: -0.2px;}
[data-testid="stMetricValue"] {font-size: 1.45rem;}
div[data-baseweb="tab-list"] button p {font-size: 0.95rem;}
</style>
""", unsafe_allow_html=True)

scenarier.init()
st.title("Road2Zero scenario")
st.caption("Testa tre scenarier mot varandra. Varje scenario har alla indata i Road2Zero; jämförelseflikarna visar dem sida vid sida.")
scenarier.valjare()

flikar = st.tabs(["Indata", "Emissionsfaktorer över tid", "Jämförelse", "Rättvis jämförelse", "Resultat för scenariot",
                  "Faktorer och parametrar", "Referenser"])
with flikar[0]:
    rubrik0 = st.empty()      # fylls när indata är lästa, så att ett nytt namn syns direkt
    ui_indata.visa()          # indata för det valda scenariot läses först ...
with flikar[1]:
    rubrik1 = st.empty()
    ui_utveckling.visa()
scenarier.spara_aktiv()
rubrik0.markdown(scenarier.markering(ss.aktiv, " · här ändrar du det valda scenariot"), unsafe_allow_html=True)
rubrik1.markdown(scenarier.markering(ss.aktiv), unsafe_allow_html=True)

res = {n: _berakna(till_json(ss.scenarier[n])) for n in scenarier.NAMN if ss.scenarier[n]["byggnader"]}
res_aktiv = res.get(ss.aktiv) or _berakna(till_json(ss.scen))
kor_senare(res_aktiv)         # ... sedan fylls tabeller och diagram i indataflikarna
scenarier.sidopanel(res)

with flikar[2]:
    ui_jamforelse.jamforelse(res)
with flikar[3]:
    ui_jamforelse.rattvis()
with flikar[4]:
    st.markdown(scenarier.markering(ss.aktiv), unsafe_allow_html=True)
    ui_resultat.visa(res_aktiv)
with flikar[5]:
    st.markdown(scenarier.markering(ss.aktiv), unsafe_allow_html=True)
    ui_faktorer.visa(res_aktiv)
with flikar[6]:
    ui_referenser.visa(res_aktiv)
