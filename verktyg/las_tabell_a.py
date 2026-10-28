"""Läser Tabell A utökad (Excel) och uppdaterar faktabiblioteket.

Skriver:
  road2zero/data/byggschabloner.csv   startvärden per byggnadstyp och stomme (bladet "Startvarden och proxy")
  road2zero/data/reduktionskurvor.csv faktor relativt 2025 per byggnadskategori och stomme (bladet "Reduktionskurvor")
  road2zero/data/utveckling.csv       raderna för byggpåverkan och anläggning (årlig förändring per period)

Användning (från repots rot):
  python verktyg/las_tabell_a.py                       # läser underlag/tabell_a_utokad.xlsx
  python verktyg/las_tabell_a.py sökväg/till/fil.xlsx  # annan fil

Stommar: Generisk (= Betong BAU), Betong BAU/BÄST, Stål BAU/BÄST, Trä BAU/BÄST. BAU = SBUF 14381 Insteg, BÄST = SBUF 14381 Färdplan.
Kör alltid testerna efteråt: python -m pytest -q
"""
from __future__ import annotations

import csv
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import openpyxl

ROT = Path(__file__).resolve().parents[1]
DATA = ROT / "road2zero" / "data"
STANDARDFIL = ROT / "underlag" / "tabell_a_utokad.xlsx"

TYP = {"Flerbostadshus": "flerbostadshus", "Kontor": "kontor", "Småhus": "småhus", "Handelshus": "handel", "Skola": "skola",
       "Vårdbyggnad": "vård", "Mobilitetshus": "mobilitetshus", "Industribyggnad": "industribyggnad", "Övriga byggnader": "övriga_byggnader"}
STOMMAR = ["betong_bau", "betong_bast", "stal_bau", "stal_bast", "tra_bau", "tra_bast"]
STOMNAMN = {"betong_bau": "Betong BAU", "betong_bast": "Betong BÄST", "stal_bau": "Stål BAU", "stal_bast": "Stål BÄST",
            "tra_bau": "Trä BAU", "tra_bast": "Trä BÄST"}
# Typer som saknas i tabellen får kontorets värden (modellval)
PROXY_KONTOR = ("lokaler", "underjordisk_parkering")
KALLA = {"flerbostadshus": "MALMQVIST2023,SBUF14381", "kontor": "MALMQVIST2023,SBUF14381", "skola": "MALMQVIST2023,SBUF14381",
         "småhus": "SBUF14381,MALMQVIST2023", "handel": "SBUF14381,BOVERKET_KD_STATISTIK", "vård": "SBUF14381",
         "mobilitetshus": "SBUF14381", "industribyggnad": "SBUF14381,BOVERKET_KD_UNDANTAG", "övriga_byggnader": "SBUF14381"}
PERIODER = [(2027, 2030), (2031, 2035), (2036, 2040), (2041, 2045), (2046, 2050), (2051, 2060), (2061, 2070), (2071, 2100)]
PERIODKOL = [f"p{a}_{b}" for a, b in PERIODER]
KURVKATEGORI = "Flerbostad/kontor/skola m.fl."   # standardtakten per stomme härleds ur denna kategori


