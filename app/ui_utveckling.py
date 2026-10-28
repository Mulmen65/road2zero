"""Fliken Emissionsfaktorer över tid: årlig procentuell förändring per period 2027–2100 för modellens viktigaste faktorer."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from road2zero.kontext import Kontext
from road2zero.modules.mobilitet import mix_for_ar
from road2zero.utveckling import BASAR, KOPPLINGAR, PERIODNAMN, PROCENTENHETER, SLUTAR, Utveckling
from road2zero.utveckling import standard as utveckling_standard

from .common import editor, eget_param, fb, k, kalla_kort, kalla_text, ny_version, param_info, senare, ss

COL = st.column_config
INK = "#0b0b0b"; INK2 = "#52514e"; GRID = "#e6e5e1"; SURF = "#fcfcfb"
BLA, ORANGE, AQUA, NEUTRAL = "#2a78d6", "#eb6834", "#1baf7a", "#52514e"
CONF = {"displaylogo": False, "locale": "sv", "toImageButtonOptions": {"format": "png", "scale": 2}}
GRUPPER = ["Byggpåverkan", "Energi", "Mobilitet", "Konsumtion och offentlig sektor"]
NYCKELAR = [2030, 2035, 2040, 2050, 2070, 2100]
# Stommarna: material ger kulör, BAU heldragen och BÄST streckad linje
STOMLINJE = {
    "bygg.betong_bau": (BLA, "solid"), "bygg.betong_bast": (BLA, "dash"),
    "bygg.stal_bau": (ORANGE, "solid"), "bygg.stal_bast": (ORANGE, "dash"),
    "bygg.tra_bau": (AQUA, "solid"), "bygg.tra_bast": (AQUA, "dash"),
    "anl": (NEUTRAL, "dot"),
}
LINJE = {"el": (BLA, "solid"), "fjv": (ORANGE, "solid"),
         "bilprod": (BLA, "solid"), "forbranning": (ORANGE, "solid"), "bilar_hh": (AQUA, "solid"), "km_bil": (NEUTRAL, "solid"),
         "mat": (AQUA, "solid"), "ovrig": (BLA, "solid"), "flyg": (ORANGE, "solid"), "offentlig": (NEUTRAL, "solid")}


def _meta() -> pd.DataFrame:
    return fb().utveckling.set_index("faktor")


def _u() -> dict:
    u = ss.scen.get("utveckling")
    if not u:
        u = ss.scen["utveckling"] = utveckling_standard(fb())
    std = utveckling_standard(fb())
    u.setdefault("takt", {})
    for f, v in std["takt"].items():
        u["takt"].setdefault(f, list(v))
    for flagga in ("anl_foljer_betong", "ovrig_foljer_bilprod"):
        u.setdefault(flagga, std[flagga])
    return u


def _lankad(u: dict, f: str) -> bool:
    return f in KOPPLINGAR and bool(u.get(KOPPLINGAR[f][0]))


def _tabell(grupp: str, u: dict):
    """Redigerbar tabell: en rad per faktor i gruppen, en kolumn per period."""
    meta = _meta()
    faktorer = [f for f in meta.index if meta.loc[f, "grupp"] == grupp and not _lankad(u, f)]
    if not faktorer:
        return

    def bas():
        rader = []
        for f in faktorer:
            r = {"Faktor": meta.loc[f, "namn"], "Enhet": meta.loc[f, "enhet"]}
            r.update({n: float(u["takt"][f][i]) for i, n in enumerate(PERIODNAMN)})
            r["Källa"] = kalla_kort(meta.loc[f, "kalla"])
            rader.append(r)
        return pd.DataFrame(rader)
    df = editor(f"utv_{grupp}", bas, hide_index=True, disabled=["Faktor", "Enhet", "Källa"], column_config={
        "Faktor": COL.TextColumn(width="large", pinned=True),
        **{n: COL.NumberColumn(n, min_value=-100.0, max_value=100.0, step=0.01, format="%.2f",
                               help=f"Förändring per år {n}. Negativt värde = minskning.") for n in PERIODNAMN},
    })
    for f, r in zip(faktorer, df.to_dict("records")):
        u["takt"][f] = [float(r[n]) if r[n] is not None and r[n] == r[n] else 0.0 for n in PERIODNAMN]


def _kommentarer(grupp: str, u: dict):
    meta = _meta()
    with st.expander("Källor och motivering för standardvärdena"):
        for f in [f for f in meta.index if meta.loc[f, "grupp"] == grupp]:
            r = meta.loc[f]
            st.markdown(f"**{r['namn']}.** {r['kommentar']}  \n<span style='color:{INK2};font-size:13px'>{r['status']} · "
                        f"{kalla_text(r['kalla'])}</span>", unsafe_allow_html=True)


def _aterstall(grupp: str):
    if st.button(f"Återställ standard för {grupp.lower()}", key=k(f"utv_std_{grupp}")):
        std = utveckling_standard(fb())
        u = _u()
        for f in _meta().index:
            if _meta().loc[f, "grupp"] == grupp:
                u["takt"][f] = list(std["takt"][f])
        if grupp == "Byggpåverkan":
            u["anl_foljer_betong"] = True
        if grupp == "Konsumtion och offentlig sektor":
            u["ovrig_foljer_bilprod"] = True
        ny_version(); st.rerun()


def _figur(titel: str, undertitel: str, serier: list[tuple[str, list[int], list[float], str, str]], yt: str, procent: bool = False,
           legend_hoger: bool = False):
    fig = go.Figure()
    for namn, x, y, farg, streck in serier:
        fig.add_scatter(x=x, y=y, name=namn, mode="lines", line=dict(color=farg, width=2, dash=streck),
                        hovertemplate=f"{namn}<br>%{{x}}: %{{y:.{0 if procent else 1}f}}{' %' if procent else ''}<extra></extra>")
    fig.update_layout(
        title=dict(text=f"<b>{titel}</b><br><span style='font-size:12px;color:{INK2}'>{undertitel}</span>", x=0, xanchor="left", font=dict(size=15)),
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK), height=380, plot_bgcolor=SURF, paper_bgcolor=SURF,
        margin=dict(l=10, r=10, t=64, b=10), hovermode="x unified", separators=", ",
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0, title=None, font=dict(size=11)),
    )
    if legend_hoger:
        fig.update_layout(legend=dict(orientation="v", yanchor="top", y=1, x=1.02, xanchor="left"), margin=dict(l=10, r=10, t=64, b=10))
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickcolor=GRID, range=[BASAR, SLUTAR])
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=INK2, title=yt, rangemode="tozero")
    return fig


def _diagram(u: dict):
    utv = Utveckling(fb(), ss.scen)
    meta = _meta()
    ar = list(range(BASAR, SLUTAR + 1))
    idx = lambda f: [utv.index(f, y) * 100 for y in ar]  # noqa: E731
    namn = lambda f: meta.loc[f, "namn"]  # noqa: E731

    c1, c2 = st.columns(2)
    with c1:
        serier = [(namn(f), ar, idx(f), *STOMLINJE[f]) for f in STOMLINJE if f != "anl"]
        if not u.get("anl_foljer_betong"):
            serier.append(("Anläggning", ar, idx("anl"), *STOMLINJE["anl"]))
        st.plotly_chart(_figur("Byggpåverkan per stomme", "Index 2026 = 100 · heldragen = BAU, streckad = BÄST · Generisk följer Betong BAU", serier, "Index"),
                        width="stretch", config=CONF)
    with c2:
        kx = Kontext(fb(), ss.scen)
        serier = [("El (svensk elmix)", ar, [kx.el(y) for y in ar], *LINJE["el"]),
                  ("Fjärrvärme (ortens värde)", ar, [kx.fjv(y) for y in ar], *LINJE["fjv"])]
        st.plotly_chart(_figur("Elens och fjärrvärmens klimatfaktor", "g CO2e per kWh", serier, "g CO2e/kWh"), width="stretch", config=CONF)
    c1, c2 = st.columns(2)
    with c1:
        serier = [(namn(f), ar, idx(f), *LINJE[f]) for f in ("bilprod", "forbranning", "bilar_hh", "km_bil")]
        st.plotly_chart(_figur("Mobilitet", "Index 2026 = 100", serier, "Index"), width="stretch", config=CONF)
    with c2:
        mixar = [mix_for_ar(kx, y) for y in ar]
        serier = [("Elbilar", ar, [m["bev"] * 100 for m in mixar], BLA, "solid"),
                  ("Laddhybrider", ar, [m["phev"] * 100 for m in mixar], ORANGE, "solid"),
                  ("Summa laddbara", ar, [(m["bev"] + m["phev"]) * 100 for m in mixar], NEUTRAL, "dash")]
        st.plotly_chart(_figur("Elbilar och laddhybrider", "Andel av personbilarnas körsträcka, %", serier, "%", procent=True),
                        width="stretch", config=CONF)
    serier = [(namn(f), ar, idx(f), *LINJE[f]) for f in ("mat", "ovrig", "flyg", "offentlig")]
    st.plotly_chart(_figur("Konsumtion och offentlig sektor", "Index 2026 = 100", serier, "Index", legend_hoger=True), width="stretch", config=CONF)

    rader = []
    for f in meta.index:
        if f in PROCENTENHETER:
            m0 = ss.scen["mobilitet"]["mix"].get(f, 0.0)
            rad = {"Faktor": namn(f) + " (% av körsträckan)", "2026": round(m0 * 100, 1)}
            rad.update({str(y): round(mix_for_ar(kx, y)[f] * 100, 1) for y in NYCKELAR})
        else:
            rad = {"Faktor": namn(f), "2026": 100.0}
            rad.update({str(y): round(utv.index(f, y) * 100, 1) for y in NYCKELAR})
        rader.append(rad)
    st.markdown("##### Index och andelar vid nyckelår")
    st.dataframe(pd.DataFrame(rader), hide_index=True, width="stretch",
                 column_config={str(y): COL.NumberColumn(format="%.1f") for y in [2026] + NYCKELAR})
    st.caption("Index 2026 = 100. Elbilar och laddhybrider visas som andel av körsträckan i procent.")


def visa():
    st.markdown("Här styr du hur modellens viktigaste emissionsfaktorer utvecklas över tid. Startvärdet gäller **2026**; från **2027** till "
                "**2100** anges en årlig förändring i procent per period, där negativt värde betyder minskning. Värdena är förifyllda med "
                "källa och gäller hela modellen.")
    u = _u()

    st.markdown("##### Startvärden 2026")
    c1, c2, c3 = st.columns(3)
    el0 = c1.number_input("Elens klimatfaktor (g CO2e/kWh)", 0.0, 1000.0, eget_param("el.startvarde"), 1.0, key=k("utv_el0"),
                          help=f"Svensk elmix enligt Boverket: {param_info('el.startvarde')}. Gäller byggnader, elbilar och solel.")
    if abs(el0 - fb().param("el.startvarde")) > 1e-9:
        ss.scen.setdefault("parametrar", {})["el.startvarde"] = el0
    else:
        ss.scen.get("parametrar", {}).pop("el.startvarde", None)
    ss.scen["fjarrvarme"]["startvarde"] = c2.number_input(
        "Ortens fjärrvärme (g CO2e/kWh)", 0.0, 1000.0, float(ss.scen["fjarrvarme"]["startvarde"]), 1.0, key=k("utv_fjv0"),
        help=f"Ange leverantörens värde enligt Energiföretagens miljövärdering. Förifyllt: {param_info('fjv.startvarde')}.")
    c3.caption("Byggpåverkan per byggnadstyp och stomme (nivå 2026) väljs under Indata → Byggnader och visas i fliken Faktorer och "
               "parametrar. Drivlinemixen 2025 anges under Indata → Mobilitet.")

    st.markdown("#### Byggpåverkan")
    st.caption("Byggskedets klimatpåverkan per stomme, A1–A5. Standard: Tabell A utökad, där BAU följer SBUF 14381 Insteg och BÄST följer "
               "SBUF 14381 Färdplan till 2035, med försiktig extrapolering till 2070. Generisk stomme är Betong BAU och följer dess kurva.")
    u["anl_foljer_betong"] = st.toggle("Anläggning följer betongstommens kurva", value=bool(u["anl_foljer_betong"]), key=k("utv_anl"),
                                       help="Gäller ytor, betong, massor, ledningar, pålning och spont. Engångsvärden räknas som angivna.")
    _tabell("Byggpåverkan", u)
    c1, c2 = st.columns([1, 3])
    with c1:
        _aterstall("Byggpåverkan")
    with c2:
        _kommentarer("Byggpåverkan", u)

    st.markdown("#### Energi")
    st.caption("Elens förändring gäller i hela modellen: byggnadernas el, elbilarnas laddning och solel.")
    _tabell("Energi", u)
    c1, c2 = st.columns([1, 3])
    with c1:
        _aterstall("Energi")
    with c2:
        _kommentarer("Energi", u)

    st.markdown("#### Mobilitet")
    st.caption("Bilproduktionens klimatavtryck följer den globala elens klimatfaktor. Elbilar och laddhybrider ökar i **procentenheter** "
               "av körsträckan per år, tillsammans högst 100 %; övriga drivlinor minskar i proportion.")
    _tabell("Mobilitet", u)
    c1, c2 = st.columns([1, 3])
    with c1:
        _aterstall("Mobilitet")
    with c2:
        _kommentarer("Mobilitet", u)

    st.markdown("#### Konsumtion och offentlig sektor")
    u["ovrig_foljer_bilprod"] = st.toggle("Övrig konsumtion följer bilproduktionens kurva (globalt elsnitt)", value=bool(u["ovrig_foljer_bilprod"]),
                                          key=k("utv_ovr"))
    _tabell("Konsumtion och offentlig sektor", u)
    c1, c2 = st.columns([1, 3])
    with c1:
        _aterstall("Konsumtion och offentlig sektor")
    with c2:
        _kommentarer("Konsumtion och offentlig sektor", u)

    st.markdown("#### Resulterande utveckling")
    senare(lambda res: _diagram(_u()))
