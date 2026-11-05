"""Bakgrund och förklaring: sidorna Karta & områden, Så räknas resultatet, Antaganden & scenario, Trafik & geodata och
Metod & källor. Samma sidor finns i Road2Zero-Plan och Road2Zero-CityScenario (och motsvarande vyer i Road2Zero-OP).

Sidorna arbetar på ss.scen (planen eller det valda scenariot). Delar som behöver resultatet ritas med senare(), så att de
fylls när alla indata är lästa och resultatet är beräknat.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from road2zero import __version__
from road2zero.kontext import Kontext
from road2zero.konstanter import BYGGNADSTYPER, KATEGORI_NAMN, NIVA, NIVA_INNEHALL, NIVA_NAMN
from road2zero.modules.mobilitet import faktorer, mix_for_ar
from road2zero.scenario import takt

from . import geodata, karta, ui_berakningar, ui_faktorer, ui_referenser, ui_utveckling
from .common import fb, fmt, k, kalla_text, ny_version, senare, ss
from .varumarke import TEAL, kort, notis, sidrubrik, steg

PLANFARG = TEAL


# ---------- geografi ----------
def geografi() -> dict:
    """Planens geografi med standardkommun ur projektets kommunnamn."""
    g = ss.scen.setdefault("geografi", {"kommunkod": "", "deso": [], "kommentar": ""})
    g.setdefault("deso", []); g.setdefault("kommentar", "")
    if not g.get("kommunkod"):
        g["kommunkod"] = geodata.kommun_for(g["deso"]) or geodata.kommunkod(ss.scen["projekt"].get("kommun", "")) or ""
    return g


def stig() -> list[str]:
    p = ss.scen["projekt"]
    namn = p.get("namn") or ""
    if "scenarier" in ss and ss.get("aktiv"):          # Road2Zero-CityScenario
        namn = f"Scenario {ss.aktiv} · {namn}"
    return [p.get("kommun") or "", namn]


def _vaxla_deso(kod: str):
    g = geografi()
    g["deso"] = [x for x in g["deso"] if x != kod] if kod in g["deso"] else g["deso"] + [kod]
    if not g.get("kommunkod"):
        g["kommunkod"] = geodata.per_kod()[kod]["kommun"]
    ny_version()


def _klick(nyckel: str):
    kod = karta.klickad(nyckel)
    if kod:
        _vaxla_deso(kod)


def _lagg_till_regso(nyckel: str, kommun: str):
    namn = st.session_state.get(nyckel)
    koder = geodata.regso(kommun).get(namn, [])
    g = geografi()
    g["deso"] = g["deso"] + [x for x in koder if x not in g["deso"]]
    ny_version()


def deso_tabell(koder: list[str]) -> pd.DataFrame:
    rader = [geodata.per_kod()[x] for x in geodata.giltiga(koder)]
    return pd.DataFrame([{"DeSO": r["kod"], "RegSO": r["namn"], "Invånare": r["invanare"], "Hushåll": r["hushall"],
                          "Personbilar": r["bilar"], "Bilar per hushåll": round(r["bilar_per_hushall"], 3),
                          "Personer per hushåll": round(r["invanare"] / r["hushall"], 2) if r["hushall"] else None,
                          "km per bil och år": r["km_per_bil"]} for r in rader])


def _tal_kol(df: pd.DataFrame) -> dict:
    return {c: st.column_config.NumberColumn(format="localized") for c in df.columns if c not in ("DeSO", "RegSO")}


def valj_omrade(lager_extra: list[dict] | None = None, rubrik_lager: str = "Planområdet", nyckel: str = "karta_omrade",
                farg: str = PLANFARG):
    """Kommunval, karta med klickbara DeSO, sökbar lista och tabell för det valda området."""
    g = geografi()
    kommuner = geodata.kommuner()
    if not kommuner:
        st.error("DeSO-underlaget saknas (gemensamt/data/vagvis_deso.json).")
        return
    koder = list(kommuner)
    if g["kommunkod"] not in koder:
        notis(f"DeSO-underlag finns för {', '.join(kommuner.values())}, de kommuner som finns i Vägvis {geodata.kalla()['version']}. "
              "Välj en av dem för kartan, eller lämna kartan tom. En ny kommun läggs till i Vägvis och läses in med "
              "<code>verktyg/hamta_vagvis.py</code>.")
    c1, c2, c3 = st.columns([1, 2, 1.3])
    kommun = c1.selectbox("Kommun i kartan", koder, index=koder.index(g["kommunkod"]) if g["kommunkod"] in koder else 0,
                          format_func=kommuner.get, key=k("geo_kommun"))
    if kommun != g["kommunkod"]:
        g["kommunkod"] = kommun
        g["deso"] = [x for x in g["deso"] if geodata.per_kod().get(x, {}).get("kommun") == kommun]
    alla = [d["kod"] for d in geodata.deso(kommun)]
    val = c2.multiselect(f"DeSO i {rubrik_lager.lower()}", alla, default=[x for x in g["deso"] if x in alla],
                         format_func=geodata.etikett, key=k("geo_deso"), placeholder="Sök på kod eller områdesnamn",
                         help="Klicka på kartan eller sök här. DeSO är SCB:s demografiska statistikområden.")
    g["deso"] = val
    regso = geodata.regso(kommun)
    rk = k("geo_regso")
    c3.selectbox("Lägg till alla DeSO i en RegSO", list(regso), index=None, key=rk, placeholder="Välj RegSO",
                 on_change=_lagg_till_regso, args=(rk, kommun))

    lager = [{"namn": rubrik_lager, "farg": farg, "koder": g["deso"]}] + (lager_extra or [])
    karta.karta([kommun] + [geodata.kommun_for(x["koder"]) for x in lager_extra or []], lager, nyckel=nyckel, valbar=True,
                on_klick=lambda: _klick(nyckel), hojd=560, fokus=kommun)
    st.caption("Bakgrundskarta © OpenStreetMap-bidragsgivare. DeSO-gränser: " + kalla_text("SCB_DESO2025") + ", förenklade till cirka 5 m. "
               "Håll muspekaren över ett område för invånare, hushåll och bilinnehav 2024.")
    g["kommentar"] = st.text_input("Kommentar till områdesvalet", g.get("kommentar", ""), key=k("geo_kommentar"),
                                   placeholder="Till exempel: planområdet ligger i den södra delen av DeSO …")
    s = geodata.summera(g["deso"])
    if s:
        c = st.columns(5)
        c[0].metric("Valda DeSO", fmt(s["antal"]))
        c[1].metric("Invånare 2024", fmt(s["invanare"]))
        c[2].metric("Hushåll 2024", fmt(s["hushall"]))
        c[3].metric("Bilar per hushåll", fmt(s["bilar_per_hushall"], 3))
        c[4].metric("Personer per hushåll", fmt(s["personer_per_hushall"], 2))
        df = deso_tabell(g["deso"])
        st.dataframe(df, hide_index=True, width="stretch", column_config=_tal_kol(df))
    else:
        st.info("Inga DeSO valda ännu. Klicka på de områden där planen ligger.")


# ---------- Karta & områden ----------
def karta_sida(lager_extra: list[dict] | None = None, rubrik_lager: str = "Planområdet", farg: str = PLANFARG, fore=None):
    sidrubrik(stig(), "Karta & områden", "Var ligger planen?", "Samma områden i hela modellen.",
              "Planområdet beskrivs med SCB:s demografiska statistikområden (DeSO). Valet visas i kartorna och kan föra över "
              "dagens bilinnehav i området till mobiliteten (sidan Trafik & geodata). Själva beräkningen ändras först när du för över värdena.")
    c = st.columns(3)
    c[0].markdown(kort("DeSO", "SCB:s indelning i cirka 6 000 områden med 700–2 700 invånare. Gränserna följer gator, vattendrag och "
                                "liknande, så att områdena är stabila över tid."), unsafe_allow_html=True)
    c[1].markdown(kort("Planområdet", "Välj de DeSO som planen ligger i eller som bäst motsvarar den. En plan på obebyggd mark får sitt "
                                     "bilinnehav från närliggande DeSO med liknande läge."), unsafe_allow_html=True)
    c[2].markdown(kort("Underlag", f"Hushåll, invånare och personbilar per DeSO {geodata.kalla()['dataar']} ur SCB:s register, via "
                                  f"Vägvis {geodata.kalla()['version']}. Kartan använder OpenStreetMap som bakgrund."), unsafe_allow_html=True)
    st.write("")
    if fore:
        fore()
    valj_omrade(lager_extra, rubrik_lager, farg=farg)


# ---------- Så räknas resultatet ----------
def sa_raknas(fore=None):
    sidrubrik(stig(), "Så räknas resultatet", "Från indata till klimatbudget.", "Varje steg går att följa.",
              "Road2Zero räknar tio klimatkategorier år för år och summerar dem i tre redovisningsnivåer. Exemplen nedan är räknade "
              "med dina indata; formlerna för varje modul finns längst ned.")
    if fore:
        fore()
    senare(_sa_raknas_steg)
    st.markdown("#### Formler per modul")
    senare(ui_berakningar.visa)


def _sa_raknas_steg(res):
    s = res.scen
    nk = res.nyckeltal()
    pph = float(s["hushall"]["personer_per_hushall"]); bph_bta = float(s["hushall"]["bta_per_hushall"])
    bta_bo = sum(sum(takt(b).values()) for b in s["byggnader"] if BYGGNADSTYPER.get(b.get("typ"), ("", False))[1])
    kx = Kontext(fb(), s)
    ar = res.ar()
    y_ex = 2040 if 2040 in ar else ar[min(len(ar) - 1, 14)]
    t = res.totalt_per_kategori()
    b = res.budget
    niva = int(s["budget"]["niva"])
    html = steg(1, "Byggbestånd och invånare",
                "Varje andel av byggbeståndet har byggnadstyp, stomme, BTA och utbyggnadstakt. Bostädernas BTA delat med BTA per hushåll "
                "ger hushållen; hushållen gånger personer per hushåll ger invånarna. Invånarna flyttar in när bostäderna blir klara "
                "(halvårsregel: halva första året).",
                f"{fmt(bta_bo)} m² BTA bostäder ÷ {fmt(bph_bta)} m² per hushåll × {fmt(pph, 2)} personer = "
                f"<b>{fmt(nk['invanare_full'])} invånare</b> vid full utbyggnad. Totalt {fmt(nk['bta'])} m² BTA.")
    html += steg(2, "Emissionsfaktorer år för år",
                 "Varje faktor har ett startvärde som gäller 2026 och en årlig förändring i procent per period till 2100. "
                 "Samma elfaktor används i hela modellen: byggnadernas el, elbilarnas laddning och solelen.",
                 f"Elens klimatfaktor: {fmt(kx.el(2026), 1)} g CO₂e/kWh 2026 → <b>{fmt(kx.el(y_ex), 1)} g/kWh {y_ex}</b>. "
                 f"Fjärrvärme: {fmt(kx.fjv(2026), 1)} → {fmt(kx.fjv(y_ex), 1)} g/kWh.")
    rader = "".join(f"<tr><td>{c}</td><td style='text-align:center'>{NIVA[c]}</td><td style='text-align:right'>{fmt(t[c])}</td></tr>"
                    for c in KATEGORI_NAMN)
    html += steg(3, "Tio klimatkategorier",
                 "Aktivitet × emissionsfaktor för varje år och delpost. Byggskedet bokförs det år BTA:n blir klar; drift, mobilitet och "
                 "konsumtion följer invånarna år för år. Negativa utsläpp (kolinlagring i trästomme, träd, biokol) dras av.",
                 f"<table style='width:100%;font-size:0.9rem'><tr><th style='text-align:left'>Kategori</th><th>Nivå</th>"
                 f"<th style='text-align:right'>t CO₂e {ar[0]}–{ar[-1]}</th></tr>{rader}</table>")
    html += steg(4, "Tre redovisningsnivåer",
                 "Nivåerna bygger på varandra, så att planens egna utsläpp, invånarnas och den offentliga sektorns kan redovisas var för sig.",
                 "<br>".join(f"<b>{NIVA_NAMN[L]}</b>: {NIVA_INNEHALL[L]} = <b>{fmt(nk['netto'][L])} t CO₂e</b>" for L in (1, 2, 3)))
    slut = b["slutar"].get(niva)
    html += steg(5, "Klimatbudget",
                 f"Den globala koldioxidbudgeten enligt {kalla_text('FORSTER2026')} räknas upp för andra växthusgaser och fördelas lika per "
                 "person och år på de invånare som faktiskt bor i området. Budgeten är förbrukad det första år då de ackumulerade "
                 "nettoutsläppen är större än områdets hela budget för perioden.",
                 f"{s['budget']['temperatur']} °C, {s['budget']['sannolikhet']} %: global budget {fmt(b['global_gt'])} Gt CO₂ → "
                 f"{fmt(b['per_person_total'], 1)} t per person för perioden → områdets budget <b>{fmt(b['stadsdel_t'])} t CO₂e</b>. "
                 f"Nivå {niva}: budgeten förbrukad <b>{slut or 'inte under perioden'}</b>.")
    st.markdown(html, unsafe_allow_html=True)


# ---------- Antaganden & scenario ----------
def antaganden(fore=None):
    sidrubrik(stig(), "Antaganden & scenario", "Antaganden som går att ändra.", "Med källa och status.",
              "Alla värden som påverkar resultatet är förifyllda med källa och statusklass. Ändra startvärden och utveckling över tid här; "
              "byggbestånd, hushåll och konsumtion anges under Indata.")
    c = st.columns(3)
    c[0].markdown(kort("Tid", "Hela år, standard 2026–2076. Startvärdena gäller 2026; år före 2026 använder startvärdena och får ingen "
                               "budgetandel. Drift och invånare räknas med halvårsregel."), unsafe_allow_html=True)
    c[1].markdown(kort("Utveckling över tid", "Årlig förändring i procent per period (2027–2030, 2031–2035 … 2071–2100). Elbilar och "
                                               "laddhybrider ökar i procentenheter av körsträckan."), unsafe_allow_html=True)
    c[2].markdown(kort("Statusklasser", "Officiell statistik, vetenskaplig källa, branschuppgift, modellval eller antagande. Värden utan "
                                         "extern källa har statusen Modellval eller Antagande."), unsafe_allow_html=True)
    st.write("")
    if fore:
        fore()
    t1, t2 = st.tabs(["Emissionsfaktorer över tid", "Faktorer och parametrar"])
    with t1:
        ui_utveckling.visa()
    with t2:
        senare(ui_faktorer.visa)


# ---------- Trafik & geodata ----------
def _anvand_deso():
    g = geografi(); s = geodata.summera(g["deso"])
    if not s:
        return
    mob = ss.scen["mobilitet"]
    mob["kommunvarden"] = False
    mob["bilar_per_hushall"] = round(s["bilar_per_hushall"], 4)
    mob["km_per_bil"] = float(round(s["km_per_bil"]))
    kalla_ = geodata.kalla()
    mob["kalla_deso"] = {"deso": list(geodata.giltiga(g["deso"])), "dataar": kalla_["dataar"],
                         "modell": f"{kalla_['modell']} {kalla_['version']}"}
    ny_version()


def _anvand_kommun():
    mob = ss.scen["mobilitet"]
    mob["kommunvarden"] = True
    mob.pop("kalla_deso", None)
    kf = fb().kommuner
    r = kf[kf["kommun"] == ss.scen["projekt"]["kommun"]]
    if not r.empty:
        mob["bilar_per_hushall"] = float(r.iloc[0]["bilar_per_hushall"]); mob["km_per_bil"] = float(r.iloc[0]["km_per_bil"])
    ny_version()


def trafik_geodata(jamfor: list[tuple[str, dict]] | None = None, fore=None):
    kalla_ = geodata.kalla()
    sidrubrik(stig(), "Trafik & geodata", "Hushållens bilar.", "Kopplat till Vägvis.",
              f"Mobiliteten i Road2Zero räknar de boendes bilar: hushåll × bilar per hushåll × körsträcka per bil, med livscykelfaktor per "
              f"drivlina. Bilinnehavet i de valda DeSO hämtas från Vägvis {kalla_['version']} (SCB:s register {kalla_['dataar']}).")
    c = st.columns(2)
    c[0].markdown(kort("Vägvis modell A · trafik inom området",
                       "Vägarnas längd × trafikmängd (ÅDT): all trafik som kör i området, oavsett var bilarna hör hemma. Territoriellt "
                       "perspektiv, som används i Road2Zero-OP för hela staden."), unsafe_allow_html=True)
    c[1].markdown(kort("Vägvis modell B · hushållens bilar",
                       "Bilinnehav × körsträcka: de boendes bilar, var de än kör. Samma perspektiv som kategorin Mobilitet och transport i "
                       "Road2Zero. A och B är alternativa perspektiv och ska inte adderas."), unsafe_allow_html=True)
    st.write("")
    if fore:
        fore()
    g = geografi()
    s = geodata.summera(g["deso"])
    mob = ss.scen["mobilitet"]
    if not s:
        notis("Inga DeSO är valda. Välj planområdet under <b>Karta & områden</b> för att se och föra över bilinnehavet i området.")
    else:
        anvands = mob.get("kalla_deso", {}).get("deso") == geodata.giltiga(g["deso"]) and not mob.get("kommunvarden", True)
        st.markdown("#### Bilinnehav i planens DeSO jämfört med beräkningen")
        kf = fb().kommuner
        kr = kf[kf["kommun"] == ss.scen["projekt"]["kommun"]]
        jam = pd.DataFrame([
            {"Underlag": f"Valda DeSO ({s['antal']} st), SCB {kalla_['dataar']} via Vägvis", "Bilar per hushåll": round(s["bilar_per_hushall"], 3),
             "km per bil och år": round(s["km_per_bil"]), "Personer per hushåll": round(s["personer_per_hushall"], 2)},
            *([{"Underlag": f"{kr.iloc[0]['kommun']}, kommunvärde i faktabiblioteket", "Bilar per hushåll": float(kr.iloc[0]["bilar_per_hushall"]),
                "km per bil och år": float(kr.iloc[0]["km_per_bil"]), "Personer per hushåll": float(kr.iloc[0]["personer_per_hushall_scb"])}]
              if not kr.empty else []),
            {"Underlag": "Används i beräkningen nu", "Bilar per hushåll": float(mob["bilar_per_hushall"]),
             "km per bil och år": float(mob["km_per_bil"]), "Personer per hushåll": float(ss.scen["hushall"]["personer_per_hushall"])},
        ])
        st.dataframe(jam, hide_index=True, width="stretch", column_config=_tal_kol(jam))
        c1, c2, c3 = st.columns([1.3, 1.1, 2])
        c1.button("Använd värdena för valda DeSO", type="primary", disabled=anvands, on_click=_anvand_deso, width="stretch",
                  help="Sätter bilar per hushåll och körsträcka i mobiliteten till de valda DeSO:s värden. Personer per hushåll ändras inte.")
        c2.button("Använd kommunens värden", disabled=mob.get("kommunvarden", True), on_click=_anvand_kommun, width="stretch")
        c3.caption("Valda DeSO används i beräkningen." if anvands else
                   "Beräkningen använder " + ("kommunens värden." if mob.get("kommunvarden", True) else "egna värden från Indata → Mobilitet."))
        senare(lambda res: _trafik_steg(res, s))
        with st.expander(f"DeSO i urvalet ({s['antal']})"):
            df = deso_tabell(g["deso"])
            st.dataframe(df, hide_index=True, width="stretch", column_config=_tal_kol(df))
    if jamfor:
        st.markdown("#### Alla scenarier")
        rader = []
        for namn, scen in jamfor:
            sx = geodata.summera(scen.get("geografi", {}).get("deso", []))
            m = scen["mobilitet"]
            rader.append({"Scenario": namn, "Valda DeSO": sx["antal"] if sx else 0,
                          "Bilar per hushåll i DeSO": round(sx["bilar_per_hushall"], 3) if sx else float("nan"),
                          "Bilar per hushåll i beräkningen": float(m["bilar_per_hushall"]), "km per bil i beräkningen": float(m["km_per_bil"]),
                          "Källa": "valda DeSO" if m.get("kalla_deso") and not m.get("kommunvarden", True) else
                                   ("kommunen" if m.get("kommunvarden", True) else "eget värde")})
        df = pd.DataFrame(rader)
        st.dataframe(df, hide_index=True, width="stretch", column_config={c: st.column_config.NumberColumn(format="localized")
                                                                          for c in df.columns if c not in ("Scenario", "Källa")})
    st.markdown("#### Underlag")
    falt = kalla_["falt"]
    st.markdown("\n".join(f"- **{n}**: {falt[f]}" for n, f in [("Personbilar", "bilar"), ("Hushåll", "hushall"), ("Invånare", "invanare"),
                                                                 ("Körsträcka per bil", "km_per_bil"), ("Områdesgränser", "geometri")]))
    st.caption(f"Vägvis {kalla_['version']}, paketerad {kalla_['paketerad']}, data för {kalla_['dataar']}, DeSO-version {kalla_['deso_version']}. "
               f"Källkod och data: [{kalla_['repo'].replace('https://', '')}]({kalla_['repo']}). Vägvis ändras inte av Road2Zero; "
               "underlaget läses in med verktyg/hamta_vagvis.py. Personbilar avser bilar registrerade på folkbokförda personer 31 december "
               "(privatleasing och enskild firma ingår, förmånsbilar ingår inte).")


def _trafik_steg(res, s: dict):
    sc = res.scen
    mob = sc["mobilitet"]
    pph = float(sc["hushall"]["personer_per_hushall"])
    inv = res.nyckeltal()["invanare_full"]
    hh = inv / pph if pph else 0.0
    bph, km = float(mob["bilar_per_hushall"]), float(mob["km_per_bil"])
    fkm = hh * bph * km
    kx = Kontext(fb(), sc)
    y0 = max(res.ar()[0], 2026)
    f, mix = faktorer(kx, y0), mix_for_ar(kx, y0)
    gkm = sum(mix[d] * f[d]["total"] for d in mix)
    mobt = float(res.totalt_per_kategori()["Mobilitet och transport"])
    html = "<div class='r2z-eyebrow' style='margin:1.4rem 0 0.8rem 0'>Så räknas planens bilar</div>"
    html += steg(1, "Hushållen och deras bilar i valda DeSO",
                 "Antal hushåll, invånare och personbilar i trafik registrerade på de folkbokförda den 31 december, ur SCB:s registerstatistik.",
                 f"{fmt(s['hushall'])} hushåll, {fmt(s['invanare'])} invånare och {fmt(s['bilar'])} personbilar.")
    html += steg(2, "Bilar per hushåll",
                 "Registrerade bilar delat med antalet hushåll. Ingen uppräkning görs för förmånsbilar.",
                 f"{fmt(s['bilar'])} ÷ {fmt(s['hushall'])} = <b>{fmt(s['bilar_per_hushall'], 3)} bilar per hushåll</b>"
                 f" (beräkningen använder {fmt(bph, 3)}).")
    html += steg(3, "Körsträcka per bil",
                 "Kommunvärde: riksmedel 12 753 km per bil och år gånger kommunens kvot mot riket enligt RUS och SCB:s körsträckedata. "
                 "Samma värde för alla DeSO i kommunen.",
                 f"<b>{fmt(s['km_per_bil'])} km per bil och år</b> (beräkningen använder {fmt(km)}).")
    html += steg(4, "Planens fordonskilometer vid full utbyggnad",
                 "Planens hushåll × bilar per hushåll × körsträcka. Bilinnehav och körsträcka kan förändras över tid enligt "
                 "Antaganden & scenario.",
                 f"{fmt(inv)} invånare ÷ {fmt(pph, 2)} = {fmt(hh)} hushåll × {fmt(bph, 3)} × {fmt(km)} km = <b>{fmt(fkm)} fordonskm per år</b>.")
    html += steg(5, "Livscykelutsläpp",
                 "Fordonskilometer × livscykelfaktor per drivlina (bränsle, el, fordon och batteri, underhåll) viktad med drivlinemixen. "
                 "Andelen elbilar ökar och elens klimatfaktor minskar år för år.",
                 f"{fmt(fkm)} fordonskm × {fmt(gkm, 1)} g CO₂e/km ({y0}) ÷ 1 000 000 = <b>{fmt(fkm * gkm / 1e6)} t CO₂e per år</b>. "
                 f"Mobilitet och transport {res.ar()[0]}–{res.ar()[-1]}: <b>{fmt(mobt)} t CO₂e</b>.")
    st.markdown(html, unsafe_allow_html=True)


# ---------- Metod & källor ----------
def metod_kallor(modell_namn: str):
    sidrubrik(stig(), "Metod & källor", "Öppen metod.", "Spårbara källor.",
              f"{modell_namn} använder samma beräkningsmotor som alla Road2Zero-modeller. Alla faktorer ligger i ett faktabibliotek "
              "med källa och statusklass, och koden har regressionstester.")
    st.markdown("""
