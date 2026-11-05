"""Road2Zero-OP – stadens klimatavtryck per DeSO (energi i befintliga byggnader, mobilitet och exploatering enligt översiktsplanen).

Bygger på MalmoOP 1.2. Varje stad eller plan är ett projekt i op/projekt/<id>/ med projekt.json och data/; först Malmö_ÖP.
Starta lokalt från repots rot:   python -m streamlit run op/streamlit_app.py
Streamlit Community Cloud:       repo Mulmen65/road2zero, huvudfil op/streamlit_app.py
Beräkningen körs i webbläsaren. Sidan "Underlag" kan hämta nya energideklarationer och koppla nya adresser (kräver internet).
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from functools import lru_cache
from html import escape as html_escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent            # op/
REPO = ROOT.parent                                # repots rot, med gemensamt/ (logotyp) och road2zero/data (klimatbudget)
R2Z_DATA = REPO / "road2zero" / "data"
PROJEKTMAPP = ROOT / "projekt"
STANDARD = "malmo_op"
SHELL = "app/shell.html"
MARKER = re.compile(r"\{\{([^}]+)\}\}")
OVERRIDABLE = ("data/energi_deklarationer.json", "data/metadata.json")


def projekt_lista() -> dict[str, dict]:
    """Projekten i op/projekt/: en mapp per stad eller plan med projekt.json och data/."""
    ut = {}
    for f in sorted(PROJEKTMAPP.glob("*/projekt.json")):
        try:
            meta = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ut[f.parent.name] = meta
    if STANDARD in ut:
        ut = {STANDARD: ut[STANDARD], **{k: v for k, v in ut.items() if k != STANDARD}}
    return ut


def projekt_rot(projekt: str = STANDARD) -> Path:
    if projekt not in projekt_lista():
        raise ValueError(f"Okänt projekt: {projekt}")
    return PROJEKTMAPP / projekt


def _embed(name: str, text: str) -> str:
    text = text.strip()
    if name.endswith((".json", ".geojson")):
        json.loads(text)  # validera
        return text.replace("<", "\\u003c")
    if name.endswith(".js"):
        return re.sub(r"</script", r"<\\/script", text, flags=re.IGNORECASE)
    if name.endswith(".css"):
        return re.sub(r"</style", r"<\\/style", text, flags=re.IGNORECASE)
    return text


def _plotly_fil() -> Path:
    """Plotly.js från Python-paketet plotly, så att diagrammen ser ut som i Road2Zero-Plan och fungerar utan internet."""
    import plotly
    return Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


def r2z_underlag() -> dict:
    """Underlag för Resultat & klimatbudget ur Road2Zero:s faktabibliotek: budget enligt Forster m.fl. (2026) per temperaturgräns
    och sannolikhet, världsbefolkningen (UN WPP 2024), globala utsläpp 2025 och påslaget för andra växthusgaser, samt
    kategorifärgerna. Samma filer som Road2Zero-Plan använder."""
    import csv

    def rader(namn):
        with open(R2Z_DATA / namn, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))

    par = {r["id"]: float(r["varde"]) for r in rader("parametrar.csv") if r["id"] in ("budget.e0", "budget.k")}
    farg = {}
    for rad in (R2Z_DATA.parent / "konstanter.py").read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*\("([^"]+)", \d, "(#[0-9a-fA-F]{6})"\),', rad)
        if m:
            farg[m[1]] = m[2]
    return {"budget": [{"temperatur": r["temperatur"], "sannolikhet": int(r["sannolikhet"]), "gt_co2": float(r["gt_co2"])}
                       for r in rader("budget_forster2026.csv")],
            "befolkning": [{"ar": int(r["ar"]), "miljarder": float(r["miljarder"])} for r in rader("befolkning_unwpp2024.csv")],
            "e0": par["budget.e0"], "k": par["budget.k"], "farg": farg}


def _signature(projekt: str) -> tuple:
    rot = projekt_rot(projekt)
    files = [ROOT / SHELL, *sorted((ROOT / "app").glob("*")), *sorted((rot / "data").glob("*.json")), rot / "projekt.json",
             rot / "data/kalla/deso_2025_malmo.geojson", rot / "data/kalla/land_malmo_osm.json", REPO / "gemensamt" / "logo.svg",
             R2Z_DATA / "budget_forster2026.csv", R2Z_DATA / "befolkning_unwpp2024.csv", R2Z_DATA / "parametrar.csv",
             R2Z_DATA.parent / "konstanter.py", _plotly_fil()]
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.is_file())


@lru_cache(maxsize=8)
def _assemble_cached(signature: tuple, projekt: str, overrides_key: str) -> str:
    del signature
    overrides = json.loads(overrides_key) if overrides_key else {}
    return assemble(overrides, projekt)


def assemble(overrides: dict | None = None, projekt: str = STANDARD) -> str:
    """Bygg en fristående HTML-sida med all kod och allt underlag för ett projekt inbäddat."""
    overrides = overrides or {}
    rot = projekt_rot(projekt)
    shell = (ROOT / SHELL).read_text(encoding="utf-8")
    meta = json.loads(overrides.get("data/metadata.json") or (rot / "data/metadata.json").read_text(encoding="utf-8"))
    pmeta = json.loads((rot / "projekt.json").read_text(encoding="utf-8"))

    def sub(match: re.Match) -> str:
        name = match[1]
        if name == "byggdatum":
            return meta.get("byggdatum", "")
        if name == "logo":
            return (REPO / "gemensamt" / "logo.svg").read_text(encoding="utf-8").strip()
        if name == "projekt":
            return _embed("projekt.json", json.dumps(pmeta, ensure_ascii=False))
        if name == "r2z":
            return _embed("r2z.json", json.dumps(r2z_underlag(), ensure_ascii=False))
        if name == "plotly":
            return _embed("plotly.js", _plotly_fil().read_text(encoding="utf-8"))
        if name.startswith("projekt:"):
            return html_escape(str(pmeta.get(name.split(":", 1)[1], "")))
        if ".." in name.split("/") or not (name.startswith("app/") or name.startswith("data/")):
            raise ValueError("Otillåten sökväg i mallen: " + name)
        if name in overrides:
            text = overrides[name]
        else:
            text = ((ROOT if name.startswith("app/") else rot) / name).read_text(encoding="utf-8")
        return _embed(name, text)

    html = MARKER.sub(sub, shell)
    if MARKER.search(html):
        raise ValueError("Mallen innehåller platshållare som inte kunde fyllas.")
    return html


def page_html(st=None, projekt: str = STANDARD) -> str:
    overrides = {}
    if st is not None and st.session_state.get("op_overrides", {}).get(projekt):
        overrides = {k: v for k, v in st.session_state["op_overrides"][projekt].items() if k in OVERRIDABLE}
    key = json.dumps(overrides, sort_keys=True) if overrides else ""
    return _assemble_cached(_signature(projekt), projekt, key)


def data_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


def _valt_projekt(st) -> str:
    lista = projekt_lista()
    val = st.session_state.get("op_projekt") or st.query_params.get("projekt") or STANDARD
    return val if val in lista else next(iter(lista))


def underlag_page(st, back) -> None:
    pid = _valt_projekt(st)
    rot = projekt_rot(pid)
    pmeta = projekt_lista()[pid]
    with st.container(border=True):
        st.title(f"Underlag · {pmeta.get('namn', pid)}")
        st.write("Ladda ned modellens underlag eller uppdatera energideklarationerna. Nya adresser kopplas automatiskt till DeSO med "
                 "Malmö stads adresstjänst.")
        st.page_link(back, label="Tillbaka till Road2Zero-OP", icon="⬅️")
        meta = json.loads((rot / "data/metadata.json").read_text(encoding="utf-8"))
        energi = json.loads((rot / "data/energi_deklarationer.json").read_text(encoding="utf-8"))
        q = energi["urval"]
        c1, c2, c3 = st.columns(3)
        sv = lambda n: f"{n:,}".replace(",", "\u00a0")  # noqa: E731
        c1.metric("Energideklarationer kartlagda", sv(q["kartlagda"]))
        c1.caption(f"av {sv(q['beraknade_deklarationer'])} beräkningsbara deklarationer")
        c2.metric("Adresser kopplade till DeSO", sv(meta["adresskoppling"]["godkanda"]))
        c2.caption(f"av {sv(meta['adresskoppling']['totalt'])} adresser · Malmö stads adresstjänst")
        c3.metric("Utbyggnadsområden", sv(pmeta.get("utbyggnadsomraden", 0)))
        c3.caption(f"{sv(pmeta.get('bostader', 0))} bostäder · {sv(pmeta.get('arbetsplatser', 0))} arbetsplatser")

        st.subheader("Ladda ned")
        names = ["data/adresskoppling.csv", "data/energi_deklarationer.json", "data/mobilitet_vagvis.json", "data/exploatering_op2023.json", "data/metadata.json"]
        st.download_button("Adresskoppling (adress → koordinat → DeSO) · CSV", (rot / names[0]).read_bytes(), "adresskoppling.csv", "text/csv")
        st.download_button("Allt beräkningsunderlag · ZIP", data_zip({n: (rot / n).read_text(encoding="utf-8") for n in names}),
                           f"road2zero_op_{pid}_underlag.zip", "application/zip")

        st.subheader("Uppdatera energideklarationer")
        st.write("Välj en ny CSV med samma kolumner som *Energikarta filer.csv*, eller hämta Malmö stads aktuella energideklarationer. "
                 "Bara adresser som saknas geokodas; OSM-byggnader hämtas för dem. Resultatet används direkt i din session.")
        source = st.radio("Källa", ["Egen CSV-fil", "Malmö stads energikarta (geo.malmo.se)"], horizontal=True)
        upload = st.file_uploader("CSV (semikolon, UTF-8)", type=["csv"]) if source == "Egen CSV-fil" else None
        overrides = st.session_state.setdefault("op_overrides", {})
        loggar = st.session_state.setdefault("op_logg", {})
        if st.button("Läs in och koppla adresser", type="primary"):
            try:
                from tools import uppdatera
                with st.status("Uppdaterar underlaget…", expanded=True) as status:
                    if source == "Egen CSV-fil":
                        if upload is None:
                            raise ValueError("Välj en CSV-fil först.")
                        text = upload.getvalue().decode("utf-8-sig")
                    else:
                        status.write("Hämtar energideklarationer från Malmö stad…")
                        text = uppdatera.fetch_malmo_csv()
                    result = uppdatera.run_update(text, progress=status.write, root=rot)
                    overrides[pid] = result["files"]
                    loggar[pid] = result["log"]
                    status.update(label="Klart – det nya underlaget används nu i appen", state="complete")
            except Exception as err:  # visas för användaren
                st.error(f"Uppdateringen kunde inte genomföras: {err}")
        if overrides.get(pid):
            log = loggar.get(pid, {})
            st.success(f"Nytt underlag aktivt i sessionen: {log.get('energi', {}).get('kartlagda', '–')} kartlagda deklarationer.")
            st.page_link(back, label="Visa resultatet i Road2Zero-OP", icon="🗺️")
            st.write(f"För att spara för alla användare: ladda ned filerna och ersätt dem i GitHub under op/projekt/{pid}/ (samma sökvägar), "
                     "eller be Claude pusha dem.")
            st.download_button("Uppdaterade datafiler · ZIP", data_zip(overrides[pid]), f"road2zero_op_{pid}_uppdaterat_underlag.zip", "application/zip")
            with st.expander("Logg"):
                st.json(log, expanded=False)
            if st.button("Återgå till underlaget i GitHub"):
                overrides.pop(pid, None)
                loggar.pop(pid, None)
                st.rerun()


def main() -> None:
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(page_title="Road2Zero-OP", page_icon=str(REPO / "gemensamt" / "logo.svg"), layout="wide",
                       initial_sidebar_state="collapsed")
    st.markdown("""<style>
