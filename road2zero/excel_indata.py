"""Indata som Excel: en arbetsbok med ett eller flera scenarier som går att fylla i, skicka runt och läsa in igen.

Arbetsboken har
  - bladet "Läs mig" med en förklaring,
  - bladet "Värden": alla enskilda värden i långt format (Scenario, Sökväg, Värde), till exempel hushall/personer_per_hushall,
  - bladet "Utveckling": årlig förändring per emissionsfaktor och period (en rad per scenario och faktor),
  - ett blad per lista med en rad per post, till exempel "byggnader" och "anlaggning.ytor", med kolumnen Scenario först,
  - bladet "Listor", som talar om vilket blad som hör till vilken del av indata.
Listor med enkla värden (till exempel valda DeSO) och inbäddade tabeller (till exempel utbyggnadstakt per år) står som JSON i cellen.

fran_excel() bygger indata per scenario och kör dem genom scenario.fran_json(), så att saknade värden får standardvärden och
äldre format migreras på samma sätt som för JSON-filer. Modulen använder inte Streamlit.
"""
from __future__ import annotations

import io
import json

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .factlib import Faktabibliotek
from .scenario import fran_json, ny_andel
from .utveckling import PERIODNAMN

SEP = "/"
VARDEN, UTVECKLING, LISTOR, LAS_MIG = "Värden", "Utveckling", "Listor", "Läs mig"
UTV_SOK = f"utveckling{SEP}takt"
RUBRIK = Font(bold=True, color="FFFFFF")
RUBRIKFARG = PatternFill("solid", fgColor="103C38")

# Kolumner för listor som kan vara tomma, så att mallen går att fylla i
LISTKOLUMNER = {
    "byggnader": list(ny_andel().keys()),
    f"anlaggning{SEP}ytor": ["namn", "typ", "utforande", "yta_m2", "forsta_ar", "sista_ar"],
    f"anlaggning{SEP}massor": ["typ", "volym_m3", "transport_km", "forsta_ar", "sista_ar"],
    f"anlaggning{SEP}betong": ["utforande", "volym_m3", "forsta_ar", "sista_ar"],
    f"anlaggning{SEP}ledningar": ["meter", "forsta_ar", "sista_ar"],
    f"anlaggning{SEP}engangsvarden": ["namn", "t_co2e", "ar"],
    f"mark{SEP}overgangar": ["fran", "till", "ha", "ar", "tradslag", "skotsel", "skogsalder", "bevarat_soc", "bevarat_dom", "bevarat_bio"],
    f"negativa{SEP}biokol": ["gropar", "ar", "certifierat"],
    f"negativa{SEP}trad": ["antal", "planteringsar"],
}


def _platta(d: dict, bas: str, varden: list, listor: dict, utv: list, sid: str):
    for nyckel, v in d.items():
        sok = f"{bas}{SEP}{nyckel}" if bas else str(nyckel)
        if sok == UTV_SOK and isinstance(v, dict):
            utv.extend((sid, f, rad) for f, rad in v.items())
        elif isinstance(v, dict):
            if v and not any(SEP in str(x) for x in v):
                _platta(v, sok, varden, listor, utv, sid)
            else:                                       # tomma tabeller och nycklar med snedstreck står som JSON
                varden.append((sid, sok, json.dumps(v, ensure_ascii=False)))
        elif isinstance(v, list) and (sok in LISTKOLUMNER or (v and all(isinstance(x, dict) for x in v))):
            listor.setdefault(sok, []).extend((sid, x) for x in v)
        elif isinstance(v, list):
            varden.append((sid, sok, json.dumps(v, ensure_ascii=False)))
        else:
            varden.append((sid, sok, v))


