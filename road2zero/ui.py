"""Svenska inmatningskort och resultatvyer. Beräkningar finns bara i engine.py."""
from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pydantic import ValidationError

from . import __version__
from . import engine
from .engine import calculate, parameter_audit
from .io import csv_bytes, load_scenario, result_zip, scenario_json, transport_csv
from .methods import METHODS
from .schema import (CATEGORIES, Activity, Programme, Consumption, Curve, CurvePoint, Factor,
                     Land, Phase, Project, Removal, Scenario, Source, Transport)
from .seeds import demonstration, jagersro

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "id":"Unikt ID", "name":"Namn", "source_id":"Källa för objektets uppgifter", "phase_id":"Etapp", "note":"Kommentar / avgränsning",
    "start":"Byggstart", "end":"Byggslut", "share":"Andel av projektets invånare/BTA (0–1)",
    "population_override":"Eget antal invånare (tomt = skattning på projektnivå)",
    "status":"Status", "kind":"Typ", "material":"Stommaterial", "residential":"Bostäder – ingår i befolkning", "bta_m2":"Egen BTA (m²; ersätter projektandel)",
    "project_bta_share":"Andel av projektets bostads-BTA (0–1)", "bya_m2":"BYA (m²; dokumentation)", "homes":"Antal bostäder", "construction_factor_id":"Byggnadsfaktor (kg CO₂e/m² BTA)",
    "construction_total_kg":"Egen byggskedestotal (kg CO₂e; ersätter BTA × faktor)", "energy_mode":"Energiberäkning", "energy_class":"Energiklass (metadata)",
    "atemp_m2":"Egen Atemp (m²)", "atemp_ratio_factor_id":"Atemp/BTA-schablon om egen Atemp saknas", "electricity_specific":"El (kWh/m² Atemp/år)",
    "heat_specific":"Värme (kWh/m² Atemp/år)", "electricity_annual":"El vid full drift (kWh/år)", "heat_annual":"Värme vid full drift (kWh/år)",
    "electricity_factor_id":"Elmix, faktor eller årskurva", "heat_factor_id":"Värme, faktor eller årskurva", "solar_kwh_year":"Solel vid full drift (kWh/år; 0 om ingen)",
    "solar_self_use":"Egenanvänd andel solel (0–1)", "piling":"Pålning", "piling_factor_id":"Pålningsfaktor (kg CO₂e/m² BTA)",
    "sheet_piling":"Spontning", "sheet_area_m2":"Spontyta (m²)", "sheet_factor_id":"Spontfaktor (kg CO₂e/m² spont)",
    "submodule":"Submodul", "land_id":"Länk till mark-ID (ingen dubbel areabokföring)", "quantity":"Mängd", "unit":"Enhet", "factor_id":"Faktor", "total_kg":"Egen total för aktivitetsraden (kg CO₂e)",
    "area_m2":"Area (m²)", "before":"Marktyp före", "after":"Marktyp efter", "soil":"Jordtyp", "change_year":"År för markförändring", "release_years":"Antal år som lagerförlusten fördelas över",
    "soc_factor_id":"SOC före (kg C/m²)", "dom_factor_id":"Dött organiskt material före (kg C/m²)", "biomass_factor_id":"Biomassa före (kg C/m²)",
    "keep_soc":"Bevarad SOC-andel (0–1)", "keep_dom":"Bevarad DOM-andel (0–1)", "keep_biomass":"Bevarad biomassaandel (0–1)",
    "after_flow_factor_id":"Nettoflöde efter förändring (kg CO₂e/m²/år)", "reference_flow_factor_id":"Referensmarkens nettoflöde (kg CO₂e/m²/år)",
    "flow_mode":"Markens fortsatta kolflöde", "growth_m3_ha_year":"Skogstillväxt (m³sk/ha/år)", "expansion_factor_id":"Biomass expansion factor (ratio)",
    "wood_density_factor_id":"Torr veddensitet (kg/m³)", "carbon_fraction_factor_id":"Kolfraktion (ratio)", "biomass_capacity_factor_id":"Maximalt biomassakollager (kg C/m²)",
    "category":"Klimatkategori", "mode":"Inmatningssätt", "coverage":"Andel av befolkning/mängd (0–1)", "overlaps_energy_transport":"Underlaget överlappar energi/transport (måste lösas)",
    "share_bta":"Andel av projektets totala nybyggda BTA (0–1)",
    "year":"År", "end_year":"Slutår för årligt trädupptag", "release_year":"År för full återföring av kol (valfritt)", "lifecycle_kg":"Åtgärdens livscykelutsläpp (kg CO₂e; 0 kräver underlag)",
    "include_in_total":"Räkna avdrag och åtgärdsutsläpp i totalen", "eligibility_confirmed":"Varaktighet, additionalitet, ägande och avgränsning är dokumenterade",
    "epd_already_includes_storage":"Kolinlagringen ingår redan i EPD/annan byggnadsfaktor", "value":"Värde (tomt = saknas)", "locator":"Sida, tabell, cell eller datapost",
    "quality":"Källstatus", "boundary":"Systemgräns, moduler och GWP-version", "reference_year":"Referensår", "annual_change":"Årlig förändring (−0,02 = −2 %)",
    "curve_id":"Årskurva (ersätter konstant/förändring)", "uncertainty_pct":"Angiven osäkerhet ± % (metadata)", "title":"Titel", "author":"Författare / organisation", "url":"Länk", "tail":"Utanför kurvans intervall",
    "perspective":"Transportperspektiv", "tco2e":"Årliga ton CO₂e (redan beräknade i Vägvis)", "includes_building_electricity":"Inkluderar el som också finns under byggnad",
    "includes_construction":"Inkluderar redan räknade byggtransporter",
}
CHOICES = {
    "status":{"planned":"Planerad", "existing":"Befintlig"}, "energy_mode":{"area":"Specifika värden × Atemp", "annual":"Årsmängder direkt", "excluded":"Exkludera objektets driftenergi"},
    "piling":{"unknown":"Ej utrett", "yes":"Ja", "no":"Nej"}, "sheet_piling":{"unknown":"Ej utrett", "yes":"Ja", "no":"Nej"},
    "mode":{"person":"Faktor per invånare och år", "quantity":"Mängd per invånare och år", "total":"Total mängd per år"},
    "flow_mode":{"factor":"Dokumenterat årligt nettoflöde", "forest":"Förenklad skogstillväxt med kapacitet"},
    "tail":{"error":"Kräv data för hela perioden", "hold":"Behåll närmaste ändvärde"},
    "perspective":{"residents":"Boendes resor", "all":"All trafik i underlaget"},
}
PROGRAMME_GROUPS = {
    "Programandel och egenskaper":["id","name","share_bta","kind","material","residential","source_id"],
    "Byggskede":["construction_factor_id","construction_total_kg"],
    "Driftenergi":["energy_mode","energy_class","atemp_m2","atemp_ratio_factor_id","electricity_specific","heat_specific","electricity_annual","heat_annual","electricity_factor_id","heat_factor_id","solar_kwh_year","solar_self_use"],
    "Grundläggning → Anläggning":["piling","piling_factor_id","sheet_piling","sheet_area_m2","sheet_factor_id"],
    "Kommentar":["note"],
}
LAND_GROUPS = {
    "Markpost":["id","name","source_id","area_m2","before","after","soil","change_year","release_years"],
    "Kolpooler och bevarande":["soc_factor_id","keep_soc","dom_factor_id","keep_dom","biomass_factor_id","keep_biomass"],
    "Fortsatt flöde och referens":["flow_mode","after_flow_factor_id","reference_flow_factor_id"],
    "Förenklad skogstillväxt":["growth_m3_ha_year","expansion_factor_id","wood_density_factor_id","carbon_fraction_factor_id","biomass_capacity_factor_id"],
    "Kommentar":["note"],
}


