"""Källmärkta startscenarier. Demonstrationsvärden blandas aldrig in i SMT-scenariot."""
from .schema import (Activity, Programme, Consumption, Factor, Land, Phase, Project,
                     Removal, Scenario, Source, Transport)


def jagersro() -> Scenario:
    sources = [
        Source(id="USER", title="Användarens projektuppgifter", author="Projektets användare", year="2026", note="SMT:s område och 4 000 bostäder är användarens avgränsning. Egna senare indata är inte externt verifierade."),
        Source(id="ASSUMPTION", title="Road2Zero – uttryckliga arbetsantaganden", year="2026", kind="Antagande", note="Proportionering från hela FÖP, fyra lika stora etapper och arbetsårtal ska bekräftas av SMT."),
        Source(id="FOP2025", title="Översiktsplan för Jägersro – granskningshandling", author="Malmö stad", year="2025", locator="s. 14–15, program och park; s. 20, genomförande", url="https://malmo.se/download/18.50574bcf196ed960a55a894/1758803712161/F%C3%96P2040_J%C3%A4gersro_granskningshandling_tg.pdf", note="Hela planområdet: 4 300 bostäder, 440 000 m² bostads-BTA, 8 900 invånare. Detta är inte fastställda SMT-mängder. Park >5 ha; 50 000 m² används som preliminärt nedre arbetsvärde."),
        Source(id="STMX", title="Klimatmodell CO2e-budget, Avatar-MFF.stmx", author="Tillhandahållen Jägersromodell", kind="Äldre modell", locator="Exploatering.Total_yta_stadsdel_(m2)", note="Sparat värde 410 000 m²; bekräfta fastighetsarean. SHA256: 4d30512e1048c8e6d5b16681fbd1410b1fc843af8c5096e4f4633534c4699c59. Äldre Mat-parametrar har delvis motstridiga enhetsnamn."),
        Source(id="OCEAN2026", title="Oceanhamnen Etapp 1, 2, 3 & 4 2026-08-28-underlag.xlsx", kind="Äldre modell", locator="Schablonvärden", note="Spårbar återanvändning av exportvärden. Ursprungskällor är delvis breda eller ofullständiga. Inga värden här är projektspecifikt verifierade för SMT."),
        Source(id="MANUAL3", title="Klimatanalys 3.0 – tillhandahållen manual", kind="Modellbeskrivning", note="Kategorier och objektfält. Road2Zero använder manuell area och separat redovisning av inventering, jämförelse och kollager."),
        Source(id="IPCC2006", title="2006 IPCC Guidelines, Volume 4, Chapter 2", author="IPCC", year="2006", kind="Metod", locator="Avsnitt 2.2–2.3; kolpooler och C–CO2-omvandling", url="https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/4_Volume4/V4_02_Ch2_Generic.pdf", note="Metodstöd för kolpooler; modellens lokala markfaktorer måste tillföras och verifieras. Road2Zero är en förenklad projektmodell, inte en fullständig IPCC-inventering."),
        Source(id="GHG2023", title="Inventory and Project Accounting: A Comparative Review", author="GHG Protocol", year="2023", kind="Metod", url="https://ghgprotocol.org/blog/inventory-and-project-accounting", note="Stöd för separat redovisning av inventering och skillnad mot referensalternativ."),
        Source(id="BOVERKET", title="Om klimatdeklarationen – byggskedets A1–A5", author="Boverket", kind="Metod", url="https://www.boverket.se/sv/klimatdeklaration/om-klimatdeklaration/", note="Road2Zero-faktorer kräver uttrycklig omfattning. Hela stadsdelens scenario är inte en juridisk klimatdeklaration."),
        Source(id="VAGVIS", title="Vägvis 2.3.0 – projektspecifik export behövs", kind="Ej tillfört underlag", note="Ingen faktisk export har tillförts. Ange systemgräns, perspektiv, etapp och årliga ton CO2e. CSV-adaptern kräver ett dokumenterat exportformat; appen anropar inte Vägvis."),
        Source(id="STREAMLIT", title="Streamlit – API, app testing och Community Cloud", author="Streamlit", kind="Programvara", url="https://docs.streamlit.io/", note="Streamlit Community Cloud: välj GitHub-repository och streamlit_app.py. Python 3.12 rekommenderas."),
    ]
    factors = [
        Factor(id="bta_per_home", name="Bostads-BTA per bostad, proportioneringsantagande", value=440000/4300, unit="m2/home", source_id="FOP2025", locator="s. 14; 440000 / 4300", quality="Antagande", note="Hela FÖP:s genomsnitt används provisoriskt för SMT."),
        Factor(id="people_per_home", name="Invånare per bostad, proportioneringsantagande", value=8900/4300, unit="person/home", source_id="FOP2025", locator="s. 14; 8900 / 4300", quality="Antagande", note="Kan ersättas med egna invånare utan att skattningen skrivs över."),
        Factor(id="legacy_piling", name="Pålning, äldre BTA-schablon", value=26, unit="kgCO2e/m2", source_id="OCEAN2026", locator="Schablonvärden!D36: 0,026 ton/m² × 1000", quality="Äldre schablon", boundary="Pålning; kontrollera omfattning gentemot byggnadsfaktor", note="Export hänvisar till SBUF/CARBONARA-187. Ursprunglig rapport behöver identifieras."),
        Factor(id="legacy_sheet", name="Spontning, äldre totalfaktor", value=280.5, unit="kgCO2e/m2", source_id="OCEAN2026", locator="Schablonvärden!D39: 0,2805 ton/m² × 1000", quality="Äldre schablon", boundary="Ny spont + arbete", note="Gäller spontyta, inte BTA eller planarea."),
        Factor(id="legacy_atemp", name="Atemp/BTA, äldre uppskattning", value=.9, unit="Atemp/BTA", source_id="OCEAN2026", locator="Schablonvärden!D2", quality="Äldre schablon", note="Mätt Atemp har företräde; ratio används endast om det uttryckligen väljs."),
        Factor(id="legacy_building", name="Byggnad, äldre generell faktor", value=375, unit="kgCO2e/m2", source_id="OCEAN2026", locator="Schablonvärden!D18", quality="Ej verifierad", boundary="Antagen A1–A5; exkludera grundläggning före användning", note="Enhet och ursprungskälla saknas i schablonraden. Använd först efter kontroll. Ingen materialdifferentiering har verifierats."),
        Factor(id="grid", name="Elmix – komplettera värde eller årskurva", unit="gCO2e/kWh", boundary="Vald elmix och livscykelomfattning anges här"),
        Factor(id="heat", name="Fjärrvärme – projektspecifikt värde/kurva", unit="gCO2e/kWh"),
        Factor(id="public", name="Offentliga investeringar, årlig invånarfaktor", unit="tCO2e/person/year", note="Saknas. Avgränsa mot redan inkluderade offentliga byggnader, vägar och investeringar."),
        Factor(id="other", name="Övrig konsumtion exklusive mat, energi och transport", unit="kgCO2e/person/year"),
    ]
    for fid, name, value, unit, row in [
        ("legacy_park", "Park, äldre ytfaktor", 5, "m2", 75),
        ("legacy_street", "Lokalgata, äldre ytfaktor", 20, "m2", 71),
        ("legacy_gc", "GC-väg, äldre ytfaktor", 10, "m2", 63),
        ("legacy_excavation", "Schaktning, äldre faktor", 15, "m3", 50),
        ("legacy_remediation", "Marksanering, äldre faktor", 75, "m3", 51),
        ("legacy_haul", "Masstransport, äldre faktor", .072, "tkm", 53),
    ]:
        factors.append(Factor(id=fid, name=name, value=value, unit="kgCO2e/"+unit, source_id="OCEAN2026", locator=f"Schablonvärden!D{row}; ton omräknat till kg", quality="Äldre schablon", boundary="Enligt äldre exportschablon; omfattning behöver granskas"))
    factors.extend([
        Factor(id="soc", name="SOC före markändring", unit="kgC/m2"),
        Factor(id="dom", name="Dött organiskt material före markändring", unit="kgC/m2"),
        Factor(id="biomass", name="Biomassa före markändring", unit="kgC/m2"),
        Factor(id="land_after", name="Markens faktiska nettoflöde efter åtgärd", unit="kgCO2e/m2/year"),
        Factor(id="land_reference", name="Referensmarkens årliga nettoflöde", unit="kgCO2e/m2/year"),
        Factor(id="bef", name="Skogens biomass expansion factor", unit="ratio"),
        Factor(id="wood_density", name="Skogens torra veddensitet", unit="kg/m3"),
        Factor(id="carbon_fraction", name="Kolfraktion i torr biomassa", unit="ratio"),
        Factor(id="biomass_capacity", name="Maximalt biomassakollager", unit="kgC/m2"),
        Factor(id="biochar", name="Biokol, beständig kolinlagring före livscykelavdrag", unit="kgCO2e/t"),
        Factor(id="timber", name="Inbyggt virke, temporärt biogent kollager", unit="kgCO2e/m3"),
        Factor(id="trees", name="Träd, årligt brutto-CO2-upptag", unit="kgCO2e/st/year"),
    ])
    phases = [Phase(id=f"E{i+1}", name=f"Etapp {i+1} (antagande)", start=2029+5*i, end=2033+5*i, share=.25, source_id="ASSUMPTION") for i in range(4)]
    programme = [Programme(id="BTA-TOTAL", name="Totalt bostadsprogram", share_bta=1,
                           kind="Bostäder, blandad typ", source_id="ASSUMPTION",
                           note="Total bostads-BTA är en proportioneringsskattning från hela FÖP. Lokalers BTA är inte fastställd. Komplettera totalen och fördelningen när SMT:s program är känt. Ingen inmatning per byggnad.")]
    activities = [Activity(id="A-PARK", name="Central park", phase_id="E1", submodule="Ytbeläggning", quantity=50000, unit="m2", land_id="M-PARK", source_id="ASSUMPTION", note=">5 ha enligt FÖP; 50 000 m² är ett nedre arbetsvärde. Faktor ännu inte vald.")]
    for i, (name, sub, unit) in enumerate([
        ("Gator", "Ytbeläggning", "m2"), ("Gång och cykel", "Ytbeläggning", "m2"),
        ("Torg", "Ytbeläggning", "m2"), ("Gårdar", "Ytbeläggning", "m2"),
        ("Ledningar och VA", "Ledningar", "m"), ("Schaktning", "Masshantering", "m3"),
        ("Masstransport", "Masstransport", "tkm"), ("Sanering", "Marksanering", "m3"),
        ("Rivning och återbruk", "Rivning", "st")], 1):
        activities.append(Activity(id=f"A-{i:02d}", name=name, phase_id="E1", submodule=sub, unit=unit))
    food = []
    for i, name in enumerate(("Rött kött", "Övrigt kött", "Fisk", "Mejeri och ägg", "Vegetabilier", "Drycker och övrigt"), 1):
        fid = f"food_{i}"
        factors.append(Factor(id=fid, name=f"Mat – {name}", unit="kgCO2e/kg", note="Verifiera livsmedelsgrupp, ätbar vikt, svinn och systemgräns."))
        food.append(Consumption(id=f"MAT-{i}", name=name, category="Matkonsumtion", mode="quantity", unit="kg", factor_id=fid))
    return Scenario(project=Project(id="JAG-SMT-FOP-01", name="Jägersro SMT – 4 000 bostäder", homes=4000,
                       area_m2=410000, land_reference="SMT utan ny exploatering efter hästsportens flytt",
                       note="SMT:s avgränsning. FÖP för hela området är programreferens. 2029–2048 och fyra lika etapper är arbetsantaganden, inte beslutad tidplan."),
                    phases=phases, programme=programme, activities=activities,
                    lands=[Land(id="M-PARK", name="Parkens mark", area_m2=50000, after="Park", source_id="ASSUMPTION"),
                           Land(id="M-REST", name="Övrig mark – klassificering återstår", area_m2=360000, source_id="ASSUMPTION")],
                    consumption=food+[Consumption(id="KONS-1", name="Övrig konsumtion", category="Övrig konsumtion", factor_id="other"), Consumption(id="OFF-1", name="Offentliga investeringar", category="Offentliga investeringar", factor_id="public")],
                    factors=factors, sources=sources, parameter_sources={"project.area_m2":"STMX", "project.homes":"USER", "project.start_year":"ASSUMPTION", "project.end_year":"ASSUMPTION", "project.build_start_year":"ASSUMPTION", "project.build_end_year":"ASSUMPTION", "project.occupation":"ASSUMPTION"})


