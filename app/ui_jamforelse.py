"""Flikarna Jämförelse och Rättvis jämförelse i road2zero-scenario."""
from __future__ import annotations

import io
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from road2zero import jamforelse as jm
from road2zero.konstanter import FARG as KATFARG
from road2zero.konstanter import KATEGORI_NAMN, NIVA, NIVA_INNEHALL, NIVA_NAMN
from road2zero.scenario import till_json

from .common import fb, fmt, giltigt, ss
from .scenarier import FARG, etikett, kort, markering, medtagna
from .diagram import CONF, INK, INK2, SURF
from .diagram import layout as _layout


@st.cache_data(max_entries=60, show_spinner=False)
def _analys(scen_json: str, lika: bool, livslangd: float, m2: float) -> dict:
    return jm.analys(json.loads(scen_json), fb(), livslangd, m2, lika=lika)


def _fmt_delta(v: float, d: int = 0, enhet: str = "") -> str:
    """Skillnad med tecken. Ett vanligt minustecken först, så att st.metric visar nedåtpil."""
    s = fmt(abs(v), d)
    return ("+" if v > 0 else "-" if v < 0 else "") + s + enhet


def _tecken(v: float, d: int = 2) -> str:
    """Skillnad med tecken för löptext (typografiskt minustecken)."""
    return ("+" if v > 0 else "") + fmt(v, d)


def _rel(x: float, bas: float) -> str:
    return "–" if not bas else _fmt_delta((x / bas - 1) * 100, 0, " %")


def _saknas(n_med: list[str]) -> bool:
    if len(n_med) < 2:
        st.info("Jämförelsen visas när minst två scenarier har byggnader. Välj scenario överst och lägg in indata, "
                "öppna en sparad fil eller hämta ett färdigt fall i sidopanelen.")
        return True
    return False


