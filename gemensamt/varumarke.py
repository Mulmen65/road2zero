"""Road2Zero som varumärke: logotyp, färger, mörkgrön meny och sidrubriker, gemensamt för Plan och CityScenario.

Färgerna är desamma som i Road2Zero-OP och Vägvis, så att alla modeller känns igen som en familj.
Menyn är en st.radio med fasta etiketter (regel 9 i CLAUDE.md); numren läggs till med CSS.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from road2zero import __version__

LOGO_FIL = Path(__file__).resolve().parent / "logo.svg"
LOGO = LOGO_FIL.read_text(encoding="utf-8")

MORK, MORK2, AKTIV, TEAL, BLEK, PAPPER = "#103C38", "#1D5149", "#28554B", "#167567", "#E2EEE7", "#F5F5EF"
GULD, BARNSTEN, BLACK, TEXT, DOV, LINJE = "#EDCE93", "#A76019", "#183B3B", "#283F44", "#647579", "#DCE3DE"

MODELLER = {
    "op": ("Road2Zero-OP", "ÖVERSIKTSPLAN · HELA STADEN"),
    "plan": ("Road2Zero-Plan", "EN PLAN · KLIMATBERÄKNING"),
    "cityscenario": ("Road2Zero-CityScenario", "SCENARIER · JÄMFÖRELSE"),
}

_CSS = f"""
<style>
.block-container {{padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1500px;}}
h1, h2, h3, h4, h5 {{letter-spacing: -0.2px; color: {BLACK};}}
[data-testid="stMetricValue"] {{font-size: 1.5rem;}}
[data-testid="stMetric"] {{background: #f1f5f3; border-radius: 6px; padding: 0.6rem 0.8rem;}}
[data-testid="stMetricLabel"] p {{font-size: 0.85rem; color: #56635e;}}
div[data-baseweb="tab-list"] button p {{font-size: 0.95rem;}}
[data-testid="stButtonGroup"] > div {{flex-wrap: wrap; overflow-x: visible; row-gap: 0.4rem;}}

/* mörkgrön sidopanel som i Vägvis */
section[data-testid="stSidebar"] {{background: {MORK};}}
section[data-testid="stSidebar"] > div {{background: {MORK};}}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] h5 {{color: #d9e9df;}}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{color: #9fc3b2;}}
section[data-testid="stSidebar"] hr {{border-color: #2c5e54; margin: 0.9rem 0;}}
section[data-testid="stSidebar"] [data-testid="stAlert"] > div {{background: {BLEK} !important; border-radius: 8px;}}
section[data-testid="stSidebar"] [data-testid="stAlert"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stAlert"] p {{color: {BLACK} !important;}}
section[data-testid="stSidebar"] button[kind="secondary"], section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{
  background: {MORK2}; border: 1px solid #3f8c76; color: #ffffff;}}
section[data-testid="stSidebar"] button[kind="secondary"]:hover, section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
  background: {AKTIV}; border-color: #7fc8a9; color: #ffffff;}}
section[data-testid="stSidebar"] button p {{color: #ffffff;}}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{background: {MORK2}; border: 1px dashed #3f8c76;}}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{color: #d9e9df;}}
section[data-testid="stSidebar"] [data-baseweb="select"] * {{color: {BLACK};}}
[data-testid="stSidebarCollapseButton"] svg, [data-testid="stSidebarHeader"] svg {{color: #d9e9df; fill: #d9e9df;}}

/* menyn: radioknappar som menyrader med nummer till höger */
.st-key-r2z_meny, .st-key-r2z_meny [data-testid="stRadio"], .st-key-r2z_meny [role="radiogroup"] {{width: 100%;}}
.st-key-r2z_meny [role="radiogroup"] {{gap: 1px; counter-reset: r2z;}}
.st-key-r2z_meny [role="radiogroup"] > div {{width: 100%; counter-increment: r2z; border-radius: 8px; margin: 0;}}
.st-key-r2z_meny [data-testid="stRadioOption"] {{width: 100%; padding: 8px 11px; margin: 0; cursor: pointer;}}
.st-key-r2z_meny [data-testid="stRadioOption"] p {{margin: 0;}}
.st-key-r2z_meny [data-testid="stRadioOption"] > div {{width: 100%; display: flex; align-items: center;}}
.st-key-r2z_meny [data-testid="stRadioOption"] > div > div:first-child {{display: none;}}
.st-key-r2z_meny [data-testid="stRadioOption"] p {{color: #c3d9cd; font-size: 14px;}}
.st-key-r2z_meny [data-testid="stRadioOption"] > div::after {{content: counter(r2z, decimal-leading-zero); margin-left: auto;
  color: #c3d9cd; opacity: .55; font-size: 11px;}}
.st-key-r2z_meny [role="radiogroup"] > div:hover, .st-key-r2z_meny [role="radiogroup"] > div[data-selected="true"] {{background: {AKTIV};}}
.st-key-r2z_meny [role="radiogroup"] > div[data-selected="true"] p {{color: #ffffff; font-weight: 600;}}
.r2z-sb-rad {{display: flex; justify-content: space-between; font-size: 14px; color: #d9e9df; margin-bottom: 2px;}}
.r2z-sb-rad b {{color: #ffffff;}}
.r2z-sb-not {{font-size: 12.5px; color: #9fc3b2; margin-top: 6px;}}
.r2z-sb-status {{font-size: 13px; margin-top: 10px; padding: 7px 10px; border-radius: 8px; background: {MORK2}; color: #d9e9df;}}
.r2z-sb-status.ok::before {{content: "●"; color: #7fc8a9; margin-right: 7px;}}
.r2z-sb-status.varning::before {{content: "▲"; color: {GULD}; margin-right: 7px;}}
.r2z-sb-status.fel::before {{content: "■"; color: #f08c7a; margin-right: 7px;}}

/* sidrubrik som i Vägvis */
.r2z-crumb {{font-size: 10px; letter-spacing: 1.6px; font-weight: 700; color: {DOV}; text-transform: uppercase; margin-bottom: 14px;}}
.r2z-crumb span {{padding: 0 9px; color: #a3b3ac;}}
.r2z-crumb b {{color: {BLACK};}}
.r2z-eyebrow {{font-size: 10px; letter-spacing: 2px; color: {TEAL}; font-weight: 750; text-transform: uppercase;}}
.r2z-h1 {{font-size: 2.3rem; line-height: 1.08; font-weight: 750; color: {BLACK}; margin: 6px 0 8px 0; letter-spacing: -0.8px;}}
.r2z-h1 em {{font-style: normal; color: {TEAL};}}
.r2z-ingress {{font-size: 1.02rem; color: {TEXT}; max-width: 880px; margin-bottom: 0.6rem;}}
.r2z-kort {{background: #ffffff; border: 1px solid {LINJE}; border-radius: 14px; padding: 16px 18px; height: 100%;}}
.r2z-kort .rubrik {{margin: 0 0 6px 0; font-size: 1.0rem; font-weight: 650; color: {BLACK};}}
.r2z-kort p {{margin: 0; color: {TEXT}; font-size: 0.92rem;}}
.r2z-steg {{display: flex; gap: 14px; margin: 0 0 14px 0;}}
.r2z-steg .nr {{flex: 0 0 30px; height: 30px; border-radius: 50%; background: {BLEK}; color: {TEAL}; font-weight: 750;
  display: flex; align-items: center; justify-content: center;}}
.r2z-steg .rubrik {{margin: 3px 0 4px 0; font-size: 1.0rem; font-weight: 650; color: {BLACK};}}
.r2z-steg p {{margin: 0 0 4px 0;}}
.r2z-ex {{background: {PAPPER}; border-left: 3px solid {TEAL}; padding: 7px 11px; border-radius: 0 8px 8px 0; font-size: 0.92rem;
  color: {BLACK}; margin-top: 5px;}}
.r2z-notis {{background: #fcf1db; border-left: 3px solid {BARNSTEN}; padding: 8px 12px; border-radius: 0 8px 8px 0; font-size: 0.92rem;}}
.r2z-fot {{margin-top: 2.5rem; padding-top: 0.8rem; border-top: 1px solid {LINJE}; font-size: 12px; color: {DOV};}}
</style>
"""


def sidinstallning(modell: str):
    """st.set_page_config med modellens namn och logotyp. Anropas först i appfilen."""
    st.set_page_config(page_title=MODELLER[modell][0], page_icon=str(LOGO_FIL), layout="wide", initial_sidebar_state="expanded")


def stil():
    st.markdown(_CSS, unsafe_allow_html=True)


def ordmarke(modell: str, storlek: int = 44) -> str:
    namn, under = MODELLER[modell]
    rest = namn.split("-", 1)[1] if "-" in namn else ""
    return (f'<div style="display:flex;align-items:center;gap:12px;margin:4px 0 6px 0">'
            f'<div style="width:{storlek}px;height:{storlek}px;flex:0 0 {storlek}px;border-radius:12px;box-shadow:0 0 0 1px #3f8c76">{LOGO}</div>'
            f'<div><div style="font-size:{23 if len(namn) <= 15 else 19}px;font-weight:750;letter-spacing:-0.6px;line-height:1.05;color:#ffffff">'
            f'Road<span style="color:{GULD}">2</span>Zero<span style="color:#7fc8a9;font-weight:600">{"-" + rest if rest else ""}</span></div>'
            f'<div style="font-size:9px;letter-spacing:1.5px;color:#adcec0;margin-top:3px">{under}</div></div></div>')


def meny(modell: str, sidor: dict[str, str], vid_byte=None) -> str:
    """Sidopanelens överdel: logotyp, modellnamn och menyn. Returnerar id för vald sida.

    sidor: id → fast etikett, i menyns ordning. vid_byte anropas när användaren byter sida (till exempel ny_version)."""
    sb = st.sidebar
    sb.markdown(ordmarke(modell), unsafe_allow_html=True)
    sb.markdown(f'<div style="font-size:9px;letter-spacing:1.3px;display:flex;justify-content:space-between;color:#acd0bd;'
                f'margin:16px 0 8px 0">MODELLVERSION {__version__}<span style="color:{GULD}">SCREENING</span></div>',
                unsafe_allow_html=True)
    ids = list(sidor)
    if st.session_state.get("r2z_meny") not in ids:
        st.session_state["r2z_meny"] = ids[0]
    val = sb.radio("Meny", ids, format_func=sidor.get, key="r2z_meny", label_visibility="collapsed",
                   on_change=vid_byte or (lambda: None))
    return val if val in ids else ids[0]


def ga_till(sida: str, vid_byte=None):
    """Knapp eller länk på en sida som byter sida i menyn (anropas som callback)."""
    st.session_state["r2z_meny"] = sida
    if vid_byte:
        vid_byte()


def sidrubrik(stig: list[str], eyebrow: str, titel: str, betonad: str = "", ingress: str = ""):
    """Sidrubrik som i Vägvis: stig (t.ex. kommun / projekt), liten överrubrik, rubrik med betonad andra rad och ingress."""
    delar = [escape(s) for s in stig if s]
    crumb = "<span>/</span>".join(delar[:-1] + [f"<b>{delar[-1]}</b>"]) if delar else ""
    st.markdown(
        (f'<div class="r2z-crumb">{crumb}</div>' if crumb else "") +
        f'<div class="r2z-eyebrow">{escape(eyebrow)}</div>'
        f'<div class="r2z-h1">{escape(titel)}{"<br><em>" + escape(betonad) + "</em>" if betonad else ""}</div>'
        + (f'<div class="r2z-ingress">{ingress}</div>' if ingress else ""), unsafe_allow_html=True)


def kort(rubrik: str, text: str) -> str:
    return f'<div class="r2z-kort"><div class="rubrik">{escape(rubrik)}</div><p>{text}</p></div>'


def steg(nr: int | str, rubrik: str, text: str, exempel: str = "") -> str:
    return (f'<div class="r2z-steg"><div class="nr">{nr}</div><div><div class="rubrik">{escape(rubrik)}</div><p>{text}</p>'
            + (f'<div class="r2z-ex">{exempel}</div>' if exempel else "") + "</div></div>")


def notis(text: str):
    st.markdown(f'<div class="r2z-notis">{text}</div>', unsafe_allow_html=True)


def sidfot(modell: str):
    st.markdown(f'<div class="r2z-fot">{MODELLER[modell][0]} {__version__} · ton CO₂e per kalenderår · '
                f'beräkningsmotor Road2Zero · kartor © OpenStreetMap-bidragsgivare, DeSO © SCB</div>', unsafe_allow_html=True)