def nice(value, digits=0):
    return "Saknas" if value is None else f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def install_scenario(s):
    st.session_state.scenario = s.model_dump()
    st.session_state.generation = uuid4().hex[:8]


def save_scenario(s):
    # Korsvalidera hela objektet innan det ersätter det aktuella scenariot.
    install_scenario(Scenario.model_validate(s.model_dump()))
    st.rerun()


def widget(key, field, value, model_field, s, record):
    label = LABELS.get(field, field)
    anno = str(model_field.annotation)
    if field == "id":
        return st.text_input(label, value=value, key=key, disabled=True)
    options = None
    display = CHOICES.get(field, {})
    if field == "source_id":
        options = [x.id for x in s.sources]
        display = {x.id:f"{x.id} · {x.title}" for x in s.sources}
    elif field == "phase_id":
        options = ([""] if isinstance(record, Transport) else []) + [x.id for x in s.phases]
        display = {x.id:f"{x.id} · {x.name}" for x in s.phases}
    elif field == "land_id":
        options = [""] + [x.id for x in s.lands]
    elif field == "curve_id":
        options = [""] + [x.id for x in s.curves]
    elif field.endswith("factor_id"):
        options = [""] + [x.id for x in s.factors]
        display = {x.id:f"{x.name} · {x.value if x.value is not None else 'saknas'} {x.unit} [{x.id}]" for x in s.factors}
    elif "Literal" in anno:
        from typing import get_args
        options = list(get_args(model_field.annotation))
    elif field == "kind" and isinstance(record, Programme):
        options = ["Bostäder, blandad typ","Flerbostadshus","Småhus","Kontor","Handel","Skola","Förskola","Vård","Mobilitetshus","Underjordisk parkering","Industri","Övrig byggnad"]
    elif field == "material":
        options = ["Ej valt","Generisk","Betong","Trä","Stål","Klimatförbättrad betong","Klimatförbättrat trä","Klimatförbättrat stål"]
    elif field == "energy_class":
        options = ["Ej valt","A","B","C","D","E","F","G","Ouppvärmd"]
    elif field in ("before","after"):
        options = ["Ej klassificerad","Bebyggd mark","Hårdgjord mark","Gräsmark","Park","Skog","Odlingsmark","Våtmark","Övrig naturmark"]
    elif field == "soil":
        options = ["Ej utrett","Mineraljord","Organisk jord","Våtmark"]
    elif field == "submodule":
        options = ["Ytbeläggning","Grundläggning","Masshantering","Masstransport","Marksanering","Ledningar","Rivning","Återbruk","Övrig anläggning"]
    if options is not None:
        if value not in options:
            options = [value] + options
        return st.selectbox(label, options, index=options.index(value), key=key, format_func=lambda v:display.get(v, v or "Välj / ingen"))
    if model_field.annotation is bool:
        return st.checkbox(label, value=value, key=key)
    if "float" in anno or "int" in anno:
        integer = "int" in anno and "float" not in anno
        opts = dict(value=int(value) if integer and value is not None else float(value) if value is not None else None,
                    step=1 if integer else .01, key=key)
        # Pydantic ger de auktoritativa gränserna när formuläret sparas.
        return st.number_input(label, **opts, placeholder="Ej angivet")
    if field in ("note","boundary"):
        return st.text_area(label, value=value or "", key=key, height=90)
    return st.text_input(label, value=str(value or ""), key=key)


