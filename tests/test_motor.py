"""Regressionstester: ett påhittat testfall, byggbeståndets andelar, faktabibliotekets konsistens och ett rent gränssnitt."""
import json
import re
from pathlib import Path

import pytest

from road2zero.algoritmer import ALGORITMER, TABELLKALLOR
from road2zero.engine import berakna
from road2zero.factlib import ladda
from road2zero.modules.byggnader import energi_kwh_m2
from road2zero.scenario import exempel, fran_json, ny_andel, takt, till_json, tomt, validera

ROT = Path(__file__).resolve().parents[1]

FORVANTAT = {  # ton CO2e 2026–2076 för testfallet i scenario.exempel()
    "Byggnad": 17736, "Energi": 10108, "Anläggning": 3124, "Förändrad markanvändning": 2112,
    "Mobilitet och transport": 21550, "Flygresor": 59850, "Matkonsumtion": 111638, "Övrig konsumtion": 88018,
    "Offentliga investeringar": 65628, "Negativa utsläpp": -5520,
}


@pytest.fixture(scope="module")
def res():
    return berakna(exempel())


def test_kategorier(res):
    t = res.totalt_per_kategori()
    for k, v in FORVANTAT.items():
        assert abs(t[k] - v) <= max(10, abs(v) * 0.001), (k, t[k], v)


def test_niva1_och_nyckeltal(res):
    assert abs(res.netto(1) - 27560) <= 3
    nk = res.nyckeltal()
    assert abs(nk["per_m2_niva1"] - 340.2) < 0.5
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
    assert b["slutar"][1] is None and b["slutar"][3] == 2043


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
    assert [b["stomme"] for b in ny["byggnader"][:2]] == ["trä", "klimatförbättrad_betong"]
    assert [b["bta"] for b in ny["byggnader"][:2]] == [36000, 24000]
    t = berakna(ny).totalt_per_kategori()
    for k in ("Byggnad", "Energi", "Negativa utsläpp"):
        assert abs(t[k] - res.totalt_per_kategori()[k]) < 1, k


def test_energival_per_andel():
    """Varje andel har egna energival: byter en andel till eluppvärmning ändras bara den andelens energi."""
    fb = ladda()
    s = tomt(fb)
    s["byggnader"] = [ny_andel("flerbostadshus", "trä", 10000, 2027), ny_andel("flerbostadshus", "betong", 10000, 2027)]
    bas = berakna(s).lang
    s["byggnader"][1]["uppvarmning"] = "el"
    ny = berakna(s).lang
    e0 = bas[bas["kategori"] == "Energi"].groupby("delpost")["t"].sum()
    e1 = ny[ny["kategori"] == "Energi"].groupby("delpost")["t"].sum()
    assert abs(e1["Fjärrvärme"] - e0["Fjärrvärme"] / 2) < 1e-6
    assert e1["El"] > e0["El"]
    # byggskedet påverkas inte av energivalet
    assert abs(bas[bas["kategori"] == "Byggnad"]["t"].sum() - ny[ny["kategori"] == "Byggnad"]["t"].sum()) < 1e-9


def test_ouppvarmd_klass_ger_ingen_fjarrvarme():
    fb = ladda()
    b = ny_andel("mobilitetshus", "betong", 5000, 2028)
    assert b["energiklass"] == "Ouppvärmt" and b["uppvarmning"] == "el"
    b["uppvarmning"] = "fjärrvärme"
    e = energi_kwh_m2(fb, b)
    assert e["fjv"] == 0 and e["el"] > 0
    assert any("ingen fjärrvärme" in t for _, _, t in validera({**tomt(fb), "byggnader": [b]}, fb))


def test_energiklass_maste_finnas_for_typen():
    fb = ladda()
    b = ny_andel("kontor", "generisk", 5000, 2028, energiklass="Ouppvärmt")
    assert any(a == "fel" and "energiklass" in t for a, _, t in validera({**tomt(fb), "byggnader": [b]}, fb))


def test_stommens_schablon_per_typ():
    fb = ladda()
    assert fb.byggschablon("flerbostadshus", "trä") < fb.byggschablon("flerbostadshus", "betong")
    assert fb.byggschablon("skola", "trä") != fb.byggschablon("flerbostadshus", "trä")


def test_virke_bara_for_trastomme():
    fb = ladda()
    s = tomt(fb)
    s["byggnader"] = [ny_andel("flerbostadshus", "betong", 10000, 2027, ccf_andel=100)]
    assert berakna(s).totalt_per_kategori().get("Negativa utsläpp", 0) == 0
    s["byggnader"] = [ny_andel("flerbostadshus", "trä", 10000, 2027, ccf_andel=100)]
    assert berakna(s).totalt_per_kategori()["Negativa utsläpp"] < 0


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
        if f.name == "skogskol_kurvbibliotek.csv":
            continue
        for nr, rad in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            assert not (text.search(rad) or kallid.search(rad)), f"{f.relative_to(ROT)}:{nr}: {rad[:120]}"
