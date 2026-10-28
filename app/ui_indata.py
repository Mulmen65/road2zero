"""Fliken Indata: moduler 0–8 och klimatbudget. Varje fält har ett standardvärde med källa."""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from road2zero.konstanter import (ANLAGGNING_FRAN_NAMN, ANLAGGNINGSTYPER, BYGGNADSTYPER, DRIVLINOR, ENERGIKATEGORI_NAMN,
                                  MARKTYPER, OUPPVARMDA_KLASSER, SKOGSTYPER, SKOTSEL, STOMME_FRAN_NAMN, STOMMAR, TILL_MARK,
                                  SCHABLON_PRODUKT, STANDARD_VIRKESPRODUKT, TRADSLAG, TRASTOMMAR, TYP_FRAN_NAMN, VIRKESPRODUKTER)
from road2zero.kontext import Kontext
from road2zero.modules.byggnader import bygg_kg_m2, energi_kwh_m2
from road2zero.modules.mobilitet import faktorer, mix_for_ar
from road2zero.scenario import (etikett, ny_andel, standard_fjv_andel, standard_mat, standard_ovrig, standardklass, takt,
                                validera)
from road2zero.utveckling import Utveckling

from .common import editor, eget_param, fb, fmt, k, kalla_kort, kalla_text, ny_version, param_info, senare, ss

COL = st.column_config


# ---------- små hjälpare ----------
def _get(path):
    d = ss.scen
    for p in path:
        d = d[p]
    return d


def _set(path, v):
    d = ss.scen
    for p in path[:-1]:
        d = d[p]
    d[path[-1]] = v


def num(label, path, **kw):
    v = st.number_input(label, value=_get(path), key=k("/".join(map(str, path))), **kw)
    _set(path, v)
    return v


def sel(label, path, options, fmt_func=None, **kw):
    cur = _get(path)
    idx = options.index(cur) if cur in options else 0
    v = st.selectbox(label, options, index=idx, key=k("/".join(map(str, path))), format_func=fmt_func or str, **kw)
    _set(path, v)
    return v


def chk(label, path, **kw):
    v = st.toggle(label, value=bool(_get(path)), key=k("/".join(map(str, path))), **kw)
    _set(path, v)
    return v


def tal(x, standard=None):
    if x is None:
        return standard
    try:
        if isinstance(x, float) and math.isnan(x):
            return standard
    except TypeError:
        pass
    if pd.isna(x):
        return standard
    return x


def kalla(text: str):
    st.caption(text)


def bidrag(modulprefix: str):
    senare(lambda res: _bidrag(res, modulprefix))


def _bidrag(res, modulprefix: str):
    d = res.lang[res.lang["modul"].str.startswith(modulprefix)]
    if d.empty:
        st.info("Modulen ger inget resultat med nuvarande indata.")
        return
    t = d.groupby(["kategori", "delpost"], as_index=False)["t"].sum()
    t["t CO2e"] = t["t"].map(lambda x: fmt(x))
    st.dataframe(t[["kategori", "delpost", "t CO2e"]].rename(columns={"kategori": "Klimatkategori", "delpost": "Delpost"}),
                 hide_index=True, width="stretch")
    st.caption(f"Summa för modulen {res.ar()[0]}–{res.ar()[-1]}: **{fmt(d['t'].sum())} t CO2e**")


# ---------- 0 Projekt ----------
def projekt():
    s = ss.scen
    c1, c2, c3 = st.columns(3)
    with c1:
        s["projekt"]["namn"] = st.text_input("Projektnamn", s["projekt"]["namn"], key=k("p_namn"))
    with c2:
        kommuner = list(fb().kommuner["kommun"])
        gammal = s["projekt"]["kommun"]
        ny = sel("Kommun (styr bilinnehav och körsträcka)", ("projekt", "kommun"), kommuner,
                 help="Kommuner med förifyllda värden från SCB och Trafikanalys. Annan kommun: riksmedel för körsträcka; ange kommunens bilinnehav under Mobilitet.")
        if ny != gammal and s["mobilitet"].get("kommunvarden", True):
            r = fb().kommuner[fb().kommuner["kommun"] == ny].iloc[0]
            s["mobilitet"]["bilar_per_hushall"] = float(r["bilar_per_hushall"]); s["mobilitet"]["km_per_bil"] = float(r["km_per_bil"])
        sel("Planeringsfas", ("projekt", "fas"), ["Inför planuppdrag", "Planprogram", "Detaljplan, samråd", "Detaljplan, granskning", "Genomförande"])
    with c3:
        a, b = st.columns(2)
        with a:
            num("Startår", ("projekt", "startar"), min_value=2015, max_value=2100, step=1)
        with b:
            num("Slutår", ("projekt", "slutar"), min_value=2016, max_value=2150, step=1)
        st.caption(f"{s['projekt']['slutar'] - s['projekt']['startar']} år. Standard är innevarande år och 50 år framåt, som EU:s referensperiod för livscykel-GWP.")

    st.info("Elens och fjärrvärmens klimatfaktor och hur alla emissionsfaktorer utvecklas över tid anges i fliken **Emissionsfaktorer över tid**.")

    st.markdown("##### Hushåll")
    c1, c2, c3 = st.columns(3)
    with c1: num("Personer per hushåll", ("hushall", "personer_per_hushall"), min_value=0.5, max_value=6.0, step=0.1, help=param_info("allm.personer_per_hushall"))
    with c2: num("BTA per hushåll (m²)", ("hushall", "bta_per_hushall"), min_value=20.0, max_value=400.0, step=5.0, help=param_info("allm.bta_per_hushall"))
    with c3:
        senare(lambda res: st.metric("Invånare vid full utbyggnad", fmt(res.nyckeltal()["invanare_full"])))
    kalla("Invånarna flyttar in i takt med att bostäderna blir klara. Antalet år för år styr mobilitet, konsumtion och budgetandel.")


# ---------- 1 Byggnader ----------
FORDELNINGAR = ["jämn", "framtung", "baktung", "egen"]
ALLA_KLASSER = ["A", "B", "C", "D", "E", "F", "G", "Uppvärmt", "Ouppvärmt"]


def _utv() -> Utveckling:
    return Utveckling(fb(), ss.scen)


def _stomme_text(typ: str, stomme: str) -> str:
    return f"{STOMMAR[stomme]} · {fmt(fb().byggschablon(typ, stomme), 1)} kg CO2e/m²"


def _produkt_text(stomme: str | None = None) -> str:
    if stomme in STANDARD_VIRKESPRODUKT:
        p = STANDARD_VIRKESPRODUKT[stomme]
        return f"{p} ({fmt(eget_param(VIRKESPRODUKTER[p]), 1)} kg CO2/m³)"
    return ", ".join(f"{STOMMAR[s_]}: {p.lower()} ({fmt(eget_param(VIRKESPRODUKTER[p]), 1)} kg CO2/m³)" for s_, p in STANDARD_VIRKESPRODUKT.items())


def _energi_text(e: dict) -> str:
    """Köpt energi per m² BTA, som text."""
    if e["fjv"]:
        return f"fjärrvärme {fmt(e['fjv'], 1)} + el {fmt(e['el'], 1)}"
    return f"el {fmt(e['el'], 1)}"


def _varme_text(b: dict) -> str:
    e = energi_kwh_m2(fb(), b, eget_param("allm.atemp_andel"))
    if e["klass"] in OUPPVARMDA_KLASSER:
        return f"Klass {e['klass']}, el"
    return f"Klass {e['klass']}, {e['fjv_andel']*100:.0f} % fjv / {(1-e['fjv_andel'])*100:.0f} % VP"


