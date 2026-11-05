"""Fliken Referenser: alla källor, grupperade, med länk och var de används."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from road2zero.algoritmer import TABELLKALLOR

from .common import fb, k


def visa(res):
    f = fb()
    ref = f.referenser.copy()
    # var används källan?
    anv = {r: [] for r in ref["id"]}
    for p in f.parametrar.itertuples():
        for r in p.kalla.split(","):
            anv.setdefault(r, []).append(p.namn)
    for t, (namn, kallor) in TABELLKALLOR.items():
        for r in kallor.split(","):
            anv.setdefault(r, []).append(f"tabell: {namn}")
    ref["antal"] = ref["id"].map(lambda r: len(anv.get(r, [])))
    sok = st.text_input("Sök i referenserna", key=k("r_sok"), placeholder="författare, titel eller användning")
    if sok:
        ref = ref[ref.apply(lambda r: sok.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    st.caption(f"{len(ref)} referenser. Alla parametrar och tabeller i faktabiblioteket pekar på någon av dem.")
    for grupp, d in ref.groupby("grupp", sort=True):
        st.markdown(f"##### {grupp}")
        for r in d.itertuples():
            titel = f"[{r.titel}]({r.url})" if r.url else r.titel
            st.markdown(f"**{r.kortnamn}.** {titel}  \n<span style='color:#52514e;font-size:13px'>Används till: {r.anvands_till}. "
                        f"Id `{r.id}` · {r.antal} parametrar eller tabeller.</span>", unsafe_allow_html=True)
            if anv.get(r.id):
                with st.expander("Visa var källan används", expanded=False):
                    st.write(", ".join(sorted(set(anv[r.id]))))
    st.download_button("Ladda ned referenslistan (CSV)", f.referenser.to_csv(sep=";", index=False).encode("utf-8-sig"), "road2zero_referenser.csv", "text/csv")
