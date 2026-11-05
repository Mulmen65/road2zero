"""Fliken Resultat: urval av klimatkategorier, nyckeltal, diagram, klimatbudget, tabeller med export och källor.

Urvalet styr alla diagram och tabeller i fliken. Klimatbudgeten jämförs med nettot för en redovisningsnivå, eftersom budgeten
gäller nivåerna; summan av urvalet visas som en extra linje när urvalet skiljer sig från nivån.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from road2zero.algoritmer import ALGORITMER
from road2zero.kontext import Kontext
from road2zero.konstanter import FARG, KATEGORI_NAMN, NIVA, NIVA_INNEHALL, NIVA_NAMN
from road2zero.modules.budget import andel_per_person, global_gt
from road2zero.modules.mobilitet import mix_for_ar
from road2zero.scenario import till_json

from .common import fb, fmt, k, ss
from .diagram import BUDGET, CONF, GRID, INK, INK2, MELLANBLA, PETROL, SURF, VARNING, layout, rgba
from .ui_berakningar import visa_modul

SNITT = (2027, 2050)           # förvald analysperiod för snittet per person och år
HOGHOJD = "Höghöjdseffekt"     # flygets delpost som kan väljas bort
ENHETER = {"t": "t CO2e", "person": "t CO2e per person och år", "m2": "kg CO2e per m² BTA"}
# Vilka moduler i fliken Beräkningar som räknar fram varje klimatkategori
KATEGORI_MODULER = {
    "Byggnad": ["1 "], "Energi": ["1 "], "Anläggning": ["2 ", "1 "], "Förändrad markanvändning": ["3 "],
    "Mobilitet och transport": ["4 "], "Flygresor": ["6 "], "Matkonsumtion": ["5 "], "Övrig konsumtion": ["6 "],
    "Offentliga investeringar": ["7 "], "Negativa utsläpp": ["8 ", "1 ", "3 "],
}


@dataclass
class Urval:
    niva: int
    kat: list[str]
    hoghojd: bool
    lang: pd.DataFrame          # res.lang för urvalet
    egen: bool                  # urvalet skiljer sig från nivåns kategorier
    period: tuple[int, int]     # analysperiod för snittet per person och år


# ---------- urval och sammanställningar ----------
def nivans_kategorier(niva: int) -> list[str]:
    return [c for c in KATEGORI_NAMN if NIVA[c] <= niva]


def valj(res) -> Urval:
    c1, c2 = st.columns([1, 3], vertical_alignment="top")
    niva = c1.radio("Utgå från redovisningsnivå", [1, 2, 3], index=int(ss.scen["budget"]["niva"]) - 1, format_func=NIVA_NAMN.get,
                    key=k("res_niva"), help="Nivån förväljer kategorierna. Lägg till eller ta bort kategorier till höger.")
    std = nivans_kategorier(niva)
    kat = c2.pills("Klimatkategorier i diagram och tabeller", KATEGORI_NAMN, selection_mode="multi", default=std,
                   key=k(f"res_kat_{niva}")) or []
    kat = [c for c in KATEGORI_NAMN if c in kat]
    hoghojd = True
    if "Flygresor" in kat:
        hoghojd = c2.toggle("Räkna med flygets höghöjdseffekt", value=True, key=k("res_hoghojd"),
                            help="Flygets värde per invånare räknar med höghöjdseffekt (faktor 1,89 enligt Kamb och Larsson 2018), "
                                 "som är vetenskapligt osäker. Utan den räknas bara koldioxiden från bränslet.")
    c2.caption(NIVA_INNEHALL[niva] if kat == std else f"Eget urval: {len(kat)} av {len(KATEGORI_NAMN)} kategorier.")
    a0, a1 = res.ar()[0], res.ar()[-1]
    std_p = (min(max(SNITT[0], a0), a1), max(min(SNITT[1], a1), a0))
    period = c1.slider("Analysperiod för snitt per person", a0, a1, std_p, 1, key=k(f"res_period_{a0}_{a1}"),
                       help="Snittet per person och år och jämförelsen med budgetutrymmet räknas över de här åren (år med invånare).")         if a1 > a0 else (a0, a1)
    d = res.lang[res.lang["kategori"].isin(kat)]
    if not hoghojd:
        d = d[~((d["kategori"] == "Flygresor") & (d["delpost"] == HOGHOJD))]
    return Urval(niva, kat, hoghojd, d, kat != std or not hoghojd, (int(period[0]), int(period[1])))


def per_ar(res, u: Urval) -> pd.DataFrame:
    """t CO2e per år och vald kategori."""
    if u.lang.empty:
        return pd.DataFrame(0.0, index=pd.Index(res.ar(), name="ar"), columns=u.kat)
    return u.lang.pivot_table(index="ar", columns="kategori", values="t", aggfunc="sum").reindex(index=res.ar(), columns=u.kat).fillna(0.0)


def invanare(res) -> pd.Series:
    return pd.Series({y: res.invanare.get(y, 0.0) for y in res.ar()}, dtype=float)


def per_person(res, u: Urval) -> pd.DataFrame:
    """t CO2e per person och år, per vald kategori; bara år med invånare."""
    inv = invanare(res)
    p = per_ar(res, u)
    return p[inv > 0].div(inv[inv > 0], axis=0)


def person_matt(res, u: Urval) -> dict:
    """Per person: per år, ackumulerat över perioden och snitt för analysperioden, med budgetandelen för samma år."""
    pp = per_person(res, u).sum(axis=1)
    bud = res.budget["tabell"].set_index("ar")["andel_per_person_t"].reindex(pp.index).fillna(0.0)
    i_snitt = [y for y in pp.index if u.period[0] <= y <= u.period[1]]
    return {
        "per_ar": pp, "kum": pp.cumsum(), "budget_per_ar": bud, "budget_kum": bud.cumsum(),
        "snitt": float(pp.loc[i_snitt].mean()) if i_snitt else None, "snitt_budget": float(bud.loc[i_snitt].mean()) if i_snitt else None,
        "snitt_ar": (min(i_snitt), max(i_snitt)) if i_snitt else None,
        "ackumulerat": float(pp.sum()) if len(pp) else None, "ackumulerat_budget": float(bud.sum()) if len(bud) else None,
    }


def omraknad(res, df: pd.DataFrame, enhet: str) -> pd.DataFrame:
    """Tabell i t CO2e per år räknad om till vald enhet."""
    if enhet == "person":
        inv = invanare(res).reindex(df.index)
        return df.div(inv.where(inv > 0), axis=0)
    if enhet == "m2":
        bta = res.bta_totalt()
        return df * 1000 / bta if bta else df * float("nan")
    return df


# ---------- diagram ----------
def _undertitel(res, u: Urval) -> str:
    return f"{res.ar()[0]}–{res.ar()[-1]} · " + ("eget urval" if u.egen else NIVA_NAMN[u.niva].lower())


def stapel_per_kategori(res, u: Urval):
    tot = per_ar(res, u).sum()
    tot = tot[tot.abs() > 0].sort_values()
    pos = tot[tot > 0].sum()
    # positiva staplar får etiketten utanför stapelns ände; negativa får den till höger om nollinjen, som de andra
    text = [f"{fmt(v)} t" + (f" · {fmt(v / pos * 100)} %" if pos else "") if v > 0 else "" for v in tot.values]
    fig = go.Figure(go.Bar(y=tot.index, x=tot.values, orientation="h", marker=dict(color=[FARG[c] for c in tot.index], line=dict(color=SURF, width=2)),
                           text=text, textposition="outside", cliponaxis=False, textfont=dict(color=INK, size=12),
                           hovertemplate="%{y}: %{x:,.0f} t CO2e<extra></extra>"))
    for kat, v in tot[tot < 0].items():
        fig.add_annotation(x=0, y=kat, text=f"{fmt(v)} t", showarrow=False, xanchor="left", xshift=6, font=dict(color=INK, size=12))
    fig = layout(fig, "Summa per klimatkategori", _undertitel(res, u) + " · andel av bruttoutsläppen", 46 * len(tot) + 150, yt=None)
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=INK2, tickformat=",.0f", title="t CO2e", showgrid=True)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", title=None)
    fig.update_layout(showlegend=False, margin=dict(l=10, r=110, t=72, b=10))
    return fig


def tradkarta(res, u: Urval):
    d = u.lang[u.lang["t"] > 0].groupby(["kategori", "delpost"], as_index=False)["t"].sum()
    if d.empty:
        return None
    kat = d.groupby("kategori")["t"].sum()
    ids = list(kat.index) + [f"{r.kategori}/{r.delpost}" for r in d.itertuples()]
    fig = go.Figure(go.Treemap(
        ids=ids, labels=list(kat.index) + list(d["delpost"]), parents=[""] * len(kat) + list(d["kategori"]),
        values=list(kat.values) + list(d["t"]), branchvalues="total",
        marker=dict(colors=[FARG[c] for c in kat.index] + [rgba(FARG[c], 0.72) for c in d["kategori"]], line=dict(color=SURF, width=2)),
        texttemplate="<b>%{label}</b><br>%{value:,.0f} t<br>%{percentRoot:.0%}", hovertemplate="%{label}<br>%{value:,.0f} t CO2e · %{percentRoot:.1%} av allt<extra></extra>",
        tiling=dict(pad=2), pathbar=dict(visible=True), root=dict(color=SURF)))
    fig = layout(fig, "Vad utsläppen består av", "Klimatkategorier och delposter, bara utsläpp · klicka på en ruta för att zooma", 520, yt=None)
    fig.update_layout(margin=dict(l=4, r=4, t=72, b=4))
    return fig


def vattenfall(res, u: Urval):
    tot = per_ar(res, u).sum()
    kat = [c for c in u.kat if c != "Negativa utsläpp" and tot[c]]
    x, y = kat[:], [float(tot[c]) for c in kat]
    if "Negativa utsläpp" in u.kat and tot.get("Negativa utsläpp", 0):
        x.append("Negativa utsläpp"); y.append(float(tot["Negativa utsläpp"]))
    x.append("Summa"); y.append(0.0)
    fig = go.Figure(go.Waterfall(
        x=x, y=y, measure=["relative"] * (len(x) - 1) + ["total"], text=[fmt(v) for v in y[:-1]] + [fmt(sum(y))], textposition="outside",
        connector=dict(line=dict(color=GRID)), increasing=dict(marker=dict(color=MELLANBLA)), decreasing=dict(marker=dict(color=BUDGET)),
        totals=dict(marker=dict(color=PETROL)), cliponaxis=False, hovertemplate="%{x}: %{y:,.0f} t<extra></extra>"))
    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickangle=-30)
    return layout(fig, "Från bruttoutsläpp till summa", "Kategorierna läggs på varandra, negativa utsläpp dras av", 460)


def staplar_per_ar(res, u: Urval, enhet: str = "t"):
    p = omraknad(res, per_ar(res, u), enhet)
    fig = go.Figure()
    for kat in u.kat:
        if p[kat].abs().sum():
            fig.add_bar(x=p.index, y=p[kat], name=kat, marker=dict(color=FARG[kat], line=dict(color=SURF, width=1)),
                        hovertemplate=f"{kat}: %{{y:,.{2 if enhet == 'person' else 0}f}}<extra></extra>")
    s = p.sum(axis=1)
    fig.add_scatter(x=s.index, y=s.values, name="Summa", mode="lines", line=dict(color=INK, width=2),
                    hovertemplate=f"Summa: %{{y:,.{2 if enhet == 'person' else 0}f}}<extra></extra>")
    fig.update_layout(barmode="relative", bargap=0.18, hovermode="x unified")
    fig = layout(fig, "Utsläpp per år och klimatkategori", _undertitel(res, u) + " · negativa utsläpp under nollinjen · linjen är summan",
                 480, yt=ENHETER[enhet])
    if enhet == "person":
        fig.update_yaxes(tickformat=",.1f")
    return fig


def kumulativ_yta(res, u: Urval):
    p = per_ar(res, u).cumsum()
    fig = go.Figure()
    for kat in u.kat:
        if not p[kat].abs().sum():
            continue
        fig.add_scatter(x=p.index, y=p[kat], name=kat, mode="lines", stackgroup="neg" if p[kat].iloc[-1] < 0 else "pos",
                        line=dict(color=FARG[kat], width=1), fillcolor=rgba(FARG[kat], 0.85),
                        hovertemplate=f"{kat}: %{{y:,.0f}} t<extra></extra>")
    s = p.sum(axis=1)
    fig.add_scatter(x=s.index, y=s.values, name="Summa", mode="lines", line=dict(color=INK, width=2, dash="dot"),
                    hovertemplate="Summa: %{y:,.0f} t<extra></extra>")
    fig.update_layout(hovermode="x unified")
    return layout(fig, "Ackumulerade utsläpp", _undertitel(res, u) + " · summerat från startåret", 440)


def smahus(res, u: Urval):
    """Små diagram: en panel per kategori med egen skala och gemensam tidsaxel."""
    p = per_ar(res, u)
    kat = [c for c in u.kat if p[c].abs().sum()]
    if not kat:
        return None
    kol = 3 if len(kat) > 4 else 2
    rader = math.ceil(len(kat) / kol)
    fig = make_subplots(rows=rader, cols=kol, shared_xaxes=True, subplot_titles=kat, vertical_spacing=0.12 if rader > 2 else 0.18,
                        horizontal_spacing=0.07)
    for i, c in enumerate(kat):
        r, cc = divmod(i, kol)
        fig.add_scatter(x=p.index, y=p[c], mode="lines", line=dict(color=FARG[c], width=2), fill="tozeroy", fillcolor=rgba(FARG[c], 0.18),
                        name=c, showlegend=False, row=r + 1, col=cc + 1, hovertemplate=f"{c}<br>%{{x}}: %{{y:,.0f}} t<extra></extra>")
    fig = layout(fig, "Varje kategori för sig", "t CO2e per år · varje panel har egen skala", 200 * rader + 90, yt=None)
    fig.update_annotations(font=dict(size=12, color=INK), xanchor="left", x=None)
    for a, i in zip(fig.layout.annotations, range(len(kat))):
        a.x = fig.get_subplot(i // kol + 1, i % kol + 1).xaxis.domain[0]
    fig.update_yaxes(tickformat=",.0f", title=None)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(margin=dict(l=10, r=10, t=104, b=10))
    return fig


def per_person_ar(res, u: Urval, m: dict):
    pp = per_person(res, u)
    fig = go.Figure()
    for kat in u.kat:
        if kat in pp and pp[kat].abs().sum():
            fig.add_bar(x=pp.index, y=pp[kat], name=kat, marker=dict(color=FARG[kat], line=dict(color=SURF, width=1)),
                        hovertemplate=f"{kat}: %{{y:,.2f}} t<extra></extra>")
    fig.add_scatter(x=m["per_ar"].index, y=m["per_ar"].values, name="Summa per person", mode="lines", line=dict(color=INK, width=2),
                    hovertemplate="Summa: %{y:,.2f} t per person<extra></extra>")
    fig.add_scatter(x=m["budget_per_ar"].index, y=m["budget_per_ar"].values, name="Budgetandel per person och år", mode="lines",
                    line=dict(color=BUDGET, width=2, dash="dash"), hovertemplate="Budgetandel: %{y:,.2f} t<extra></extra>")
    if m["snitt_ar"]:
        a0, a1 = m["snitt_ar"]
        fig.add_vrect(x0=a0 - 0.5, x1=a1 + 0.5, fillcolor=rgba(MELLANBLA, 0.07), line_width=0)
        fig.add_shape(type="line", x0=a0 - 0.5, x1=a1 + 0.5, y0=m["snitt"], y1=m["snitt"], line=dict(color=PETROL, width=2, dash="dot"))
        fig.add_annotation(x=a1 + 0.5, y=m["snitt"], text=f"Snitt {a0}–{a1}: {fmt(m['snitt'], 2)} t", showarrow=False, xanchor="right",
                           yanchor="bottom", font=dict(color=PETROL, size=12))
    fig.update_layout(barmode="relative", bargap=0.18, hovermode="x unified")
    fig = layout(fig, "Per person och år", "t CO2e per invånare och år · skuggat: perioden för snittet · byggskedet slås ut på dem som bor där samma år",
                 460, yt="t CO2e per person och år")
    fig.update_yaxes(tickformat=",.1f")
    return fig


def per_person_kum(res, u: Urval, m: dict):
    fig = go.Figure()
    fig.add_scatter(x=m["budget_kum"].index, y=m["budget_kum"].values, name="Budgetandel per person, ackumulerad", mode="lines",
                    fill="tozeroy", fillcolor=rgba(BUDGET, 0.10), line=dict(color=BUDGET, width=2, dash="dash"),
                    hovertemplate="Budget t.o.m. %{x}: %{y:,.1f} t<extra></extra>")
    fig.add_scatter(x=m["kum"].index, y=m["kum"].values, name="Ackumulerat per person", mode="lines", line=dict(color=INK, width=2.5),
                    hovertemplate="Ackumulerat t.o.m. %{x}: %{y:,.1f} t<extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig = layout(fig, "Ackumulerat per person", "Summan av t CO2e per person och år från startåret, jämfört med budgetandelen per person",
                 420, yt="t CO2e per person")
    fig.update_yaxes(tickformat=",.1f")
    return fig


def mot_budget(res, u: Urval):
    t = res.budget["tabell"]
    total = res.budget["stadsdel_t"]
    niva = u.niva
    fig = go.Figure()
    fig.add_scatter(x=t["ar"], y=t["budget_kum_t"], name="Stadsdelens budget, ackumulerad", mode="lines", fill="tozeroy",
                    line=dict(color=BUDGET, width=2, dash="dash"), fillcolor=rgba(BUDGET, 0.10),
                    hovertemplate="Budget t.o.m. %{x}: %{y:,.0f} t<extra></extra>")
    fig.add_scatter(x=t["ar"], y=t[f"netto_kum_niva{niva}"], name=f"Nettoutsläpp nivå {niva}, ackumulerade", mode="lines",
                    line=dict(color=INK, width=2.5), hovertemplate="Netto t.o.m. %{x}: %{y:,.0f} t<extra></extra>")
    if u.egen:
        s = per_ar(res, u).sum(axis=1).cumsum()
        fig.add_scatter(x=s.index, y=s.values, name="Urvalet, ackumulerat", mode="lines", line=dict(color=MELLANBLA, width=2, dash="dot"),
                        hovertemplate="Urvalet t.o.m. %{x}: %{y:,.0f} t<extra></extra>")
    slut = res.budget["slutar"][niva]
    if slut:
        fig.add_vline(x=slut, line=dict(color=VARNING, width=1.5, dash="dot"))
        fig.add_annotation(x=slut, y=1, yref="paper", text=f"Budgeten förbrukad {slut}", showarrow=False, xanchor="left", xshift=6,
                           font=dict(color=VARNING, size=12))
    fig.add_hline(y=total, line=dict(color=BUDGET, width=1), annotation_text=f"Hela budgeten {fmt(total)} t",
                  annotation_position="top left", annotation_font=dict(color=INK2, size=12))
    fig.update_layout(hovermode="x unified")
    b = ss.scen["budget"]
    return layout(fig, "Vägen mot noll: ackumulerade nettoutsläpp mot klimatbudgeten",
                  f"{b['temperatur']} °C och {b['sannolikhet']} % sannolikhet · Forster m.fl. (2026), lika per person, faktiska invånare", 460)


# ---------- utsläpp per person mot budgetutrymmet ----------
SANNOLIKHETER = [10, 17, 33, 50, 67, 83, 90]


def _gron_skala(n: int) -> list[str]:
    """Sekventiell grön skala, ljus till mörk (högre sannolikhet ger mindre budget och mörkare linje)."""
    a, b = (0xb9, 0xd6, 0xa8), (0x1d, 0x4a, 0x2a)
    return ["#%02x%02x%02x" % tuple(round(x + (y - x) * i / max(1, n - 1)) for x, y in zip(a, b)) for i in range(n)]


def budget_snitt(res, u: Urval, temp: str, sann: int) -> tuple[float | None, float]:
    """Budgetutrymmet per person och år (t CO2e, med andra växthusgaser) i snitt över analysperioden, för år med invånare,
    samt påslaget k. Samma bana och fördelning som modulen Klimatbudget."""
    kx = Kontext(fb(), ss.scen)
    kf = kx.p("budget.k")
    andel, _ = andel_per_person(fb(), global_gt(fb(), temp, sann), kx.p("budget.e0"), kf, res.ar())
    inv = invanare(res)
    ar = [y for y in res.ar() if u.period[0] <= y <= u.period[1] and inv.get(y, 0) > 0]
    return (sum(andel.get(y, 0.0) for y in ar) / len(ar) if ar else None), kf


def snitt_per_kategori(res, u: Urval) -> pd.Series:
    pp = per_person(res, u)
    pp = pp[(pp.index >= u.period[0]) & (pp.index <= u.period[1])]
    return pp.mean() if len(pp) else pd.Series(0.0, index=u.kat)


def person_mot_budget(res, u: Urval, temp: str, sann: int):
    kat = snitt_per_kategori(res, u)
    bud, kf = budget_snitt(res, u, temp, sann)
    if bud is None:
        return None
    co2 = bud / kf
    rad_u, rad_b = "Utsläpp, urvalet", "Budgetutrymme"
    fig = go.Figure()
    for c in u.kat:
        if c in kat and abs(kat[c]) > 1e-9:
            fig.add_bar(y=[rad_u], x=[kat[c]], name=c, orientation="h", marker=dict(color=FARG[c], line=dict(color=SURF, width=2)),
                        hovertemplate=f"{c}: %{{x:,.2f}} t per person och år<extra></extra>")
    # budgeten är genomskinlig med mörk kant så att den inte förväxlas med negativa utsläpp, som är heltäckande gröna
    fig.add_bar(y=[rad_b], x=[co2], name="Budget, koldioxid", orientation="h", marker=dict(color=rgba(BUDGET, 0.55), line=dict(color=BUDGET, width=1.5)),
                hovertemplate="Koldioxid: %{x:,.2f} t per person och år<extra></extra>")
    fig.add_bar(y=[rad_b], x=[bud - co2], name="Budget, andra växthusgaser", orientation="h",
                marker=dict(color=rgba(BUDGET, 0.18), line=dict(color=BUDGET, width=1.5)),
                hovertemplate="Andra växthusgaser: %{x:,.2f} t per person och år<extra></extra>")
    summa = float(kat.sum())
    for y, v in ((rad_u, summa), (rad_b, bud)):
        fig.add_annotation(x=max(v, float(kat[kat > 0].sum()) if y == rad_u else v), y=y, text=f"<b>{fmt(v, 2)} t</b>", showarrow=False,
                           xanchor="left", xshift=8, font=dict(color=INK, size=13))
    fig.update_layout(barmode="relative", bargap=0.35, legend=dict(traceorder="normal"))
    fig = layout(fig, "Utsläpp per person mot budgetutrymmet",
                 f"Snitt {u.period[0]}–{u.period[1]}, t CO2e per person och år · budget {temp} °C, {sann} % sannolikhet (Forster m.fl. 2026), "
                 "inklusive andra växthusgaser", 420, yt=None)
    fig.update_xaxes(gridcolor=GRID, showgrid=True, zerolinecolor=INK2, tickformat=",.1f", title=None)   # enheten står i undertiteln
    fig.update_yaxes(autorange="reversed", title=None)
    fig.add_vline(x=0, line=dict(color=INK2, width=1))
    # förklaringen längst ned i figuren, under talen på x-axeln
    fig.update_layout(margin=dict(l=10, r=80, t=72, b=110), legend=dict(yref="container", y=0.01, yanchor="bottom"))
    return fig


def budget_per_temperatur(res, u: Urval, temp: str, sann: int):
    temps = list(dict.fromkeys(fb().budget["temperatur"]))
    x = [float(t.replace(",", ".")) for t in temps]
    snitt = float(snitt_per_kategori(res, u).sum())
    fig = go.Figure()
    for farg, p in zip(_gron_skala(len(SANNOLIKHETER)), SANNOLIKHETER):
        y = [budget_snitt(res, u, t, p)[0] for t in temps]
        valt = p == int(sann)
        fig.add_scatter(x=x, y=y, name=f"{p} %", mode="lines+markers", line=dict(color=farg, width=3 if valt else 1.8),
                        marker=dict(size=8 if valt else 6, color=farg, line=dict(color=SURF, width=1)),
                        hovertemplate=f"{p} % sannolikhet, %{{x:.1f}} °C: %{{y:,.2f}} t per person och år<extra></extra>")
    vx = float(str(temp).replace(",", "."))
    vy = budget_snitt(res, u, temp, sann)[0]
    fig.add_scatter(x=[vx], y=[vy], mode="markers", name="Valt", showlegend=False, hoverinfo="skip",
                    marker=dict(size=15, color="rgba(0,0,0,0)", line=dict(color=INK, width=2)))
    fig.add_hline(y=snitt, line=dict(color=INK, width=2, dash="dot"), annotation_text=f"Urvalet: {fmt(snitt, 2)} t",
                  annotation_position="top left", annotation_font=dict(color=INK, size=12))
    fig = layout(fig, "Budgetutrymme per person och år för alla temperaturgränser",
                 f"Snitt {u.period[0]}–{u.period[1]} · en linje per sannolikhet att hålla gränsen · ringen är valet ovan · prickad linje: urvalets utsläpp",
                 430, yt="t CO2e per person och år")
    fig.update_xaxes(tickvals=x, ticktext=[f"{t} °C" for t in temps], title="Temperaturgräns")
    fig.update_yaxes(tickformat=",.1f", rangemode="tozero")
    fig.update_layout(legend=dict(title=dict(text="Sannolikhet "), y=-0.25))
    return fig


def person_over_tid(res, u: Urval, temp: str, sann: int):
    """Utsläpp per person och år över tiden mot budgetutrymmet per person och år för vald temperatur och sannolikhet."""
    pp = per_person(res, u)
    if pp.empty:
        return None
    kx = Kontext(fb(), ss.scen)
    kf = kx.p("budget.k")
    andel, _ = andel_per_person(fb(), global_gt(fb(), temp, sann), kx.p("budget.e0"), kf, res.ar())
    ar = list(pp.index)
    bud = [andel.get(y, 0.0) for y in ar]
    fig = go.Figure()
    for kat in u.kat:
        if kat in pp and pp[kat].abs().sum():
            fig.add_bar(x=ar, y=pp[kat], name=kat, marker=dict(color=FARG[kat], line=dict(color=SURF, width=1)),
                        hovertemplate=f"{kat}: %{{y:,.2f}} t<extra></extra>")
    fig.add_scatter(x=ar, y=[b / kf for b in bud], name="Budget, koldioxid", mode="lines", fill="tozeroy",
                    fillcolor=rgba(BUDGET, 0.35), line=dict(color=BUDGET, width=1), hovertemplate="Budget, koldioxid: %{y:,.2f} t<extra></extra>")
    fig.add_scatter(x=ar, y=bud, name="Budget med andra växthusgaser", mode="lines", fill="tonexty", fillcolor=rgba(BUDGET, 0.15),
                    line=dict(color=BUDGET, width=2, dash="dash"), hovertemplate="Budget med andra växthusgaser: %{y:,.2f} t<extra></extra>")
    summa = pp.sum(axis=1)
    fig.add_scatter(x=ar, y=summa, name="Summa per person", mode="lines", line=dict(color=INK, width=2),
                    hovertemplate="Summa: %{y:,.2f} t per person<extra></extra>")
    i = [y for y in ar if u.period[0] <= y <= u.period[1]]
    if i:
        a0, a1 = min(i), max(i)
        snitt = float(summa.loc[i].mean())
        fig.add_vrect(x0=a0 - 0.5, x1=a1 + 0.5, fillcolor=rgba(MELLANBLA, 0.07), line_width=0)
        fig.add_shape(type="line", x0=a0 - 0.5, x1=a1 + 0.5, y0=snitt, y1=snitt, line=dict(color=PETROL, width=2, dash="dot"))
        fig.add_annotation(x=a1 + 0.5, y=snitt, text=f"Snitt {a0}–{a1}: {fmt(snitt, 2)} t", showarrow=False, xanchor="right",
                           yanchor="bottom", font=dict(color=PETROL, size=12))
    fig.update_layout(barmode="relative", bargap=0.18, hovermode="x unified")
    fig = layout(fig, "Utsläpp och budgetutrymme per person, år för år",
                 f"t CO2e per invånare och år · budget {temp} °C, {sann} % sannolikhet · skuggat: analysperioden",
                 yt="t CO2e per person och år", hojd=520)
    fig.update_yaxes(tickformat=",.1f")
    fig.update_layout(margin=dict(l=10, r=10, t=72, b=120), legend=dict(yref="container", y=0.01, yanchor="bottom"))
    return fig


def visa_person_mot_budget(res, u: Urval):
    b = ss.scen["budget"]
    temps = list(dict.fromkeys(fb().budget["temperatur"]))
    c1, c2, c3 = st.columns([1.3, 1.6, 1.4], vertical_alignment="bottom")
    temp = c1.select_slider("Temperaturgräns", temps, value=str(b["temperatur"]), format_func=lambda t: f"{t} °C", key=k("pb_temp"))
    sann = c2.select_slider("Sannolikhet att hålla gränsen", SANNOLIKHETER, value=int(b["sannolikhet"]), format_func=lambda p: f"{p} %",
                            key=k("pb_sann"))
    bud, kf = budget_snitt(res, u, temp, sann)
    snitt = float(snitt_per_kategori(res, u).sum())
    if bud:
        c3.metric("Utsläpp i förhållande till budgeten", f"{fmt(snitt / bud, 1)} gånger",
                  help=f"Urvalets snitt {fmt(snitt, 2)} t delat med budgetutrymmet {fmt(bud, 2)} t per person och år, {u.period[0]}–{u.period[1]}.")
    fig = person_mot_budget(res, u, temp, sann)
    if fig is None:
        st.info("Inga invånare under analysperioden, så det finns inget att jämföra per person.")
        return
    _visa(fig)
    f = person_over_tid(res, u, temp, sann)
    if f is not None:
        _visa(f)
    _visa(budget_per_temperatur(res, u, temp, sann))
    st.caption(f"Budgetutrymmet är den globala kvarvarande koldioxidbudgeten från 2026 (Forster m.fl. 2026) som en jämnt minskande bana, "
               f"räknad upp med {fmt(kf, 3)} (56,8/43,2) för andra växthusgaser och delad lika per person med världsbefolkningen år för år "
               "(UN WPP 2024). Snittet tas över analysperiodens år med invånare, för både utsläppen och budgeten. Utsläppen följer "
               "kategorierna du valt överst. Reglagen här ändrar inte projektets budgetval under Indata.")


def sankey(res, u: Urval):
    d = u.lang[u.lang["t"] > 0].groupby(["modul", "kategori"], as_index=False)["t"].sum()
    if d.empty:
        return None
    moduler = sorted(d["modul"].unique())
    kat = [c for c in KATEGORI_NAMN if c in set(d["kategori"])]
    noder = moduler + kat
    idx = {n: i for i, n in enumerate(noder)}
    fig = go.Figure(go.Sankey(
        arrangement="snap", valueformat=",.0f", valuesuffix=" t",
        node=dict(label=noder, pad=14, thickness=14, line=dict(width=0), color=["#c9d4cf"] * len(moduler) + [FARG[c] for c in kat]),
        link=dict(source=[idx[m] for m in d["modul"]], target=[idx[c] for c in d["kategori"]], value=d["t"].tolist(),
                  color=[rgba(FARG[c], 0.35) for c in d["kategori"]])))
    return layout(fig, "Från indatamodul till klimatkategori", "Utsläpp i urvalet; negativa utsläpp visas inte", 460, yt=None)


def forutsattningar(res):
    kx = Kontext(fb(), ss.scen)
    ar = res.ar()
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Elens klimatfaktor (g CO2e/kWh)", "Laddbara bilar, andel av körsträckan (%)", "Invånare"))
    fig.add_scatter(x=ar, y=[kx.el(y) for y in ar], mode="lines", line=dict(color=MELLANBLA, width=2), row=1, col=1,
                    hovertemplate="%{x}: %{y:.1f} g/kWh<extra></extra>")
    fig.add_scatter(x=ar, y=[(lambda m: (m["bev"] + m["phev"]) * 100)(mix_for_ar(kx, y)) for y in ar], mode="lines",
                    line=dict(color=FARG["Mobilitet och transport"], width=2), row=1, col=2, hovertemplate="%{x}: %{y:.0f} %<extra></extra>")
    fig.add_scatter(x=ar, y=[res.invanare.get(y, 0) for y in ar], mode="lines", line=dict(color=PETROL, width=2), row=1, col=3,
                    hovertemplate="%{x}: %{y:,.0f} invånare<extra></extra>")
    fig.update_layout(showlegend=False)
    fig = layout(fig, "Förutsättningar över tid", "Enligt Emissionsfaktorer över tid och byggbeståndet", 330, yt=None)
    fig.update_annotations(font=dict(size=12, color=INK))
    fig.update_layout(margin=dict(l=10, r=10, t=104, b=10))
    return fig


def _visa(fig):
    if fig is not None:
        st.plotly_chart(fig, width="stretch", config=CONF)


# ---------- tabeller ----------
def tabell_kategori(res, u: Urval, m: dict) -> pd.DataFrame:
    p = per_ar(res, u)
    pp = per_person(res, u)
    tot = p.sum()
    brutto = tot[tot > 0].sum()
    personar = res.personar()
    i_snitt = [y for y in pp.index if u.period[0] <= y <= u.period[1]]
    bta = res.bta_totalt()
    rader = [{"Klimatkategori": c, "Nivå": NIVA[c], "t CO2e": round(float(tot[c])),
              "Andel av brutto": tot[c] / brutto if tot[c] > 0 and brutto else None,
              "kg CO2e per m² BTA": tot[c] * 1000 / bta if bta else None,
              "t per person och år, hela perioden": tot[c] / personar if personar else None,
              f"t per person och år, snitt {u.period[0]}–{u.period[1]}": float(pp.loc[i_snitt, c].mean()) if i_snitt else None,
              "t per person, ackumulerat": float(pp[c].sum()) if len(pp) else None} for c in u.kat]
    rader.append({"Klimatkategori": "Summa för urvalet", "Nivå": None, "t CO2e": round(float(tot.sum())), "Andel av brutto": None,
                  "kg CO2e per m² BTA": tot.sum() * 1000 / bta if bta else None,
                  "t per person och år, hela perioden": tot.sum() / personar if personar else None,
                  f"t per person och år, snitt {u.period[0]}–{u.period[1]}": m["snitt"], "t per person, ackumulerat": m["ackumulerat"]})
    rader.append({"Klimatkategori": "Budgetandel per person", "t per person och år, hela perioden": None,
                  f"t per person och år, snitt {u.period[0]}–{u.period[1]}": m["snitt_budget"], "t per person, ackumulerat": m["ackumulerat_budget"]})
    return pd.DataFrame(rader)


def tabell_per_ar(res, u: Urval, enhet: str) -> pd.DataFrame:
    p = per_ar(res, u)
    p["Summa"] = p.sum(axis=1)
    tab = omraknad(res, p, enhet)
    if enhet == "person":
        tab["Ackumulerat per person"] = tab["Summa"].fillna(0).cumsum().where(tab["Summa"].notna())
        tab["Budgetandel per person"] = res.budget["tabell"].set_index("ar")["andel_per_person_t"].reindex(tab.index)
    else:
        tab["Summa, ackumulerad"] = tab["Summa"].cumsum()
    tab["Invånare"] = invanare(res)
    tab.index.name = "År"
    return tab


def tabell_delposter(res, u: Urval) -> pd.DataFrame:
    d = u.lang.groupby(["kategori", "delpost", "modul"], as_index=False)["t"].sum()
    d["kategori"] = pd.Categorical(d["kategori"], KATEGORI_NAMN, ordered=True)
    d = d.sort_values(["kategori", "t"], ascending=[True, False])
    personar = res.personar()
    d["t per person och år"] = d["t"] / personar if personar else None
    return d.rename(columns={"kategori": "Klimatkategori", "delpost": "Delpost", "modul": "Indatamodul", "t": "t CO2e"})


def excel(res, urval: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for namn, df in urval.items():
            df.to_excel(w, sheet_name=namn, index=namn.startswith("Per år"))
        p = res.per_ar_och_kategori()
        n = res.netto_per_niva().set_index("ar")
        pd.concat([p, n.rename(columns={"niva1": "Netto nivå 1", "niva2": "Netto nivå 2", "niva3": "Netto nivå 3"})], axis=1).to_excel(w, sheet_name="Alla kategorier per år")
        res.lang.sort_values(["ar", "kategori"]).to_excel(w, sheet_name="Lång tabell", index=False)
        res.budget["tabell"].to_excel(w, sheet_name="Klimatbudget", index=False)
        res.spar.to_excel(w, sheet_name="Mellanled", index=False)
        if not res.utanfor.empty:
            res.utanfor.to_excel(w, sheet_name="Undvikna utsläpp", index=False)
        pd.DataFrame(indata_rader(till_json(res.scen)), columns=["indata_json", "fortsatter"]).to_excel(w, sheet_name="Indata", index=False)
    return buf.getvalue()


# ---------- fliken ----------
def nyckeltal(res, u: Urval, m: dict):
    tot = per_ar(res, u).sum()
    bta = res.bta_totalt()
    nk = res.nyckeltal()
    slut = res.budget["slutar"][u.niva]
    c = st.columns([1, 1.35, 1.2, 0.95, 0.9])
    c[0].metric("Summa, t CO2e", fmt(tot.sum()), help=f"t CO2e för de valda kategorierna {res.ar()[0]}–{res.ar()[-1]}")
    snitt_namn = f"{m['snitt_ar'][0]}–{m['snitt_ar'][1]}" if m["snitt_ar"] else f"{u.period[0]}–{u.period[1]}"
    c[1].metric(f"Snitt {snitt_namn}", f"{fmt(m['snitt'], 2)} t/person, år",
                help=f"Medelvärdet av t CO2e per invånare och år {snitt_namn}. Budgetandelen för samma år: {fmt(m['snitt_budget'], 2)} t per person och år.")
    c[2].metric("Ackumulerat", f"{fmt(m['ackumulerat'], 1)} t/person",
                help=f"Summan av t CO2e per invånare och år {res.ar()[0]}–{res.ar()[-1]}. Budgetandelen per person under samma år: {fmt(m['ackumulerat_budget'], 1)} t.")
    c[3].metric("Per m² BTA", f"{fmt(tot.sum() * 1000 / bta if bta else None)} kg", help=f"kg CO2e per m² BTA, {fmt(bta)} m² BTA")
    c[4].metric("Budget förbrukad", str(slut) if slut else "Inte före slutåret",
                help=f"Nivå {u.niva}, {ss.scen['budget']['temperatur']} °C och {ss.scen['budget']['sannolikhet']} %: stadsdelens budget {fmt(res.budget['stadsdel_t'])} t CO2e. "
                     f"{fmt(nk['invanare_full'])} invånare vid full utbyggnad.")


def kallor(res, u: Urval):
    st.markdown("Så räknas de valda kategorierna: formler, parametrar med källa och mellanled för dina indata. "
                "Alla moduler finns också under Så räknas resultatet.")
    visade = set()
    for kat in u.kat:
        moduler = [a for pre in KATEGORI_MODULER.get(kat, []) for a in ALGORITMER if a["modul"].startswith(pre)]
        with st.expander(kat, expanded=(kat == "Flygresor")):
            for a in moduler:
                if len(moduler) > 1:
                    st.markdown(f"**{a['modul']}**")
                if a["modul"] in visade:
                    st.caption("Visas även under en annan kategori ovan.")
                visa_modul(a, res, kallor_med_lank=True)
                visade.add(a["modul"])

def indata_rader(text: str, max_tecken: int = 30000) -> list[tuple[str, int]]:
    """Indata-JSON som rader för Excel, där en cell rymmer högst 32 767 tecken. En rad per JSON-rad; längre rader delas och
    får fortsatter = 1. Indatafilen fås tillbaka som "".join(t + ("" if f else "\\n") for t, f in rader)."""
    ut = []
    for rad in text.splitlines():
        while len(rad) > max_tecken:
            i = max_tecken
            while rad[i] == "=":                 # en cell som börjar med = blir en formel i Excel
                i -= 1
            ut.append((rad[:i], 1))
            rad = rad[i:]
        ut.append((rad, 0))
    return ut


def visa(res):
    if not ss.scen["byggnader"]:
        st.info("Inga byggnader ännu. Lägg till byggbeståndet under Indata → 1 Byggnader; invånarna och deras utsläpp följer av bostäderna.")
    u = valj(res)
    if not u.kat:
        st.warning("Välj minst en klimatkategori.")
        return
    m = person_matt(res, u)
    nyckeltal(res, u, m)

    flikar = st.tabs(["Översikt", "Över tid", "Per person", "Klimatbudget", "Tabeller och export", "Källor och beräkning"])
    with flikar[0]:
        c1, c2 = st.columns([5, 4])
        with c1:
            _visa(stapel_per_kategori(res, u))
        with c2:
            _visa(vattenfall(res, u))
        _visa(tradkarta(res, u))
    with flikar[1]:
        _visa(staplar_per_ar(res, u))
        _visa(kumulativ_yta(res, u))
        _visa(smahus(res, u))
        _visa(forutsattningar(res))
    with flikar[2]:
        c = st.columns(3)
        snitt_namn = f"{m['snitt_ar'][0]}–{m['snitt_ar'][1]}" if m["snitt_ar"] else f"{u.period[0]}–{u.period[1]}"
        c[0].metric(f"Snitt {snitt_namn}", f"{fmt(m['snitt'], 2)} t per person och år",
                    delta=f"budgetandel {fmt(m['snitt_budget'], 2)} t", delta_color="off")
        c[1].metric(f"Ackumulerat {res.ar()[0]}–{res.ar()[-1]}", f"{fmt(m['ackumulerat'], 1)} t per person",
                    delta=f"budgetandel {fmt(m['ackumulerat_budget'], 1)} t", delta_color="off")
        topp = m["per_ar"].idxmax() if len(m["per_ar"]) else None
        c[2].metric("Högst per person och år", f"{fmt(m['per_ar'].max(), 2)} t" if topp else "–", delta=f"år {topp}" if topp else None, delta_color="off")
        _visa(per_person_ar(res, u, m))
        _visa(per_person_kum(res, u, m))
        st.caption("Per person och år = urvalets utsläpp det året delat med invånarna samma år (halvårsregel). Ackumulerat per person är summan "
                   "av dessa årsvärden, och budgetandelen är summan av andelen per person och år för samma år, så att de går att jämföra. "
                   "Byggskedet slås ut på dem som bor i området samma år och ger höga värden de första åren; välj bort Byggnad och "
                   "Anläggning i urvalet för att se invånarnas egna utsläpp.")
    with flikar[3]:
        visa_person_mot_budget(res, u)
        st.divider()
        b = res.budget
        c = st.columns(4)
        c[0].metric("Global budget", f"{fmt(b['global_gt'])} Gt CO2", help=f"{ss.scen['budget']['temperatur']} °C, {ss.scen['budget']['sannolikhet']} % sannolikhet")
        c[1].metric("Andel per person, hela perioden", f"{fmt(b['per_person_total'], 1)} t CO2e", help=b["bana"])
        c[2].metric("Stadsdelens budget", f"{fmt(b['stadsdel_t'])} t CO2e")
        tot = b["tabell"][f"netto_kum_niva{u.niva}"].iloc[-1]
        c[3].metric(f"Andel av budgeten, nivå {u.niva}", f"{fmt(tot / b['stadsdel_t'] * 100 if b['stadsdel_t'] else 0)} %",
                    help=f"Ackumulerade nettoutsläpp {fmt(tot)} t")
        _visa(mot_budget(res, u))
        st.caption("Budgeten gäller redovisningsnivåerna; välj nivå överst. Budgeten är förbrukad det första år då de ackumulerade "
                   "nettoutsläppen överstiger stadsdelens hela budget för perioden. Utsläpp före 2026 får ingen budget.")
    with flikar[4]:
        enhet = st.segmented_control("Enhet i tabellen per år", list(ENHETER), format_func=ENHETER.get, default="t", key=k("res_enhet")) or "t"
        st.markdown("##### Per klimatkategori")
        tk = tabell_kategori(res, u, m)
        tk = tk.round({"kg CO2e per m² BTA": 0} | {c: 2 for c in tk.columns if c.startswith("t per person")})
        st.dataframe(tk, hide_index=True, width="stretch", column_config={
            "Nivå": st.column_config.NumberColumn(format="%d"),
            "t CO2e": st.column_config.NumberColumn(format="localized"),
            "Andel av brutto": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
            "kg CO2e per m² BTA": st.column_config.NumberColumn(format="localized"),
            **{c: st.column_config.NumberColumn(format="localized") for c in tk.columns if c.startswith("t per person")},
        })
        st.caption(f"{fmt(res.personar())} personår under perioden. Undvikna utsläpp från exporterad solel, utanför summan: {fmt(res.nyckeltal()['undvikna'])} t.")
        st.markdown(f"##### Per år, {ENHETER[enhet]}")
        tab = tabell_per_ar(res, u, enhet)
        tab = tab.round(2 if enhet == "person" else 1).round({"Invånare": 0})
        st.dataframe(tab, width="stretch", height=380, column_config={c: st.column_config.NumberColumn(format="localized") for c in tab.columns})
        st.markdown("##### Delposter")
        dp = tabell_delposter(res, u)
        dp = dp.round({"t CO2e": 1, "t per person och år": 3})
        st.dataframe(dp, hide_index=True, width="stretch", column_config={"t CO2e": st.column_config.NumberColumn(format="localized"),
                                                                          "t per person och år": st.column_config.NumberColumn(format="localized")})
        urval = {"Per kategori": tk, f"Per år ({enhet})": tab, "Delposter": dp}
        c1, c2 = st.columns(2)
        c1.download_button("Ladda ned tabellen per år (CSV)", tab.to_csv(sep=";", decimal=",").encode("utf-8-sig"),
                           f"road2zero_per_ar_{enhet}.csv", "text/csv", width="stretch")
        c2.download_button("Ladda ned urvalet och alla resultat (Excel)", excel(res, urval), "road2zero_resultat.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        with st.expander("Flöden från indatamodul till klimatkategori"):
            _visa(sankey(res, u))
    with flikar[5]:
        kallor(res, u)

    if res.kontroller:
        with st.expander(f"Kontroller av indata ({len(res.kontroller)})"):
            for allvar, modul, text in res.kontroller:
                {"fel": st.error, "varning": st.warning}.get(allvar, st.info)(f"{modul}: {text}")