[data-testid="stHeader"], [data-testid="stSidebar"], footer {display:none;}
.block-container {padding:0 !important;max-width:100% !important;}
[data-testid="stMainBlockContainer"] {padding:0 !important;}
iframe {border:0;}
.st-key-op_rad {padding: 6px 16px 2px 16px; background: #f5f5ef;}
</style>""", unsafe_allow_html=True)

    def show() -> None:
        lista = projekt_lista()
        if not lista:
            st.error("Road2Zero-OP hittar inga projekt i op/projekt/.")
            return
        pid = _valt_projekt(st)
        with st.container(key="op_rad"):
            c1, c2 = st.columns([1, 3], vertical_alignment="center")
            if len(lista) > 1:
                val = c1.selectbox("Projekt", list(lista), index=list(lista).index(pid), format_func=lambda k: lista[k].get("namn", k),
                                   label_visibility="collapsed")
                if val != pid:
                    st.session_state["op_projekt"] = val
                    st.query_params["projekt"] = val
                    st.rerun()
            else:
                c1.markdown(f"**Projekt:** {lista[pid].get('namn', pid)}")
            c2.page_link(pages[1], label="Underlag: ladda ned eller uppdatera energideklarationer och adresskoppling", icon="📥")
        try:
            html = page_html(st, pid)
        except (OSError, ValueError, KeyError) as error:
            st.error(f"Road2Zero-OP kunde inte läsa underlaget för {pid}. Kontrollera mappen op/projekt/{pid}/.")
            st.caption(str(error))
            return
        components.html(html, height=1080, scrolling=True)

    pages = [
        st.Page(show, title="Road2Zero-OP", url_path="op", default=True),
        st.Page(lambda: underlag_page(st, pages[0]), title="Underlag", url_path="underlag"),
    ]
    st.navigation(pages, position="hidden").run()


if __name__ == "__main__":
    main()