def _byggare():
    """Formulär för att lägga till byggbestånd: en byggnadstyp, total BTA och en fördelning på stommar med egna energival."""
    p0 = int(ss.scen["projekt"]["startar"])
    with st.container(border=True):
        st.markdown("##### Lägg till byggbestånd")
        st.caption("Välj byggnadstyp och total BTA. Fördela sedan BTA:n på stommar; varje rad blir en egen andel av byggbeståndet med "
                   "egen energiklass och egen fördelning av fastighetsvärmen mellan fjärrvärme och värmepump (el). Stommens "
                   "byggpåverkan (Tabell A utökad, startvärde 2026) står i rullistan och gäller den valda byggnadstypen. "
                   "Väljer du Trä BAU eller Trä BÄST räknas kolinlagringen i stommen som negativt utsläpp.")
        c1, c2, c3, c4, c5 = st.columns([2.2, 1.3, 1, 1, 1.3])
        typ = c1.selectbox("Byggnadstyp", list(BYGGNADSTYPER), format_func=lambda t: BYGGNADSTYPER[t][0], key=k("nb_typ"))
        bta = c2.number_input("BTA totalt (m²)", min_value=0.0, value=10000.0, step=500.0, format="%.0f", key=k("nb_bta"))
        a0 = int(c3.number_input("Första år klar", min_value=2015, max_value=2150, value=p0 + 2, step=1, key=k("nb_a0")))
        a1 = int(c4.number_input("Sista år klar", min_value=2015, max_value=2150, value=max(a0, p0 + 2), step=1, key=k("nb_a1")))
        ford = c5.selectbox("Fördelning över åren", FORDELNINGAR[:3], key=k("nb_ford"),
                            help="Hur BTA:n blir klar mellan första och sista år. Egen takt per år anges i tabellen efteråt.")
        klasser = fb().energiklasser_for(typ)
        std_k = standardklass(typ)
        stom_opt = {_stomme_text(typ, s_): s_ for s_ in STOMMAR}
        r0 = fb().byggschablon_rad(typ, "generisk")
        st.caption(f"SBUF-kategori/proxy: **{r0['kategori']}** · startankare {fmt(float(r0['startankare']), 1)} kg CO2e/m² · "
                   f"datakvalitet: {r0['datakvalitet'].lower()}")

        def bas():
            return pd.DataFrame([{"Stomme": _stomme_text(typ, "generisk"), "Andel av BTA (%)": 100.0, "Energiklass": std_k,
                                  "Fjärrvärme (%)": standard_fjv_andel(std_k), "Köpt el (kWh/m² BTA)": float("nan")}])
        rader = editor(f"nb_andelar_{typ}", bas, num_rows="dynamic", hide_index=True, column_config={
            "Stomme": COL.SelectboxColumn(options=list(stom_opt), required=True, width="large",
                                          help="Förifylld byggpåverkan för byggnadstypen, moduler A1–A5 (Tabell A utökad). Generisk = Betong BAU."),
            "Andel av BTA (%)": COL.NumberColumn(min_value=0.0, max_value=100.0, step=5.0, format="%.0f %%", required=True),
            "Energiklass": COL.SelectboxColumn(options=klasser, required=True,
                                               help="Boverkets energiklasser. C motsvarar nybyggnadskravet i BBR."),
            "Fjärrvärme (%)": COL.NumberColumn(min_value=0.0, max_value=100.0, step=10.0, format="%.0f %%",
                                               help="Andel av fastighetsvärmen från fjärrvärme. Resten är värmepump (el)."),
            "Köpt el (kWh/m² BTA)": COL.NumberColumn(min_value=0.0, step=1.0, format="%.1f",
                                                     help="Valfritt. Ersätter energiklassens köpta el med ett eget värde per m² BTA."),
        })
        c1, c2 = st.columns([1.2, 1])
        sol = c1.number_input("Solceller för hela typen (m² panel)", min_value=0.0, value=0.0, step=50.0, format="%.0f", key=k("nb_sol"),
                              help="Fördelas på andelarna i proportion till BTA")
        paln = c2.toggle("Pålning", value=False, key=k("nb_paln"), help=f"{fmt(eget_param('bygg.paln') * 1000)} kg CO2e per m² BTA: {param_info('bygg.paln')}")
        tra_valda = [stom_opt.get(tal(r.get("Stomme"), None)) for r in rader.to_dict("records")]
        tra_valda = [s_ for s_ in tra_valda if s_ in TRASTOMMAR]
        with st.container(border=True):
            st.markdown("**Kolinlagring i trästomme**")
            st.caption("Gäller andelar med Trä BAU eller Trä BÄST" + ("" if tra_valda else " (ingen vald ovan)") +
                       ". Kolinlagring = −(BTA × v × F_produkt), där F_produkt är bundet kol per m³ virke enligt EN 16449. "
                       "Redovisas som negativt utsläpp och fördelas över byggtiden.")
            c1, c2 = st.columns(2)
            produkt = c1.selectbox("Trä-produkt", [SCHABLON_PRODUKT] + list(VIRKESPRODUKTER), key=k("nb_produkt"), disabled=not tra_valda,
                                   format_func=lambda p: f"{p}: {_produkt_text()}" if p == SCHABLON_PRODUKT else
                                   f"{p} ({fmt(eget_param(VIRKESPRODUKTER[p]), 1)} kg CO2/m³)",
                                   help="Schablon: stomvirke för Trä BAU och limträ/glulam för Trä BÄST")
            virke = c2.number_input("Mängd virke (m³/m² BTA)", min_value=0.0, max_value=1.0, value=float(eget_param("bygg.virke_m3_m2")),
                                    step=0.01, format="%.2f", key=k("nb_virke"), disabled=not tra_valda,
                                    help=f"Mängd inbyggt stomvirke per m² BTA. Schablonvärde {fmt(eget_param('bygg.virke_m3_m2'), 2)} m³/m² BTA "
                                         f"({kalla_kort('DODOO2026')}).")
            if abs(virke - eget_param("bygg.virke_m3_m2")) < 1e-9:
                virke = None

        nya, summa = [], 0.0
        for r in rader.to_dict("records"):
            st_ = stom_opt.get(tal(r.get("Stomme"), None))
            andel = float(tal(r.get("Andel av BTA (%)"), 0) or 0)
            if st_ is None or andel <= 0:
                continue
            summa += andel
            klass = tal(r.get("Energiklass"), std_k)
            klass = klass if klass in klasser else std_k
            fjv = float(tal(r.get("Fjärrvärme (%)"), standard_fjv_andel(klass)))
            if klass in OUPPVARMDA_KLASSER:
                fjv = 0.0
            eget_el = tal(r.get("Köpt el (kWh/m² BTA)"), None)
            tra = st_ in TRASTOMMAR
            nya.append(ny_andel(typ, st_, bta * andel / 100, a0, sista_ar=max(a0, a1), fordelning=ford, energiklass=klass,
                                fjv_andel=max(0.0, min(100.0, fjv)), egen_el_kwh=float(eget_el) if eget_el is not None else None,
                                sol_m2=sol * andel / 100, palning=paln, virkesprodukt=produkt if tra else SCHABLON_PRODUKT,
                                virke_m3_m2=virke if tra else None))
        if nya:
            utv = _utv()
            fv = []
            for b in nya:
                t = takt(b)
                bygg = sum(v * bygg_kg_m2(fb(), utv, b, a_) for a_, v in t.items())
                kol = _kolinlagring(b) if b["stomme"] in TRASTOMMAR else 0.0
                fv.append({"Stomme": STOMMAR[b["stomme"]], "BTA (m²)": fmt(b["bta"]),
                           "Byggpåverkan 2026 (kg/m²)": fmt(fb().byggschablon(typ, b["stomme"]), 1),
                           "När BTA blir klar (kg/m²)": fmt(bygg / sum(t.values()) if t else 0), "Byggskede (t CO2e)": fmt(bygg / 1000),
                           "Värme": _varme_text(b),
                           "Köpt energi (kWh/m² BTA)": _energi_text(energi_kwh_m2(fb(), b, eget_param("allm.atemp_andel"))),
                           "Kolinlagring (t CO2)": fmt(-kol) if kol else "–"})
            st.dataframe(pd.DataFrame(fv), hide_index=True, width="stretch")
        ok = abs(summa - 100) < 0.01 and bta > 0 and nya
        if nya and not ok:
            st.warning(f"Andelarna summerar till {fmt(summa, 1)} %. De ska summera till 100 %.")
        if st.button(f"Lägg till {len(nya)} {'andel' if len(nya) == 1 else 'andelar'} av byggbeståndet", key=k("nb_lagg_till"),
                     type="primary", disabled=not ok):
            ss.scen["byggnader"].extend(nya)
            ny_version(); st.rerun()
        kalla("Byggpåverkan: " + kalla_text("TABELL_A_UTOKAD,MALMQVIST2023,SBUF14381") + "; utvecklingen över tid styrs i fliken "
              "Emissionsfaktorer över tid. Energiklasser: " + kalla_text("BOVERKET_BBR") + ".")


