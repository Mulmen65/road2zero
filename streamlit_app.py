"""Road2Zero – Streamlit-app.

Starta lokalt med:  streamlit run streamlit_app.py
"""
import streamlit as st

st.set_page_config(page_title="Road2Zero", page_icon="app/logo.svg", layout="wide", initial_sidebar_state="expanded")

from app import ui_berakningar, ui_faktorer, ui_illustration, ui_indata, ui_referenser, ui_resultat, ui_utveckling  # noqa: E402
from app.common import init, kor_senare, resultat, sidopanel  # noqa: E402

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1500px;}
h1, h2, h3, h4, h5 {letter-spacing: -0.2px;}
[data-testid="stMetricValue"] {font-size: 1.55rem;}
div[data-baseweb="tab-list"] button p {font-size: 0.95rem;}
</style>
""", unsafe_allow_html=True)

init()
st.title("Road2Zero")
st.caption("Klimatberäkning för stadsdelar utan karta: aggregerade indata, tio klimatkategorier år för år och jämförelse med en "
           "vetenskapligt baserad koldioxidbudget.")

flikar = st.tabs(["Indata", "Emissionsfaktorer över tid", "Resultat", "Illustration", "Beräkningar", "Faktorer och parametrar", "Referenser"])
with flikar[0]:
    ui_indata.visa()          # alla indata läses först ...
with flikar[1]:
    ui_utveckling.visa()

res = resultat()              # ... sedan beräknas resultatet en gång
kor_senare(res)               # och tabeller och diagram i indataflikarna fylls med aktuella värden
sidopanel(res)
with flikar[2]:
    ui_resultat.visa(res)
with flikar[3]:
    ui_illustration.visa(res)
with flikar[4]:
    ui_berakningar.visa(res)
with flikar[5]:
    ui_faktorer.visa(res)
with flikar[6]:
    ui_referenser.visa(res)
