"""Regressionstester: ett påhittat testfall, byggbeståndets andelar, faktabibliotekets konsistens och ett rent gränssnitt."""
import json
import re
from pathlib import Path

import pytest

from road2zero.algoritmer import ALGORITMER, TABELLKALLOR
from road2zero.engine import berakna
from road2zero.factlib import ladda
from road2zero.modules.byggnader import energi_kwh_m2
from road2zero.modules.budget import andel_per_person, global_gt
from road2zero.scenario import exempel, fran_json, ny_andel, standardprojekt, takt, till_json, tomt, validera
from road2zero.utveckling import PERIODER, Utveckling

ROT = Path(__file__).resolve().parents[1]

FORVANTAT = {  # ton CO2e 2026–2076 för testfallet i scenario.exempel(), med standardtakterna i data/utveckling.csv
    "Byggnad": 17967, "Energi": 10268, "Anläggning": 2607, "Förändrad markanvändning": 2112,
    "Mobilitet och transport": 17682, "Flygresor": 26839, "Matkonsumtion": 61460, "Övrig konsumtion": 36639,
    "Offentliga investeringar": 9539, "Negativa utsläpp": -5520,
}


@pytest.fixture(scope="module")
def res():
    return berakna(exempel())


def test_kategorier(res):
    t = res.totalt_per_kategori()
    for k, v in FORVANTAT.items():
        assert abs(t[k] - v) <= max(10, abs(v) * 0.001), (k, t[k], v)


def test_flyg_delas_i_bransle_och_hoghojdseffekt(res):
    """Flyget redovisas som koldioxid från bränslet och höghöjdseffekt; summan är invånare × per_inv × index."""
    fb = ladda()
    d = res.lang[res.lang["kategori"] == "Flygresor"].groupby("delpost")["t"].sum()
    assert set(d.index) == {"Koldioxid från flygbränslet", "Höghöjdseffekt"}
    h = fb.param("flyg.hoghojd_faktor")
    assert abs(h - 170 / 90) < 0.01
    assert abs(d["Höghöjdseffekt"] / d.sum() - (1 - 1 / h)) < 1e-9
    utv = Utveckling(fb, res.scen)
    vantat = sum(n * fb.param("flyg.per_inv") * utv.index("flyg", y) for y, n in res.invanare.items())
    assert abs(d.sum() - vantat) < 1e-6


def test_niva1_och_nyckeltal(res):
    assert abs(res.netto(1) - 27434) <= 3
    nk = res.nyckeltal()
    assert abs(nk["per_m2_niva1"] - 338.7) < 0.5
    assert abs(nk["personar"] - 54409.1) < 0.5


def test_budget(res):
    b = res.budget
    assert b["global_gt"] == 130
    assert abs(b["per_person_total"] - 20.27) < 0.01
    assert abs(b["stadsdel_t"] - 6653) < 2
    assert b["slutar"] == {1: 2028, 2: 2028, 3: 2028}


def test_budget_2_grader():
    s = exempel(); s["budget"].update(temperatur="2,0", sannolikhet=50)
    b = berakna(s).budget
    assert b["slutar"][1] is None and b["slutar"][3] == 2053


def test_halvarsregel(res):
    assert abs(res.invanare[2027] - 12000 * 0.5 / 110 * 2.1) < 1e-6
    assert abs(res.invanare[2032] - 60000 / 110 * 2.1) < 1e-6


def test_takt():
    b = {"bta": 1000, "forsta_ar": 2030, "sista_ar": 2033, "fordelning": "framtung"}
    t = takt(b)
    assert abs(sum(t.values()) - 1000) < 1e-9 and t[2030] > t[2033]


def test_json_runda():
    s = exempel()
    assert fran_json(till_json(s)) == json.loads(till_json(s))