def _kolinlagring(b: dict) -> float:
    """Kolinlagring i trästomme för en andel, t CO2 (positivt tal): BTA × v × F_produkt."""
    from road2zero.scenario import virkesprodukt
    v = b.get("virke_m3_m2")
    v = eget_param("bygg.virke_m3_m2") if v in (None, "") or (isinstance(v, float) and v != v) else float(v)
    return sum(takt(b).values()) * v * eget_param(VIRKESPRODUKTER[virkesprodukt(b)]) / 1000


def _bygg_df():
    rader = []
    for b in ss.scen["byggnader"]:
        rader.append({
            "Byggnadstyp": BYGGNADSTYPER[b["typ"]][0], "Stomme": STOMMAR.get(b.get("stomme"), "Generisk"), "BTA (m²)": float(b["bta"]),
            "Första år klar": int(b["forsta_ar"]), "Sista år klar": int(b["sista_ar"]), "Fördelning": b.get("fordelning", "jämn"),
            "Energiklass": b.get("energiklass", "C"), "Fjärrvärme (%)": float(b.get("fjv_andel", 100) or 0),
            "Köpt el (kWh/m² BTA)": b.get("egen_el_kwh"), "Köpt fjärrvärme (kWh/m² BTA)": b.get("egen_fjv_kwh"),
            "Solceller (m²)": float(b.get("sol_m2") or 0), "Pålning": bool(b.get("palning")), "Pålad andel (%)": float(b.get("paln_andel", 100) or 0),
            "Spontyta (m²)": float(b.get("spont_m2") or 0), "Trä-produkt": b.get("virkesprodukt") or SCHABLON_PRODUKT,
            "Virke (m³/m² BTA)": b.get("virke_m3_m2"),
            "Eget byggvärde (kg CO2e/m²)": b.get("manuellt_kg_m2"), "Namn (valfritt)": b.get("namn") or "",
        })
    kol = ["Byggnadstyp", "Stomme", "BTA (m²)", "Första år klar", "Sista år klar", "Fördelning", "Energiklass", "Fjärrvärme (%)",
           "Köpt el (kWh/m² BTA)", "Köpt fjärrvärme (kWh/m² BTA)", "Solceller (m²)", "Pålning", "Pålad andel (%)", "Spontyta (m²)",
           "Trä-produkt", "Virke (m³/m² BTA)", "Eget byggvärde (kg CO2e/m²)", "Namn (valfritt)"]
    df = pd.DataFrame(rader, columns=kol)
    for c in ("Köpt el (kWh/m² BTA)", "Köpt fjärrvärme (kWh/m² BTA)", "Virke (m³/m² BTA)", "Eget byggvärde (kg CO2e/m²)"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)   # tomma fält som NaN, inte "None"
    return df


def _las_bygg_df(df: pd.DataFrame) -> tuple[list[dict], list[str]]:
    """Läser tabellen över byggbeståndet. Rättar energival som inte passar byggnadstypen och returnerar vad som rättades."""
    gamla = ss.scen["byggnader"]
    p0 = int(ss.scen["projekt"]["startar"])
    nya, rattat = [], []
    for idx, r in df.iterrows():
        typ = TYP_FRAN_NAMN.get(tal(r["Byggnadstyp"], "Flerbostadshus"), "flerbostadshus")
        st_ = STOMME_FRAN_NAMN.get(tal(r["Stomme"], "Generisk"), "generisk")
        a0 = int(tal(r["Första år klar"], p0 + 2))
        klass = tal(r["Energiklass"], standardklass(typ))
        if klass not in fb().energiklasser_for(typ):
            rattat.append(f"{BYGGNADSTYPER[typ][0]}: energiklass {klass} finns inte för typen och har ersatts med {standardklass(typ)}.")
            klass = standardklass(typ)
        fjv = float(tal(r["Fjärrvärme (%)"], standard_fjv_andel(klass)))
        if klass in OUPPVARMDA_KLASSER and fjv > 0:
            rattat.append(f"{BYGGNADSTYPER[typ][0]}: klassen {klass} har ingen fjärrvärme; andelen fjärrvärme är satt till 0 %.")
            fjv = 0.0
        virke = tal(r["Virke (m³/m² BTA)"], None)
        b = ny_andel(
            typ, st_, float(tal(r["BTA (m²)"], 0)), a0,
            sista_ar=max(a0, int(tal(r["Sista år klar"], a0))), fordelning=tal(r["Fördelning"], "jämn"),
            energiklass=klass, fjv_andel=max(0.0, min(100.0, fjv)),
            egen_el_kwh=tal(r["Köpt el (kWh/m² BTA)"], None), egen_fjv_kwh=tal(r["Köpt fjärrvärme (kWh/m² BTA)"], None),
            sol_m2=float(tal(r["Solceller (m²)"], 0)),
            palning=bool(tal(r["Pålning"], False)), paln_andel=float(tal(r["Pålad andel (%)"], 100)),
            spont_m2=float(tal(r["Spontyta (m²)"], 0)), virke_m3_m2=float(virke) if virke is not None else None,
            virkesprodukt=tal(r["Trä-produkt"], SCHABLON_PRODUKT),
            manuellt_kg_m2=tal(r["Eget byggvärde (kg CO2e/m²)"], None), namn=str(tal(r["Namn (valfritt)"], "") or ""),
        )
        if isinstance(idx, int) and 0 <= idx < len(gamla):
            b["takt"] = gamla[idx].get("takt", {})
        nya.append(b)
    return nya, rattat