def records_editor(s, attr, cls, groups=None, category=None):
    records = getattr(s,attr)
    shown = [x for x in records if category is None or getattr(x,"category",None)==category]
    prefix = f"{st.session_state.generation}-{attr}-{category or ''}"
    focus_key="focus-"+attr+str(category)
    ids=[x.id for x in shown]
    preferred=st.session_state.get(focus_key)
    selected = st.selectbox("Välj programandel" if cls is Programme else "Välj post", ids, index=ids.index(preferred) if preferred in ids else 0, format_func=lambda i: next((f"{x.name if hasattr(x,'name') else x.title if hasattr(x,'title') else x.id} · {i}" for x in shown if x.id==i),i), key=prefix+"pick") if shown else None
    if selected:st.session_state[focus_key]=selected
    c1,c2,c3 = st.columns(3)
    if c1.button("＋ Lägg till",key=prefix+"add",use_container_width=True):
        data = dict(id=attr[:2].upper()+"-"+uuid4().hex[:6], source_id="USER")
        fields = cls.model_fields
        if "name" in fields: data["name"]="Ny post"
        if "phase_id" in fields: data["phase_id"]=s.phases[0].id if s.phases else ""
        if cls is Phase: data.update(start=s.project.start_year,end=s.project.start_year,share=0)
        if cls is Consumption: data["category"]=category or "Matkonsumtion"
        if cls is Programme:data["share_bta"]=0
        if cls is Factor: data.update(unit="kgCO2e/m2")
        if cls is Source: data.update(title="Ny källa",source_id=None);data.pop("source_id")
        if cls is Curve: data.update(unit="gCO2e/kWh")
        if cls is Transport: data.update(year=s.project.start_year,perspective="residents",tco2e=0)
        records.append(cls.model_validate(data))
        st.session_state[focus_key]=data["id"]
        save_scenario(s)
    obj = next((x for x in shown if x.id==selected), None)
    if obj is None:
        st.info("Lägg till en post eller läs in ett scenario. Tomma mängder behandlas som saknat underlag.")
        return
    if c2.button("Duplicera",key=prefix+"copy",use_container_width=True):
        data = obj.model_dump();data["id"]=attr[:2].upper()+"-"+uuid4().hex[:6]
        if "name" in data: data["name"]+=" – kopia"
        records.append(cls.model_validate(data));st.session_state[focus_key]=data["id"];save_scenario(s)
    if c3.button("Ta bort post",key=prefix+"remove",use_container_width=True):
        setattr(s,attr,[x for x in records if x.id!=selected]);save_scenario(s)
    groups = groups or {"Uppgifter": [f for f in cls.model_fields if f not in ("points",)]}
    data = obj.model_dump()
    with st.form(prefix+obj.id+"form",border=True):
        for i,(heading,fields) in enumerate(groups.items()):
            with st.expander(heading, expanded=i==0 or len(groups)==1):
                cols=st.columns(2)
                for j,f in enumerate(fields):
                    with cols[j%2]:
                        data[f]=widget(prefix+obj.id+f,f,data[f],cls.model_fields[f],s,obj)
        if cls is Curve:
            points=st.data_editor(pd.DataFrame(obj.model_dump()["points"],columns=["year","value"]).astype({"year":"Int64","value":"float64"}),num_rows="dynamic",hide_index=True,key=prefix+obj.id+"points",use_container_width=True,column_config={"year":st.column_config.NumberColumn("År",format="%d"),"value":st.column_config.NumberColumn("Faktorvärde")})
            data["points"]=clean_rows(points)
        submitted=st.form_submit_button("Spara ändringar",type="primary",use_container_width=True)
    if submitted:
        try:
            updated=cls.model_validate(data)
            setattr(s,attr,[updated if x.id==selected else x for x in records])
            save_scenario(s)
        except (ValidationError,ValueError) as e: st.error(str(e))


def clean_rows(df):
    return json.loads(df.to_json(orient="records"))


def project_inputs(s,r):
    p=s.project
    st.subheader("Projektets omfattning och tid")
    st.caption("Fälten sparas tillsammans. Egen BTA och egna invånare ersätter skattningar; 0 är en giltig egen uppgift.")
    with st.form("project-"+st.session_state.generation):
        a,b=st.columns(2)
        data=p.model_dump()
        with a:
            data["name"]=st.text_input("Scenarionamn",p.name)
            data["id"]=st.text_input("Scenario-ID",p.id)
            data["homes"]=st.number_input("Bostäder inom projektets avgränsning",min_value=0,value=p.homes,step=1)
            data["area_m2"]=st.number_input("Total projektarea (m²)",min_value=0.,value=p.area_m2)
            data["total_bta_override"]=st.number_input("Total nybyggd BTA (m²; tomt = preliminär skattning)",min_value=0.,value=p.total_bta_override)
            st.caption("En enda total för hela byggperioden. Fördelning mellan bostäder och lokaler görs som andelar av denna BTA, utan uppgifter per byggnad.")
            data["bta_per_home_factor_id"]=widget("proj-bta-"+st.session_state.generation,"factor_id",p.bta_per_home_factor_id,Factor.model_fields["id"],s,p)
            levels=["project","phase"]
            data["population_level"]=st.selectbox("Invånare anges på nivå",levels,index=levels.index(p.population_level),format_func=lambda x:{"project":"Projekt","phase":"Etapp (kräver etappindelning)"}[x])
            data["population_method"]=st.selectbox("Skatta invånare från",["homes","bta"],index=["homes","bta"].index(p.population_method),format_func=lambda x:{"homes":"Antal bostäder","bta":"Bostads-BTA"}[x])
            data["population_override"]=st.number_input("Eget antal invånare för projektet",min_value=0.,value=p.population_override)
            data["people_per_home_factor_id"]=widget("proj-pers-"+st.session_state.generation,"factor_id",p.people_per_home_factor_id,Factor.model_fields["id"],s,p)
            data["bta_per_person_factor_id"]=widget("proj-mpers-"+st.session_state.generation,"factor_id",p.bta_per_person_factor_id,Factor.model_fields["id"],s,p)
        with b:
            data["build_start_year"]=st.number_input("Byggperiodens startår",min_value=1900,max_value=2200,value=p.build_start_year,step=1)
            data["build_end_year"]=st.number_input("Byggperiodens slutår",min_value=1900,max_value=2200,value=p.build_end_year,step=1)
            data["phasing_enabled"]=st.checkbox("Fördela total BTA mellan etapper",value=p.phasing_enabled)
            data["start_year"]=st.number_input("Gemensamt startår",min_value=1900,max_value=2200,value=p.start_year,step=1)
            data["end_year"]=st.number_input("Gemensamt slutår, inklusive",min_value=1900,max_value=2300,value=p.end_year,step=1)
            data["time_mode"]=st.selectbox("Redovisningsperiod",["calendar","cohort"],index=["calendar","cohort"].index(p.time_mode),format_func=lambda x:{"calendar":"Gemensam kalenderperiod","cohort":"Byggtid + driftår per etapp"}[x])
            data["operating_years"]=st.number_input("Hela driftår efter varje etapps byggslut",min_value=1,max_value=100,value=p.operating_years,step=1)
            data["occupation"]=st.selectbox("Inflyttning/driftstart",["linear","after"],index=["linear","after"].index(p.occupation),format_func=lambda x:{"linear":"Linjärt under byggtiden (årsmedel)","after":"Från året efter byggslut"}[x])
            data["land_mode"]=st.selectbox("Markregistrets omfattning",["full","changed"],index=["full","changed"].index(p.land_mode),format_func=lambda x:{"full":"Hela projektarean inklusive bevarad mark","changed":"Enbart förändrade/åtgärdade areor"}[x])
            data["land_reference"]=st.text_area("Referens för fortsatt markanvändning",p.land_reference)
            data["source_id"]=widget("proj-source-"+st.session_state.generation,"source_id",p.source_id,Project.model_fields["source_id"],s,p)
            data["note"]=st.text_area("Projektets antaganden och systemgräns",p.note,height=130)
        if st.form_submit_button("Spara projekt",type="primary",use_container_width=True):
            try:
                s.project=Project.model_validate(data)
                for k,v in data.items():
                    if v != p.model_dump().get(k):s.parameter_sources[f"project.{k}"]=data["source_id"]
                save_scenario(s)
            except ValueError as e: st.error(str(e))
    a,b,c=st.columns(3)
    a.metric("Aktiv total nybyggd BTA",nice(r.project_bta)+" m²")
    b.metric("Skattade invånare",nice(r.estimated_population))
    c.metric("Aktiva invånare vid full utbyggnad",nice(r.full_population))
    st.subheader("Byggperiod och eventuell etappfördelning")
    st.caption("Utan etappindelning fördelas den totala BTA:n jämnt över den valda byggperioden. Med etapper fördelas samma total med etappernas andelar; inga byggnadsobjekt behövs.")
    if not p.phasing_enabled:
        st.info(f"All nybyggd BTA fördelas över {p.build_start_year}–{p.build_end_year}. Aktivera etapper ovan om du vill ange flera delperioder.")
    with st.expander("Etapptabell (används bara när etappindelning är aktiverad)",expanded=p.phasing_enabled), st.form("phase-table-"+st.session_state.generation):
        df=pd.DataFrame([p.model_dump() for p in s.phases],columns=list(Phase.model_fields))
        for col in ("share","population_override"): df[col]=pd.to_numeric(df[col]).astype(float)
        edited=st.data_editor(df,num_rows="dynamic",hide_index=True,use_container_width=True,key="phases-"+st.session_state.generation,column_config={
            "id":st.column_config.TextColumn("Etapp-ID",required=True),"name":"Namn", "start":st.column_config.NumberColumn("Byggstart",format="%d"),
            "end":st.column_config.NumberColumn("Byggslut",format="%d"),"share":st.column_config.NumberColumn("Andel (0–1)",min_value=0,max_value=1,format="%.4f"),
            "population_override":st.column_config.NumberColumn("Invånare, etappnivå",min_value=0),"source_id":st.column_config.SelectboxColumn("Källa",options=[x.id for x in s.sources])})
        if st.form_submit_button("Spara etapper"):
            try: s.phases=[Phase.model_validate(x) for x in clean_rows(edited)];save_scenario(s)
            except ValueError as e: st.error(str(e))
    st.subheader("Klimatkategorier som ingår")
    with st.form("enabled-"+st.session_state.generation):
        cols=st.columns(3)
        enabled={}
        for i,cat in enumerate(CATEGORIES):
            with cols[i%3]: enabled[cat]=st.checkbox(cat,s.enabled[cat])
        st.caption("Exkluderade klimatkategorier redovisas som exkluderade. Det ändrar omfattningen för totalen.")
        if st.form_submit_button("Spara omfattning"): s.enabled=enabled;save_scenario(s)


