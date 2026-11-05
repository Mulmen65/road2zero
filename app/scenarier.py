"""Tre scenarier i samma session för road2zero-scenario.

Indataflikarna från Road2Zero arbetar på ss.scen och widgetnycklar med ss.v. Här pekar ss.scen på det scenario som ändras,
och varje scenario har ett eget nummerområde för ss.v, så att fälten alltid läser om värdena när man byter scenario.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from road2zero import __version__
from road2zero.scenario import SCENARIOSET, fran_json, till_json, tomt

from .common import LOGO, fb, giltigt, ss

NAMN = ["A", "B", "C"]
FARG = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a"}   # de tre första kategorifärgerna; validerade för alla par
STEG = 1_000_000                                          # nummerområde per scenario för widgetnycklarna
FALL = Path(__file__).resolve().parents[1] / "fall"


def _nytt(n: str) -> dict:
    s = tomt(fb())
    s["projekt"]["namn"] = f"Scenario {n}"
    return s


def init():
    ss["_senare"] = []
    if "scenarier" not in ss:
        ss.scenarier = {n: _nytt(n) for n in NAMN}
        ss.versioner = {n: (i + 1) * STEG for i, n in enumerate(NAMN)}
        ss.aktiv = "A"
    for i, n in enumerate(NAMN):
        ss.scenarier.setdefault(n, _nytt(n))
        ss.versioner.setdefault(n, (i + 1) * STEG)
    if ss.get("aktiv") not in NAMN:
        ss.aktiv = "A"
    ss.scen = ss.scenarier[ss.aktiv]
    ss.v = ss.versioner[ss.aktiv]


def spara_aktiv():
    """Efter indataflikarna: behåll det ändrade scenariot och dess nyckelversion."""
    ss.scenarier[ss.aktiv] = ss.scen
    ss.versioner[ss.aktiv] = ss.v


def _ny_version(n: str):
    ss.versioner[n] = ss.versioner.get(n, (NAMN.index(n) + 1) * STEG) + 1
    for nyckel in [x for x in ss.keys() if str(x).startswith("bas_")]:
        del ss[nyckel]


def kort(n: str) -> str:
    """Fast etikett: ändras aldrig, så att valet alltid kan läsas tillbaka."""
    return f"Scenario {n}"


def _byt():
    ss.aktiv = giltigt(ss.get("scenario_val"), NAMN, ss.get("aktiv", "A"), kort)
    _ny_version(ss.aktiv)


def satt(n: str, s: dict):
    """Ersätt ett scenario (öppnad fil, kopia eller tomt) och läs om alla fält."""
    ss.scenarier[n] = s
    _ny_version(n)
    if n == ss.aktiv:
        ss.scen = s
        ss.v = ss.versioner[n]


def oppna(text: str, mal: str) -> str:
    """Läser en fil. Tre scenarier läses till A, B och C; ett scenario till mal. Returnerar vad som lästes in."""
    d = json.loads(text)
    if isinstance(d, dict) and d.get("typ") == SCENARIOSET:
        delar = d.get("scenarier") or {}
        lasta = [n for n in NAMN if n in delar]
        if not lasta:
            raise ValueError("filen innehåller inga scenarier")
        for n in lasta:
            satt(n, fran_json(json.dumps(delar[n]), fb()))
        return "Läste in " + "; ".join(f"{n}: {ss.scenarier[n]['projekt']['namn']}" for n in lasta) + "."
    s = fran_json(text, fb())
    satt(mal, s)
    return f"Läste in {s['projekt']['namn']} till scenario {mal}."


def etikett(n: str) -> str:
    return f"{n} · {ss.scenarier[n]['projekt']['namn']}"


def medtagna() -> list[str]:
    """Scenarier med byggnader; tomma scenarier jämförs inte."""
    return [n for n in NAMN if ss.scenarier[n]["byggnader"]]


def valjare():
    """Väljer vilket scenario som ändras i indataflikarna."""
    st.radio("Scenario som ändras", NAMN, index=NAMN.index(ss.aktiv), horizontal=True, key="scenario_val", on_change=_byt,
             format_func=kort, captions=[ss.scenarier[n]["projekt"]["namn"] for n in NAMN],
             help="Indata, emissionsfaktorer och parametrar gäller det valda scenariot. Jämförelseflikarna visar alla tre.")


def markering(n: str, text: str = "") -> str:
    return (f"<span style='display:inline-block;width:12px;height:12px;border-radius:3px;background:{FARG[n]};"
            f"margin-right:8px;vertical-align:-1px'></span><b>{etikett(n)}</b>{text}")


def _fall_i_mappen(paket: bool) -> dict[str, Path]:
    ut = {}
    for f in sorted(FALL.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if paket and d.get("typ") == SCENARIOSET:
                ut[d.get("namn") or f.stem] = f
            elif not paket and "projekt" in d:
                ut[d["projekt"]["namn"]] = f
        except Exception:  # noqa: BLE001
            continue
    return ut


def fardiga_fall() -> dict[str, Path]:
    """Färdiga fall med ett scenario var i mappen fall/."""
    return _fall_i_mappen(False)


def fardiga_paket() -> dict[str, Path]:
    """Färdiga filer med tre scenarier i mappen fall/; läses till A, B och C med en knapp."""
    return _fall_i_mappen(True)


def sidopanel(resultat: dict):
    sb = st.sidebar
    sb.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">'
        f'<div style="width:46px;height:46px">{LOGO}</div>'
        f'<div><div style="font-size:20px;font-weight:700;line-height:1.1">Road2Zero scenario</div>'
        f'<div style="font-size:12px;color:#56635E">version {__version__}</div></div></div>', unsafe_allow_html=True)
    sb.caption("Tre scenarier med alla indata, beräknade med Road2Zero och jämförda med varandra.")
    sb.markdown("##### Nettoutsläpp, nivå 1 / 2 / 3")
    for n in NAMN:
        r = resultat.get(n)
        txt = (" · " + " / ".join(f"{r.netto(L)/1000:,.0f}".replace(",", " ") for L in (1, 2, 3)) + " kt") if r else " · inga byggnader"
        sb.markdown(f"<div style='font-size:13px;margin-bottom:4px'>{markering(n, txt)}</div>", unsafe_allow_html=True)

    a = ss.aktiv
    sb.divider()
    sb.markdown("##### Öppna och spara")
    if ss.get("_meddelande"):
        sb.success(ss.pop("_meddelande"))
    fil = sb.file_uploader("Öppna fil", type=["json"], key=f"upp_{sum(ss.versioner.values())}",
                           help=f"En fil med alla tre scenarier läses till A, B och C. En fil med ett scenario (från Road2Zero eller "
                                f"Spara scenario) läses till scenario {a}.")
    if fil is not None:
        try:
            ss["_meddelande"] = oppna(fil.getvalue().decode("utf-8"), a)
            st.rerun()
        except Exception as e:  # noqa: BLE001
            sb.error(f"Filen kunde inte läsas: {e}")
    for namn, f in fardiga_paket().items():
        if sb.button(f"Hämta {namn.split(':')[0]} till A, B och C", width="stretch", help=namn):
            ss["_meddelande"] = oppna(f.read_text(encoding="utf-8"), a); st.rerun()
    paket = {"typ": SCENARIOSET, "modellversion": __version__, "aktiv": a, "scenarier": ss.scenarier}
    sb.download_button("Spara alla tre (JSON)", data=json.dumps(paket, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name="road2zero_scenarier.json", mime="application/json", width="stretch")

    sb.divider()
    sb.markdown(f"##### Scenario {a}")
    p = ss.scenarier[a]["projekt"]
    sb.download_button(f"Spara scenario {a} (JSON)", data=till_json(ss.scenarier[a]).encode("utf-8"),
                       file_name=f"road2zero_{a}_{p['namn']}.json".replace(" ", "_"), mime="application/json", width="stretch")
    fall = fardiga_fall()
    if fall:
        val = giltigt(sb.selectbox("Färdigt fall", ["Välj …"] + list(fall), key="fall_val",
                                   help="Fallen som följer med verktyget (mappen fall/ i repot). Egna filer öppnar du med Öppna fil."),
                      ["Välj …"] + list(fall), "Välj …")
        if sb.button(f"Hämta till scenario {a}", width="stretch", disabled=val == "Välj …"):
            ss["_meddelande"] = oppna(fall[val].read_text(encoding="utf-8"), a); st.rerun()
    andra = [n for n in NAMN if n != a]
    fran = giltigt(sb.selectbox("Kopiera från", andra, key="kopiera_fran", format_func=kort), andra, andra[0], kort)
    if sb.button(f"Kopiera till scenario {a}", width="stretch", help=f"Ersätter scenario {a} med en kopia av det valda scenariot"):
        kopia = fran_json(till_json(ss.scenarier[fran]), fb())
        kopia["projekt"]["namn"] = f"{kopia['projekt']['namn']} (kopia)"
        satt(a, kopia); st.rerun()
    if sb.button(f"Töm scenario {a}", width="stretch"):
        satt(a, _nytt(a)); st.rerun()