def byggnader():
    _byggare()

    st.markdown("##### Byggbeståndet")
    if not ss.scen["byggnader"]:
        st.info("Inga andelar ännu. Lägg till byggbestånd i formuläret ovan, eller lägg till rader direkt i tabellen.")
    st.caption("En rad per andel av byggbeståndet. Byggnadstyp, stomme och energival hör till samma BTA. Fjärrvärme (%) är andelen av "
               "fastighetsvärmen från fjärrvärme; resten är värmepump (el). Köpt el och köpt fjärrvärme per m² BTA är valfria och ersätter "
               "energiklassens värden. Trä-produkt och virke gäller Trä BAU och Trä BÄST och ger kolinlagring som negativt utsläpp. "
               "Tomma fält betyder att schablonen med källa används.")
    df = editor("byggnader", _bygg_df, num_rows="dynamic", column_config={
        "Byggnadstyp": COL.SelectboxColumn(options=[v[0] for v in BYGGNADSTYPER.values()], required=True),
        "Stomme": COL.SelectboxColumn(options=list(STOMMAR.values()), required=True, help="Byggpåverkan per typ och stomme visas i tabellen Härledda värden"),
        "BTA (m²)": COL.NumberColumn(min_value=0, step=100, format="%d", required=True),
        "Första år klar": COL.NumberColumn(min_value=2015, max_value=2150, step=1, format="%d"),
        "Sista år klar": COL.NumberColumn(min_value=2015, max_value=2150, step=1, format="%d"),
        "Fördelning": COL.SelectboxColumn(options=FORDELNINGAR, help="Hur BTA fördelas på åren. Egen: skriv in BTA per år nedan."),
        "Energiklass": COL.SelectboxColumn(options=ALLA_KLASSER, help="A–G för bostäder och lokaler; uppvärmt eller ouppvärmt för garage, industri och övriga byggnader"),
        "Fjärrvärme (%)": COL.NumberColumn(min_value=0, max_value=100, step=10, format="%d %%", help="Andel av fastighetsvärmen från fjärrvärme; resten är värmepump (el)"),
        "Köpt el (kWh/m² BTA)": COL.NumberColumn(min_value=0.0, step=1.0, format="%.1f", help="Valfritt eget värde: all köpt el, inklusive värmepump och fastighetsel"),
        "Köpt fjärrvärme (kWh/m² BTA)": COL.NumberColumn(min_value=0.0, step=1.0, format="%.1f", help="Valfritt eget värde för köpt fjärrvärme"),
        "Solceller (m²)": COL.NumberColumn(min_value=0, step=50, format="%d"),
        "Pålning": COL.CheckboxColumn(help=f"{fmt(eget_param('bygg.paln') * 1000)} kg CO2e per m² BTA ({kalla_kort('SBUF_SCHABLON')})"),
        "Pålad andel (%)": COL.NumberColumn(min_value=0, max_value=100, step=10, format="%d %%"),
        "Spontyta (m²)": COL.NumberColumn(min_value=0, step=50, format="%d", help=f"{fmt(eget_param('bygg.spont') * 1000)} kg CO2e per m² spont. 0 som standard."),
        "Trä-produkt": COL.SelectboxColumn(options=[SCHABLON_PRODUKT] + list(VIRKESPRODUKTER),
                                           help="Gäller Trä BAU och Trä BÄST. Schablon: stomvirke för Trä BAU, limträ/glulam för Trä BÄST (EN 16449)"),
        "Virke (m³/m² BTA)": COL.NumberColumn(min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
                                              help="Mängd inbyggt stomvirke. Tomt = schablonen 0,15 m³/m² BTA för trästomme; räknas inte för andra stommar"),
        "Eget byggvärde (kg CO2e/m²)": COL.NumberColumn(min_value=0, step=5, help="Ersätter schablonen och ändras inte över tid"),
        "Namn (valfritt)": COL.TextColumn(),
    })
    nya, rattat = _las_bygg_df(df)
    ss.scen["byggnader"] = nya
    if rattat:
        ss["bygg_rattat"] = rattat
        ny_version(); st.rerun()
    for t in ss.pop("bygg_rattat", []):
        st.info(t)
    if not nya:
        return

    egna = [(i, b) for i, b in enumerate(nya, 1) if b["fordelning"] == "egen"]
    if egna:
        st.markdown("##### Egen utbyggnadstakt: färdigställd BTA per år")
        ar = list(range(ss.scen["projekt"]["startar"], ss.scen["projekt"]["slutar"] + 1))
        rubrik = {i: f"{i}. {etikett(b)}" for i, b in egna}

        def matris():
            data = {"År": ar}
            for i, b in egna:
                t = b["takt"] or takt({**b, "fordelning": "jämn"})
                data[rubrik[i]] = [float(t.get(a, t.get(str(a), 0)) or 0) for a in ar]
            return pd.DataFrame(data)
        m = editor("takt_" + "|".join(rubrik.values()), matris, hide_index=True, disabled=["År"],
                   column_config={r: COL.NumberColumn(min_value=0, step=500, format="%d") for r in rubrik.values()}, height=300)
        for i, b in egna:
            b["takt"] = {int(a): float(v) for a, v in zip(m["År"], m[rubrik[i]]) if float(tal(v, 0)) > 0}
            s_ = sum(b["takt"].values())
            if abs(s_ - b["bta"]) > 1:
                st.warning(f"{rubrik[i]}: utbyggnadstakten summerar till {fmt(s_)} m², BTA i tabellen är {fmt(b['bta'])} m². Beräkningen använder takten.")

    st.markdown("##### Härledda värden per andel")
    senare(lambda res: _harledda())
    st.markdown("##### Modulens bidrag")
    bidrag("1 ")


def _harledda():
    nya = ss.scen["byggnader"]
    tot_bta = sum(sum(takt(b).values()) for b in nya) or 1
    kx = Kontext(fb(), ss.scen)
    atemp_andel = eget_param("allm.atemp_andel")
    rader = []
    for i, b in enumerate(nya, 1):
        t = takt(b)
        bta = sum(t.values())
        bygg = sum(v * bygg_kg_m2(fb(), kx.utv, b, a_) for a_, v in t.items()) / 1000
        e = energi_kwh_m2(fb(), b, atemp_andel)
        helt = (max(t) + 1) if t else None
        e_t = (bta * e["fjv"] * kx.fjv(helt) + bta * e["el"] * kx.el(helt)) / 1e6 if helt else 0
        bostad = BYGGNADSTYPER[b["typ"]][1]
        rad = fb().byggschablon_rad(b["typ"], b.get("stomme") or "generisk")
        rader.append({
            "Andel": f"{i}. {etikett(b)}", "BTA (m²)": bta, "Av total BTA": bta / tot_bta,
            "Klar": ", ".join(f"{a_}: {fmt(v)}" for a_, v in sorted(t.items())),
            "Byggpåverkan 2026 (kg/m²)": float(b["manuellt_kg_m2"]) if b.get("manuellt_kg_m2") else float(rad["kg_co2e_m2"]),
            "När BTA blir klar (kg/m²)": bygg * 1000 / bta if bta else 0, "Byggskede (t CO2e)": bygg,
            "Värme": f"{ENERGIKATEGORI_NAMN.get(e['kategori'], e['kategori'])}, " + _varme_text(b).lower(),
            "Köpt energi (kWh/m² BTA)": _energi_text(e), "Energi första hela året (t CO2e)": e_t,
            "Kolinlagring (t CO2)": -_kolinlagring(b) if b["stomme"] in TRASTOMMAR else None,
            "SBUF-kategori/proxy": rad["kategori"],
            "Invånare vid full utbyggnad": bta / ss.scen["hushall"]["bta_per_hushall"] * ss.scen["hushall"]["personer_per_hushall"] if bostad else 0,
            "Källa byggvärde": "eget värde" if b.get("manuellt_kg_m2") else kalla_kort(rad["kalla"]),
            "Källa energi": "eget värde" if e["eget"] else kalla_kort(e["kalla"]),
        })
    st.dataframe(pd.DataFrame(rader), hide_index=True, width="stretch", column_config={
        "BTA (m²)": COL.NumberColumn(format="localized"), "Av total BTA": COL.ProgressColumn(format="percent", min_value=0, max_value=1),
        "Byggpåverkan 2026 (kg/m²)": COL.NumberColumn(format="%.1f"), "När BTA blir klar (kg/m²)": COL.NumberColumn(format="%.0f"),
        "Byggskede (t CO2e)": COL.NumberColumn(format="localized"), "Energi första hela året (t CO2e)": COL.NumberColumn(format="%.1f"),
        "Invånare vid full utbyggnad": COL.NumberColumn(format="%.0f"), "Kolinlagring (t CO2)": COL.NumberColumn(format="localized")})
    kalla("Byggpåverkan per typ och stomme: " + kalla_text("TABELL_A_UTOKAD,MALMQVIST2023,SBUF14381") + ". Energiklasser: " + kalla_text("BOVERKET_BBR") +
          " (kWh per m² Atemp, räknat om till BTA med Atemp = " + fmt(atemp_andel * 100) + " % av BTA). Pålning och spont: " +
          kalla_text("SBUF_SCHABLON") + ". Kolinlagring i trästomme: " + kalla_text("EN16449") + ", mängd virke " + kalla_text("DODOO2026") + ".")
    with st.expander("Anmärkning till byggpåverkan per byggnadstyp"):
        for typ in sorted({b["typ"] for b in nya}):
            r = fb().byggschablon_rad(typ, "generisk")
            st.markdown(f"**{BYGGNADSTYPER[typ][0]}** (datakvalitet: {r['datakvalitet'].lower()}). {r['anmarkning']}")

    st.markdown("##### Byggbeståndet i sammandrag (m² BTA)")
    sm = pd.DataFrame([{"Byggnadstyp": BYGGNADSTYPER[b["typ"]][0], "Stomme": STOMMAR[b["stomme"]], "Värme": _varme_text(b),
                        "BTA": sum(takt(b).values())} for b in nya])
    c1, c2 = st.columns(2)
    with c1:
        pv = sm.pivot_table(index="Byggnadstyp", columns="Stomme", values="BTA", aggfunc="sum", fill_value=0, margins=True, margins_name="Summa")
        st.dataframe(pv, width="stretch", column_config={c: COL.NumberColumn(format="localized") for c in pv.columns})
        st.caption("Per byggnadstyp och stomme.")
    with c2:
        pv = sm.pivot_table(index="Byggnadstyp", columns="Värme", values="BTA", aggfunc="sum", fill_value=0, margins=True, margins_name="Summa")
        st.dataframe(pv, width="stretch", column_config={c: COL.NumberColumn(format="localized") for c in pv.columns})
        st.caption("Per byggnadstyp och energival (fjv = fjärrvärme, VP = värmepump). Summorna är desamma som till vänster, "
                   "eftersom energivalen hör till samma andelar.")


