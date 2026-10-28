"""Fliken Beräkningar: algoritmer och formler per modul, med mellanled för det aktuella scenariot."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from road2zero.algoritmer import ALGORITMER, TABELLKALLOR

from .common import eget_param, fb, fmt, kalla_kort, ss


def _spar_modul(titel: str) -> str | None:
    if titel.startswith("Klimatbudget"):
        return "Klimatbudget"
    if titel[0].isdigit():
        return titel[0]
    return None


def _txt(v) -> str:
    """Värden som text, så att tal och kurvnamn kan stå i samma kolumn."""
    try:
        return fmt(float(v), 6).rstrip("0").rstrip(",")
    except (TypeError, ValueError):
        return str(v)


def visa(res):
    st.markdown("Varje modul beskrivs med formler, steg i beräkningen, parametrar med källa och mellanled för dina indata. "
                "Koden finns i paketet `road2zero` och har regressionstester i `tests/`.")
    st.markdown("**Teckenkonvention:** positivt värde är utsläpp, negativt är upptag. Alla resultat är ton CO2e per år och summeras över perioden.")
    pdf = fb().parametrar.set_index("id")
    for a in ALGORITMER:
        with st.expander(a["modul"], expanded=a["modul"].startswith("Tidsmodell")):
            st.markdown(a["text"])
            for f in a["formler"]:
                st.latex(f)
            if a["steg"]:
                st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(a["steg"], 1)))
            if a["parametrar"]:
                rader = []
                for pid in a["parametrar"]:
                    r = pdf.loc[pid]
                    std = r["varde"]
                    try:
                        anv = eget_param(pid)
                        eget = pid in ss.scen.get("parametrar", {})
                    except ValueError:
                        anv, eget = std, False
                    rader.append({"Parameter": r["namn"], "Id": pid, "Värde i beräkningen": _txt(anv), "Standard": _txt(std), "Eget värde": eget,
                                  "Enhet": r["enhet"], "Status": r["status"], "Källa": kalla_kort(r["kalla"]),
                                  "Använd": pid in res.anvanda})
                st.dataframe(pd.DataFrame(rader), hide_index=True, width="stretch",
                             column_config={"Eget värde": st.column_config.CheckboxColumn(), "Använd": st.column_config.CheckboxColumn(help="Användes i den senaste beräkningen")})
            if a["tabeller"]:
                st.caption("Tabeller: " + "; ".join(f"{TABELLKALLOR[t][0]} ({kalla_kort(TABELLKALLOR[t][1])})" for t in a["tabeller"]))
            st.caption(f"Kod: `{a['kod']}`")
            m = _spar_modul(a["modul"])
            if a["modul"].startswith("Tidsmodell"):
                inv = pd.DataFrame({"År": res.ar(), "Invånare": [round(res.invanare.get(y, 0), 1) for y in res.ar()]})
                st.markdown("**Mellanled med dina indata: invånare per år**")
                st.dataframe(inv.set_index("År").T, width="stretch")
            elif m is not None:
                d = res.spar[res.spar["modul"].str.startswith(m)]
                if not d.empty:
                    st.markdown("**Mellanled med dina indata**")
                    d = d.copy()
                    d["Värde"] = d["varde"].map(lambda v: fmt(v, 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))
                    st.dataframe(d[["rubrik", "Värde", "enhet", "kommentar"]].rename(columns={"rubrik": "Steg", "enhet": "Enhet", "kommentar": "Kommentar"}),
                                 hide_index=True, width="stretch")
