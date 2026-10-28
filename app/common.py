"""Gemensamt för gränssnittet: sessionstillstånd, tabellredigering, format och sidopanel."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from road2zero import __version__
from road2zero.engine import Resultat, berakna
from road2zero.factlib import Faktabibliotek, ladda
from road2zero.konstanter import KATEGORI_NAMN, NIVA_NAMN
from road2zero.scenario import fran_json, till_json, tomt

LOGO = (Path(__file__).parent / "logo.svg").read_text(encoding="utf-8")
ss = st.session_state


# ---------- format ----------
def fmt(x, d: int = 0) -> str:
    """Svenskt talformat: mellanslag som tusentalsavgränsare och decimalkomma."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "–"
    s = f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
    return s.replace("-", "−") if s.startswith("-") else s


def fb() -> Faktabibliotek:
    return ladda()


# ---------- tillstånd ----------
def init():
    ss["_senare"] = []
    if "scen" not in ss:
        ss.scen = tomt(fb())
        ss.v = 0


def senare(fn):
    """Reserverar en plats på sidan som fylls när alla indata är lästa och resultatet är beräknat.
    Då visar tabeller och diagram i indataflikarna alltid aktuella värden, även när indata ändras i en annan flik."""
    ss.setdefault("_senare", []).append((st.container(), fn))


def kor_senare(res):
    for plats, fn in ss.pop("_senare", []):
        with plats:
            fn(res)


def ny_version():
    """Ny nyckeluppsättning för alla fält, så att de läser om värdena ur scenariot."""
    ss.v = ss.get("v", 0) + 1
    for k in [k for k in ss.keys() if str(k).startswith("bas_")]:
        del ss[k]


def ladda_indata(s: dict):
    ss.scen = s
    ny_version()


def k(namn: str) -> str:
    """Widgetnyckel som byts när nya indata läses in."""
    return f"{namn}__{ss.v}"


@st.cache_data(max_entries=30, show_spinner=False)
def _berakna(scen_json: str) -> Resultat:
    return berakna(json.loads(scen_json))


def resultat() -> Resultat:
    return _berakna(till_json(ss.scen))


def editor(namn: str, bygg, **kw) -> pd.DataFrame:
    """st.data_editor med stabil utgångstabell: utgångsläget sparas en gång per scenarioversion,
    och redigeringarna läggs ovanpå. Returnerar den redigerade tabellen."""
    nyckel = k(namn)
    bas = "bas_" + nyckel
    if bas not in ss:
        ss[bas] = bygg()
    return st.data_editor(ss[bas], key=nyckel, width="stretch", **kw)


def kalla_text(ids: str) -> str:
    """Kortnamn med länk för en kommaseparerad lista med käll-id."""
    out = []
    for rid in str(ids).split(","):
        r = fb().referens(rid.strip())
        out.append(f"[{r['kortnamn']}]({r['url']})" if r.get("url") else r["kortnamn"])
    return ", ".join(out)


def kalla_kort(ids: str) -> str:
    return ", ".join(fb().referens(r.strip())["kortnamn"] for r in str(ids).split(",") if r.strip())


def param_info(pid: str) -> str:
    r = fb().param_rad(pid)
    return f"{r['status']} · {kalla_kort(r['kalla'])}"


def eget_param(pid: str) -> float:
    egna = ss.scen.get("parametrar", {})
    return float(egna[pid]) if pid in egna and egna[pid] not in (None, "") else fb().param(pid)


# ---------- sidopanel ----------
def sidopanel(res: Resultat):
    sb = st.sidebar
    sb.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">'
        f'<div style="width:46px;height:46px">{LOGO}</div>'
        f'<div><div style="font-size:22px;font-weight:700;line-height:1.1">Road2Zero</div>'
        f'<div style="font-size:12px;color:#56635E">version {__version__}</div></div></div>', unsafe_allow_html=True)
    p = ss.scen["projekt"]
    sb.caption(f"**{p['namn']}** · {p['kommun']} · {p['startar']}–{p['slutar']}")

    nk = res.nyckeltal()
    b = res.budget
    sb.markdown("##### Resultat i korthet")
    for L in (1, 2, 3):
        sb.markdown(f"<div style='display:flex;justify-content:space-between;font-size:14px'><span>{NIVA_NAMN[L]}</span>"
                    f"<b>{fmt(nk['netto'][L])} t</b></div>", unsafe_allow_html=True)
    slut = b["slutar"].get(int(ss.scen["budget"]["niva"]))
    sb.markdown(f"<div style='font-size:13px;color:#56635E;margin-top:6px'>{fmt(nk['bta'])} m² BTA · {fmt(nk['invanare_full'])} invånare vid full utbyggnad · "
                f"budgeten förbrukad {slut or 'inte under perioden'} på nivå {ss.scen['budget']['niva']}</div>", unsafe_allow_html=True)
    fel = [x for x in res.kontroller if x[0] == "fel"]
    varn = [x for x in res.kontroller if x[0] == "varning"]
    if fel:
        sb.error(f"{len(fel)} fel i indata. Se fliken Indata.")
    elif varn:
        sb.warning(f"{len(varn)} varningar i indata. Se fliken Indata.")
    else:
        sb.success("Indata är kompletta.")

    sb.divider()
    sb.markdown("##### Indata")
    sb.download_button("Spara indata (JSON)", data=till_json(ss.scen).encode("utf-8"),
                       file_name=f"road2zero_{p['namn']}.json".replace(" ", "_"), mime="application/json", width="stretch")
    fil = sb.file_uploader("Öppna sparade indata", type=["json"], key=k("uppladdning"))
    if fil is not None:
        try:
            ladda_indata(fran_json(fil.getvalue().decode("utf-8"), fb()))
            st.rerun()
        except Exception as e:  # noqa: BLE001
            sb.error(f"Filen kunde inte läsas: {e}")
    if sb.button("Börja om med tomt projekt", width="stretch", help="Tar bort alla indata och återställer alla schabloner"):
        ladda_indata(tomt(fb())); st.rerun()


def kategori_ordning(df: pd.DataFrame, kol: str = "kategori") -> pd.DataFrame:
    df[kol] = pd.Categorical(df[kol], categories=KATEGORI_NAMN, ordered=True)
    return df.sort_values(kol)