# ---------- 2 Anläggning ----------
def _records(df, mapping, standard):
    out = []
    for r in df.to_dict("records"):
        d = {}
        for kol, (nyckel, konv) in mapping.items():
            d[nyckel] = konv(tal(r.get(kol), standard.get(nyckel)))
        out.append(d)
    return out


def anlaggning():
    a = ss.scen["anlaggning"]
    p0 = ss.scen["projekt"]["startar"] + 1
    st.markdown("##### Ytor per anläggningstyp")
    df = editor("ytor", lambda: pd.DataFrame([{"Typ": ANLAGGNINGSTYPER[r["typ"]], "Utförande": r.get("utforande", "standard"), "Yta (m²)": float(r["yta_m2"]),
                                               "Första år": int(r["forsta_ar"]), "Sista år": int(r["sista_ar"])} for r in a["ytor"]],
                                             columns=["Typ", "Utförande", "Yta (m²)", "Första år", "Sista år"]),
                num_rows="dynamic", column_config={
                    "Typ": COL.SelectboxColumn(options=list(ANLAGGNINGSTYPER.values()), required=True),
                    "Utförande": COL.SelectboxColumn(options=["standard", "klimatförbättrad"]),
                    "Yta (m²)": COL.NumberColumn(min_value=0, step=100, format="%d"),
                    "Första år": COL.NumberColumn(format="%d", step=1), "Sista år": COL.NumberColumn(format="%d", step=1)})
    a["ytor"] = [{"typ": ANLAGGNING_FRAN_NAMN.get(r["typ"], "lokalgata"), "utforande": r["utforande"], "yta_m2": r["yta_m2"],
                  "forsta_ar": r["forsta_ar"], "sista_ar": max(r["sista_ar"], r["forsta_ar"])}
                 for r in _records(df, {"Typ": ("typ", str), "Utförande": ("utforande", str), "Yta (m²)": ("yta_m2", float),
                                        "Första år": ("forsta_ar", int), "Sista år": ("sista_ar", int)},
                                   {"typ": "Lokalgata", "utforande": "standard", "yta_m2": 0, "forsta_ar": p0, "sista_ar": p0})]
    tab = fb().ytschabloner.pivot(index="anlaggningstyp", columns="utforande", values="t_co2e_m2").astype(float) * 1000
    tab.index = [ANLAGGNINGSTYPER.get(i, i) for i in tab.index]
    with st.expander("Ytschabloner (kg CO2e/m²)"):
        st.dataframe(tab, width="stretch")
        kalla("Källa: " + kalla_text("SBUF_SCHABLON") + ". Kaj och bro saknar ytschablon och anges som engångsvärden.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Masshantering")
        df = editor("massor", lambda: pd.DataFrame([{"Typ": r.get("typ", "Schakt"), "Volym (m³)": float(r["volym_m3"]), "Transport (km)": float(r.get("transport_km") or 0),
                                                     "Första år": int(r["forsta_ar"]), "Sista år": int(r["sista_ar"])} for r in a["massor"]],
                                                   columns=["Typ", "Volym (m³)", "Transport (km)", "Första år", "Sista år"]),
                    num_rows="dynamic", column_config={"Typ": COL.SelectboxColumn(options=["Schakt", "Sanering"]),
                                                       "Volym (m³)": COL.NumberColumn(min_value=0, step=100, format="%d"),
                                                       "Första år": COL.NumberColumn(format="%d"), "Sista år": COL.NumberColumn(format="%d")})
        a["massor"] = _records(df, {"Typ": ("typ", str), "Volym (m³)": ("volym_m3", float), "Transport (km)": ("transport_km", float),
                                    "Första år": ("forsta_ar", int), "Sista år": ("sista_ar", int)},
                               {"typ": "Schakt", "volym_m3": 0, "transport_km": 0, "forsta_ar": p0, "sista_ar": p0})
        kalla(f"Schakt {eget_param('anl.schakt')} och sanering {eget_param('anl.sanering')} t CO2e/m³; transport {eget_param('anl.transport')} t per ton och km ({kalla_text('SBUF_SCHABLON')}).")
        st.markdown("##### Betong i anläggning")
        df = editor("betong", lambda: pd.DataFrame([{"Utförande": r.get("utforande", "standard"), "Volym (m³)": float(r["volym_m3"]), "Första år": int(r["forsta_ar"]),
                                                     "Sista år": int(r["sista_ar"])} for r in a["betong"]], columns=["Utförande", "Volym (m³)", "Första år", "Sista år"]),
                    num_rows="dynamic", column_config={"Utförande": COL.SelectboxColumn(options=["standard", "klimatförbättrad"]),
                                                       "Första år": COL.NumberColumn(format="%d"), "Sista år": COL.NumberColumn(format="%d")})
        a["betong"] = _records(df, {"Utförande": ("utforande", str), "Volym (m³)": ("volym_m3", float), "Första år": ("forsta_ar", int), "Sista år": ("sista_ar", int)},
                               {"utforande": "standard", "volym_m3": 0, "forsta_ar": p0, "sista_ar": p0})
    with c2:
        st.markdown("##### Ledningar")
        df = editor("ledningar", lambda: pd.DataFrame([{"Meter": float(r["meter"]), "Första år": int(r["forsta_ar"]), "Sista år": int(r["sista_ar"])} for r in a["ledningar"]],
                                                      columns=["Meter", "Första år", "Sista år"]),
                    num_rows="dynamic", column_config={"Första år": COL.NumberColumn(format="%d"), "Sista år": COL.NumberColumn(format="%d")})
        a["ledningar"] = _records(df, {"Meter": ("meter", float), "Första år": ("forsta_ar", int), "Sista år": ("sista_ar", int)},
                                  {"meter": 0, "forsta_ar": p0, "sista_ar": p0})
        kalla(f"{fmt(eget_param('anl.ledning') * 1000, 1)} kg CO2e per meter: {param_info('anl.ledning')}.")
        st.markdown("##### Engångsvärden (till exempel kaj, bro, tunnel)")
        df = editor("engang", lambda: pd.DataFrame([{"Namn": r["namn"], "t CO2e": float(r["t_co2e"]), "År": int(r["ar"])} for r in a["engangsvarden"]],
                                                   columns=["Namn", "t CO2e", "År"]),
                    num_rows="dynamic", column_config={"År": COL.NumberColumn(format="%d")})
        a["engangsvarden"] = _records(df, {"Namn": ("namn", str), "t CO2e": ("t_co2e", float), "År": ("ar", int)}, {"namn": "Engångsvärde", "t_co2e": 0, "ar": p0})
    st.caption("Biokol och stadsträd matas in under modul 8 Negativa utsläpp. Pålning och spont kommer från Byggnader.")
    st.markdown("##### Modulens bidrag")
    bidrag("2 ")


