"""Fliken Resultat: nyckeltal, tabeller per kategori, delpost och år, klimatbudget och export."""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from road2zero.konstanter import KATEGORI_NAMN, NIVA, NIVA_INNEHALL, NIVA_NAMN
from road2zero.scenario import till_json

from .common import fmt, k, ss


def excel(res) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        p = res.per_ar_och_kategori()
        n = res.netto_per_niva().set_index("ar")
        pd.concat([p, n.rename(columns={"niva1": "Netto nivå 1", "niva2": "Netto nivå 2", "niva3": "Netto nivå 3"})], axis=1).to_excel(w, sheet_name="Per år")
        res.lang.sort_values(["ar", "kategori"]).to_excel(w, sheet_name="Lång tabell", index=False)
        res.budget["tabell"].to_excel(w, sheet_name="Klimatbudget", index=False)
        res.spar.to_excel(w, sheet_name="Mellanled", index=False)
        if not res.utanfor.empty:
            res.utanfor.to_excel(w, sheet_name="Undvikna utsläpp", index=False)
        pd.DataFrame(indata_rader(till_json(res.scen)), columns=["indata_json", "fortsatter"]).to_excel(w, sheet_name="Indata", index=False)
    return buf.getvalue()


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
    niva = st.radio("Redovisningsnivå", [1, 2, 3], index=int(ss.scen["budget"]["niva"]) - 1, horizontal=True,
                    format_func=NIVA_NAMN.get, key=k("res_niva"))
    st.caption(NIVA_INNEHALL[niva])
    nk = res.nyckeltal()
    b = res.budget
    c = st.columns(5)
    c[0].metric(f"Nettoutsläpp {res.ar()[0]}–{res.ar()[-1]}", f"{fmt(nk['netto'][niva])} t")
    c[1].metric(f"Per invånare och år {nk['ref_ar']}", f"{fmt(nk['per_inv_ref'][niva], 2)} t", help=f"{fmt(nk['invanare_full'])} invånare vid full utbyggnad")
    c[2].metric("Exploateringen per m² BTA", f"{fmt(nk['per_m2_niva1'])} kg", help=f"Nivå 1, netto, {fmt(nk['bta'])} m² BTA")
    c[3].metric("Negativa utsläpp", f"{fmt(nk['negativa'])} t", help=f"{nk['negativ_andel']:.1%} av exploateringens bruttoutsläpp".replace(".", ","))
    slut = b["slutar"][niva]
    c[4].metric("Budgeten förbrukad", str(slut) if slut else "Inte före slutåret",
                help=f"{ss.scen['budget']['temperatur']} °C och {ss.scen['budget']['sannolikhet']} %: stadsdelens budget {fmt(b['stadsdel_t'])} t CO2e")

    st.markdown("##### Per klimatkategori")
    t = res.totalt_per_kategori()
    brutto = sum(v for kk, v in t.items() if NIVA[kk] <= niva and v > 0)
    rader = []
    for kat in KATEGORI_NAMN:
        ingar = NIVA[kat] <= niva
        rad = {"Klimatkategori": kat, "Nivå": NIVA[kat], "Ingår": ingar, "t CO2e": round(t[kat]),
               "Andel av brutto": (t[kat] / brutto if (ingar and t[kat] > 0 and brutto) else None),
               "t per invånare och år": (t[kat] / nk["personar"] if nk["personar"] else None)}
        rader.append(rad)
    rader.append({"Klimatkategori": f"Netto, {NIVA_NAMN[niva].lower()}", "Nivå": niva, "Ingår": True, "t CO2e": round(nk["netto"][niva]),
                  "Andel av brutto": None, "t per invånare och år": nk["netto"][niva] / nk["personar"] if nk["personar"] else None})
    df = pd.DataFrame(rader)
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        "t CO2e": st.column_config.NumberColumn(format="localized"),
        "Andel av brutto": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "t per invånare och år": st.column_config.NumberColumn(format="%.3f", help="Kategorins summa delad med alla personår under perioden"),
    })
    st.caption(f"{fmt(nk['personar'])} personår under perioden. Undvikna utsläpp från exporterad solel, utanför nettot: {fmt(nk['undvikna'])} t.")

    with st.expander("Delposter per klimatkategori"):
        d = res.lang.groupby(["kategori", "delpost", "modul"], as_index=False)["t"].sum()
        d["kategori"] = pd.Categorical(d["kategori"], KATEGORI_NAMN, ordered=True)
        d = d.sort_values(["kategori", "t"], ascending=[True, False])
        st.dataframe(d.rename(columns={"kategori": "Klimatkategori", "delpost": "Delpost", "modul": "Indatamodul", "t": "t CO2e"}),
                     hide_index=True, width="stretch", column_config={"t CO2e": st.column_config.NumberColumn(format="%.1f")})

    st.markdown("##### Per år")
    p = res.per_ar_och_kategori()
    n = res.netto_per_niva().set_index("ar")
    tab = pd.concat([p, n.rename(columns={f"niva{L}": f"Netto nivå {L}" for L in (1, 2, 3)})], axis=1)
    tab["Invånare"] = [res.invanare.get(y, 0) for y in tab.index]
    tab["Budget (t)"] = res.budget["tabell"].set_index("ar")["budget_t"]
    tab.index.name = "År"
    st.dataframe(tab.round(1), width="stretch", height=360)
    c1, c2 = st.columns(2)
    c1.download_button("Ladda ned per år (CSV)", tab.to_csv(sep=";", decimal=",").encode("utf-8-sig"), "road2zero_per_ar.csv", "text/csv",
                       width="stretch")
    c2.download_button("Ladda ned allt (Excel)", excel(res), "road2zero_resultat.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")

    st.markdown("##### Klimatbudget")
    c = st.columns(4)
    c[0].metric("Global budget", f"{fmt(b['global_gt'])} Gt CO2", help=f"{ss.scen['budget']['temperatur']} °C, {ss.scen['budget']['sannolikhet']} % sannolikhet")
    c[1].metric("Andel per person", f"{fmt(b['per_person_total'], 1)} t CO2e", help=b["bana"])
    c[2].metric("Stadsdelens budget", f"{fmt(b['stadsdel_t'])} t CO2e")
    tot = res.budget["tabell"][f"netto_kum_niva{niva}"].iloc[-1]
    c[3].metric(f"Andel av budgeten, nivå {niva}", f"{fmt(tot / b['stadsdel_t'] * 100 if b['stadsdel_t'] else 0)} %",
                help=f"Kumulativa nettoutsläpp {fmt(tot)} t")
    st.caption("Budgeten är förbrukad det första år då kumulativa nettoutsläpp överstiger stadsdelens hela budget för perioden. "
               "Utsläpp före 2026 får ingen budget.")

    if res.kontroller:
        with st.expander(f"Kontroller av indata ({len(res.kontroller)})"):
            for allvar, modul, text in res.kontroller:
                {"fel": st.error, "varning": st.warning}.get(allvar, st.info)(f"{modul}: {text}")