def consumption_inputs(s,category):
    st.subheader(category)
    st.caption("Välj mängder per invånare, en faktor per invånare eller totala årsmängder. Mängdbaserad mat anges i kg/person/år. Faktorer och källor väljs per grupp.")
    if category=="Offentliga investeringar": st.info("Den årliga invånarfaktorn ska anges i ton CO₂e/invånare/år. Avgränsa mot offentliga byggnader och anläggningar som redan räknas explicit.")
    rows=[x for x in s.consumption if x.category==category]
    with st.expander("Snabbinmatning för alla grupper",expanded=True):
        with st.form("cons-table-"+category+st.session_state.generation):
            cols=["id","name","mode","quantity","unit","coverage","factor_id","source_id","overlaps_energy_transport","note"]
            if category=="Offentliga investeringar":cols=[x for x in cols if x not in ("mode","quantity","unit")]
            df=pd.DataFrame([x.model_dump() for x in rows],columns=cols)
            for c in ("quantity","coverage"):
                if c in df:df[c]=pd.to_numeric(df[c]).astype(float)
            ed=st.data_editor(df,num_rows="dynamic",hide_index=True,use_container_width=True,key="ct-"+category+st.session_state.generation,column_config={
                "id":st.column_config.TextColumn("Unikt ID",required=True),"name":"Livsmedelsgrupp / delpost","mode":st.column_config.SelectboxColumn("Metod",options=["person","quantity","total"]),
                "quantity":st.column_config.NumberColumn("Mängd/person/år eller totalt/år",min_value=0),"unit":st.column_config.SelectboxColumn("Enhet",options=["person/year","kg","SEK","st","kWh"]),
                "coverage":st.column_config.NumberColumn("Andel (0–1)",min_value=0,max_value=1),"factor_id":st.column_config.SelectboxColumn("Faktor-ID",options=[x.id for x in s.factors]),
                "source_id":st.column_config.SelectboxColumn("Källa",options=[x.id for x in s.sources]),"overlaps_energy_transport":"Överlapp kvarstår","note":"Kommentar"})
            st.caption("person = faktor per invånare; quantity = mängd per invånare; total = hela projektets årsmängd. Total kräver gemensam kalenderperiod. För person används enheten person/year.")
            if st.form_submit_button("Spara grupper",type="primary"):
                try:
                    updated=[Consumption.model_validate({**x,"category":category}) for x in clean_rows(ed)]
                    s.consumption=[x for x in s.consumption if x.category!=category]+updated;save_scenario(s)
                except ValueError as e:st.error(str(e))
    with st.expander("Detaljerat kort / duplicera grupp"):
        public_groups={"Årlig invånarfaktor":["id","name","factor_id","coverage","source_id","overlaps_energy_transport","note"]} if category=="Offentliga investeringar" else None
        records_editor(s,"consumption",Consumption,groups=public_groups,category=category)
    if category=="Matkonsumtion":
        st.warning("Äldre Jägersroparametrar har delvis oklara enhetsnamn. De har inte förts över som verifierade SMT-värden. Råparametrarna följer med i data/legacy_jagersro_parameters.csv för granskning.")
    if category=="Övrig konsumtion":st.info("Använd grupper som kläder/skor, fritid och övriga varor/tjänster med avgränsning mot mat, energi, boendeinvesteringar och resor. Samma konsumtion ska bara ingå en gång.")