# ---------- 3 Förändrad markanvändning ----------
def mark():
    m = ss.scen["mark"]
    st.markdown("En rad per markövergång. Arean ersätter kartans polygoner. Skog räknas med Skogskolmodellen 10.4; öppen mark med kolförråd per pool.")
    df = editor("overgangar", lambda: pd.DataFrame([{
        "Från marktyp": o["fran"], "Till markanvändning": o["till"], "Yta (ha)": float(o["ha"]), "År": int(o["ar"]),
        "Trädslag (ny skog)": o.get("tradslag") or "Blandskog (gran/bok)", "Skötsel (ny skog)": o.get("skotsel") or "Fri utveckling",
        "Skogens ålder (befintlig)": int(o.get("skogsalder") or 40), "Bevarat SOC (%)": o.get("bevarat_soc"), "Bevarat DOM (%)": o.get("bevarat_dom"),
        "Bevarat bio (%)": o.get("bevarat_bio")} for o in m["overgangar"]],
        columns=["Från marktyp", "Till markanvändning", "Yta (ha)", "År", "Trädslag (ny skog)", "Skötsel (ny skog)", "Skogens ålder (befintlig)",
                 "Bevarat SOC (%)", "Bevarat DOM (%)", "Bevarat bio (%)"]),
        num_rows="dynamic", column_config={
            "Från marktyp": COL.SelectboxColumn(options=MARKTYPER, required=True),
            "Till markanvändning": COL.SelectboxColumn(options=TILL_MARK, required=True),
            "Yta (ha)": COL.NumberColumn(min_value=0.0, step=0.1, format="%.2f"), "År": COL.NumberColumn(format="%d"),
            "Trädslag (ny skog)": COL.SelectboxColumn(options=list(TRADSLAG)), "Skötsel (ny skog)": COL.SelectboxColumn(options=list(SKOTSEL)),
            "Skogens ålder (befintlig)": COL.SelectboxColumn(options=[40, 80]),
            "Bevarat SOC (%)": COL.NumberColumn(min_value=0, max_value=100, help="Tomt = förifyllt värde för markanvändningen"),
            "Bevarat DOM (%)": COL.NumberColumn(min_value=0, max_value=100), "Bevarat bio (%)": COL.NumberColumn(min_value=0, max_value=100)})
    p0 = ss.scen["projekt"]["startar"] + 1
    nya = []
    for r in df.to_dict("records"):
        o = {"fran": tal(r["Från marktyp"], "Åkermark"), "till": tal(r["Till markanvändning"], "Bebyggd kvartersmark"), "ha": float(tal(r["Yta (ha)"], 0)),
             "ar": int(tal(r["År"], p0)), "tradslag": tal(r["Trädslag (ny skog)"], "Blandskog (gran/bok)"), "skotsel": tal(r["Skötsel (ny skog)"], "Fri utveckling"),
             "skogsalder": int(tal(r["Skogens ålder (befintlig)"], 40))}
        for p, kol in (("soc", "Bevarat SOC (%)"), ("dom", "Bevarat DOM (%)"), ("bio", "Bevarat bio (%)")):
            v = tal(r[kol], None)
            o[f"bevarat_{p}"] = float(v) if v is not None else None
        nya.append(o)
    m["overgangar"] = nya

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Kolförråd per marktyp (t C/ha)")
        std = fb().markpooler.set_index("marktyp")

        def pool_df():
            rader = []
            for mt in std.index:
                e = m.get("pooler", {}).get(mt)
                rader.append({"Marktyp": mt, "SOC": float(e["soc"]) if e else float(std.loc[mt, "soc_tc_ha"]),
                              "DOM": float(e["dom"]) if e else float(std.loc[mt, "dom_tc_ha"]),
                              "Biomassa": float(e["bio"]) if e else float(std.loc[mt, "bio_tc_ha"]), "Status": std.loc[mt, "status"]})
            return pd.DataFrame(rader)
        pdf = editor("pooler", pool_df, hide_index=True, disabled=["Marktyp", "Status"])
        m["pooler"] = {}
        for r in pdf.to_dict("records"):
            d = std.loc[r["Marktyp"]]
            if (float(r["SOC"]), float(r["DOM"]), float(r["Biomassa"])) != (float(d["soc_tc_ha"]), float(d["dom_tc_ha"]), float(d["bio_tc_ha"])):
                m["pooler"][r["Marktyp"]] = {"soc": float(r["SOC"]), "dom": float(r["DOM"]), "bio": float(r["Biomassa"])}
        if m["pooler"]:
            st.caption("Egna värden: " + ", ".join(m["pooler"]))
        kalla("Åker: matjorden 0–20 cm enligt Mark- och grödoinventeringen, " + kalla_text("KSLA2025") + ". Betes- och gräsmark och urban grönyta: "
              "öppen fastmark med vegetation, SOC 0–50 cm, " + kalla_text("SLU2025") + " (länsvärde; riksvärde saknas). Ändra till projektets "
              "egna värden när de finns.")
        with st.expander("Status och kommentar per marktyp"):
            st.dataframe(std[["status", "kommentar"]].rename(columns={"status": "Status", "kommentar": "Kommentar"}), width="stretch")
        skog = []
        for mt, sp in SKOGSTYPER.items():
            for alder in (40, 80):
                d = fb().skogskurva(f"befintlig_skog|forest|{sp}|natural|{alder}")
                skog.append({"Skog": mt, "Ålder": alder, "Ekosystem (t C/ha)": round(float(d.loc[d["ar"] == 0, "projekt_ekosystem_tC_ha"].iloc[0]), 1),
                             "Förlorat upptag 50 år (t CO2/ha)": round(float(d.loc[d["ar"] == 50, "netto_kumulativt_tCO2_ha"].iloc[0]), 1)})
        with st.expander("Skog: kolförråd och förlorat upptag ur Skogskolmodellen"):
            st.dataframe(pd.DataFrame(skog), hide_index=True, width="stretch")
            kalla("Fördelas på pooler med SLU:s proportioner (biomassa 30 %, DOM 18 %, SOC 52 %). Lövskog använder blandskogens kurva.")
    with c2:
        st.markdown("##### Bevarad andel per markanvändning (%)")
        bstd = fb().bevarande.set_index("till_markanvandning")

        def bev_df():
            rader = []
            for t in bstd.index:
                e = m.get("bevarande", {}).get(t)
                rader.append({"Till markanvändning": t, "SOC": float(e["soc"]) if e else float(bstd.loc[t, "soc"]),
                              "DOM": float(e["dom"]) if e else float(bstd.loc[t, "dom"]), "Biomassa": float(e["bio"]) if e else float(bstd.loc[t, "bio"]),
                              "Status": bstd.loc[t, "status"]})
            return pd.DataFrame(rader)
        bdf = editor("bevarande", bev_df, hide_index=True, disabled=["Till markanvändning", "Status"])
        m["bevarande"] = {}
        for r in bdf.to_dict("records"):
            d = bstd.loc[r["Till markanvändning"]]
            if (float(r["SOC"]), float(r["DOM"]), float(r["Biomassa"])) != (float(d["soc"]), float(d["dom"]), float(d["bio"])):
                m["bevarande"][r["Till markanvändning"]] = {"soc": float(r["SOC"]), "dom": float(r["DOM"]), "bio": float(r["Biomassa"])}
        kalla("Förlust = kolförråd × (1 − bevarad andel) × 44/12. Värden per rad i tabellen ovan går före.")
        nyskog = [o for o in nya if o["till"] == "Nyplanterad skog"]
        if nyskog:
            from road2zero.konstanter import TIDIGARE_MARK_FOR_SKOG
            o = nyskog[0]
            namn = f"nybeskogning|{TIDIGARE_MARK_FOR_SKOG.get(o['fran'], 'grassland')}|{TRADSLAG[o['tradslag']]}|{SKOTSEL[o['skotsel']]}|"
            d = fb().skogskurva(namn)
            st.markdown(f"##### Kurva för ny skog: {o['tradslag']}, {o['skotsel'].lower()}")
            st.line_chart(d.rename(columns={"ar": "År efter plantering", "netto_kumulativt_tCO2_ha": "Kumulativt upptag (t CO2/ha)"}),
                          x="År efter plantering", y="Kumulativt upptag (t CO2/ha)", height=200, color="#2f6b3f")
            kalla("Förberäknad med " + kalla_text("SKOGSKOL104") + ".")
    st.markdown("##### Modulens bidrag")
    bidrag("3 ")


