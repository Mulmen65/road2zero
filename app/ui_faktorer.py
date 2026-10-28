"""Fliken Faktorer och parametrar: hela faktabiblioteket med värde, enhet, status och källa, egna värden och tidskurvor."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from road2zero.algoritmer import TABELLKALLOR
from road2zero.konstanter import ANLAGGNINGSTYPER, BYGGNADSTYPER, STATUS_FARG, STOMMAR
from road2zero.kontext import Kontext

from .common import fb, fmt, k, kalla_kort, kalla_text, ny_version, ss

STATUS_TEXT = {
    "Officiell statistik": "Värde från myndighetsstatistik (SCB, Naturvårdsverket, Trafikanalys, Boverket).",
    "Lagstiftning": "Värde ur EU-rätt eller svensk författning.",
    "Officiellt scenario": "Officiell framskrivning, till exempel EU:s referensscenario.",
    "Litteraturvärde": "Värde ur vetenskaplig rapport eller artikel.",
    "Litteraturvärde (länsvärde)": "Värde ur vetenskaplig rapport för ett län; riksvärde saknas.",
    "Litteraturvärde, ska kontrolleras": "Värde ur vetenskaplig artikel som ännu inte är kontrollerat mot originalet.",
    "Branschschablon": "Schablon från bransch (SBUF) eller vanlig projekteringsschablon.",
    "Modellvärde": "Värde ur en annan beräkningsmodell (Skogskolmodellen).",
    "Härlett": "Räknat fram ur andra källor; härledningen står i kommentaren.",
    "Modellantagande": "Redovisat modellval med stöd i underlaget.",
    "Antagande": "Antagande utan direkt externt belägg; bör ersättas med eget värde när det finns.",
    "Modellval": "Redovisat modellval; kan ändras av användaren.",
    "Användarval": "Värde som användaren förväntas ange.",
    "Källa ska verifieras": "Värdet används men källan är inte bekräftad.",
}


KURVNAMN = {
    "el_eu_referens": "El: EU:s referensscenario",
    "el_eu_wam": "El: EU:s scenario med ytterligare åtgärder",
    "fjarrvarme_eu_referens": "Fjärrvärme: EU:s referensscenario",
    "tradtillvaxt": "Stadsträdens tillväxt efter plantering",
}


def parametrar(res):
    p = fb().parametrar.copy()
    egna = ss.scen.get("parametrar", {})
    p["Eget värde"] = p["id"].map(lambda i: str(egna[i]).replace(".", ",") if i in egna else "")
    p["Används"] = p["id"].isin(res.anvanda)
    p["Källa"] = p["kalla"].map(kalla_kort)
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    moduler = c1.multiselect("Modul", sorted(p["modul"].unique()), key=k("f_modul"), placeholder="Alla moduler")
    status = c2.multiselect("Status", sorted(p["status"].unique()), key=k("f_status"), placeholder="Alla statusklasser")
    sok = c3.text_input("Sök", key=k("f_sok"), placeholder="namn, id eller källa")
    bara = c4.toggle("Bara använda", key=k("f_anv"))
    d = p
    if moduler: d = d[d["modul"].isin(moduler)]
    if status: d = d[d["status"].isin(status)]
    if sok: d = d[d.apply(lambda r: sok.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    if bara: d = d[d["Används"]]
    st.dataframe(d[["modul", "namn", "varde", "Eget värde", "enhet", "status", "Källa", "kommentar", "id", "Används"]].rename(
        columns={"modul": "Modul", "namn": "Parameter", "varde": "Standardvärde", "enhet": "Enhet", "status": "Status", "kommentar": "Kommentar", "id": "Id"}),
        hide_index=True, width="stretch", height=420, column_config={"Används": st.column_config.CheckboxColumn()})
    st.caption(f"{len(d)} av {len(p)} parametrar. {int(p['Används'].sum())} används i den senaste beräkningen.")

    st.markdown("##### Ange eget värde för en parameter")
    numeriska = [r for r in p.itertuples() if _ar_tal(r.varde)]
    val = st.selectbox("Parameter", [r.id for r in numeriska], format_func=lambda i: f"{p.set_index('id').loc[i, 'namn']} ({i})", key=k("f_val"))
    r = p.set_index("id").loc[val]
    c1, c2, c3 = st.columns([2, 1, 1])
    nytt = c1.number_input(f"Värde ({r['enhet']})", value=float(egna.get(val, r["varde"])), format="%.6g", key=k(f"f_v_{val}"))
    if c2.button("Använd eget värde", key=k("f_anvand"), width="stretch"):
        ss.scen.setdefault("parametrar", {})[val] = nytt
        ny_version(); st.rerun()
    if c3.button("Återställ standard", key=k("f_aterstall"), width="stretch", disabled=val not in egna):
        ss.scen["parametrar"].pop(val, None)
        ny_version(); st.rerun()
    st.caption(f"Standard {r['varde']} {r['enhet']}: {r['status']}, {kalla_text(r['kalla'])}. {r['kommentar']}")
    if egna:
        st.info("Egna värden i indata: " + ", ".join(f"{i} = {v}" for i, v in egna.items()))


def _ar_tal(v) -> bool:
    try:
        float(v); return True
    except ValueError:
        return False


def tabeller():
    f = fb()
    val = st.selectbox("Tabell", list(TABELLKALLOR), format_func=lambda t: TABELLKALLOR[t][0], key=k("f_tab"))
    st.caption("Källa: " + kalla_text(TABELLKALLOR[val][1]))
    if val == "byggschabloner":
        t = f.byggschabloner.copy()
        t["kg_co2e_m2"] = t["kg_co2e_m2"].astype(float)
        t = t[t["byggnadstyp"].isin(BYGGNADSTYPER)]
        pv = t.pivot(index="byggnadstyp", columns="stomme", values="kg_co2e_m2")
        pv = pv[[c for c in STOMMAR if c != "generisk"]]
        pv.columns = [STOMMAR[c] for c in pv.columns]
        info = t[t["stomme"] == "generisk"].set_index("byggnadstyp")[["kategori", "startankare"]]
        pv.insert(0, "Startankare", info["startankare"].astype(float))
        pv.insert(0, "SBUF-kategori/proxy", info["kategori"])
        pv.index = [BYGGNADSTYPER.get(i, (i,))[0] for i in pv.index]
        pv = pv.loc[[BYGGNADSTYPER[k_][0] for k_ in BYGGNADSTYPER if BYGGNADSTYPER[k_][0] in pv.index]]
        st.dataframe(pv, width="stretch", column_config={c: st.column_config.NumberColumn(format="%.1f") for c in pv.columns if c != "SBUF-kategori/proxy"})
        st.caption("kg CO2e per m² BTA, moduler A1–A5. BAU = SBUF 14381 Insteg, BÄST = SBUF 14381 Färdplan. Generisk = Betong BAU. "
                   "Lokaler och underjordisk parkering saknas i Tabell A utökad och använder kontorets värden. Startvärdet gäller 2026 och "
                   "följer stommens index i fliken Emissionsfaktorer över tid.")
        with st.expander("Anmärkning och datakvalitet per byggnadstyp"):
            an = t[t["stomme"] == "generisk"][["byggnadstyp", "datakvalitet", "anmarkning", "kalla"]].copy()
            an["byggnadstyp"] = an["byggnadstyp"].map(lambda i: BYGGNADSTYPER[i][0]); an["kalla"] = an["kalla"].map(kalla_kort)
            st.dataframe(an.rename(columns={"byggnadstyp": "Byggnadstyp", "datakvalitet": "Datakvalitet", "anmarkning": "Anmärkning", "kalla": "Källa"}),
                         hide_index=True, width="stretch")
    elif val == "reduktionskurvor":
        t = f.reduktion.copy(); t["ar"] = t["ar"].astype(int); t["faktor"] = t["faktor"].astype(float)
        g = st.selectbox("Byggnadskategori", sorted(t["kategori"].unique()), key=k("f_red"))
        farg = {"betong": "#2a78d6", "stal": "#eb6834", "tra": "#1baf7a"}
        fig = go.Figure()
        for st_ in STOMMAR:
            d = t[(t["kategori"] == g) & (t["stomme"] == st_)]
            if d.empty or st_ == "generisk":
                continue
            bas, niva = st_.split("_")
            fig.add_scatter(x=d["ar"], y=d["faktor"], name=STOMMAR[st_], mode="lines+markers",
                            line=dict(color=farg[bas], width=2, dash="dash" if niva == "bast" else "solid"), marker=dict(size=5))
        fig.update_layout(height=380, yaxis_title="Faktor relativt 2025", margin=dict(l=10, r=10, t=10, b=10), separators=", ",
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")
        st.caption("Tabell A utökad: SBUF 14381 Insteg (BAU, heldragen) och Färdplan (BÄST, streckad) 2025–2035, därefter försiktig "
                   "extrapolering till 2070. Ingen CCS för cement; försiktig extra reduktion för Stål BÄST efter 2030. "
                   "Modellen använder kurvorna som standardtakt per stomme i fliken Emissionsfaktorer över tid.")
    elif val == "utveckling":
        u = f.utveckling.copy()
        from road2zero.utveckling import PERIODKOL, PERIODNAMN
        u = u.rename(columns=dict(zip(PERIODKOL, PERIODNAMN)))
        for c in PERIODNAMN:
            u[c] = u[c].astype(float)
        u["kalla"] = u["kalla"].map(kalla_kort)
        st.dataframe(u[["grupp", "namn", "enhet"] + PERIODNAMN + ["status", "kalla", "kommentar"]].rename(
            columns={"grupp": "Grupp", "namn": "Faktor", "enhet": "Enhet", "status": "Status", "kalla": "Källa", "kommentar": "Kommentar"}),
            hide_index=True, width="stretch", column_config={c: st.column_config.NumberColumn(format="%.2f") for c in PERIODNAMN})
        st.caption("Standardvärden för årlig förändring per period. Värdena med dina ändringar visas i fliken Emissionsfaktorer över tid.")
    elif val == "ytschabloner":
        t = f.ytschabloner.copy(); t["kg"] = t["t_co2e_m2"].astype(float) * 1000
        pv = t.pivot(index="anlaggningstyp", columns="utforande", values="kg"); pv.index = [ANLAGGNINGSTYPER.get(i, i) for i in pv.index]
        st.dataframe(pv, width="stretch"); st.caption("kg CO2e per m².")
    elif val == "kurvor":
        t = f.kurvor.copy(); t["ar"] = t["ar"].astype(float); t["varde"] = t["varde"].astype(float)
        kur = st.selectbox("Kurva", [c for c in KURVNAMN if c in set(t["kurva"])], format_func=KURVNAMN.get, key=k("f_kurva"))
        d = t[t["kurva"] == kur]
        st.caption("Källa: " + kalla_text(d["kalla"].iloc[0]))
        fig = go.Figure(go.Scatter(x=d["ar"], y=d["varde"], mode="lines+markers" if len(d) < 8 else "lines",
                                   line=dict(color="#2a78d6", width=2), marker=dict(size=8)))
        fig.update_layout(height=320, yaxis_title=d["enhet"].iloc[0], margin=dict(l=10, r=10, t=10, b=10), separators=", ")
        st.plotly_chart(fig, width="stretch")
        st.caption("El- och fjärrvärmekurvorna är underlag för standardtakten i fliken Emissionsfaktorer över tid. "
                   "Trädtillväxt anges per år efter plantering.")
    elif val == "skogskol_kurvbibliotek":
        kur = st.selectbox("Kurva", sorted(f.skog["kurva"].unique()), key=k("f_skog"))
        d = f.skog[f.skog["kurva"] == kur]
        fig = go.Figure(go.Scatter(x=d["ar"], y=d["netto_kumulativt_tCO2_ha"], mode="lines", line=dict(color="#008300", width=2)))
        fig.update_layout(height=320, xaxis_title="År", yaxis_title="Kumulativt nettoupptag (t CO2/ha)", margin=dict(l=10, r=10, t=10, b=10), separators=", ")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(d, hide_index=True, width="stretch", height=240)
    else:
        namn = {"personbil_livscykel": None, "energiklasser": f.energiklasser, "markpooler": f.markpooler, "bevarande": f.bevarande, "kommuner": f.kommuner,
                "kostprofiler": f.kostprofiler, "ovrig_konsumtion": f.ovrig, "budget_forster2026": f.budget, "befolkning_unwpp2024": f.befolkning}[val]
        if val == "personbil_livscykel":
            st.json(f.personbil, expanded=True)
        elif val == "budget_forster2026":
            b = namn.copy(); b["gt_co2"] = b["gt_co2"].astype(int)
            st.dataframe(b.pivot(index="temperatur", columns="sannolikhet", values="gt_co2"), width="stretch")
        else:
            st.dataframe(namn, hide_index=True, width="stretch")
    with st.expander("Personbil: fordon, batteri, förbrukning och bränslen"):
        st.json(f.personbil, expanded=False)
        st.caption(kalla_text("ICCT2025,FQD2015,PHEV_ICCT2022,TRAFA_KM_2024"))


def visa(res):
    st.markdown("Alla faktorer och parametrar som modellen använder, med värde, enhet, statusklass och källa. "
                "Du kan ange eget värde för en enskild parameter; det sparas med dina indata.")
    t1, t2, t3 = st.tabs(["Parametrar", "Tabeller och kurvor", "Statusklasser"])
    with t1:
        parametrar(res)
    with t2:
        tabeller()
        kx = Kontext(fb(), ss.scen)
        st.markdown("##### El och fjärrvärme som de används med dina indata")
        ar = res.ar()
        st.dataframe(pd.DataFrame({"År": ar, "El (g/kWh)": [round(kx.el(y), 2) for y in ar], "Fjärrvärme (g/kWh)": [round(kx.fjv(y), 2) for y in ar]}).set_index("År").T,
                     width="stretch")
    with t3:
        for s_, text in STATUS_TEXT.items():
            st.markdown(f"<span style='display:inline-block;min-width:170px;font-weight:600;color:{STATUS_FARG.get(s_, '#3E4B46')}'>{s_}</span> {text}",
                        unsafe_allow_html=True)