def transport_inputs(s):
    st.subheader("Mobilitet och transport · Vägvis")
    scope=["unset","residents","all","excluded"]
    labels={"unset":"Välj vad som ska ingå", "residents":"Boendes resor", "all":"All trafik i underlaget", "excluded":"Exkludera transport från totalen"}
    with st.form("transport-scope-"+st.session_state.generation):
        chosen=st.selectbox("Perspektiv i projektets total",scope,index=scope.index(s.project.transport_scope),format_func=lambda x:labels[x])
        st.caption("Att växla diagramvy ändrar inte detta val. Importerade årsvärden multipliceras inte med invånare igen.")
        if st.form_submit_button("Spara transportperspektiv"):s.project.transport_scope=chosen;save_scenario(s)
    template=[dict(id="VAG-E1-2029",year=2029,perspective="residents",phase_id="E1",tco2e="",source_id="VAGVIS",boundary="Beskriv fordon, resor, LCA och GWP-version",includes_building_electricity=False,includes_construction=False)]
    st.download_button("Hämta CSV-mall",csv_bytes(template),"vagvis_importmall.csv",mime="text/csv")
    uploaded=st.file_uploader("Läs in CSV med Vägvis-resultat",type=["csv"],key="vagfile")
    if uploaded:
        try:
            rows=transport_csv(uploaded.getvalue())
            st.dataframe(pd.DataFrame([x.model_dump() for x in rows]),hide_index=True,use_container_width=True)
            st.caption("Importen ersätter hela transporttabellen i det aktiva scenariot. Originalfilen påverkas inte.")
            if st.button("Använd importerade årsvärden",type="primary"):s.transport=rows;save_scenario(s)
        except ValueError as e: st.error(str(e))
    if s.transport:
        st.dataframe(pd.DataFrame([x.model_dump() for x in s.transport]),hide_index=True,use_container_width=True)
    with st.expander("Lägg till eller ändra en årspost"):
        records_editor(s,"transport",Transport)


def inputs(s,r):
    modules=["Projekt och byggperiod","Byggd BTA och energi","Anläggning","Förändrad markanvändning","Mobilitet och transport","Matkonsumtion","Övrig konsumtion","Offentliga investeringar","Negativa utsläpp"]
    module=st.selectbox("Välj inmatningsmodul",modules,key="input-module")
    st.caption("1. Ange mängder och etapper  ·  2. Välj faktorer och källor  ·  3. Granska dataluckor och resultat")
    if module==modules[0]:project_inputs(s,r)
    elif module==modules[1]:
        st.subheader("Total nybyggd BTA och energi")
        st.metric("BTA under vald byggperiod",nice(r.project_bta)+" m²")
        with st.form("quick-bta-"+st.session_state.generation):
            a,b,c=st.columns(3)
            value=a.number_input("Total BTA att bygga (m²)",min_value=0.,value=s.project.total_bta_override,placeholder="Tomt = bostadsskattning")
            begin=b.number_input("Byggperiod start",min_value=1900,max_value=2200,value=s.project.build_start_year,step=1)
            end=c.number_input("Byggperiod slut",min_value=1900,max_value=2200,value=s.project.build_end_year,step=1)
            if st.form_submit_button("Spara BTA och byggperiod",type="primary"):
                try:
                    old=s.project.model_dump()
                    s.project=Project.model_validate({**s.project.model_dump(),"total_bta_override":value,"build_start_year":begin,"build_end_year":end})
                    for k in ("total_bta_override","build_start_year","build_end_year"):
                        if getattr(s.project,k)!=old[k]:s.parameter_sources[f"project.{k}"]="USER"
                    save_scenario(s)
                except ValueError as e:st.error(str(e))
        st.caption(f"Byggperiod {s.project.build_start_year}–{s.project.build_end_year}. Ingen inmatning för enskilda byggnader används.")
        st.info("En programrad kan omfatta hela BTA:n (andel 1). Vid behov delas den upp i andelar för exempelvis bostäder och lokaler med olika material- och energifaktorer. Andelarna ska summera till 1. Alla mängder nedan avser respektive programandel under hela byggperioden.")
        if s.programme:
            st.dataframe(pd.DataFrame([{"Programandel":b.name,"Andel":b.share_bta,"Nybyggd BTA m²":r.project_bta*b.share_bta if r.project_bta is not None else None,"Typ":b.kind,"Stomme":b.material,"Källa":b.source_id} for b in s.programme]),hide_index=True,use_container_width=True)
        st.caption("Egen Atemp, solel, spontyta och eventuella årsmängder avser hela programandelen vid full utbyggnad. Etappandelarna sköter fördelningen i tid. Byggnad och Energi redovisas separat.")
        records_editor(s,"programme",Programme,PROGRAMME_GROUPS)
    elif module==modules[2]:
        st.subheader("Anläggning")
        st.info("Pålning och spontning från BTA-programmets andelar bokförs automatiskt här. Aktivitetsrader länkar till mark-ID utan att markens kol räknas igen.")
        with st.expander("Mängdhjälp för masstransport"):
            a,b,c=st.columns(3)
            volume=a.number_input("Massor (m³)",min_value=0.,value=None)
            density=b.number_input("Densitet (ton/m³)",min_value=0.,value=None)
            distance=c.number_input("Transportavstånd (km)",min_value=0.,value=None)
            if all(x is not None for x in (volume,density,distance)):
                qty=volume*density*distance;st.metric("Beräknad transportmängd",nice(qty,1)+" tkm")
                if st.button("Lägg till denna masstransport"):
                    s.activities.append(Activity(id="A-"+uuid4().hex[:6],name="Masstransport",phase_id=s.phases[0].id if s.phases else "",submodule="Masstransport",quantity=qty,unit="tkm",note=f"{volume} m³ × {density} ton/m³ × {distance} km; källa för mängder/densitet ska kompletteras."));save_scenario(s)
        records_editor(s,"activities",Activity)
    elif module==modules[3]:
        st.subheader("Förändrad markanvändning")
        area=sum(x.area_m2 or 0 for x in s.lands)
        a,b,c=st.columns(3);a.metric("Projektarea",nice(s.project.area_m2)+" m²");b.metric("Registrerad mark",nice(area)+" m²");c.metric("Areaskillnad",nice((s.project.area_m2-area) if s.project.area_m2 is not None else None)+" m²")
        st.info("Ange varje fysisk markarea en gång. Om hela projektarean registreras ska även bevarad och redan exploaterad mark ingå. Klassificering och kolfaktorer behövs även när areabalansen stämmer.")
        if s.project.land_mode=="changed":st.warning("Endast ändrade/åtgärdade areor ingår. Resterande mark ligger utanför markresultatet.")
        st.caption("Nettoflöde: positivt = utsläpp, negativt = upptag. Kontrollera att lagerförlust och årligt flöde avser olika processer. 0 % bevarande anges som 0 och 100 % som 1.")
        records_editor(s,"lands",Land,LAND_GROUPS)
    elif module==modules[4]:transport_inputs(s)
    elif module in modules[5:8]:consumption_inputs(s,module)
    else:
        st.subheader("Negativa utsläpp och temporära kollager")
        st.caption("biochar = biokol; timber = inbyggt virke; trees = trädens årliga upptag; other = övrigt dokumenterat upptag. Kolupptag från markregistret räknas där och förs automatiskt till klimatkategorin Negativa utsläpp.")
        st.info("Inbyggt virke visas som kollager. Det bokförs inte automatiskt som negativt utsläpp. Avdrag kräver dokumenterade kriterier och kontroll mot EPD och markmodulen.")
        records_editor(s,"removals",Removal)
    relevant=[x for x in r.issues if x["category"] in (["Byggnad","Energi","Anläggning"] if module==modules[1] else [module,"Projekt","Befolkning"] if module==modules[0] else [module])]
    if relevant:
        with st.expander(f"Kontroller att arbeta vidare med ({len(relevant)})",expanded=False):st.dataframe(pd.DataFrame(relevant),hide_index=True,use_container_width=True)


