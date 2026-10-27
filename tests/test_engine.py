"""Oberoende räknefall, avgränsning och regressioner för de viktigaste riskerna."""
import hashlib
import io
import json
import unittest
import zipfile

from pydantic import ValidationError

from road2zero.engine import CO2_PER_C, calculate, parameter_audit
from road2zero.io import csv_bytes, load_scenario, result_zip, scenario_json, transport_csv
from road2zero.schema import Curve, CurvePoint, Factor, Phase, Programme
from road2zero.seeds import demonstration, jagersro


def total_for(result, category):
    return next(x for x in result.categories if x["category"] == category)["kgco2e"]


class ModelTests(unittest.TestCase):
    def test_independent_complete_example(self):
        s=demonstration();r=calculate(s)
        expected={"Byggnad":200000,"Energi":8560,"Anläggning":5000,
                  "Förändrad markanvändning":2000*(2*.1+.1*.5+.2*.5)*44/12,
                  "Mobilitet och transport":20000,"Matkonsumtion":64000,
                  "Övrig konsumtion":24000,"Offentliga investeringar":32000,
                  "Negativa utsläpp":-500-1800+100}
        for category,value in expected.items():
            with self.subTest(category=category):self.assertAlmostEqual(total_for(r,category),value)
        self.assertAlmostEqual(r.total_kg,sum(expected.values()))
        self.assertAlmostEqual(r.total_kg,sum(x["kgco2e"] for x in r.ledger if x["in_total"]))
        self.assertAlmostEqual(r.person_years,80)

    def test_smt_is_aggregate_and_incomplete(self):
        s=jagersro();r=calculate(s)
        self.assertEqual(s.project.homes,4000)
        self.assertNotIn("buildings",s.model_dump())
        self.assertEqual(len(s.programme),1)
        self.assertAlmostEqual(r.project_bta,440000*4000/4300)
        self.assertAlmostEqual(r.full_population,8900*4000/4300)
        self.assertIsNone(r.total_kg)
        self.assertIsNone(total_for(r,"Byggnad"))
        self.assertFalse(s.project.phasing_enabled)

    def test_changing_total_bta_scales_building_and_energy(self):
        s=demonstration();s.project.total_bta_override=2000
        s.programme[0].atemp_m2=None
        s.programme[0].atemp_ratio_factor_id="ratio"
        s.factors.append(Factor(id="ratio",name="Atemp",value=.9,unit="Atemp/BTA",source_id="DEMO"))
        s.programme[0].solar_kwh_year=0
        r=calculate(s)
        self.assertEqual(total_for(r,"Byggnad"),400000)
        self.assertAlmostEqual(total_for(r,"Energi"), (1800*20*.05+1800*40*.04)*4)

    def test_aggregate_programme_split_is_not_double_counted(self):
        s=demonstration();a=s.programme[0];a.share_bta=.7
        b=a.model_copy(deep=True);b.id="P2";b.share_bta=.3;s.programme.append(b)
        r=calculate(s)
        self.assertEqual(total_for(r,"Byggnad"),200000)
        s.programme[0].construction_total_kg=70000
        s.programme[1].construction_total_kg=30000
        self.assertEqual(total_for(calculate(s),"Byggnad"),100000)

    def test_phase_split_preserves_total_construction_and_manual_total(self):
        s=demonstration();s.project.phasing_enabled=True;s.project.build_end_year=2030
        s.phases=[Phase(id="E1",name="1",start=2029,end=2029,share=.4),Phase(id="E2",name="2",start=2030,end=2030,share=.6)]
        self.assertEqual(total_for(calculate(s),"Byggnad"),200000)
        s.programme[0].construction_total_kg=123456
        self.assertEqual(total_for(calculate(s),"Byggnad"),123456)

    def test_invalid_programme_or_phase_balance_blocks_total(self):
        s=demonstration();s.programme[0].share_bta=.8
        self.assertIsNone(calculate(s).total_kg)
        s=demonstration();s.project.phasing_enabled=True;s.phases[0].share=.8
        self.assertIsNone(calculate(s).total_kg)

    def test_zero_population_override_is_honoured(self):
        s=demonstration();s.project.population_override=0
        r=calculate(s)
        self.assertEqual(r.full_population,0)
        self.assertEqual(r.estimated_population,20)
        self.assertEqual(r.person_years,0)
        for cat in ("Matkonsumtion","Övrig konsumtion","Offentliga investeringar"):
            self.assertEqual(total_for(r,cat),0)

    def test_zero_bta_override_is_honoured(self):
        s=demonstration();s.project.total_bta_override=0
        self.assertEqual(total_for(calculate(s),"Byggnad"),0)

    def test_missing_value_is_not_zero(self):
        s=demonstration();s.factors[2].value=None
        r=calculate(s)
        self.assertIsNone(total_for(r,"Byggnad"))
        self.assertIsNone(r.total_kg)

    def test_wrong_unit_is_blocking(self):
        s=demonstration();next(f for f in s.factors if f.id=="build").unit="kgCO2e/m3"
        r=calculate(s)
        self.assertIsNone(total_for(r,"Byggnad"))
        self.assertTrue(any("enhet" in x["message"] for x in r.issues))

    def test_factor_curve_interpolation_and_range(self):
        s=demonstration();f=next(f for f in s.factors if f.id=="grid")
        f.curve_id="EL";f.value=999;f.annual_change=.9
        s.curves=[Curve(id="EL",name="El",unit="gCO2e/kWh",source_id="DEMO",points=[CurvePoint(year=2030,value=40),CurvePoint(year=2033,value=10)])]
        r=calculate(s)
        self.assertAlmostEqual(total_for(r,"Energi"),14000*(40+30+20+10)/1000+1440*4)
        s.curves[0].points.pop()
        self.assertIsNone(total_for(calculate(s),"Energi"))
        s.curves[0].tail="hold"
        self.assertAlmostEqual(total_for(calculate(s),"Energi"),14000*40*4/1000+1440*4)

    def test_manual_construction_total_has_precedence(self):
        s=demonstration();s.programme[0].construction_total_kg=0
        next(f for f in s.factors if f.id=="build").value=None
        self.assertEqual(total_for(calculate(s),"Byggnad"),0)

    def test_construction_uses_start_year_factor(self):
        s=demonstration();s.project.build_end_year=2030
        f=next(f for f in s.factors if f.id=="build");f.reference_year=2029;f.annual_change=-.1
        r=calculate(s)
        rows=[x for x in r.ledger if x["category"]=="Byggnad"]
        self.assertEqual([x["kgco2e"] for x in rows],[100000,100000])

    def test_piling_spont_in_infrastructure_only(self):
        s=demonstration();p=s.programme[0];p.piling="yes";p.piling_factor_id="pile";p.sheet_piling="yes";p.sheet_area_m2=100;p.sheet_factor_id="sheet"
        s.factors += [Factor(id="pile",name="Pile",value=26,unit="kgCO2e/m2",source_id="DEMO"),Factor(id="sheet",name="Sheet",value=280.5,unit="kgCO2e/m2",source_id="DEMO")]
        r=calculate(s)
        self.assertEqual(total_for(r,"Byggnad"),200000)
        self.assertEqual(total_for(r,"Anläggning"),5000+26000+28050)

    def test_solar_export_is_not_removal(self):
        s=demonstration();p=s.programme[0];p.solar_kwh_year=100000;p.solar_self_use=.8
        r=calculate(s)
        self.assertEqual(total_for(r,"Energi"),1440*4)
        exports=[x for x in r.ledger if x["view"]=="Solelexport"]
        self.assertEqual(sum(x["quantity"] for x in exports),82000*4)
        self.assertTrue(all(not x["in_total"] and x["kgco2e"]==0 for x in exports))

    def test_transport_perspectives_never_sum(self):
        s=demonstration()
        from road2zero.schema import Transport
        s.transport += [Transport(id=f"A{y}",year=y,perspective="all",tco2e=15,source_id="DEMO",boundary="All") for y in range(2030,2034)]
        self.assertEqual(total_for(calculate(s),"Mobilitet och transport"),20000)
        s.project.transport_scope="all"
        self.assertEqual(total_for(calculate(s),"Mobilitet och transport"),60000)

    def test_missing_transport_year_is_blocking(self):
        s=demonstration();s.transport=[x for x in s.transport if x.year!=2032]
        r=calculate(s)
        self.assertIsNone(total_for(r,"Mobilitet och transport"))
        self.assertTrue(any("2032" in x["message"] for x in r.issues))

    def test_land_area_and_unique_ids(self):
        s=demonstration();s.lands[0].area_m2=1999
        self.assertIsNone(total_for(calculate(s),"Förändrad markanvändning"))
        s.project.land_mode="changed"
        self.assertIsNotNone(total_for(calculate(s),"Förändrad markanvändning"))
        s.lands.append(s.lands[0])
        with self.assertRaises(ValidationError):load_scenario(scenario_json(s))

    def test_reference_does_not_change_project_inventory(self):
        s=demonstration();r=calculate(s)
        next(f for f in s.factors if f.id=="land_reference").value=-100
        rr=calculate(s)
        self.assertEqual(r.total_kg,rr.total_kg)
        self.assertNotEqual(sum(x["kgco2e"] for x in r.ledger if x["view"]=="Referensmark"),sum(x["kgco2e"] for x in rr.ledger if x["view"]=="Referensmark"))

    def test_removal_eligibility_and_epd_checks(self):
        for field in ("eligibility_confirmed","epd_already_includes_storage"):
            s=demonstration();setattr(s.removals[0],field,field=="epd_already_includes_storage")
            self.assertIsNone(calculate(s).total_kg)

    def test_timber_storage_not_automatic_removal(self):
        s=demonstration();x=s.removals[0];x.kind="timber";x.include_in_total=False;x.unit="m3"
        next(f for f in s.factors if f.id=="biochar").unit="kgCO2e/m3"
        r=calculate(s)
        self.assertEqual(total_for(r,"Negativa utsläpp"),-500)
        self.assertTrue(any(x["view"]=="Kollager" for x in r.ledger))
        x.include_in_total=True
        self.assertIsNone(calculate(s).total_kg)

    def test_release_reverses_storage(self):
        s=demonstration();s.removals[0].release_year=2033
        self.assertEqual(total_for(calculate(s),"Negativa utsläpp"),-500+100)

    def test_cohort_period_and_physical_population_are_separate(self):
        s=demonstration();s.project.time_mode="cohort";s.project.operating_years=2;s.project.transport_scope="excluded"
        r=calculate(s)
        self.assertEqual(r.person_years,40)
        y=next(x for x in r.population if x["year"]==2033)
        self.assertEqual(y["physical_population"],20)
        self.assertEqual(y["reporting_population"],0)
        self.assertAlmostEqual(total_for(r,"Negativa utsläpp"),-500-1700) # Mark använder gemensam kalenderperiod.

    def test_linear_occupation_annual_midpoint(self):
        s=demonstration();s.project.build_end_year=2030;s.project.occupation="linear"
        r=calculate(s)
        values={x["year"]:x["reporting_population"] for x in r.population}
        self.assertEqual(values[2029],5)
        self.assertEqual(values[2030],15)
        self.assertEqual(values[2031],20)

    def test_explicit_category_exclusion(self):
        s=demonstration();s.enabled["Energi"]=False;s.programme[0].electricity_specific=None
        r=calculate(s)
        self.assertIsNotNone(r.total_kg)
        self.assertEqual(next(x for x in r.categories if x["category"]=="Energi")["status"],"Exkluderad")

    def test_roundtrip_and_export_digest(self):
        s=demonstration();raw=scenario_json(s);r=calculate(s)
        self.assertEqual(load_scenario(raw).model_dump(),s.model_dump())
        with zipfile.ZipFile(io.BytesIO(result_zip(s,r))) as z:
            meta=json.loads(z.read("metadata.json"))
            self.assertEqual(meta["scenario_sha256"],hashlib.sha256(z.read("scenario.json")).hexdigest())
            self.assertEqual(meta["total_kgco2e"],r.total_kg)
        self.assertTrue(any(x["parameter"]=="constant.CO2_per_C" for x in parameter_audit(s)))

    def test_csv_import_zero_swedish_decimal_and_malformed(self):
        raw="year;perspective;tco2e;source_id;boundary\n2030;residents;0;USER;Test\n2031;all;1,5;USER;Test\n".encode()
        rows=transport_csv(raw);self.assertEqual(rows[0].tco2e,0);self.assertEqual(rows[1].tco2e,1.5)
        for content in (b"",b"a,b\n1,2",b"year;perspective;tco2e;source_id;boundary\n2030;residents;;USER;Test\n"):
            with self.subTest(content=content),self.assertRaises(ValueError):transport_csv(content)

    def test_schema_rejects_unknown_and_nonfinite_input(self):
        s=demonstration().model_dump();s["unexpected"]=1
        with self.assertRaises(ValidationError):load_scenario(json.dumps(s).encode())
        s=demonstration().model_dump();s["project"]["total_bta_override"]=float("nan")
        with self.assertRaises(ValidationError):load_scenario(json.dumps(s).encode())

    def test_forest_growth_stops_at_carbon_capacity(self):
        s=demonstration();l=s.lands[0];l.flow_mode="forest";l.growth_m3_ha_year=6
        l.expansion_factor_id="bef";l.wood_density_factor_id="rho";l.carbon_fraction_factor_id="cf";l.biomass_capacity_factor_id="cap"
        s.factors += [Factor(id=i,name=i,value=v,unit=u,source_id="DEMO") for i,v,u in [("bef",1.4,"ratio"),("rho",400,"kg/m3"),("cf",.5,"ratio"),("cap",.3,"kgC/m2")]]
        r=calculate(s)
        forest=[x for x in r.ledger if x["submodule"]=="Skogstillväxt"]
        self.assertAlmostEqual(sum(x["kgco2e"] for x in forest),-(.3-.1)*2000*44/12)
        self.assertEqual(forest[-1]["kgco2e"],0)

    def test_source_and_overlap_validation(self):
        s=demonstration();s.project.source_id="MISSING"
        self.assertIsNone(calculate(s).total_kg)
        s=demonstration();s.transport[0].includes_construction=True
        self.assertIsNone(calculate(s).total_kg)
        s=demonstration();s.consumption[0].overlaps_energy_transport=True
        self.assertIsNone(calculate(s).total_kg)

    def test_duplicate_transport_aggregate_and_phase_rows(self):
        s=demonstration();row=s.transport[0].model_copy(deep=True);row.id="DUP";row.phase_id="E1";s.transport.append(row)
        self.assertIsNone(calculate(s).total_kg)

    def test_phase_population_overrides_replace_project_estimate(self):
        s=demonstration();s.project.phasing_enabled=True;s.project.population_level="phase"
        s.phases[0].population_override=100
        self.assertEqual(calculate(s).full_population,100)
        s.phases[0].population_override=None
        self.assertIsNone(calculate(s).full_population)

    def test_forest_history_is_carried_into_reporting_window(self):
        s=demonstration();l=s.lands[0];l.flow_mode="forest";l.change_year=2020;l.growth_m3_ha_year=6
        l.expansion_factor_id="bef";l.wood_density_factor_id="rho";l.carbon_fraction_factor_id="cf";l.biomass_capacity_factor_id="cap"
        s.factors += [Factor(id=i,name=i,value=v,unit=u,source_id="DEMO") for i,v,u in [("bef",1.4,"ratio"),("rho",400,"kg/m3"),("cf",.5,"ratio"),("cap",.3,"kgC/m2")]]
        r=calculate(s)
        self.assertEqual(sum(x["kgco2e"] for x in r.ledger if x["submodule"]=="Skogstillväxt"),0)

    def test_public_factor_requires_annual_person_method(self):
        from road2zero.schema import Consumption
        with self.assertRaises(ValidationError):
            Consumption(id="P",name="P",category="Offentliga investeringar",mode="total",unit="kg",quantity=100)


if __name__=="__main__":unittest.main()