def _cell(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v


def _rubrik(ws, bredder: list[int]):
    for i, b in enumerate(bredder, 1):
        c = ws.cell(row=1, column=i)
        c.font, c.fill = RUBRIK, RUBRIKFARG
        ws.column_dimensions[get_column_letter(i)].width = b
    ws.freeze_panes = "B2"


def till_excel(scenarier: dict[str, dict]) -> bytes:
    """Arbetsbok med ett eller flera scenarier: {"A": indata, "B": indata, …} eller {"Plan": indata}."""
    varden: list = []
    listor: dict[str, list] = {s: [] for s in LISTKOLUMNER}
    utv: list = []
    for sid, s in scenarier.items():
        _platta(s, "", varden, listor, utv, sid)
    wb = Workbook()
    las = wb.active
    las.title = LAS_MIG
    for r in [
        "Road2Zero – indata",
        "",
        "Arbetsboken innehåller indata för " + "; ".join(f"{sid}: {s.get('projekt', {}).get('namn', '')}" for sid, s in scenarier.items()) + ".",
        "Värden: alla enskilda värden. Ändra kolumnen Värde; sökvägen visar var värdet hör hemma.",
        "Utveckling: årlig förändring i procent per period för varje emissionsfaktor (elbilar och laddhybrider i procentenheter).",
        "Övriga blad: en rad per post, till exempel byggnader och anlaggning.ytor. Lägg till eller ta bort rader.",
        "Kolumnen Scenario anger vilket scenario raden hör till. Celler inom [ ] eller { } är inbäddade tabeller i JSON.",
        "Värden som saknas får modellens standardvärden när filen läses in. Budgetens temperatur (1,5 eller 2) ska stå som text.",
        "Läs in filen med Öppna fil i Road2Zero-Plan eller Road2Zero-CityScenario.",
    ]:
        las.append([r])
    las["A1"].font = Font(bold=True, size=14)
    las.column_dimensions["A"].width = 120

    ws = wb.create_sheet(VARDEN)
    ws.append(["Scenario", "Sökväg", "Värde"])
    for sid, sok, v in varden:
        ws.append([sid, sok, _cell(v)])
    _rubrik(ws, [10, 52, 40])

    ws = wb.create_sheet(UTVECKLING)
    ws.append(["Scenario", "Faktor", *PERIODNAMN])
    for sid, f, rad in utv:
        ws.append([sid, f, *[_cell(x) for x in (rad if isinstance(rad, list) else [rad])]])
    _rubrik(ws, [10, 22] + [11] * len(PERIODNAMN))

    karta = wb.create_sheet(LISTOR)
    karta.append(["Blad", "Sökväg i indata"])
    for sok, poster in listor.items():
        namn = sok.replace(SEP, ".")[:31]
        ws = wb.create_sheet(namn)
        kol = list(LISTKOLUMNER.get(sok, []))
        for _, x in poster:
            kol += [c for c in x if c not in kol]
        ws.append(["Scenario", *kol])
        for sid, x in poster:
            ws.append([sid, *[_cell(x.get(c)) for c in kol]])
        _rubrik(ws, [10] + [max(11, min(36, len(c) + 4)) for c in kol])
        karta.append([namn, sok])
    _rubrik(karta, [24, 30])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _tolka(v):
    if isinstance(v, str):
        s = v.strip()
        if (s[:1], s[-1:]) in (("[", "]"), ("{", "}")):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return v
    return v


def _satt(d: dict, sok: str, v):
    delar = sok.split(SEP)
    for nyckel in delar[:-1]:
        d = d.setdefault(nyckel, {})
        if not isinstance(d, dict):
            raise ValueError(f"Sökvägen {sok} krockar med ett annat värde.")
    d[delar[-1]] = v


def lasa_excel(data: bytes) -> dict[str, dict]:
    """Läser arbetsboken till indata per scenario, utan standardvärden."""
    try:
        wb = load_workbook(io.BytesIO(data), data_only=True)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Filen kunde inte läsas som Excel ({e}).") from e
    if VARDEN not in wb.sheetnames:
        raise ValueError("Arbetsboken saknar bladet Värden. Spara indata som Excel från Road2Zero och använd den som mall.")
    ut: dict[str, dict] = {}

    def scen(sid) -> dict:
        return ut.setdefault(str(sid).strip(), {})

    for rad in wb[VARDEN].iter_rows(min_row=2, values_only=True):
        if not rad or rad[0] in (None, "") or len(rad) < 2 or rad[1] in (None, ""):
            continue
        s = scen(rad[0])
        if len(rad) > 2 and rad[2] is not None:
            _satt(s, str(rad[1]).strip(), _tolka(rad[2]))
    if UTVECKLING in wb.sheetnames:
        for rad in wb[UTVECKLING].iter_rows(min_row=2, values_only=True):
            if not rad or rad[0] in (None, "") or rad[1] in (None, ""):
                continue
            vals = [0.0 if v is None else float(v) for v in rad[2:2 + len(PERIODNAMN)]]
            vals += [0.0] * (len(PERIODNAMN) - len(vals))
            _satt(scen(rad[0]), f"{UTV_SOK}{SEP}{str(rad[1]).strip()}", vals)
    blad_sok = {}
    if LISTOR in wb.sheetnames:
        for rad in wb[LISTOR].iter_rows(min_row=2, values_only=True):
            if rad and rad[0] and len(rad) > 1 and rad[1]:
                blad_sok[str(rad[0])] = str(rad[1])
    for blad in wb.sheetnames:
        if blad in (VARDEN, UTVECKLING, LISTOR, LAS_MIG):
            continue
        rader = list(wb[blad].iter_rows(values_only=True))
        if not rader or not rader[0] or rader[0][0] != "Scenario":
            continue
        sok = blad_sok.get(blad, blad.replace(".", SEP))
        kol = [str(c) if c is not None else "" for c in rader[0]]
        per: dict[str, list] = {}
        for r in rader[1:]:
            if not r or r[0] in (None, ""):
                continue
            post = {c: _tolka(v) for c, v in zip(kol[1:], r[1:]) if c and v is not None}
            if post:
                per.setdefault(str(r[0]).strip(), []).append(post)
                scen(r[0])
        for sid in ut:
            _satt(ut[sid], sok, per.get(sid, []))
    return ut


def fran_excel(data: bytes, fb: Faktabibliotek | None = None) -> dict[str, dict]:
    """Indata per scenario ur en arbetsbok från till_excel(), med standardvärden och migrering som för JSON."""
    ra = lasa_excel(data)
    if not ra:
        raise ValueError("Arbetsboken innehåller inga scenarier.")
    ut = {}
    for sid, s in ra.items():
        try:
            ut[sid] = fran_json(json.dumps(s, ensure_ascii=False), fb)
        except ValueError as e:
            raise ValueError(f"Scenario {sid}: {e}") from e
    return ut