def test_aldre_format_delas_i_andelar(res):
    """En rad med två stommar (60 % trä, 40 % klimatförbättrad betong) blir två andelar med samma resultat."""
    s = exempel()
    gammal = {"namn": "Flerbostadshus", "typ": "flerbostadshus", "bta": 60000, "forsta_ar": 2027, "sista_ar": 2031,
              "fordelning": "jämn", "takt": {}, "stomme1": "trä", "andel1": 60, "stomme2": "klimatförbättrad_betong",
              "manuellt_kg_m2": None, "energiklass": "B", "fjv_andel": 1.0, "sol_m2": 2000, "palning": True,
              "paln_andel": 100, "spont_m2": 0, "virke_m3_m2": 0.15, "virkesprodukt": "Stomvirke", "ccf_andel": 100}
    s["byggnader"] = [gammal] + s["byggnader"][2:]
    ny = fran_json(json.dumps(s))
    assert [b["stomme"] for b in ny["byggnader"][:2]] == ["tra_bau", "betong_bast"]
    assert [b["bta"] for b in ny["byggnader"][:2]] == [36000, 24000]
    t = berakna(ny).totalt_per_kategori()
    for k in ("Byggnad", "Energi"):
        assert abs(t[k] - res.totalt_per_kategori()[k]) < 1, k


def test_energival_per_andel():
    """Varje andel har egna energival: byter en andel till eluppvärmning ändras bara den andelens energi."""
    fb = ladda()
    s = tomt(fb)
    s["byggnader"] = [ny_andel("flerbostadshus", "tra_bau", 10000, 2027), ny_andel("flerbostadshus", "betong_bau", 10000, 2027)]
    bas = berakna(s).lang
    s["byggnader"][1]["fjv_andel"] = 0.0
    ny = berakna(s).lang
    e0 = bas[bas["kategori"] == "Energi"].groupby("delpost")["t"].sum()
    e1 = ny[ny["kategori"] == "Energi"].groupby("delpost")["t"].sum()
    assert abs(e1["Fjärrvärme"] - e0["Fjärrvärme"] / 2) < 1e-6
    assert e1["El"] > e0["El"]
    # byggskedet påverkas inte av energivalet
    assert abs(bas[bas["kategori"] == "Byggnad"]["t"].sum() - ny[ny["kategori"] == "Byggnad"]["t"].sum()) < 1e-9


def test_fjarrvarmeandel_och_egen_el_per_bta():
    """Fastighetsvärmen kan delas mellan fjärrvärme och värmepump, och köpt el kan anges per m² BTA."""
    fb = ladda()
    b = ny_andel("flerbostadshus", "tra_bau", 10000, 2027, energiklass="C", fjv_andel=50.0)
    e = energi_kwh_m2(fb, b, 0.9)
    ek = fb.energiklass("flerbostadshus", "C")
    assert abs(e["fjv"] - 0.5 * ek["kopt_fjarrvarme"] * 0.9) < 1e-9
    assert abs(e["el"] - (0.5 * ek["fastighetsel_fjv"] + 0.5 * ek["el_eluppvarmd"]) * 0.9) < 1e-9
    b["egen_el_kwh"] = 25.0
    e = energi_kwh_m2(fb, b, 0.9)
    assert e["el"] == 25.0 and e["eget"]
    s = tomt(fb); s["byggnader"] = [b]
    r = berakna(s)
    el_2030 = r.lang[(r.lang["delpost"] == "El") & (r.lang["ar"] == 2030)]["t"].sum()
    assert abs(el_2030 - 10000 * 25.0 * berakna_el(s, 2030) / 1e6) < 1e-6


def berakna_el(s, y):
    from road2zero.kontext import Kontext
    return Kontext(ladda(), s).el(y)


