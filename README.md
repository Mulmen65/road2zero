# Road2Zero 1.0

En Python- och Streamlit-modell för klimatberäkningar med manuell inmatning, utan karta. Startscenariot är **Jägersro SMT, 4 000 bostäder**. All inmatning om byggande utgår från **total nybyggd BTA under en valbar byggperiod**. Inga uppgifter om enskilda byggnader behövs.

## Starta lokalt

Använd Python **3.12** (även 3.11 ingår i testkonfigurationen).

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell, använd i stället:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Du kan också använda `starta_windows.bat` eller `bash starta_mac_linux.sh`. Skripten skapar en lokal Pythonmiljö och installerar beroenden.

Appen öppnas normalt på `http://localhost:8501`. Den kräver ingen API-nyckel och gör inga automatiska anrop till klimatdatabaser eller Vägvis. Källänkar öppnas bara när användaren väljer dem.

## GitHub och Streamlit Community Cloud

1. Packa upp projektet. Lägg innehållet i mappen `road2zero` i roten av ett eget GitHub-repository. Även `.streamlit` och `.github` ska med. Det går också att använda projektmappen som undermapp, men ange då dess sökväg som appfil i nästa steg.
2. I [Streamlit Community Cloud](https://share.streamlit.io/), välj **Create app** och ditt repository/branch.
3. Ange **`streamlit_app.py`** som appfil om projektet ligger i repositoryts rot. Välj **Python 3.12** under Advanced settings.
4. Starta publiceringen. Appens dependencies installeras från `requirements.txt`.
5. Kontrollera testerna under GitHub Actions. Arbetsflödet kör beräknings- och Streamlit-tester på Python 3.11 och 3.12.

Paketet innehåller körbar källkod och publiceringskonfiguration. Något externt GitHub-repository eller någon Streamlit-publicering har inte skapats i detta arbete.

Officiell instruktion: <https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy>.

## Appens sex flikar

| Flik | Innehåll |
| --- | --- |
| Indata | Projekt, total BTA och byggperiod, programandelar, energi, anläggning, mark, Vägvis, mat, övrig konsumtion, offentliga investeringar, negativa utsläpp |
| Resultat | Klimatkategorier, årsvisa tabeller, kända delresultat, dataluckor, nyckeltal och vald omfattning |
| Visualisering | Klimatkategorier, årsutsläpp, ackumulerat resultat, befolkning, separata transportperspektiv, markreferens och alternativ utformning |
| Beräkningar och algoritmer | Formler, avgränsningar, Python-kod och verifikation per beräkningspost |
| Faktorer och parametrar | Redigerbara faktorer, enheter, årskurvor, källstatus, parameterregister och särskild källa per parameter |
| Referenser | Fullständigt källregister med länkar och uppgifter om dokumentens omfattning |

## Så matas total BTA in

Ange **total BTA att bygga**, **byggperiodens startår** och **slutår** i `Indata → Byggd BTA och energi` eller i projektinställningarna. En BTA-total räcker för hela programmet. Tom BTA kan uppskattas från antal bostäder och en vald BTA/bostad-faktor; skattningen är tydligt märkt. Ett eget BTA-värde, även noll, har företräde.

En programrad med **andel 1** kan omfatta hela BTA:n. Om bostäder, kontor eller materialalternativ behöver olika faktorer kan totalen delas upp i programandelar. Dessa andelar ska summera till 1. Detta är en fördelning av det samlade programmet, inget register över individuella byggnader.

Utan etappindelning fördelas byggskedet jämnt över den valda byggperioden. Med etapper fördelas samma BTA med etappandelarna och respektive byggperiod. Inga extra BTA-mängder skapas:

```text
BTA per programandel och etapp = total BTA × programandel × etappandel
```

Egen Atemp, årsenergi, solel, spontyta och egen byggskedestotal på en programrad avser **hela den programandelen**. Motorn fördelar mängderna med etappernas andelar. Specifika energivärden avser kWh/m² Atemp/år. Pålning använder BTA; spontning använder spontyta. Dessa grundläggningsposter redovisas i Anläggning. Byggnad och Energi visas separat.

Invånare kan skattas från antal bostäder eller bostads-BTA och ersättas med egna uppgifter. Vid invånarskattning från BTA används bara programandelar markerade som bostäder. Om BTA skattas från bostäder och programmet också innehåller lokaler, räknas totalen upp med bostadsprogrammets andel; det är ett uttryckligt antagande.

## Klimatkategorier och viktiga avgränsningar

- **Byggnad:** mängd × vald byggskedesfaktor eller egen byggskedestotal. Faktorn bestäms vid byggstart och fördelas över byggåren. Materialval dokumenteras och matchas av användaren mot faktorn.
- **Energi:** el och värme som specifika eller totala årsmängder, valfria årskurvor och solel. Export redovisas i kWh utan automatisk klimatkredit. Energiklass är dokumentation; inga overifierade klassvärden skapas automatiskt.
- **Anläggning:** grundläggning, ytor, masshantering, masstransport, sanering, ledningar, rivning/återbruk och egna aktivitetsrader. En masstransporthjälp räknar m³ × ton/m³ × km till tkm.
- **Förändrad markanvändning:** manuell area, mark före/efter, jordtyp, SOC, DOM, biomassa, bevarande, utsläppsperiod och årliga nettoflöden. En förenklad skogsmodell kan använda tillväxt, BEF, torr densitet, kolfraktion och maximal biomassakapacitet. Detta är inte en fullständig skogstillväxtsimulator.
- **Mobilitet och transport:** Vägvis-resultat importeras via dokumenterad CSV. Boendes resor och all trafik hålls åtskilda; högst ett perspektiv summeras. Ingen direktkoppling till Vägvis finns i denna version.
- **Matkonsumtion:** livsmedelsgrupper med kg/person/år och faktor per kg, alternativt en samlad invånarfaktor. Äldre Jägersroparametrar med oklara enheter följer med för granskning men används inte som verifierade nya värden.
- **Övrig konsumtion:** invånarfaktorer eller mängdbaserade delposter. Underlaget måste avgränsas från mat, energi och transport som redan ingår.
- **Offentliga investeringar:** ton CO₂e/invånare/år, multiplicerat med årets invånare. Offentliga byggnader, vägar och andra explicita investeringar ska avgränsas för att undvika överlapp.
- **Negativa utsläpp:** markens faktiska upptag, biokol och dokumenterade åtgärder. Temporärt kollager i virke visas separat. Avdrag kräver särskild dokumentation och ska inte finnas inräknat i EPD eller markmodulen redan.

Mark har två inmatningslägen: hela projektarean med areabalans, eller enbart förändrade/åtgärdade areor. Mark-ID är unikt. Länkade anläggningsposter räknar inga kolpooler. Manuell areabalans kan inte upptäcka verkliga geografiska överlappningar.

Referensmarkens nettoflöde och skillnaden mot projektet visas separat. Förlorat framtida upptag bokförs inte en andra gång som fysisk lagerförlust. Mark och kolsänkor använder alltid gemensam kalenderperiod även när andra kategorier använder driftår per etapp.

## Datakvalitet och startscenariot

**Saknade obligatoriska värden ger inget automatiskt nollutsläpp.** En ofullständig klimatkategori och projektets total visas som ofullständiga, medan kända delposter kan granskas. Kategorier kan exkluderas uttryckligen; detta ändrar totalens systemgräns. En komplett beräkning betyder att nödvändiga indata går att beräkna, inte att alla källor är vetenskapligt verifierade.

SMT-startscenariot innehåller:

| Uppgift | Värde | Källstatus |
| --- | --- | --- |
| Bostäder | 4 000 | Användarens avgränsning |
| Area | 410 000 m² | Äldre sparad modell; ska bekräftas |
| Bostads-BTA | cirka 409 302 m² | 440 000 × 4 000/4 300, proportionering från hela FÖP |
| Invånare | cirka 8 279 | 8 900 × 4 000/4 300, proportionering från hela FÖP |
| Byggperiod | 2029–2048 | Arbetsantagande |
| Etapper | Fyra lika stora delperioder, valfria | Arbetsantagande; inaktiva vid start |
| Parkarea | 50 000 m² | Nedre arbetsvärde från FÖP:s >5 ha; ska bekräftas |

Lokaler, infrastruktur, energimängder, emissionskurvor, Vägvis-export och flera konsumtions- och markfaktorer behöver kompletteras. Den förifyllda BTA:n avser det uppskattade bostadsprogrammet; lokaler har ingen verifierad SMT-mängd. Den föreslagna FÖP:n avser ett större område. Skola, mobilitetshus eller alla parker i hela FÖP:n har därför inte kopierats som SMT-mängder.

Äldre Oceanhamnen-faktorer har exakta rad-/cellhänvisningar och tydlig status. Ingen saknad EU WEM/WAM- eller fjärrvärmekurva har återskapats från ett kurvnamn. Egna kurvor ersätter faktorvärdet och interpoleras linjärt. Utanför kurvans intervall krävs komplettering, om inte konstant ändvärde uttryckligen väljs.

## Spara, importera och dela scenarier

Appen håller det aktiva scenariot i **sessionen**. Spara JSON innan du stänger sidan. På en publik Streamlit-installation finns ingen gemensam projektdatabas eller fleranvändarredigering. Varje session är separat. Ett JSON-scenario innehåller hela uppsättningen indata, faktorer, årskurvor och referenser. Det valideras vid import.

`Hämta komplett beräkningspaket` ger scenario, beräkningsrader, kategorier, datakontroller, invånarserier, parametrar, faktorer, källor och SHA-256 för scenariofilen. CSV är UTF-8 med BOM och semikolon. Text som skulle kunna tolkas som kalkylbladsformel skyddas vid export.

### Vägvis-adapter

Använd `data/vagvis_importmall.csv` eller hämta mallen i appen. Kolumner:

```text
id;year;perspective;phase_id;tco2e;source_id;boundary;includes_building_electricity;includes_construction
```

`perspective` är `residents` eller `all`. `tco2e` är **redan beräknade årsvärden**, inte faktor per invånare. Ange alla relevanta år; ingen automatisk interpolation görs. Etapp-ID krävs för etappvis tid när etappindelning används. Projektets total och etappvärden får inte blandas för samma år/perspektiv. `source_id` måste finnas i källregistret. Den tillhandahållna mallen saknar utsläppsvärde med avsikt och kan inte räknas förrän det fyllts i. Mallens format är Road2Zeros adapterformat, inte ett påstående om Vägvis originalexport.

## Köra utan gränssnitt

```bash
python -m road2zero --demo --output exports/demo
python -m road2zero --scenario data/jagersro_smt.json --output exports/smt
```

`null` för total betyder ofullständigt underlag. Ett separat demoexempel med syntetiska faktorer och fullständig beräkning ingår. Det ska inte användas som resultat för Jägersro.

## Testning

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Testerna kontrollerar ett oberoende handräknat räkneexempel, BTA- och etappfördelning, noll jämfört med saknat värde, enheter, kurvor, energi/solel, markens lager och flöden, skogskapacitet, transportperspektiv, offentliga investeringar, kollager, återföring och exportens reproducerbarhet. Streamlits AppTest kontrollerar appstart, samtliga inmatningsmoduler och ändring av total BTA.

Se `docs/VALIDERING.md` för vad som faktiskt har kunnat köras i leveransmiljön och vilka tester som återstår i en installation med alla webbberoenden.

## Kodstruktur

```text
streamlit_app.py           Streamlit-startfil
road2zero/schema.py        Validerat scenarioformat och enheter
road2zero/engine.py        Ren beräkningsmotor med verifikation
road2zero/ui.py            Inmatning, resultat, diagram och källvyer
road2zero/methods.py       Läsbara algoritmer och metodbegränsningar
road2zero/seeds.py         Källmärkta SMT- och demoscenarier
road2zero/io.py            JSON, CSV och beräkningspaket
road2zero/__main__.py      Kommandoradskörning
data/                     Scenarier, importmall och äldre granskningsunderlag
docs/                     Metod- och valideringsanteckningar
tests/                    Beräknings- och Streamlit-tester
.github/workflows/         Kontroller för GitHub
```

Modellen använder inga värden från den äldre Stella-motorn i bakgrunden. Dokumenterade äldre parametrar finns för granskning. Den nya motorn är uppbyggd för att kunna granskas och vidareutvecklas kategori för kategori. Den är inte en certifiering, juridisk klimatdeklaration eller automatisk kvalitetsstämpel på användarens underlag.