#### Systemgräns och redovisningsnivåer
- **Nivå 1 · exploateringen:** Byggnad (A1–A5), Energi (drift), Anläggning, Förändrad markanvändning, minus Negativa utsläpp.
- **Nivå 2 · med invånarna:** plus Mobilitet och transport, Flygresor, Matkonsumtion och Övrig konsumtion.
- **Nivå 3 · med offentlig sektor:** plus offentlig konsumtion och den offentliga andelen av investeringarna.
- Undvikna utsläpp från exporterad solel redovisas utanför nettot.

#### Tid
Hela år, standard 2026–2076. Startår från 1990 går att välja för befintliga stadsdelar; år före 2026 använder startvärdena
(ingen bakåtskrivning) och får ingen budgetandel. Byggskedet bokförs det år BTA:n blir klar. Drift och invånare med halvårsregel.

#### Klimatbudget
Forster m.fl. (2026), uppräknad för andra växthusgaser (56,8/43,2) och fördelad lika per person på de invånare som faktiskt bor i
området år för år. Resultatet jämför också snittet per person och år för en vald analysperiod (standard 2027–2050) med
budgetutrymmet per person för valfri temperatur (1,5–2,0 °C) och sannolikhet.

#### Konsumtion
- **Mat:** kostprofiler ur EPIC-Oxford-kohorten (Scarborough m.fl. 2023), kalibrerade till svensk nivå 1,75 t per invånare och år
  (Bälter m.fl. 2017); utveckling enligt den svenska trenden för livsmedel per person (Naturvårdsverket).