# ---------------------------------------------------------------- Jämförelse
def jamforelse(res: dict):
    med = medtagna()
    if _saknas(med):
        return
    c1, c2 = st.columns([2, 1])
    niva = c1.radio("Redovisningsnivå", [1, 2, 3], index=2, horizontal=True, format_func=NIVA_NAMN.get, key="jmf_niva")
    bas = giltigt(c2.selectbox("Jämför mot", med, format_func=kort, key="jmf_bas"), med, med[0], kort)
    st.caption(NIVA_INNEHALL[niva] + ". Skillnaderna anges mot det valda scenariot; lägre är bättre.")

    nk = {n: res[n].nyckeltal() for n in med}
    kol = st.columns(len(med))
    for c, n in zip(kol, med):
        r = res[n]; x = nk[n]; b = nk[bas]
        with c:
            st.markdown(markering(n), unsafe_allow_html=True)
            st.caption(f"{r.ar()[0]}–{r.ar()[-1]} · {fmt(x['bta'])} m² BTA · {fmt(x['invanare_full'])} invånare")
            st.metric(f"Nettoutsläpp nivå {niva}", f"{fmt(x['netto'][niva])} t",
                      None if n == bas else _rel(x["netto"][niva], b["netto"][niva]), delta_color="inverse")
            st.metric(f"Per invånare och år {x['ref_ar']}", f"{fmt(x['per_inv_ref'][niva], 2)} t",
                      None if n == bas else _fmt_delta(x["per_inv_ref"][niva] - b["per_inv_ref"][niva], 2, " t"), delta_color="inverse")
            st.metric("Exploateringen per m² BTA", f"{fmt(x['per_m2_niva1'])} kg",
                      None if n == bas else _fmt_delta(x["per_m2_niva1"] - b["per_m2_niva1"], 0, " kg"), delta_color="inverse")
            slut = r.budget["slutar"][niva]
            st.metric("Budgeten förbrukad", str(slut) if slut else "Inte före slutåret")
    if len({res[n].ar()[0] for n in med}) > 1 or len({res[n].ar()[-1] for n in med}) > 1:
        st.warning("Scenarierna har olika tidsperioder. Summor över perioden går då inte att jämföra direkt; använd per invånare, "
                   "per m² BTA eller fliken Rättvis jämförelse.")

    st.plotly_chart(_per_kategori(res, med, niva), width="stretch", config=CONF)
    st.plotly_chart(_per_ar(res, med, niva), width="stretch", config=CONF)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(_mot_budget(res, med, niva), width="stretch", config=CONF)
    with c2:
        st.plotly_chart(_per_invanare(res, med, niva), width="stretch", config=CONF)

    st.markdown("##### Summa per klimatkategori")
    t = pd.DataFrame({etikett(n): res[n].totalt_per_kategori() for n in med})
    t = t.loc[[k for k in KATEGORI_NAMN if NIVA[k] <= niva]]
    t.loc[f"Netto nivå {niva}"] = t.sum()
    vis = t.map(lambda v: fmt(v))
    for n in med:
        if n != bas:
            vis[f"{n} mot {bas}"] = [_fmt_delta(a - b_) for a, b_ in zip(t[etikett(n)], t[etikett(bas)])]
    st.dataframe(vis, width="stretch")
    st.download_button("Ladda ned jämförelsen (Excel)", data=_excel(res, med), file_name="road2zero_scenariojamforelse.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _per_kategori(res, med, niva):
    kat = [k for k in KATEGORI_NAMN if NIVA[k] <= niva]
    fig = go.Figure()
    for n in med:
        tot = res[n].totalt_per_kategori()
        fig.add_bar(y=kat, x=[float(tot[k]) for k in kat], orientation="h", name=etikett(n), marker=dict(color=FARG[n], line=dict(color=SURF, width=2)),
                    hovertemplate=f"{etikett(n)}<br>%{{y}}: %{{x:,.0f}} t<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    fig.update_yaxes(autorange="reversed", title=None, gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(title="t CO2e", showgrid=True, gridcolor="#e6e5e1")
    _layout(fig, "Summa per klimatkategori", f"{NIVA_NAMN[niva]} · hela perioden för varje scenario", 120 + 70 * len(kat), yt=None)
    fig.update_xaxes(tickformat=",.0f")
    return fig


def _per_ar(res, med, niva):
    fig = go.Figure()
    for n in med:
        d = res[n].netto_per_niva()
        fig.add_scatter(x=d["ar"], y=d[f"niva{niva}"], name=etikett(n), mode="lines", line=dict(color=FARG[n], width=2),
                        hovertemplate=f"{n} %{{x}}: %{{y:,.0f}} t<extra></extra>")
    fig.update_layout(hovermode="x unified")
    return _layout(fig, "Nettoutsläpp per år", NIVA_NAMN[niva], 420)


def _mot_budget(res, med, niva):
    fig = go.Figure()
    for n in med:
        t = res[n].budget["tabell"]
        fig.add_scatter(x=t["ar"], y=t[f"netto_kum_niva{niva}"], name=f"{n}: kumulativa nettoutsläpp", mode="lines",
                        line=dict(color=FARG[n], width=2), hovertemplate=f"{n} netto t.o.m. %{{x}}: %{{y:,.0f}} t<extra></extra>")
        fig.add_scatter(x=t["ar"], y=t["budget_kum_t"], name=f"{n}: kumulativ budget", mode="lines",
                        line=dict(color=FARG[n], width=2, dash="dash"), hovertemplate=f"{n} budget t.o.m. %{{x}}: %{{y:,.0f}} t<extra></extra>")
    fig.update_layout(hovermode="x unified")
    return _layout(fig, "Kumulativa nettoutsläpp och klimatbudget", "Heldragen linje: utsläpp · streckad: budget (börjar 2026)", 440)


def _per_invanare(res, med, niva):
    fig = go.Figure()
    for n in med:
        r = res[n]; d = r.netto_per_niva()
        grans = 0.1 * max(r.invanare.values())          # tidiga år med få invånare ger mycket höga värden per person
        y = [v / r.invanare[a] if r.invanare.get(a, 0) >= grans else None for a, v in zip(d["ar"], d[f"niva{niva}"])]
        fig.add_scatter(x=d["ar"], y=y, name=etikett(n), mode="lines", line=dict(color=FARG[n], width=2), connectgaps=False,
                        hovertemplate=f"{n} %{{x}}: %{{y:.2f}} t per invånare<extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig = _layout(fig, "Nettoutsläpp per invånare och år", "Från året då minst 10 % av invånarna bor där", 440, yt="t CO2e per invånare")
    fig.update_yaxes(tickformat=",.1f")
    return fig


def _excel(res, med) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame({etikett(n): res[n].totalt_per_kategori() for n in med}).to_excel(w, sheet_name="Per kategori")
        rader = []
        for n in med:
            d = res[n].netto_per_niva().assign(scenario=etikett(n))
            d["invanare"] = [res[n].invanare.get(a, 0.0) for a in d["ar"]]
            rader.append(d)
        pd.concat(rader).to_excel(w, sheet_name="Per år", index=False)
        nk = {etikett(n): {"BTA (m²)": res[n].nyckeltal()["bta"], "Invånare vid full utbyggnad": res[n].nyckeltal()["invanare_full"],
                           **{f"Netto nivå {L} (t)": res[n].netto(L) for L in (1, 2, 3)}} for n in med}
        pd.DataFrame(nk).to_excel(w, sheet_name="Nyckeltal")
    return buf.getvalue()


# ---------------------------------------------------------------- Rättvis jämförelse
KOMPFARG = {"byggskede": KATFARG["Byggnad"], "parkering": KATFARG["Övrig konsumtion"], "anlaggning_mark": KATFARG["Anläggning"],
            "drift": KATFARG["Energi"]}


def rattvis():
    med = medtagna()
    st.markdown("Jämförelsen tar hänsyn till olika andelar bostäder och verksamheter och till att scenarierna byggs olika år. "
                "Bostäder och närservice (skolor) redovisas **per invånare**, verksamheter **per arbetsplats**; parkering, anläggning, "
                "mark och stadsträd fördelas efter BTA. Engångsutsläppen fördelas på referensstudieperioden och läggs till ett års drift "
                "vid full utbyggnad.")
    with st.expander("Metod"):
        st.markdown(jm.__doc__.replace("\n   ", " "))
    if _saknas(med):
        return
    c1, c2, c3, c4 = st.columns([1.6, 1, 1, 1.3])
    perspektiv = c1.radio("Perspektiv", ["Lika förutsättningar", "Faktisk tidpunkt"], horizontal=True, key="rv_persp",
                          help="Lika förutsättningar: alla emissionsfaktorer på 2026 års nivå, så att bara utformningen skiljer. "
                               "Faktisk tidpunkt: emissionsfaktorerna över tid och scenariernas utbyggnadsår.")
    livslangd = c2.number_input("Referensstudieperiod (år)", 10.0, 120.0, fb().param("jmf.livslangd"), 5.0, format="%.0f", key="rv_livslangd",
                                help=fb().param_rad("jmf.livslangd")["kommentar"])
    m2 = c3.number_input("BTA per arbetsplats (m²)", 5.0, 100.0, fb().param("jmf.m2_per_arbetsplats"), 1.0, format="%.0f", key="rv_m2",
                         help=fb().param_rad("jmf.m2_per_arbetsplats")["kommentar"])
    bas = giltigt(c4.selectbox("Jämför mot", med, format_func=kort, key="rv_bas"), med, med[0], kort)
    lika = perspektiv == "Lika förutsättningar"
    with st.spinner("Räknar …"):
        an = {n: _analys(till_json(ss.scenarier[n]), lika, float(livslangd), float(m2)) for n in med}
    mixval = giltigt(st.radio("Standardiserad blandning enligt", med + ["Medel"], horizontal=True, key="rv_mix", format_func=_mixtext,
                              help="Fördelningen mellan boende och verksamheter som alla scenarier vägs med."), med + ["Medel"], med[0], _mixtext)
    w = (sum(a["andel_boende"] for a in an.values()) / len(an)) if mixval == "Medel" else an[mixval]["andel_boende"]
    an = {n: dict(a) for n, a in an.items()}
    jm.standardisera(list(an.values()), w)

    kol = st.columns(len(med))
    for c, n in zip(kol, med):
        a = an[n]; b = an[bas]
        with c:
            st.markdown(markering(n), unsafe_allow_html=True)
            st.caption(f"{fmt(a['andel_boende']*100)} % boende av BTA · {fmt(a['bta_boende_per_inv'], 1)} m² per invånare · "
                       f"{fmt(a['personer_per_hushall'], 2)} personer per hushåll")
            for rubrik, nyckel, d, enhet in (("Livscykel per år, boende", "lc_kg_m2_ar_boende", 2, " kg/m²"),
                                             (f"Standardiserad blandning ({fmt(w*100)} % boende)", "standardiserad_kg_m2_ar", 2, " kg/m²"),
                                             ("Nivå 1 boende per invånare", "niva1_boende_t_per_inv", 2, " t"),
                                             ("Nivå 2 per invånare", "niva2_t_per_inv", 2, " t")):
                st.metric(rubrik, f"{fmt(a[nyckel], d)}{enhet}", None if n == bas else _fmt_delta(a[nyckel] - b[nyckel], d, enhet),
                          delta_color="inverse")

    st.markdown("##### Varför skiljer sig scenarierna?")
    for n in med:
        if n != bas:
            st.markdown(_forklaring_text(an[bas], an[n], bas, n))

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(_komponenter(an, med, perspektiv), width="stretch", config=CONF)
    with c2:
        st.plotly_chart(_per_person(an, med), width="stretch", config=CONF)

    st.markdown("##### Alla mått")
    t = jm.tabell({etikett(n): an[n] for n in med})
    vis = t.copy()
    for col in [etikett(n) for n in med]:
        vis[col] = [fmt(v, 2 if abs(v) < 100 else 0) for v in t[col]]
    st.dataframe(vis, width="stretch", hide_index=True, height=min(1300, 36 * (len(vis) + 1)),
                 column_config={"Mått": st.column_config.TextColumn(width="large"), "Grupp": st.column_config.TextColumn(width="small")})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        t.to_excel(wr, sheet_name=perspektiv[:30], index=False)
        pd.DataFrame({"Metod": [r for r in jm.__doc__.splitlines() if r.strip()]}).to_excel(wr, sheet_name="Metod", index=False)
    st.download_button("Ladda ned måtten (Excel)", data=buf.getvalue(), file_name="road2zero_rattvis_jamforelse.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _mixtext(n: str) -> str:
    return n if n == "Medel" else f"scenario {n}"


def _forklaring_text(b: dict, x: dict, nb: str, nx: str) -> str:
    f = jm.forklaring(b, x)
    riktning = "mer" if f["totalt"] > 0 else "mindre"
    (a0, a1), (p0, p1) = f["yta_per_inv"], f["personer_per_hushall"]
    komp = ", ".join(f"{jm.KOMPONENTER[k].lower()} {_tecken(v)}" for k, v in f["komponenter"].items() if abs(v) >= 0.005)
    text = (f"**Scenario {nx}** ger {fmt(abs(f['totalt']), 2)} t {riktning} per invånare och år än scenario {nb} på nivå 1 (boende). "
            f"{_tecken(f['yta'])} t beror på yta per invånare ({fmt(a1, 1)} mot {fmt(a0, 1)} m²")
    if abs(p1 - p0) > 1e-9:
        text += f"; {fmt(p1, 2)} mot {fmt(p0, 2)} personer per hushåll"
    text += f") och {_tecken(f['intensitet'])} t på utsläpp per m²"
    text += f" ({komp})." if komp else "."
    if abs(f["mobilitet"]) >= 0.005:
        text += f" Mobiliteten skiljer {_tecken(f['mobilitet'])} t per invånare och år."
    return text


def _komponenter(an, med, perspektiv):
    fig = go.Figure()
    x = [f"Scenario {n}" for n in med]
    for k, namn in jm.KOMPONENTER.items():
        fig.add_bar(x=x, y=[an[n]["lc_delar_boende"][k] for n in med], name=namn, marker=dict(color=KOMPFARG[k], line=dict(color=SURF, width=2)),
                    hovertemplate=f"{namn}<br>%{{x}}: %{{y:.2f}} kg/m² och år<extra></extra>")
    fig.update_layout(barmode="relative", bargap=0.45)
    fig = _layout(fig, "Livscykel per år, boende", f"{perspektiv} · kg CO2e per m² BTA och år", 440, yt="kg CO2e per m² och år")
    fig.update_yaxes(tickformat=",.0f")
    return fig


def _per_person(an, med):
    fig = go.Figure()
    x = [f"Scenario {n}" for n in med]
    fig.add_bar(x=x, y=[an[n]["naiv_t_per_inv"] for n in med], name="Hela området per invånare (utan uppdelning)",
                marker=dict(color="#c3c2b7", line=dict(color=SURF, width=2)), hovertemplate="%{x}: %{y:.2f} t<extra></extra>")
    fig.add_bar(x=x, y=[an[n]["niva1_boende_t_per_inv"] for n in med], name="Boende per invånare",
                marker=dict(color=INK2, line=dict(color=SURF, width=2)), hovertemplate="%{x}: %{y:.2f} t<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.35)
    fig = _layout(fig, "Nivå 1 per invånare och år", "Uppdelningen tar bort effekten av olika andelar verksamheter", 440, yt="t CO2e per invånare och år")
    fig.update_yaxes(tickformat=",.2f")
    return fig