def results(s,r):
    st.subheader("Resultat med tydlig omfattning")
    if r.total_kg is None:
        st.warning("Projektets total är ännu inte beräkningsbar. Kända delposter visas för granskning; de är inte ett komplett klimatavtryck.")
    else:st.success("Alla obligatoriska indata inom vald omfattning är beräkningsbara. Källornas kvalitet behöver fortfarande bedömas separat.")
    a,b,c=st.columns(3)
    a.metric("Total inom vald omfattning (ton CO₂e)",nice(None if r.total_kg is None else r.total_kg/1000,1))
    b.metric("Känt delresultat (ton CO₂e)",nice(r.known_subtotal_kg/1000,1))
    c.metric("Invånarår inom perioden",nice(r.person_years))
    scoped=[x for x in r.ledger if x["in_total"]]
    if r.total_kg is not None:
        gross=sum(max(0,x["kgco2e"]) for x in scoped)/1000
        removal=-sum(min(0,x["kgco2e"]) for x in scoped)/1000
        st.caption(f"Positiva poster {nice(gross,1)} ton · negativa poster {nice(removal,1)} ton · netto {nice(r.total_kg/1000,1)} ton. Totalen gäller endast valda klimatkategorier och transportperspektiv.")
    summary=pd.DataFrame(r.categories).rename(columns={"category":"Klimatkategori","status":"Status","missing":"Dataluckor","kgco2e":"Resultat (ton CO₂e)","known_subtotal_kg":"Känt delresultat (ton CO₂e)"})
    for col in ("Resultat (ton CO₂e)","Känt delresultat (ton CO₂e)"):summary[col]=summary[col]/1000
    st.dataframe(summary.drop(columns=["enabled"]),hide_index=True,use_container_width=True)
    st.subheader("Årsvisa resultat")
    if scoped:
        df=pd.DataFrame(scoped)
        table=df.pivot_table(index="year",columns="category",values="kgco2e",aggfunc="sum")/1000
        st.caption("Tom cell betyder att ingen beräknad post finns. Datakontrollerna avgör om kategorin är komplett.")
        st.dataframe(table,use_container_width=True)
    st.subheader("Datakontroller och källstatus")
    if r.issues:
        st.dataframe(pd.DataFrame(r.issues).rename(columns={"category":"Klimatkategori","object_id":"Objekt / parameter","severity":"Nivå","message":"Kontroll"}),hide_index=True,use_container_width=True)
    else:st.info("Inga blockerande dataluckor upptäcktes inom vald omfattning.")
    if r.total_kg is not None and r.person_years and r.person_years>0:
        st.metric("Periodens netto per invånarår (ton CO₂e)",nice(r.total_kg/1000/r.person_years,3))
        st.caption("Engångsutsläpp ingår i periodens netto. Detta nyckeltal är inte samma sak som en enskild invånares årliga konsumtionsavtryck.")


def styled_chart(fig):
    fig.update_layout(font=dict(family="Arial",color="#173345"),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend_title_text="",margin=dict(l=20,r=20,t=45,b=25),colorway=["#008D86","#176D9C","#E3A338","#9C6DA5","#6B90A1","#B86B4D","#557C48","#344E6A","#72B6A1"])
    st.plotly_chart(fig,use_container_width=True)