def test_utveckling_standard_traffar_kallorna():
    u = Utveckling(ladda(), tomt())
    assert u.index("el", 2026) == 1.0 and u.index("bygg.betong_bau", 2026) == 1.0
    # Tabell A utökad: Betong BAU 0,5806 år 2035 relativt startvärdet
    assert abs(u.index("bygg.betong_bau", 2035) - 0.5806) < 1e-3
    # EU: −37 % 2024 (0,57 år 2026), −55 % 2030 och −90 % 2040 mot 1990
    assert abs(u.index("offentlig", 2030) - 0.45 / 0.57) < 1e-3
    assert abs(u.index("offentlig", 2040) - 0.10 / 0.57) < 1e-3
    # IEA: global el −3,7 % per år
    assert abs(u.index("bilprod", 2030) - 0.963 ** 4) < 1e-6
    # anläggning följer betongen
    assert all(u.index("anl", y) == u.index("bygg.betong_bau", y) for y in range(2026, 2101))


def test_utveckling_egna_takter():
    s = tomt()
    s["utveckling"]["takt"]["el"] = [0.0] * len(PERIODER)
    s["utveckling"]["takt"]["mat"] = [-10.0] + [0.0] * (len(PERIODER) - 1)
    s["utveckling"]["anl_foljer_betong"] = False
    s["utveckling"]["takt"]["anl"] = [0.0] * len(PERIODER)
    u = Utveckling(ladda(), s)
    assert u.index("el", 2080) == 1.0
    assert abs(u.index("mat", 2030) - 0.9 ** 4) < 1e-12 and abs(u.index("mat", 2090) - 0.9 ** 4) < 1e-12
    assert u.index("anl", 2050) == 1.0 and u.index("bygg.betong_bau", 2050) < 1.0


def test_laddbara_bilar_hogst_100_procent():
    from road2zero.kontext import Kontext
    from road2zero.modules.mobilitet import mix_for_ar
    s = tomt()
    s["utveckling"]["takt"]["bev"] = [10.0] * len(PERIODER)
    kx = Kontext(ladda(), s)
    for y in (2026, 2030, 2040, 2060, 2100):
        m = mix_for_ar(kx, y)
        assert abs(sum(m.values()) - 1) < 1e-9 and all(v >= 0 for v in m.values())
    assert mix_for_ar(kx, 2040)["bev"] == 1.0 and mix_for_ar(kx, 2040)["phev"] == 0.0


def test_aldre_format_031():
    """Indata sparade med version 0.3.1: uppvärmning som val och LFM30 som stomme."""
    s = exempel()
    s["byggnader"][0]["uppvarmning"] = "el"; s["byggnader"][0].pop("fjv_andel")
    s["byggnader"][1]["uppvarmning"] = "fjärrvärme"; s["byggnader"][1].pop("fjv_andel")
    s["byggnader"][2]["stomme"] = "lfm30"
    s.pop("utveckling"); s["el"] = {"kurva": "boverket_eu_referens"}; s["mat"]["forandring"] = 0.0
    ny = fran_json(json.dumps(s))
    assert [b["fjv_andel"] for b in ny["byggnader"][:2]] == [0.0, 100.0]
    assert ny["byggnader"][2]["stomme"] == "betong_bast"
    assert "utveckling" in ny and "el" not in ny and "forandring" not in ny["mat"]
    berakna(ny)


def test_ouppvarmd_klass_ger_ingen_fjarrvarme():
    fb = ladda()
    b = ny_andel("mobilitetshus", "betong_bau", 5000, 2028)
    assert b["energiklass"] == "Ouppvärmt" and b["fjv_andel"] == 0
    b["fjv_andel"] = 100.0
    e = energi_kwh_m2(fb, b)
    assert e["fjv"] == 0 and e["el"] > 0
    assert any("ingen fjärrvärme" in t for _, _, t in validera({**tomt(fb), "byggnader": [b]}, fb))


def test_energiklass_maste_finnas_for_typen():
    fb = ladda()
    b = ny_andel("kontor", "generisk", 5000, 2028, energiklass="Ouppvärmt")
    assert any(a == "fel" and "energiklass" in t for a, _, t in validera({**tomt(fb), "byggnader": [b]}, fb))