# ---------- 4 Mobilitet ----------
def mobilitet():
    mob = ss.scen["mobilitet"]
    st.markdown("De boendes bilar: antal hushåll × bilar per hushåll × körsträcka, med livscykelfaktor per drivlina och modellens elkurva.")
    c1, c2, c3 = st.columns(3)
    with c1:
        if chk("Använd kommunens värden", ("mobilitet", "kommunvarden")):
            r = fb().kommuner[fb().kommuner["kommun"] == ss.scen["projekt"]["kommun"]].iloc[0]
            mob["bilar_per_hushall"] = float(r["bilar_per_hushall"]); mob["km_per_bil"] = float(r["km_per_bil"])
            st.metric("Bilar per hushåll", fmt(mob["bilar_per_hushall"], 3))
            st.metric("Körsträcka per bil (km/år)", fmt(mob["km_per_bil"]))
            kalla(f"{r['kommun']}: {r['status']} ({kalla_text(r['kalla'])}).")
        else:
            num("Bilar per hushåll", ("mobilitet", "bilar_per_hushall"), min_value=0.0, max_value=3.0, step=0.01)
            num("Körsträcka per bil (km/år)", ("mobilitet", "km_per_bil"), min_value=0.0, step=100.0, help=f"Riksmedel 12 753 km: {param_info('mob.km_riket')}")
    with c2:
        mob["phev_eldrift"] = st.slider("Laddhybridens eldriftsandel", 0.0, 1.0, float(mob["phev_eldrift"]), 0.05, key=k("phev"), help=param_info("mob.phev_eldrift"))
        st.caption("Ökningen av elbilar och laddhybrider, bilproduktionens klimatavtryck och förändringen av bilinnehav och körsträcka "
                   "anges i fliken Emissionsfaktorer över tid.")
    with c3:
        mob["bensin_fossil"] = st.slider("Fossil andel i bensin", 0.0, 1.0, float(mob["bensin_fossil"]), 0.01, key=k("bf"), help=param_info("mob.bensin.fossil"))
        mob["diesel_fossil"] = st.slider("Fossil andel i diesel", 0.0, 1.0, float(mob["diesel_fossil"]), 0.01, key=k("df"), help=param_info("mob.diesel.fossil"))

    st.markdown("##### Drivlinemix i startåret (andel av körsträckan, %)")
    cols = st.columns(6)
    for col, (d, namn) in zip(cols, DRIVLINOR.items()):
        with col:
            mob["mix"][d] = st.number_input(namn, 0.0, 100.0, float(mob["mix"][d]) * 100, 0.1, key=k(f"mix_{d}")) / 100
    s = sum(mob["mix"].values())
    c1, c2 = st.columns([3, 1])
    c1.caption(f"Summa {fmt(s * 100, 1)} %. Förifyllt: andel av personbilarnas körsträcka 2025 ({kalla_text('TRAFA_KM_2025')}); bensin "
               "inkluderar etanol. Gäller som utgångsläge 2026.")
    if abs(s - 1) > 0.001:
        if c2.button("Normalisera till 100 %", key=k("norm_mix")):
            mob["mix"] = {d: v / s for d, v in mob["mix"].items()}
            ny_version(); st.rerun()

    st.markdown("##### Livscykelfaktor per drivlina (g CO2e per fordonskm)")
    senare(lambda res: _mob_tabell(res))
    kalla("Fordon, batteri, underhåll och förbrukning: " + kalla_text("ICCT2025") + ". Bränslen: " + kalla_text("FQD2015,NV_KLIMATKLIVET_2025") +
          ". Laddhybridens eldrift: " + kalla_text("PHEV_ICCT2022") + ". Förbrukningen är kalibrerad mot " + kalla_text("TV_UTSLAPP_2025") + ".")
    st.markdown("##### Modulens bidrag")
    bidrag("4 ")


def _mob_tabell(res):
    kx = Kontext(fb(), ss.scen)
    tab = []
    for y in [2026, 2030, 2040, 2050]:
        f = faktorer(kx, y); mix = mix_for_ar(kx, y)
        tab.append({"År": str(y), **{DRIVLINOR[d]: round(f[d]["total"], 1) for d in DRIVLINOR},
                    "Elbilar och laddhybrider": f"{mix['bev']:.0%} + {mix['phev']:.0%}",
                    "Flottans snitt": round(sum(mix[d] * f[d]["total"] for d in mix), 1)})
    st.dataframe(pd.DataFrame(tab), hide_index=True, width="stretch")


# ---------- 5 Mat ----------
def mat():
    m = ss.scen["mat"]
    kp = fb().kostprofiler.set_index("profil")

    def df():
        return pd.DataFrame([{"Profil": kp.loc[p, "namn"], "Andel (%)": round(m["andelar"][p] * 100, 2), "Klimatavtryck (kg CO2e/dag)": float(m["avtryck"][p]),
                              "Standardandel (%)": round(float(kp.loc[p, "andel_standard"]) * 100, 1), "Status": kp.loc[p, "status"]} for p in kp.index])
    e = editor("mat", df, hide_index=True, disabled=["Profil", "Standardandel (%)", "Status"],
               column_config={"Andel (%)": COL.NumberColumn(min_value=0.0, max_value=100.0, step=0.5, format="%.1f"),
                              "Klimatavtryck (kg CO2e/dag)": COL.NumberColumn(min_value=0.0, step=0.1, format="%.2f")})
    for p, r in zip(kp.index, e.to_dict("records")):
        m["andelar"][p] = float(tal(r["Andel (%)"], 0)) / 100
        m["avtryck"][p] = float(tal(r["Klimatavtryck (kg CO2e/dag)"], kp.loc[p, "kg_co2e_per_dag"]))
    s = sum(m["andelar"].values())
    c1, c2, c3 = st.columns(3)
    c1.metric("Summa andelar", f"{fmt(s * 100, 1)} %")
    if abs(s - 1) > 0.001 and c1.button("Normalisera till 100 %", key=k("norm_mat")):
        m["andelar"] = {p: v / s for p, v in m["andelar"].items()}
        ny_version(); st.rerun()
    if c1.button("Återställ standard", key=k("std_mat")):
        ss.scen["mat"] = standard_mat(fb()); ny_version(); st.rerun()
    with c2:
        chk("Kalibrera mot Konsumtionskompassen", ("mat", "kalibrering"),
            help=f"Skalar avtrycket så att snittet blir {fmt(eget_param('mat.kalibrering_mal'), 2)} t per invånare och år (livsmedel, SEI 2026)")
    with c3:
        if chk("Kostomställning", ("mat", "omstallning")):
            num("Målår", ("mat", "malar"), min_value=2027, max_value=2100, step=1)
    if m.get("omstallning"):
        st.markdown("##### Målandelar vid målåret (%)")
        cols = st.columns(len(kp.index))
        for col, p in zip(cols, kp.index):
            with col:
                m["mal_andelar"][p] = st.number_input(kp.loc[p, "namn"], 0.0, 100.0, float(m["mal_andelar"][p]) * 100, 0.5, key=k(f"mal_{p}")) / 100
        st.caption(f"Summa målandelar {fmt(sum(m['mal_andelar'].values()) * 100, 1)} %. Övergången är linjär från startåret.")
    def _kost(res):
        from road2zero.modules.konsumtion import mat_per_inv
        kx = Kontext(fb(), ss.scen)
        st.caption(f"Kost per invånare 2026: **{fmt(mat_per_inv(kx, 2026), 2)} t CO2e**, 2050: {fmt(mat_per_inv(kx, 2050), 2)} t med "
                   "matproduktionens index i fliken Emissionsfaktorer över tid. Andelar och avtryck per kostprofil från EPIC-Oxford-kohorten, "
                   + kalla_text("SCARBOROUGH2023") + ". Avtrycken ska kontrolleras mot artikelns tabell.")
    senare(_kost)
    st.markdown("##### Modulens bidrag")
    bidrag("5 ")


# ---------- 6 Övrig konsumtion och flyg ----------
def ovrig():
    o = ss.scen["ovrig"]
    ov = fb().ovrig.set_index("kategori")
    tot = fb().param("ovr.hushall_total")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("##### Övrig konsumtion (t CO2e per invånare och år)")
        e = editor("ovrig", lambda: pd.DataFrame([{"Kategori": ov.loc[kat, "namn"], "t per invånare": float(o["varden"][kat]),
                                                   "Standard": round(float(ov.loc[kat, "andel_av_hushall"]) * tot, 3),
                                                   "Andel av 5,39 t": f"{float(ov.loc[kat, 'andel_av_hushall']):.0%}"} for kat in ov.index]),
                   hide_index=True, disabled=["Kategori", "Standard", "Andel av 5,39 t"],
                   column_config={"t per invånare": COL.NumberColumn(min_value=0.0, step=0.01, format="%.3f")})
        for kat, r in zip(ov.index, e.to_dict("records")):
            o["varden"][kat] = float(tal(r["t per invånare"], 0))
        st.caption(f"Summa **{fmt(sum(o['varden'].values()), 2)} t** per invånare och år. Standard: {kalla_text('SEI2026')}, data för 2023. "
                   "Värdena gäller 2026; utvecklingen därefter anges i fliken Emissionsfaktorer över tid.")
        if st.button("Återställ standard", key=k("std_ovr")):
            ss.scen["ovrig"] = standard_ovrig(fb()); ny_version(); st.rerun()
    with c2:
        st.markdown("##### Flygresor (egen klimatkategori)")
        num("Inrikes och utrikes flyg (t CO2e per invånare och år)", ("flyg", "per_inv"), min_value=0.0, step=0.05, format="%.2f")
        kalla(f"Standard 1,1 t: {param_info('flyg.per_inv')}, år 2017 med höghöjdseffekt (170 g CO2e per personkilometer mot 90 g CO2 från bränslet). "
              "Resultatet delas i två delposter, koldioxid från bränslet och höghöjdseffekt, och höghöjdseffekten kan väljas bort i fliken Resultat. "
              "Konsumtionskompassen visar att flygresandet 2023 var drygt 25 % lägre än före pandemin. "
              "Utvecklingen över tid (globalt snitt för flygbränsle) anges i fliken Emissionsfaktorer över tid.")
    st.markdown("##### Modulens bidrag")
    bidrag("6 ")


