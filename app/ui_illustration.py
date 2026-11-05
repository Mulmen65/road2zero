"""Fliken Illustration: diagram över utsläpp per år, mot klimatbudgeten, per kategori och flöden från indata till kategorier."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from road2zero.kontext import Kontext
from road2zero.konstanter import FARG, KATEGORI_NAMN, NIVA, NIVA_NAMN
from road2zero.modules.mobilitet import mix_for_ar

from .common import fb, fmt, k, ss

INK = "#0b0b0b"; INK2 = "#52514e"; GRID = "#e6e5e1"; SURF = "#fcfcfb"
FONT = dict(family="Inter, system-ui, sans-serif", size=13, color=INK)
CONF = {"displaylogo": False, "locale": "sv", "toImageButtonOptions": {"format": "png", "scale": 2}}


def _layout(fig, titel: str, undertitel: str = "", hojd: int = 420, yt: str = "t CO2e"):
    fig.update_layout(
        title=dict(text=f"<b>{titel}</b>" + (f"<br><span style='font-size:12px;color:{INK2}'>{undertitel}</span>" if undertitel else ""),
                   x=0, xanchor="left", font=dict(size=16)),
        font=FONT, height=hojd, plot_bgcolor=SURF, paper_bgcolor=SURF, margin=dict(l=10, r=10, t=70, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0, title=None), hoverlabel=dict(bgcolor="white", font_size=12),
        separators=", ",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickcolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=INK2, zerolinewidth=1, title=yt, tickformat=",.0f")
    return fig


def staplar_per_ar(res, niva):
    p = res.per_ar_och_kategori()
    fig = go.Figure()
    for kat in KATEGORI_NAMN:
        if NIVA[kat] > niva or not p[kat].abs().sum():
            continue
        fig.add_bar(x=p.index, y=p[kat], name=kat, marker=dict(color=FARG[kat], line=dict(color=SURF, width=1)),
                    hovertemplate=f"{kat}<br>%{{x}}: %{{y:,.0f}} t<extra></extra>")
    n = res.netto_per_niva()
    fig.add_scatter(x=n["ar"], y=n[f"niva{niva}"], name="Netto", mode="lines", line=dict(color=INK, width=2),
                    hovertemplate="Netto %{x}: %{y:,.0f} t<extra></extra>")
    fig.update_layout(barmode="relative", bargap=0.15, hovermode="x unified")
    topp = n.loc[n[f"niva{niva}"].idxmax()]
    fig.add_annotation(x=topp["ar"], y=topp[f"niva{niva}"], text=f"{fmt(topp[f'niva{niva}'])} t {int(topp['ar'])}", showarrow=True,
                       arrowhead=0, ax=40, ay=-25, font=dict(color=INK, size=12))
    return _layout(fig, "Utsläpp per år och klimatkategori", f"{NIVA_NAMN[niva]} · negativa utsläpp under nollinjen · linjen är nettot", 460)


def mot_budget(res, niva):
    t = res.budget["tabell"]
    total = res.budget["stadsdel_t"]
    fig = go.Figure()
    fig.add_scatter(x=t["ar"], y=t["budget_kum_t"], name="Stadsdelens kumulativa budget", mode="lines", fill="tozeroy",
                    line=dict(color="#008300", width=2, dash="dash"), fillcolor="rgba(0,131,0,0.10)",
                    hovertemplate="Budget t.o.m. %{x}: %{y:,.0f} t<extra></extra>")
    fig.add_scatter(x=t["ar"], y=t[f"netto_kum_niva{niva}"], name=f"Kumulativa nettoutsläpp, nivå {niva}", mode="lines",
                    line=dict(color=INK, width=2.5), hovertemplate="Netto t.o.m. %{x}: %{y:,.0f} t<extra></extra>")
    slut = res.budget["slutar"][niva]
    if slut:
        fig.add_vline(x=slut, line=dict(color="#d03b3b", width=1.5, dash="dot"))
        fig.add_annotation(x=slut, y=1, yref="paper", text=f"Budgeten förbrukad {slut}", showarrow=False, xanchor="left", xshift=6,
                           font=dict(color="#d03b3b", size=12))
    fig.add_hline(y=total, line=dict(color="#008300", width=1), annotation_text=f"Hela budgeten {fmt(total)} t",
                  annotation_position="top left", annotation_font=dict(color=INK2, size=12))
    fig.update_layout(hovermode="x unified")
    b = ss.scen["budget"]
    return _layout(fig, "Vägen mot noll: kumulativa nettoutsläpp mot klimatbudget",
                   f"{b['temperatur']} °C och {b['sannolikhet']} % sannolikhet · Forster m.fl. (2026), lika per person, faktiska invånare", 440)


def per_kategori(res, niva):
    tot = res.totalt_per_kategori()
    kat = [c for c in KATEGORI_NAMN if NIVA[c] <= niva]
    v = [float(tot[c]) for c in kat]
    fig = go.Figure(go.Bar(y=kat, x=v, orientation="h", marker=dict(color=[FARG[c] for c in kat]),
                           text=[f"{fmt(x)} t" for x in v], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:,.0f} t<extra></extra>"))
    fig.update_yaxes(autorange="reversed", title=None, gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=INK2, tickformat=",.0f", title="t CO2e")
    fig = _layout(fig, "Summa per klimatkategori", f"{res.ar()[0]}–{res.ar()[-1]}, {NIVA_NAMN[niva].lower()}", 40 * len(kat) + 140, yt=None)
    fig.update_xaxes(title="t CO2e"); fig.update_layout(showlegend=False, margin=dict(l=10, r=70, t=70, b=10))
    return fig


def vattenfall(res, niva):
    tot = res.totalt_per_kategori()
    kat = [c for c in KATEGORI_NAMN if NIVA[c] <= niva and c != "Negativa utsläpp"]
    x = kat + ["Negativa utsläpp", f"Netto nivå {niva}"]
    y = [float(tot[c]) for c in kat] + [float(tot["Negativa utsläpp"]), 0]
    fig = go.Figure(go.Waterfall(x=x, y=y, measure=["relative"] * (len(kat) + 1) + ["total"], text=[fmt(v) for v in y[:-1]] + [fmt(sum(y))],
                                 textposition="outside", connector=dict(line=dict(color=GRID)),
                                 increasing=dict(marker=dict(color="#52514e")), decreasing=dict(marker=dict(color="#008300")),
                                 totals=dict(marker=dict(color=INK)), hovertemplate="%{x}: %{y:,.0f} t<extra></extra>"))
    fig.update_layout(showlegend=False)
    return _layout(fig, "Från bruttoutsläpp till netto", "Kategorierna summeras, negativa utsläpp dras av", 420)


def per_invanare(res, niva):
    n = res.netto_per_niva().set_index("ar")
    t = res.budget["tabell"].set_index("ar")
    inv = pd.Series(res.invanare)
    per = (n[f"niva{niva}"] / inv.reindex(n.index)).where(inv.reindex(n.index) > 0)
    fig = go.Figure()
    fig.add_scatter(x=per.index, y=per.values, name=f"Nettoutsläpp per invånare, nivå {niva}", mode="lines", line=dict(color=INK, width=2.5),
                    hovertemplate="%{x}: %{y:.2f} t per invånare<extra></extra>")
    fig.add_scatter(x=t.index, y=t["andel_per_person_t"], name="Budgetandel per person och år", mode="lines",
                    line=dict(color="#008300", width=2, dash="dash"), hovertemplate="%{x}: %{y:.2f} t per person<extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig = _layout(fig, "Per invånare och år jämfört med budgetandelen", "Byggskedet slås ut på invånarna det år BTA:n blir klar", 400, yt="t CO2e per person och år")
    fig.update_yaxes(tickformat=",.1f")
    return fig


def sankey(res, niva):
    d = res.lang[(res.lang["t"] > 0) & (res.lang["niva"] <= niva)].groupby(["modul", "kategori"], as_index=False)["t"].sum()
    neg = res.lang[res.lang["kategori"] == "Negativa utsläpp"].groupby(["modul"], as_index=False)["t"].sum()
    moduler = sorted(d["modul"].unique())
    kat = [c for c in KATEGORI_NAMN if c in set(d["kategori"])]
    noder = moduler + kat
    idx = {n: i for i, n in enumerate(noder)}
    hex2 = lambda h, a: f"rgba({int(h[1:3], 16)},{int(h[3:5], 16)},{int(h[5:7], 16)},{a})"
    fig = go.Figure(go.Sankey(
        arrangement="snap", valueformat=",.0f", valuesuffix=" t",
        node=dict(label=noder, pad=14, thickness=14, line=dict(width=0),
                  color=["#c3c2b7"] * len(moduler) + [FARG[c] for c in kat]),
        link=dict(source=[idx[m] for m in d["modul"]], target=[idx[c] for c in d["kategori"]], value=d["t"].tolist(),
                  color=[hex2(FARG[c], 0.35) for c in d["kategori"]])))
    fig = _layout(fig, "Från indatamodul till klimatkategori", f"Utsläpp {res.ar()[0]}–{res.ar()[-1]}; negativa utsläpp {fmt(neg['t'].sum())} t visas inte", 460, yt=None)
    return fig


def sammanhang(res):
    kx = Kontext(fb(), ss.scen)
    ar = res.ar()
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Elens klimatfaktor (g CO2e/kWh)", "Elbilar och laddhybrider, andel av körsträckan (%)", "Invånare"))
    fig.add_scatter(x=ar, y=[kx.el(y) for y in ar], mode="lines", line=dict(color="#2a78d6", width=2), row=1, col=1,
                    hovertemplate="%{x}: %{y:.1f} g/kWh<extra></extra>")
    fig.add_scatter(x=ar, y=[(lambda m: (m["bev"] + m["phev"]) * 100)(mix_for_ar(kx, y)) for y in ar], mode="lines",
                    line=dict(color="#e87ba4", width=2), row=1, col=2, hovertemplate="%{x}: %{y:.0f} %<extra></extra>")
    fig.add_scatter(x=ar, y=[res.invanare.get(y, 0) for y in ar], mode="lines", line=dict(color=INK, width=2), row=1, col=3,
                    hovertemplate="%{x}: %{y:,.0f} invånare<extra></extra>")
    fig.update_layout(showlegend=False)
    fig = _layout(fig, "Förutsättningar över tid", "Elens klimatfaktor, laddbara bilars andel och antalet invånare enligt fliken Emissionsfaktorer över tid", 340, yt=None)
    # delrubrikerna ligger ovanför ritytan; större toppmarginal så att de inte krockar med undertiteln
    fig.update_layout(margin=dict(t=110))
    fig.update_annotations(font=dict(size=12, color=INK))
    fig.update_yaxes(tickformat=",.0f")
    return fig


def visa(res):
    if res.lang.empty:
        st.info("Diagrammen visas när det finns indata. Börja med byggbeståndet under Indata → 1 Byggnader.")
        return
    niva = st.radio("Redovisningsnivå", [1, 2, 3], index=int(ss.scen["budget"]["niva"]) - 1, horizontal=True, format_func=NIVA_NAMN.get, key=k("ill_niva"))
    st.plotly_chart(staplar_per_ar(res, niva), width="stretch", config=CONF)
    st.plotly_chart(mot_budget(res, niva), width="stretch", config=CONF)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(per_kategori(res, niva), width="stretch", config=CONF)
    with c2:
        st.plotly_chart(vattenfall(res, niva), width="stretch", config=CONF)
    st.plotly_chart(per_invanare(res, niva), width="stretch", config=CONF)
    st.plotly_chart(sankey(res, niva), width="stretch", config=CONF)
    st.plotly_chart(sammanhang(res), width="stretch", config=CONF)
    st.caption("Alla värden i diagrammen finns som tabeller i fliken Resultat och kan laddas ned där.")