def test_stommens_schablon_per_typ():
    fb = ladda()
    assert fb.byggschablon("flerbostadshus", "tra_bau") < fb.byggschablon("flerbostadshus", "betong_bau")
    assert fb.byggschablon("skola", "tra_bau") != fb.byggschablon("flerbostadshus", "tra_bau")


def test_virke_bara_for_trastomme():
    fb = ladda()
    s = tomt(fb)
    s["byggnader"] = [ny_andel("flerbostadshus", "betong_bau", 10000, 2027, virke_m3_m2=0.2)]
    assert berakna(s).totalt_per_kategori().get("Negativa utsläpp", 0) == 0
    s["byggnader"] = [ny_andel("flerbostadshus", "tra_bau", 10000, 2027)]
    assert berakna(s).totalt_per_kategori()["Negativa utsläpp"] < 0


def test_kolinlagring_i_trastomme():
    """Kolinlagring = −(BTA × v × F_produkt): stomvirke för Trä BAU, limträ för Trä BÄST, eget val och egen mängd."""
    s = tomt()
    s["byggnader"] = [ny_andel("flerbostadshus", "tra_bau", 10000, 2027), ny_andel("flerbostadshus", "tra_bast", 10000, 2027, sista_ar=2028)]
    r = berakna(s)
    kol = r.lang[r.lang["delpost"] == "Kolinlagring i trästomme"]
    assert abs(kol["t"].sum() - (-(10000 * 0.15 * 720.7 + 10000 * 0.15 * 786.0) / 1000)) < 1e-6
    assert sorted(kol[kol["t"] < -1200]["ar"].unique().tolist()) == [2027]          # Trä BAU: allt 2027
    assert len(kol["ar"].unique()) == 2                                             # Trä BÄST fördelas på 2027 och 2028
    s["byggnader"] = [ny_andel("flerbostadshus", "tra_bau", 10000, 2027, virkesprodukt="KL-trä", virke_m3_m2=0.25)]
    r = berakna(s)
    assert abs(r.lang[r.lang["delpost"] == "Kolinlagring i trästomme"]["t"].sum() - (-10000 * 0.25 * 680.7 / 1000)) < 1e-6


def test_startvarden_som_tabellen():
    """Startvärden och benämningar enligt Tabell A utökad; Generisk = Betong BAU."""
    fb = ladda()
    forv = {"flerbostadshus": [365.0, 281.1, 379.2, 280.6, 233.6, 200.9], "kontor": [385.0, 300.3, 400.0, 296.0, 250.0, 215.0],
            "småhus": [238.0, 183.3, 247.3, 183.0, 180.0, 154.8], "handel": [290.0, 223.3, 301.3, 223.0, 185.6, 159.6],
            "skola": [376.0, 289.5, 390.6, 289.1, 240.6, 207.0], "vård": [385.0, 296.5, 400.0, 296.0, 246.4, 211.9],
            "övriga_byggnader": [460.0, 354.2, 477.9, 353.7, 294.4, 253.2]}
    for typ, v in forv.items():
        assert [fb.byggschablon(typ, s_) for s_ in ("betong_bau", "betong_bast", "stal_bau", "stal_bast", "tra_bau", "tra_bast")] == v, typ
        assert fb.byggschablon(typ, "generisk") == fb.byggschablon(typ, "betong_bau")
    u = Utveckling(fb, tomt())
    assert all(u.index("bygg.generisk", y) == u.index("bygg.betong_bau", y) for y in range(2026, 2101))
    # tabellens nivå 2030 för flerbostadshus, Betong BAU: 288,5 kg/m²
    assert abs(365.0 * u.index("bygg.betong_bau", 2030) - 288.5) < 0.1


def test_tomt_projekt():
    s = tomt()
    assert s["byggnader"] == [] and s["mark"]["overgangar"] == [] and s["anlaggning"]["ytor"] == []
    assert abs(berakna(s).netto(3)) < 1e-9