# ---------- 7 Offentlig sektor ----------
def offentlig():
    c1, c2, c3 = st.columns(3)
    with c1:
        num("Offentlig konsumtion (t CO2e per invånare och år)", ("offentlig", "konsumtion"), min_value=0.0, step=0.01, help=param_info("off.konsumtion"))
    with c2:
        num("Investeringar, alla sektorer (t CO2e per invånare och år)", ("offentlig", "investeringar"), min_value=0.0, step=0.01, help=param_info("off.investeringar"))
    with c3:
        o = ss.scen["offentlig"]
        o["andel"] = st.slider("Offentlig andel av investeringarna (%)", 0, 100, int(round(float(o["andel"]) * 100)), 1, key=k("off_andel"),
                               help=param_info("off.andel")) / 100
    o = ss.scen["offentlig"]
    st.metric("Offentlig sektor per invånare och år", f"{fmt(o['konsumtion'] + o['investeringar'] * o['andel'], 2)} t CO2e")
    kalla("Bara den offentliga andelen av investeringarna räknas: offentliga myndigheters bruttoinvesteringar 4,2 % av BNP av totalt 23,1 % år 2014 ("
          + kalla_text("REGERINGEN2015") + "). Värden per invånare: " + kalla_text("NV_KONSUMTION,SEI2026") + ". Projektets egna byggnader ingår inte här. "
          "Värdena gäller 2026 och följer därefter EU:s klimatmål enligt fliken Emissionsfaktorer över tid.")
    st.markdown("##### Modulens bidrag")
    bidrag("7 ")


# ---------- 8 Negativa utsläpp ----------
def negativa():
    n = ss.scen["negativa"]
    p0 = ss.scen["projekt"]["startar"] + 2
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Biokol i trädgropar")
        df = editor("biokol", lambda: pd.DataFrame([{"Gropar": float(r["gropar"]), "År": int(r["ar"]), "EBC C-sink-certifierat": bool(r.get("certifierat", True))}
                                                    for r in n["biokol"]], columns=["Gropar", "År", "EBC C-sink-certifierat"]),
                    num_rows="dynamic", column_config={"År": COL.NumberColumn(format="%d"), "EBC C-sink-certifierat": COL.CheckboxColumn()})
        n["biokol"] = [{"gropar": float(tal(r["Gropar"], 0)), "ar": int(tal(r["År"], p0)), "certifierat": bool(tal(r["EBC C-sink-certifierat"], True))}
                       for r in df.to_dict("records")]
        kalla(f"{fmt(eget_param('neg.biokol_per_grop') * 1000)} kg CO2e per grop: {param_info('neg.biokol_per_grop')}. Räknas bara med certifikat.")
    with c2:
        st.markdown("##### Stadsträd")
        df = editor("trad", lambda: pd.DataFrame([{"Antal": float(r["antal"]), "Planteringsår": int(r["planteringsar"])} for r in n["trad"]],
                                                 columns=["Antal", "Planteringsår"]),
                    num_rows="dynamic", column_config={"Planteringsår": COL.NumberColumn(format="%d")})
        n["trad"] = [{"antal": float(tal(r["Antal"], 0)), "planteringsar": int(tal(r["Planteringsår"], p0))} for r in df.to_dict("records")]
        kalla(f"{eget_param('neg.trad_upptag')} kg CO2 per träd och år vid mognad, med tillväxtkurva: {param_info('neg.trad_upptag')}.")
    st.markdown("##### Undvikna utsläpp från exporterad solel (utanför nettot)")
    pan = st.number_input("Solpanelens klimatpåverkan (g CO2e per producerad kWh)", 0.0, 100.0, eget_param("sol.panel"), 1.0, key=k("panel"),
                          help=param_info("sol.panel"))
    if pan != fb().param("sol.panel"):
        ss.scen.setdefault("parametrar", {})["sol.panel"] = pan
    else:
        ss.scen.get("parametrar", {}).pop("sol.panel", None)
    st.caption("Kolinlagring i trästomme (Trä BAU och Trä BÄST) anges under Byggnader; ny skog och förgröning under Förändrad markanvändning.")
    st.markdown("##### Alla negativa utsläpp")
    senare(_negativa_tabell)


def _negativa_tabell(res):
    d = res.lang[res.lang["kategori"] == "Negativa utsläpp"].groupby("delpost", as_index=False)["t"].sum()
    if not d.empty:
        d["t CO2e"] = d["t"].map(fmt)
        st.dataframe(d[["delpost", "t CO2e"]].rename(columns={"delpost": "Post"}), hide_index=True, width="stretch")
    nk = res.nyckeltal()
    st.caption(f"Negativa utsläpp motsvarar **{nk['negativ_andel']:.1%}** av exploateringens bruttoutsläpp ({fmt(nk['brutto_niva1'])} t). "
               f"Undvikna utsläpp utanför nettot: {fmt(nk['undvikna'])} t.".replace(".", ",", 1))


# ---------- Klimatbudget ----------
def budget():
    b = ss.scen["budget"]
    d = fb().budget.copy()
    d["gt_co2"] = d["gt_co2"].astype(int)
    tab = d.pivot(index="temperatur", columns="sannolikhet", values="gt_co2")
    tab.columns = [f"{c} %" for c in tab.columns.astype(int)]
    c1, c2, c3 = st.columns(3)
    with c1:
        sel("Temperaturgräns", ("budget", "temperatur"), list(tab.index), lambda x: f"{x} °C")
    with c2:
        sel("Sannolikhet att hålla gränsen", ("budget", "sannolikhet"), [10, 17, 33, 50, 67, 83, 90], lambda x: f"{x} %")
    with c3:
        sel("Redovisningsnivå att jämföra med", ("budget", "niva"), [1, 2, 3], lambda x: {1: "Nivå 1 · exploateringen", 2: "Nivå 2 · med invånarna", 3: "Nivå 3 · med offentlig sektor"}[x])
    st.markdown("##### Kvarvarande global budget från 1 januari 2026 (Gt CO2)")
    st.dataframe(tab.style.apply(lambda col: ["background-color:#0D5C4D;color:white" if (r == b["temperatur"] and col.name == f"{b['sannolikhet']} %") else "" for r in col.index]),
                 width="stretch")
    kalla("Källa: " + kalla_text("FORSTER2026") + ". Sannolikheten avser bara osäkerheten i TCRE. Budgeten räknas upp med 56,8/43,2 för andra växthusgaser och fördelas lika per person, på faktiska invånare år för år.")


def visa():
    for allvar, modul, text in validera(ss.scen, fb()):
        if allvar in ("fel", "varning"):
            (st.error if allvar == "fel" else st.warning)(f"{modul}: {text}")
    flikar = st.tabs(["0 Projekt", "1 Byggnader", "2 Anläggning", "3 Markanvändning", "4 Mobilitet", "5 Mat",
                      "6 Övrig konsumtion och flyg", "7 Offentlig sektor", "8 Negativa utsläpp", "Klimatbudget"])
    for f, fn in zip(flikar, [projekt, byggnader, anlaggning, mark, mobilitet, mat, ovrig, offentlig, negativa, budget]):
        with f:
            fn()