- **Flygresor:** 0,88 t per invånare (Kamb och Larsson 2018, justerat för resandet efter pandemin), som koldioxid från bränslet och
  höghöjdseffekt (faktor 1,89, kan väljas bort under Resultat); utveckling enligt ReFuelEU Aviation och IATA.
- **Övrig konsumtion:** sju kategorier ur Konsumtionskompassen 2.1.

#### Kopplade modeller och underlag
- **Vägvis 2.3.1** (öppen källkod): hushåll, invånare och personbilar per DeSO 2024 ur SCB:s register, körsträcka per bil per kommun
  och DeSO-gränser. Används för kartorna och, om du väljer det, för bilinnehavet i mobiliteten.
- **Skogskolmodellen 10.4:** kolförråd och förlorat upptag för skog i Förändrad markanvändning.
- **OpenStreetMap:** bakgrundskarta.

#### Kända osäkerheter
- Fullständig referens till Dodoo m.fl. 2026 saknas.
- Riksgenomsnitt för markkol 0–50 cm saknas; gräsmark och urban grönyta använder SLU:s länsvärde för Uppsala.
- Bilinnehavet i befintliga DeSO beskriver dagens boende; för en ny plan är det en schablon som bör prövas mot planens parkeringstal.
""")
    st.caption(f"Road2Zero {__version__} · källkod: [github.com/Mulmen65/road2zero](https://github.com/Mulmen65/road2zero)")
    st.markdown("#### Referenser")
    senare(ui_referenser.visa)