def visuals(s,r):
    st.subheader("Utforska klimatpåverkan")
    if r.total_kg is None:st.warning("Diagram visar endast kända beräknade delposter. Dataluckor i resultaten måste lösas innan slutsatser om totalen dras.")
    active=pd.DataFrame([x for x in r.ledger if x["in_total"]])
    if not active.empty:
        active["ton CO₂e"]=active.kgco2e/1000
        summary=active.groupby("category",as_index=False)["ton CO₂e"].sum()
        styled_chart(px.bar(summary,x="ton CO₂e",y="category",orientation="h",color="category",labels={"category":"Klimatkategori"},title="Kända poster per klimatkategori"))
        yearly=active.groupby(["year","category"],as_index=False)["ton CO₂e"].sum()
        styled_chart(px.bar(yearly,x="year",y="ton CO₂e",color="category",barmode="relative",labels={"year":"Kalenderår","category":"Klimatkategori"},title="Årliga utsläpp och upptag"))
        cumulative=active.groupby("year",as_index=False)["ton CO₂e"].sum().sort_values("year")
        cumulative["Ackumulerat ton CO₂e"]=cumulative["ton CO₂e"].cumsum()
        styled_chart(px.line(cumulative,x="year",y="Ackumulerat ton CO₂e",labels={"year":"Kalenderår"},title="Ackumulerade kända poster"))
    else:st.info("Diagrammen fylls när de första kompletta aktivitetsraderna har beräknats. Välj demo i sidopanelen för att prova alla vyer.")
    if r.full_population is not None:
        pop=pd.DataFrame(r.population).rename(columns={"physical_population":"Fysisk befolkning","reporting_population":"Inom redovisningsperioden"})
        styled_chart(px.line(pop,x="year",y=["Fysisk befolkning","Inom redovisningsperioden"],labels={"year":"Kalenderår","value":"Invånare"},title="Etapper och befolkning"))
    st.subheader("Transport · separata perspektiv")
    view=st.radio("Visa transportperspektiv",["residents","all"],format_func=lambda x:CHOICES["perspective"][x],horizontal=True)
    rows=[x for x in r.ledger if x["category"]=="Mobilitet och transport" and x["view"]==view]
    if rows:
        df=pd.DataFrame(rows);df["ton CO₂e"]=df.kgco2e/1000
        styled_chart(px.bar(df,x="year",y="ton CO₂e",labels={"year":"År"},title=CHOICES["perspective"][view]))
    else:st.caption("Inga beräknade årsvärden för detta perspektiv.")
    st.subheader("Mark · projekt jämfört med fortsatt markanvändning")
    landrows=[x for x in r.ledger if x["record_type"]=="Land" and x["view"] in ("Projekt","Referensmark")]
    if landrows:
        df=pd.DataFrame(landrows);df["ton CO₂e"]=df.kgco2e/1000
        styled_chart(px.line(df.groupby(["year","view"],as_index=False)["ton CO₂e"].sum(),x="year",y="ton CO₂e",color="view",labels={"year":"Kalenderår","view":"Redovisning"},title="Markens fysiska utsläpp och upptag"))
        complete=not any(x["category"]=="Förändrad markanvändning" and x["severity"]=="error" for x in r.issues)
        if complete:
            project=sum(x["kgco2e"] for x in landrows if x["view"]=="Projekt")
            reference=sum(x["kgco2e"] for x in landrows if x["view"]=="Referensmark")
            st.metric("Projekt minus referensmark (ton CO₂e)",nice((project-reference)/1000,1))
        st.caption(f"Referens: {s.project.land_reference}. Skillnaden räknas inte som ett ytterligare negativt utsläpp.")
    stored=[x for x in r.ledger if x["view"]=="Kollager"]
    if stored:
        st.subheader("Temporära kollager och ej avräknade åtgärder")
        st.dataframe(pd.DataFrame(stored)[["object_id","submodule","year","kgco2e","formula"]],hide_index=True,use_container_width=True)
    st.subheader("Jämför med en alternativ utformning")
    other=st.file_uploader("Alternativt scenario, JSON",type=["json"],key="compare-json")
    if other:
        try:
            alt=load_scenario(other.getvalue());rr=calculate(alt)
            comparable=(s.project.start_year,s.project.end_year,s.project.time_mode,s.project.operating_years,s.enabled,s.project.transport_scope)==(alt.project.start_year,alt.project.end_year,alt.project.time_mode,alt.project.operating_years,alt.enabled,alt.project.transport_scope)
            if s.project.time_mode=="cohort":comparable=comparable and [(p.start,p.end) for p in s.phases]==[(p.start,p.end) for p in alt.phases]
            st.dataframe(pd.DataFrame([{"Scenario":s.project.name,"Total ton CO₂e":None if r.total_kg is None else r.total_kg/1000,"Bostäder":s.project.homes,"Area m²":s.project.area_m2},{"Scenario":alt.project.name,"Total ton CO₂e":None if rr.total_kg is None else rr.total_kg/1000,"Bostäder":alt.project.homes,"Area m²":alt.project.area_m2}]),hide_index=True,use_container_width=True)
            if comparable and r.total_kg is not None and rr.total_kg is not None:
                st.metric("Aktivt scenario minus alternativ (ton CO₂e)",nice((r.total_kg-rr.total_kg)/1000,1))
                if s.project.homes!=alt.project.homes or s.project.area_m2!=alt.project.area_m2:st.warning("Scenariernas storlek skiljer sig. Tolka absoluta skillnader med deras olika omfattning.")
            else:st.warning("Skillnaden i total visas när båda scenarier är kompletta och har samma period, tidsläge, klimatkategorier och transportperspektiv.")
            if (s.project.start_year,s.project.end_year,s.project.area_m2)==(alt.project.start_year,alt.project.end_year,alt.project.area_m2):
                def markbalance(sc,res):
                    if not sc.enabled["Förändrad markanvändning"] or any(i["severity"]=="error" and i["category"]=="Förändrad markanvändning" for i in res.issues):return None
                    return sum(x["kgco2e"] for x in res.ledger if x["record_type"]=="Land" and x["view"]=="Projekt")
                aa,bb=markbalance(s,r),markbalance(alt,rr)
                if aa is not None and bb is not None:st.metric("Markutformning A minus B (ton CO₂e)",nice((aa-bb)/1000,1))
        except (ValueError,TypeError) as e:st.error(str(e))


def calculations(s,r):
    st.subheader("Så räknar Road2Zero")
    st.caption("Algoritmer, antaganden och beräkningsrader hör ihop. Intern enhet är kg CO₂e. Resultatvyerna räknar om till ton.")
    for title,item in METHODS.items():
        with st.expander(title):
            st.code(item["formula"],language="text");st.write(item["text"]);st.caption("Metod- och underlagsreferenser: "+item["sources"])
    st.subheader("Granska en beräknad post")
    if r.ledger:
        df=pd.DataFrame(r.ledger)
        cats=st.multiselect("Klimatkategorier i verifikationen",CATEGORIES,default=CATEGORIES,key="ledger-categories")
        st.dataframe(df[df.category.isin(cats)],hide_index=True,use_container_width=True)
        st.download_button("Ladda ned beräkningsrader, CSV",csv_bytes(r.ledger),"road2zero_verifikation.csv",mime="text/csv")
    with st.expander("Visa Python-algoritmerna"):
        st.code(inspect.getsource(engine),language="python")