def r1(v) -> float:
    """Avrundning till en decimal som i Excel (halva uppåt)."""
    return float(Decimal(str(float(v))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def skriv(fil: Path, rader: list[dict], falt: list[str]):
    with open(fil, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=falt, delimiter=";")
        w.writeheader()
        for r in rader:
            w.writerow({k: r.get(k, "") for k in falt})


def las_startvarden(wb) -> dict:
    ws = wb["Startvarden och proxy"]
    start = {}
    for row in ws.iter_rows(values_only=True):
        if row[0] in TYP:
            start[TYP[row[0]]] = {"kategori": row[1], "startankare": row[2], "logik": row[3] or "",
                                  "varden": dict(zip(STOMMAR, row[4:10])), "kvalitet": row[10] or "", "kommentar": row[11] or ""}
    saknas = set(TYP.values()) - set(start)
    if saknas:
        raise SystemExit(f"Bladet 'Startvarden och proxy' saknar byggnadstyper: {sorted(saknas)}")
    return start


def byggschabloner(start: dict) -> list[dict]:
    def rad(t, s, v, o, kalla, anm):
        return {"byggnadstyp": t, "stomme": s, "kg_co2e_m2": r1(v), "kategori": o["kategori"], "startankare": r1(o["startankare"]),
                "datakvalitet": o["kvalitet"], "kalla": kalla, "anmarkning": anm}
    rader = []
    for t, o in start.items():
        anm = f"{o['logik']} {o['kommentar']}".replace("  ", " ").strip()
        rader.append(rad(t, "generisk", o["varden"]["betong_bau"], o, KALLA[t] + ",TABELL_A_UTOKAD", "Generisk = Betong BAU. " + anm))
        rader += [rad(t, s, o["varden"][s], o, KALLA[t] + ",TABELL_A_UTOKAD", anm) for s in STOMMAR]
    for t in PROXY_KONTOR:
        o = start["kontor"]
        for s in ["generisk"] + STOMMAR:
            rader.append(rad(t, s, o["varden"]["betong_bau" if s == "generisk" else s], o, "TABELL_A_UTOKAD,MODELLVAL",
                             "Proxy: kontorets värden; typen finns inte i Tabell A utökad. Ange gärna projektets värde."))
    return rader


def reduktionskurvor(wb) -> list[dict]:
    ws = wb["Reduktionskurvor"]
    rader = []
    for row in ws.iter_rows(min_row=4, values_only=True):
        if row[0] is None or not isinstance(row[1], int) or row[1] < 2025:
            continue
        # Flerbostad-blocket har en extra kolumn (Helsingborg); faktorerna står då i kolumn 9–14, annars 7–12
        f = row[8:14] if str(row[0]).startswith("Flerbostad") else row[6:12]
        if any(v is None for v in f):
            continue
        for s, v in zip(STOMMAR, f):
            rader.append({"kategori": row[0], "stomme": s, "ar": row[1], "faktor": round(float(v), 6)})
        rader.append({"kategori": row[0], "stomme": "generisk", "ar": row[1], "faktor": round(float(f[0]), 6)})
    if not rader:
        raise SystemExit("Hittade inga reduktionskurvor i bladet 'Reduktionskurvor'.")
    return rader


def _interp(pts: dict, y: int) -> float:
    xs = sorted(pts)
    if y <= xs[0]:
        return pts[xs[0]]
    if y >= xs[-1]:
        return pts[xs[-1]]
    for a, b in zip(xs, xs[1:]):
        if a <= y <= b:
            return pts[a] + (pts[b] - pts[a]) * (y - a) / (b - a)
    return pts[xs[-1]]


def takter(kurvor: list[dict]) -> dict[str, list[float]]:
    """Årlig förändring (%) per period så att kurvan träffar tabellens nivåer. Tabellens startvärde gäller 2026."""
    ut = {}
    for s in STOMMAR:
        pts = {int(r["ar"]): float(r["faktor"]) for r in kurvor if r["kategori"] == KURVKATEGORI and r["stomme"] == s}
        pts[2026] = pts[2025]
        v = []
        for a, b in PERIODER:
            if a > max(pts):
                v.append(0.0)
                continue
            v0, v1 = _interp(pts, a - 1), _interp(pts, b)
            v.append(round(((v1 / v0) ** (1 / (b - a + 1)) - 1) * 100, 2))
        ut[s] = v
    return ut


def uppdatera_utveckling(t: dict[str, list[float]]):
    fil = DATA / "utveckling.csv"
    with open(fil, encoding="utf-8") as f:
        rader = list(csv.DictReader(f, delimiter=";"))
    falt = list(rader[0].keys())
    ovriga = [r for r in rader if not r["faktor"].startswith("bygg.") and r["faktor"] != "anl"]
    nya = []
    for s in STOMMAR:
        niva = "SBUF 14381 Färdplan (BÄST)" if s.endswith("bast") else "SBUF 14381 Insteg (BAU)"
        r = {"faktor": f"bygg.{s}", "grupp": "Byggpåverkan", "namn": STOMNAMN[s], "enhet": "% per år", "kalla": "TABELL_A_UTOKAD,SBUF14381",
             "status": "Branschvägledning",
             "kommentar": f"{niva} till 2035, därefter Tabell A utökad:s försiktiga extrapolering till 2070 och 0 % efter 2070. "
                          "Tabellens startvärde gäller 2026 och kurvan träffar tabellens nivåer från 2030. Härledd ur kategorin "
                          "flerbostad/kontor/skola; övriga kategorier skiljer sig högst cirka 1 % till 2035."}
        r.update(dict(zip(PERIODKOL, t[s])))
        nya.append(r)
    anl = {"faktor": "anl", "grupp": "Byggpåverkan", "namn": "Anläggning (följer Betong BAU)", "enhet": "% per år",
           "kalla": "TABELL_A_UTOKAD,SBUF14381", "status": "Modellval",
           "kommentar": "Samma kurva som Betong BAU för hus. Gäller ytor, betong, massor, ledningar, pålning och spont; inte engångsvärden."}
    anl.update(dict(zip(PERIODKOL, t["betong_bau"])))
    skriv(fil, nya + [anl] + ovriga, falt)


def main():
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else STANDARDFIL
    if not xlsx.exists():
        raise SystemExit(f"Hittar inte {xlsx}. Lägg Excel-filen i underlag/ eller ange sökvägen.")
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    start = las_startvarden(wb)
    bs = byggschabloner(start)
    skriv(DATA / "byggschabloner.csv", bs,
          ["byggnadstyp", "stomme", "kg_co2e_m2", "kategori", "startankare", "datakvalitet", "kalla", "anmarkning"])
    rk = reduktionskurvor(wb)
    skriv(DATA / "reduktionskurvor.csv", rk, ["kategori", "stomme", "ar", "faktor"])
    t = takter(rk)
    uppdatera_utveckling(t)
    print(f"Läste {xlsx.name}: {len(bs)} startvärden, {len(rk)} kurvpunkter.")
    for s in STOMMAR:
        print(f"  {STOMNAMN[s]:12s} " + "  ".join(f"{v:6.2f}" for v in t[s]) + "  % per år")
    print("Kör nu: python -m pytest -q")


if __name__ == "__main__":
    main()