def test_faktabibliotek_konsistent():
    fb = ladda()
    refs = set(fb.referenser["id"])
    for df in [fb.parametrar, fb.byggschabloner, fb.kurvor, fb.energiklasser, fb.ytschabloner, fb.markpooler,
               fb.bevarande, fb.kostprofiler, fb.ovrig, fb.kommuner]:
        for k in df["kalla"]:
            for r in str(k).split(","):
                assert r in refs, r
    ids = set(fb.parametrar["id"])
    for a in ALGORITMER:
        for p in a["parametrar"]:
            assert p in ids, p
    for _, (_, k) in TABELLKALLOR.items():
        for r in k.split(","):
            assert r in refs, r


def test_alla_parametrar_som_anvands_finns(res):
    ids = set(ladda().parametrar["id"])
    assert res.anvanda <= ids, res.anvanda - ids


def test_rent_granssnitt():
    """Gränssnittet och faktabiblioteket hänvisar bara till publicerade källor, inte till tidigare bilagt underlag."""
    text = re.compile(r"Klimatanalys 3\.0|3\.0:s|Jägersro|Vägvis|Oceanhamn|QA-underlag|Tab_A|exempelprojekt|Lås .* referens|Scenarionamn",
                      re.IGNORECASE)
    kallid = re.compile(r"\b(KA30|JAGERSRO|VAGVIS\w*|HOLMQVIST2024|ANTAGANDE)\b")
    filer = list((ROT / "app").glob("*.py")) + list((ROT / "road2zero").rglob("*.py")) + list((ROT / "road2zero" / "data").glob("*.csv")) \
        + list((ROT / "road2zero" / "data").glob("*.json")) + [ROT / "streamlit_app.py"]
    for f in filer:
        if f.name in ("skogskol_kurvbibliotek.csv", "standardprojekt_jagersro.json"):   # standardprojektet får bära sitt namn
            continue
        for nr, rad in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            assert not (text.search(rad) or kallid.search(rad)), f"{f.relative_to(ROT)}:{nr}: {rad[:120]}"


def test_kost_per_kostprofil(res):
    """Matkonsumtionen redovisas per kostprofil, och delposterna summerar till kategorins total."""
    d = res.lang[res.lang["kategori"] == "Matkonsumtion"]
    assert set(d["delpost"]) == set(ladda().kostprofiler["namn"])
    assert round(d["t"].sum()) == FORVANTAT["Matkonsumtion"]


def test_budget_per_person_samma_som_modulen(res):
    """Budgetandelen per person kan räknas för valfri temperatur och sannolikhet med samma bana som modulen."""
    fb = ladda()
    s = exempel(fb)
    andel, _ = andel_per_person(fb, global_gt(fb, s["budget"]["temperatur"], s["budget"]["sannolikhet"]),
                                fb.param("budget.e0"), fb.param("budget.k"), res.ar())
    t = res.budget["tabell"].set_index("ar")["andel_per_person_t"]
    for y, v in andel.items():
        assert v == pytest.approx(t[y])
    assert global_gt(fb, "2,0", 90) > global_gt(fb, "1,5", 90)


def test_standardprojekt():
    """Appen startar med standardprojektet: 15 andelar, BTA ur underlaget, 3 000 träd och anläggning på 2030–2045."""
    fb = ladda()
    s = standardprojekt(fb)
    assert not [f for f in validera(s, fb) if f[0] == "fel"]
    assert len(s["byggnader"]) == 15
    assert sum(b["bta"] for b in s["byggnader"]) == pytest.approx(547267, abs=1)
    for typ in {b["typ"] for b in s["byggnader"]}:
        andelar = sorted(b["bta"] for b in s["byggnader"] if b["typ"] == typ)
        assert andelar[2] == pytest.approx(2 * andelar[0], rel=1e-3)          # 50/25/25
    assert sum(t["antal"] for t in s["negativa"]["trad"]) == pytest.approx(3000)
    assert {(r["forsta_ar"], r["sista_ar"]) for r in s["anlaggning"]["ytor"]} == {(2030, 2045)}
    r = berakna(s)
    assert r.totalt_per_kategori()["Byggnad"] > 0