def factors(s,r):
    st.subheader("Faktorer, parametrar och deras källor")
    st.caption("En vald faktor följer med scenariot: värde, enhet, källstatus, systemgräns, referensår och eventuell årskurva. En metodreferens ersätter inte en källa till ett numeriskt värde.")
    used=st.checkbox("Visa endast faktorer som motorn har efterfrågat",value=False)
    data=[f.model_dump() for f in s.factors if not used or f.id in r.used_factors]
    if data:st.dataframe(pd.DataFrame(data),hide_index=True,use_container_width=True)
    with st.expander("Ändra eller lägg till faktor"):
        records_editor(s,"factors",Factor)
    st.subheader("Årskurvor")
    st.caption("Ange faktiska årsvärden. Välj därefter kurvans ID på rätt faktor. Kurvans enhet måste matcha faktorn. EU WEM/WAM erbjuds först när en numerisk, källmärkt kurva har tillförts.")
    with st.expander("Ändra eller lägg till årskurva"):
        records_editor(s,"curves",Curve)
    st.subheader("Parameterregister")
    audit=parameter_audit(s)
    term=st.text_input("Sök parameter eller post-ID",placeholder="t.ex. BTA-TOTAL eller project.total_bta_override")
    filtered=[x for x in audit if term.lower() in x["parameter"].lower()]
    # Blandade datatyper visas som text för stabil Arrow-serialisering.
    df=pd.DataFrame(filtered)
    if not df.empty:
        df["value"]=df.value.map(lambda v:"Saknas" if v is None else str(v))
        st.dataframe(df,hide_index=True,use_container_width=True)
    st.download_button("Hämta hela parameterregistret",csv_bytes(audit),"road2zero_parametrar.csv",mime="text/csv")
    with st.expander("Ange särskild källa för en parameter"):
        with st.form("parameter-sources-"+st.session_state.generation):
            path=st.selectbox("Parametersökväg",[x["parameter"] for x in audit])
            source=st.selectbox("Käll-ID",[x.id for x in s.sources])
            if st.form_submit_button("Spara parameterkälla"):
                s.parameter_sources[path]=source;save_scenario(s)
    st.info("Årlig förändring anges som andel: −0,02 betyder −2 %. Osäkerhetsprocent är en dokumenterad uppgift; modellen räknar inte fram statistiska intervall utan ett särskilt osäkerhetsunderlag.")


def references(s,r):
    st.subheader("Referenser och underlag")
    st.caption("Detta är modellens bibliografi. Kopplingen från en enskild faktor eller parameter till käll-ID finns i föregående flik och i beräkningspaketet.")
    for src in s.sources:
        with st.expander(f"{src.id} · {src.title}",expanded=src.kind=="Metod"):
            st.write(f"{src.author} {src.year}".strip());st.caption(f"Typ: {src.kind} · {src.locator}")
            if src.url.startswith(("https://","http://")):st.link_button("Öppna källan",src.url)
            st.write(src.note)
    with st.expander("Redigera källregistret"):
        records_editor(s,"sources",Source)
    st.download_button("Hämta referensregister, JSON",json.dumps([x.model_dump() for x in s.sources],ensure_ascii=False,indent=2).encode(),"road2zero_referenser.json",mime="application/json")


def main():
    st.set_page_config(page_title="Road2Zero",page_icon="◌",layout="wide",initial_sidebar_state="expanded")
    st.markdown("""<style>
    .block-container {padding-top:2rem;max-width:1500px}
    h1,h2,h3 {letter-spacing:-.025em}
    [data-testid='stMetric'] {background:var(--secondary-background-color);padding:1rem;border-radius:14px;border:1px solid #DDE6EA}
    [data-testid='stSidebar'] {border-right:1px solid #DDE6EA}
    button[data-baseweb='tab'] {font-weight:600}
    [data-testid='stForm'] {border-radius:14px}
    </style>""",unsafe_allow_html=True)
    if "scenario" not in st.session_state:install_scenario(jagersro())
    s=Scenario.model_validate(st.session_state.scenario)
    with st.sidebar:
        logo=ROOT/"assets"/"road2zero.png"
        if logo.exists():st.image(str(logo),width=220)
        st.title("Road2Zero")
        st.caption("Från mängd till insikt")
        st.markdown("**Aktivt scenario**")
        st.write(s.project.name)
        selection=st.selectbox("Startscenario",["Jägersro SMT · 4 000 bostäder","DEMO · syntetiska testvärden"])
        if st.button("Öppna startscenario",use_container_width=True):
            install_scenario(jagersro() if selection.startswith("Jägersro") else demonstration());st.rerun()
        with st.expander("Läs in sparat scenario"):
            uploaded=st.file_uploader("Scenariofil, JSON",type=["json"],key="scenario-upload")
            if uploaded and st.button("Använd scenariofil"):
                try:install_scenario(load_scenario(uploaded.getvalue()));st.rerun()
                except ValueError as e:st.error(str(e))
        st.download_button("Spara scenario · JSON",scenario_json(s),f"{s.project.id.replace('/','_')}_scenario.json",mime="application/json",use_container_width=True)
        st.caption("Spara en fil för att behålla arbetet mellan sessioner. Appen lagrar ändringar i din aktuella session.")
        st.divider()
        st.caption(f"Road2Zero {__version__} · schema {s.schema_version}")
        st.caption("Manuella areor · inga kartor · beräkningar i Python")
    st.title("Road2Zero")
    st.caption("KLIMATSCENARIER MED SPÅRBARA INDATA")
    st.subheader(s.project.name)
    if s.project.id=="DEMO":st.warning("DEMONSTRATION: alla klimatvärden är syntetiska. Dessa är inte resultat för Jägersro SMT.")
    elif s.project.id.startswith("JAG-SMT"):
        st.info("SMT:s område · 4 000 bostäder. Arean, bostads-BTA, invånarskattningen och etapperna är ännu preliminära. Faktiska klimatfaktorer och mängder behöver kompletteras.")
    r=calculate(s)
    complete=sum(x["status"]=="Beräknad" for x in r.categories if x["enabled"])
    enabled=sum(x["enabled"] for x in r.categories)
    a,b,c,d=st.columns(4)
    a.metric("Bostäder",nice(s.project.homes));b.metric("Projektarea",nice(s.project.area_m2)+" m²")
    c.metric("Invånare vid full utbyggnad",nice(r.full_population));d.metric("Beräkningsbara kategorier",f"{complete} / {enabled}")
    tabs=st.tabs(["Indata","Resultat","Visualisering","Beräkningar och algoritmer","Faktorer och parametrar","Referenser"])
    with tabs[0]:inputs(s,r)
    with tabs[1]:results(s,r)
    with tabs[2]:visuals(s,r)
    with tabs[3]:calculations(s,r)
    with tabs[4]:factors(s,r)
    with tabs[5]:references(s,r)
    st.divider()
    st.download_button("Hämta komplett beräkningspaket · ZIP",result_zip(s,r),"road2zero_berakningspaket.zip",mime="application/zip",use_container_width=True)
    st.caption("Paketet innehåller scenario, årsserier, beräkningsrader, datakontroller, faktorer, parametrar, referenser och versionskontroll med SHA-256.")
