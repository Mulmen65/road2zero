"""Kör samma beräkningsmotor utan webbgränssnitt: python -m road2zero."""
import argparse
import json
from pathlib import Path

from .engine import calculate
from .io import load_scenario, result_zip, scenario_json
from .seeds import demonstration, jagersro


def main():
    parser=argparse.ArgumentParser(description="Road2Zero – klimatmodell utan karta")
    parser.add_argument("--scenario",type=Path,help="Versionssatt scenario-JSON")
    parser.add_argument("--demo",action="store_true",help="Använd syntetiskt räkneexempel")
    parser.add_argument("--output",type=Path,default=Path("exports"),help="Mapp för scenario och beräkningspaket")
    args=parser.parse_args()
    scenario=load_scenario(args.scenario.read_bytes()) if args.scenario else demonstration() if args.demo else jagersro()
    result=calculate(scenario)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"scenario.json").write_bytes(scenario_json(scenario))
    (args.output/"road2zero_berakningspaket.zip").write_bytes(result_zip(scenario,result))
    print(json.dumps({"scenario":scenario.project.name,"model_total_kgco2e":result.total_kg,
                      "known_subtotal_kgco2e":result.known_subtotal_kg,
                      "blocking_issues":sum(x["severity"]=="error" for x in result.issues),
                      "output":str(args.output.resolve())},ensure_ascii=False,indent=2))


if __name__=="__main__":main()