def demonstration() -> Scenario:
    """Litet komplett räkneexempel med avsiktligt syntetiska värden – aldrig SMT-resultat."""
    s = jagersro()
    s.project = Project(id="DEMO", name="DEMO – syntetiskt räkneexempel", source_id="DEMO", homes=10, area_m2=2000,
                        total_bta_override=1000, population_override=20, start_year=2029, end_year=2033,build_start_year=2029,build_end_year=2029,
                        occupation="after", transport_scope="residents")
    s.sources.append(Source(id="DEMO", title="Syntetiska testvärden för funktionsdemonstration", kind="Demonstration", note="Saknar anspråk på verklig klimatprestanda. Får inte presenteras som SMT:s prognos."))
    s.phases = [Phase(id="E1", name="Demoetapp", start=2029, end=2029, share=1, source_id="DEMO")]
    s.factors = [Factor(id="bta_per_home", name="Demo BTA", value=100, unit="m2/home", source_id="DEMO"),
                 Factor(id="people_per_home", name="Demo invånare", value=2, unit="person/home", source_id="DEMO")]
    values = [("build",200,"kgCO2e/m2"),("grid",50,"gCO2e/kWh"),("heat",40,"gCO2e/kWh"),
              ("surface",5,"kgCO2e/m2"),("soc",2,"kgC/m2"),("dom",.1,"kgC/m2"),("biomass",.2,"kgC/m2"),
              ("land_after",-.05,"kgCO2e/m2/year"),("land_reference",-.02,"kgCO2e/m2/year"),
              ("food",2,"kgCO2e/kg"),("other",300,"kgCO2e/person/year"),
              ("public",.4,"tCO2e/person/year"),("biochar",1800,"kgCO2e/t")]
    s.factors += [Factor(id=i,name=f"Demo {i}",value=v,unit=u,source_id="DEMO",quality="Demonstration") for i,v,u in values]
    s.programme = [Programme(id="BTA-DEMO", name="Hela demoprogrammets BTA", share_bta=1, atemp_m2=900,
                           construction_factor_id="build", electricity_specific=20, heat_specific=40,
                           electricity_factor_id="grid", heat_factor_id="heat", solar_kwh_year=5000,
                           solar_self_use=.8, piling="no", sheet_piling="no", source_id="DEMO")]
    s.activities = [Activity(id="A1",name="Demoyta",phase_id="E1",quantity=1000,unit="m2",factor_id="surface",source_id="DEMO")]
    s.lands = [Land(id="M1",name="Demomark",area_m2=2000,before="Gräsmark",after="Park",soil="Mineraljord",source_id="DEMO",soc_factor_id="soc",dom_factor_id="dom",biomass_factor_id="biomass",keep_soc=.9,keep_dom=.5,keep_biomass=.5,after_flow_factor_id="land_after",reference_flow_factor_id="land_reference")]
    s.consumption = [Consumption(id="C1",name="Demomat",category="Matkonsumtion",mode="quantity",quantity=400,unit="kg",factor_id="food",source_id="DEMO"),
                     Consumption(id="C2",name="Demokonsumtion",category="Övrig konsumtion",factor_id="other",source_id="DEMO"),
                     Consumption(id="C3",name="Demoinvesteringar",category="Offentliga investeringar",factor_id="public",source_id="DEMO")]
    s.transport = [Transport(id=f"T{y}",year=y,perspective="residents",tco2e=5,source_id="DEMO",boundary="Syntetiskt fullständigt årsvärde, boendes resor; energi och byggtransporter exkluderade") for y in range(2030,2034)]
    s.removals = [Removal(id="N1",name="Demobiokol",kind="biochar",quantity=1,unit="t",factor_id="biochar",lifecycle_kg=100,include_in_total=True,eligibility_confirmed=True,source_id="DEMO")]
    s.parameter_sources = {}
    return s
