"""Versionssatta scenarier, CSV-mallar och reproducerbara beräkningspaket."""
import csv
import hashlib
import io
import json
import zipfile

from . import __version__
from .engine import parameter_audit
from .schema import Scenario, Transport


def scenario_json(scenario):
    return scenario.model_dump_json(indent=2).encode("utf-8")


def load_scenario(content):
    if len(content) > 20 * 1024 * 1024:
        raise ValueError("Scenariofilen är större än 20 MB")
    return Scenario.model_validate_json(content)


def csv_bytes(rows):
    buf = io.StringIO(newline="")
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0]), delimiter=";")
        writer.writeheader()
        # Text skyddas mot formeltolkning om CSV öppnas i kalkylprogram.
        for row in rows:
            writer.writerow({k: ("'" + v if isinstance(v,str) and v.startswith(("=", "+", "-", "@")) else v) for k,v in row.items()})
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def transport_csv(content):
    text = content.decode("utf-8-sig")
    if not text.strip():
        raise ValueError("CSV-filen är tom")
    reader = csv.DictReader(io.StringIO(text), delimiter=";" if ";" in text.splitlines()[0] else ",")
    required = {"year", "perspective", "tco2e", "source_id", "boundary"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("CSV kräver kolumnerna: " + ", ".join(sorted(required)))
    rows = []
    for n, row in enumerate(reader, 2):
        if not any(row.values()):
            continue
        data = {k: v for k,v in row.items() if v != ""}
        data.setdefault("id", f"VAG-{n}")
        try:
            # Semikolonformat tillåter svensk decimalkomma.
            data["tco2e"] = float(str(data.get("tco2e", "")).replace(",", "."))
            rows.append(Transport.model_validate(data))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Fel i CSV rad {n}: {e}") from e
    if len({x.id for x in rows}) != len(rows):
        raise ValueError("Dubbla ID i Vägvis-importen")
    if not rows:
        raise ValueError("CSV-filen innehåller inga årsvärden")
    return rows


def result_zip(s, r):
    buf = io.BytesIO()
    raw = scenario_json(s)
    files = {
        "scenario.json": raw,
        "verifikation.csv": csv_bytes(r.ledger),
        "klimatkategorier.csv": csv_bytes(r.categories),
        "datakontroller.csv": csv_bytes(r.issues),
        "invanares_arsserie.csv": csv_bytes(r.population),
        "parametrar.csv": csv_bytes(parameter_audit(s)),
        "faktorer.csv": csv_bytes([f.model_dump() for f in s.factors]),
        "referenser.json": json.dumps([x.model_dump() for x in s.sources],ensure_ascii=False,indent=2).encode(),
        "metadata.json": json.dumps({"model_version":__version__, "schema_version":s.schema_version,
              "scenario_sha256":hashlib.sha256(raw).hexdigest(),"total_kgco2e":r.total_kg,
              "known_subtotal_kgco2e":r.known_subtotal_kg,"used_factors":sorted(r.used_factors)},indent=2).encode(),
        "LAS_MIG.txt": ("Road2Zero. Intern enhet kg CO2e; resultat visas normalt i ton. "
                         "null/tomt totalvärde betyder ofullständigt underlag. Känt delresultat är inte projektets total. "
                         "Transportperspektiven, referensmark och temporära kollager summeras endast enligt in_total. "
                         "CSV: UTF-8 med BOM, semikolon och decimalpunkt. Alla antaganden finns i scenario.json. "
                         "Inga filer skickas till externa beräkningstjänster av modellen.").encode("utf-8"),
    }
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name,content)
    return buf.getvalue()
