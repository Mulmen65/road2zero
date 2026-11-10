# Road2Zero – instruktioner för Claude

Road2Zero är en familj av evidensbaserade klimatmodeller för staden. Alla har samma huvudnamn, logotyp, mörkgröna meny och
förklaringssidor (Karta & områden, Så räknas resultatet, Antaganden & scenario, Trafik & geodata, Metod & källor).
Användaren är klimatforskare och skriver svenska; svara och skriv all text i gränssnitten på svenska.

| Modell | Huvudfil | Vad den gör |
|---|---|---|
| Road2Zero-OP | `op/streamlit_app.py` | Hela staden per DeSO enligt översiktsplanen, med karta (OpenStreetMap). Projekt per stad i `op/projekt/`; först Malmö_ÖP. |
| Road2Zero-Plan | `plan/streamlit_app.py` | En plan (t.ex. Jägersro): tio klimatkategorier år för år mot en koldioxidbudget, med karta. |
| Road2Zero-CityScenario | `cityscenario/streamlit_app.py` | Tre scenarier (samma eller olika stadsdelar) mot varandra, indata från JSON eller Excel. |

Repot är `Mulmen65/road2zero`. Alla tre apparna publiceras från samma repo på Streamlit Community Cloud med var sin huvudfil.
`streamlit_app.py` i roten kör Road2Zero-Plan, så att äldre publiceringar fortsätter att fungera.

## Kör och testa

```bash
pip install -r requirements.txt
python -m pytest -q                                              # alla Python-tester, även op/tests; ska vara grönt före commit
node op/tests/test_model.js                                      # beräkningstester för Road2Zero-OP
node op/tests/test_resultat.js                                   # resultatvyn och klimatbudgeten i Road2Zero-OP
python -m streamlit run plan/streamlit_app.py --server.port 8501
python -m streamlit run cityscenario/streamlit_app.py --server.port 8502
python -m streamlit run op/streamlit_app.py --server.port 8503
python verktyg/las_tabell_a.py                                   # läser underlag/tabell_a_utokad.xlsx till faktabiblioteket
python verktyg/jagersro.py                                       # bygger standardprojektet ur underlag/jagersro_*
python verktyg/bygg_malmofall.py                                 # bygger fall/ (Västra hamnen, Varvsstaden, Jägersro SMT)
python verktyg/hamta_vagvis.py sökväg/vagvis_data.json           # DeSO-underlag ur Vägvis till gemensamt/data/vagvis_deso.json
```

Efter en ändring i gränssnittet: starta appen, öppna den i webbläsaren och titta på sidan du ändrat. Testerna fångar inte layoutfel.
Streamlit läser inte om moduler utanför appens mapp (`gemensamt/`, `road2zero/`) när de ändras: starta om servern.

## Struktur

- `road2zero/` – beräkningsmotorn för Plan och CityScenario. Beroende av Streamlit får inte införas här.
  - `engine.py` – `berakna(indata) -> Resultat`.
  - `scenario.py` – indatamodell, standardvärden (`tomt()`), validering, JSON och migrering av äldre sparade filer.
  - `excel_indata.py` – indata som Excel (`till_excel`, `fran_excel`) för ett eller flera scenarier.
  - `jamforelse.py` – rättvis jämförelse (CityScenario och `verktyg/jamfor_stadsdelar.py`).
  - `utveckling.py` – index per emissionsfaktor och år. `algoritmer.py` – formler och text på sidan Så räknas resultatet.
  - `modules/` – en modul per indatamodul och klimatbudget. `data/` – faktabiblioteket (CSV med `;`, JSON), kolumnen `kalla`
    med id i `referenser.csv`.
- `gemensamt/` – gränssnitt som Plan och CityScenario delar.
  - `varumarke.py` – logotyp (`logo.svg`), färger, mörkgrön meny (`meny()`), sidrubriker, kort och steg.
  - `forklaring.py` – sidorna Karta & områden, Så räknas resultatet, Antaganden & scenario, Trafik & geodata, Metod & källor.
  - `karta.py` – karta med DeSO och OpenStreetMap (Leaflet i `leaflet/`, st.components.v2; klick på en DeSO skickas till Python).
  - `geodata.py` – DeSO-underlaget i `data/vagvis_deso.json` (hushåll, invånare, bilar, körsträcka, polygoner) utan Streamlit.
  - `common.py` – `fmt()` (svenskt talformat), `editor()`, `senare()`, `ny_version()`, `giltigt()` och sidopanelen.
  - `ui_*.py` – indata, resultat (urval av nivå och kategorier), emissionsfaktorer över tid, faktorer, beräkningar, referenser.
- `plan/streamlit_app.py` – Road2Zero-Plan. Menyn: Översikt, Indata, Resultat och förklaringssidorna.
- `cityscenario/` – Road2Zero-CityScenario: `streamlit_app.py`, `scenarier.py` (ss.scen pekar på scenariot som ändras, eget
  nummerområde för ss.v per scenario), `ui_jamforelse.py` (Jämförelse och Rättvis jämförelse).
- `op/` – Road2Zero-OP (från MalmoOP 1.2): `app/` (HTML, JavaScript och CSS; beräkningen i `model.js`), `projekt/<id>/` med
  `projekt.json` och `data/`, `tools/` (bygger underlaget; välj projekt med miljövariabeln `R2Z_OP_PROJEKT`), `tests/`.
- `fall/` – färdiga fall för CityScenario, byggda av `verktyg/bygg_malmofall.py`. Ändra skriptet, inte JSON-filerna.
- `verktyg/` – skript som bygger data. `underlag/` – källfiler som skripten läser; visas aldrig i gränssnittet.
- `tests/test_motor.py` – regressionstester, källkonsistens, Excel, geodata och test för rent gränssnitt.

## Grundregler

1. **Inga siffror i beräkningskoden.** Alla faktorer ligger i `road2zero/data/` med källa. Ny källa läggs in i `referenser.csv`.
   Värden utan extern källa får källan `MODELLVAL` och statusen Modellval eller Antagande.
2. **Rent gränssnitt.** Gränssnittet, faktabiblioteket och koden får inte hänvisa till internt eller tidigare bilagt underlag
   (Klimatanalys 3.0, Jägersro-modellen, Oceanhamnen, QA-underlag). Hänvisa till de publicerade källorna. Vägvis är en publicerad,
   kopplad modell (github.com/Mulmen65/vagvisa) och får nämnas. `test_rent_granssnitt` kontrollerar `gemensamt/`, `plan/`,
   `cityscenario/`, `road2zero/` och rotens startfil. Undantag: standardprojektets JSON-fil, `fall/`, skriptet som bygger fallen,
   DeSO-underlaget och `op/` får namnge verkliga platser.
3. **Startläge:** Road2Zero-Plan startar med standardprojektet (`scenario.standardprojekt()`, Jägersro, Svensk Travsports del).
   CityScenario startar med tre tomma scenarier; Malmöfallen hämtas med en knapp. `scenario.exempel()` används bara av testerna.
4. **Allt indata som påverkar resultatet har ett förifyllt värde med källa** som användaren kan ändra.
5. **Svenskt talformat** i gränssnittet: mellanslag som tusentalsavgränsare och decimalkomma (`fmt()`).
6. **Sidor som visar resultat** ritar dem med `senare()`, så att de fylls efter att sidans indata lästs och resultatet beräknats.
   Appen ritar en sida per körning: sidans indata, sedan `resultat()`, `kor_senare(res)` och sidopanelen.
7. **Diagram**: den dova färgskalan i `road2zero/konstanter.py` (kategorier) och `gemensamt/diagram.py` (layout och övriga linjer);
   aldrig två y-axlar. Scenariofärgerna A, B och C står i `cityscenario/scenarier.py`.
8. **Sparade indata** ska fortsätta gå att öppna, som JSON och som Excel. Ändras datamodellen: lägg migrering i
   `scenario.fran_json()` (Excel går via den) och ett test.
9. **Val i st.radio och st.selectbox:** Streamlit sparar valet som etikettens text. Etiketter som kan ändras (namn, parametervärden)
   ska inte användas som `format_func`; använd fasta etiketter och kör värdet genom `common.giltigt()`. Menyn har fasta etiketter.
10. **Byte av sida eller scenario** anropar `ny_version()`, så att alla fält läser om sina värden ur indata.
11. **Samma utseende i alla tre:** logotyp, färger och menyns förklaringssidor ändras i `gemensamt/varumarke.py` och i
    `op/app/shell.html` och `op/app/malmoop.css` samtidigt.

## Modellbeslut (ändras bara om användaren ber om det)

- **Kategorier och nivåer:** Byggnad, Energi, Anläggning, Förändrad markanvändning (nivå 1); Mobilitet och transport, Flygresor,
  Matkonsumtion, Övrig konsumtion (nivå 2); Offentliga investeringar (nivå 3); Negativa utsläpp dras av på alla nivåer.
  Undvikna utsläpp från exporterad solel redovisas utanför nettot.
- **Tid:** hela år, standard 2026–2076. Startår från 1990 går att välja för befintliga stadsdelar; år före 2026 använder startvärdena
  (ingen bakåtskrivning) och får ingen budgetandel. Byggskedet bokförs det år BTA:n blir klar. Drift och invånare med halvårsregel.
- **Emissionsfaktorer över tid:** startvärdet gäller 2026; från 2027 till 2100 årlig förändring i procent per period
  (2027–2030, 2031–2035, 2036–2040, 2041–2045, 2046–2050, 2051–2060, 2061–2070, 2071–2100). Elbilar och laddhybrider i procentenheter.
- **Byggbestånd som andelar:** varje andel har byggnadstyp, en stomme, BTA, utbyggnadstakt och egna energival:
  energiklass (Boverket), andel fjärrvärme för fastighetsvärmen (resten värmepump/el) och valfri egen köpt el och fjärrvärme per m² BTA.
- **Stommar:** Generisk (= Betong BAU), Betong BAU, Betong BÄST, Stål BAU, Stål BÄST, Trä BAU, Trä BÄST. Startvärden och kurvor ur
  Tabell A utökad (`underlag/tabell_a_utokad.xlsx`): BAU = SBUF 14381 Insteg, BÄST = SBUF 14381 Färdplan, startvärden Malmqvist m.fl. 2023.
  Generisk följer alltid Betong BAU, både värde och kurva. Lokaler och underjordisk parkering använder kontorets värden (proxy).
- **Kolinlagring i trästomme:** för Trä BAU och Trä BÄST, −(BTA × v × F_produkt), fördelat över byggtiden. F enligt EN 16449:
  stomvirke 720,7, limträ 786,0, KL-trä 680,7 kg CO2/m³. Schablon: stomvirke för Trä BAU, limträ för Trä BÄST, v = 0,15 m³/m² BTA.
  Inget krav på CCF-certifikat.
- **Grundläggning:** pålning 26 kg CO2e/m² BTA; spontyta 0 m² som standard (280,5 kg/m²). Båda redovisas under Anläggning.
- **Anläggning:** följer Betong BAU:s kurva som standard; engångsvärden räknas som angivna.
- **El (0.14.0):** tre val, `scen["utveckling"]["el_val"]`: Boverket 37 g CO2e/kWh med EU:s referensscenario 2020 (standard, raden `el`);
  IEA handelskorrigerad 26 g CO2e/kWh (IEA:s timdata för Sverige 2025/26, 9,4 g vid förbränning, plus livscykel och nätförluster;
  sammansatt IEA-kurva, raden `el_iea`); eget startvärde `el.startvarde_egen` med Sveriges WEM-prognos (raden `el_wem`).
  Samma elfaktor i hela modellen (byggnader, elbilar, solel), i OP (`EL_ALT` i `model.js`, även elbilarnas laddel ur Vägvis) och i Vägvis 2.4.0.
- **Fjärrvärme:** ortens värde (användaren anger), förändring enligt EU:s referensscenario 2020.
- **Mobilitet:** de boendes bilar: hushåll × bilar per hushåll × körsträcka; livscykelfaktor per drivlina (ICCT 2025, direktiv 2015/652).
  Drivlinemix 2025 (Trafikanalys). Bilproduktionen följer den globala elens klimatfaktor (IEA). Bilar per hushåll och körsträcka
  är kommunens värden som standard; användaren kan föra över värdena för planens DeSO från Vägvis 2.3.1 (sidan Trafik & geodata).
- **Geografi:** planen beskrivs med SCB:s DeSO 2025 (`geografi.kommunkod`, `geografi.deso`). Valet styr kartorna och påverkar
  beräkningen först när bilinnehavet förs över till mobiliteten. DeSO-underlaget finns för Malmö, Helsingborg och Gävle.
- **Mat:** kostprofiler med andelar och avtryck ur EPIC-Oxford-kohorten (Scarborough m.fl. 2023), redovisade som en delpost per
  kostprofil och som standard kalibrerade till svensk nivå 1,75 t per invånare och år (svenska LCA-studier, Bälter m.fl. 2017);
  utveckling enligt den svenska trenden för livsmedel per person, −1,73 % per år (Naturvårdsverket 2008–2023).
- **Övrig konsumtion:** sju kategorier ur Konsumtionskompassen 2.1, ändringsbara; följer bilproduktionens kurva (globalt elsnitt).
- **Flygresor:** egen kategori, 0,88 t per invånare (Kamb och Larsson 2018: 1,1 t år 2017 med höghöjdseffekt, gånger 0,8 för
  resandet efter pandemin enligt Transportstyrelsen); redovisas som två delposter, koldioxid från bränslet och höghöjdseffekt
  (faktor 170/90 ≈ 1,89). Utveckling enligt ReFuelEU Aviation (hållbart flygbränsle, antagen livscykelminskning 70 %, bara på
  koldioxiden) och bränsleeffektivitet −1,5 % per år (IATA).
- **Offentlig sektor:** offentlig konsumtion plus bara den offentliga andelen av investeringarna; följer EU:s klimatmål
  (−55 % 2030, −90 % 2040 jämfört med 1990).
- **Mark:** Skogskolmodellen 10.4 för skog; åker, gräsmark och urban grönyta med kolförråd per pool som användaren kan ändra.
  Våtmark och befintlig bebyggelse ingår inte.
- **Klimatbudget:** Forster m.fl. 2026, uppräknad för andra växthusgaser (56,8/43,2), fördelad lika per person på de invånare som
  faktiskt bor i området år för år. Resultatfliken jämför också snittet per person och år för en vald analysperiod (standard
  2027–2050) med budgetutrymmet per person för valfri temperatur (1,5–2,0 °C) och sannolikhet.
- **Standardprojektet:** BTA per byggnadstyp ur underlaget, utbyggnad 2030–2045; varje typ 50 % Trä BÄST klass A, 25 % Betong BAU
  klass C, 25 % Betong BÄST klass A. Anläggning ur planskissens färgytor skalade till 401 000 m², minus byggnadernas BYA.
  3 000 stadsträd i jämn takt 2030–2045. Förändrad markanvändning är inte ifylld.

- **Rättvis jämförelse (CityScenario):** funktionsuppdelning (boende och närservice per invånare, verksamheter per arbetsplats;
  parkering, anläggning, mark och träd fördelas efter BTA), lika förutsättningar (alla förändringstakter 0, faktorer på 2026 års nivå),
  livscykel per år (engångsutsläpp / 50 år + ett års drift vid full utbyggnad), standardiserad blandning och exakt uppdelning i
  yta och intensitet (`road2zero/jamforelse.py`).
- **Road2Zero-OP:** beräkningen per DeSO för hela staden körs i webbläsaren (`op/app/model.js`, från MalmoOP 1.2): energi i befintliga
  byggnader ur energideklarationer, mobilitet ur Vägvis 2.3.1 (modell A eller B, adderas aldrig) och exploatering enligt
  översiktsplanens utbyggnadsområden 2030–2050. Sidan Resultat & klimatbudget (`op/app/resultat.js`) visar samma resultatvy som
  Plan med samma kategorier, färger och budget (Forster m.fl. 2026, 1,5–2,0 °C enligt Parisavtalet); budgetperioden är 2026–2050.
  Budgettabell, befolkning, påslag och färger läses från `road2zero/data` och `road2zero/konstanter.py` när sidan byggs, och
  Plotly.js från Python-paketet plotly, så att diagrammen ser ut som i Plan.
  Emissionsfaktorer över tid (MalmoOP 1.3): el och fjärrvärme som i Plan, startvärde till och med 2026 och årlig förändring per
  period, standard EU:s referensscenario 2020 (`UTV` i `model.js`; testet jämför med `road2zero/data/utveckling.csv`). Sysavs
  koldioxidavskiljning är ett valbart steg för fjärrvärmen (av som standard; 2030, −43 %). Klimattrappa för nybyggnation: Boverkets
  gränsvärden 2030 (standard), Boverkets färdplan, linjär bana, SBUF Insteg, SBUF Färdplan, referensvärden eller egen takt.
  Budgettilldelning (0.12.0): de valda kategorierna jämförs med sin andel av budgeten, a_g = gruppens utsläpp per person / hela
  fotavtrycket (hushåll + offentlig konsumtion + investeringar). Grupper: boende = Energi; investeringar = Byggnad och Förändrad
  markanvändning (nybyggnation hör till investeringarna oavsett byggherre, aldrig till hushållens boende), × nybyggnationens andel
  av investeringarnas utsläpp n (0.12.1: 21,1 % = F41–F43 / fasta bruttoinvesteringar, SCB 2023 × (bostäder + lokaler) /
  bygginvesteringar, Byggföretagen 2023 × nybyggnad / (nybyggnad + ombyggnad), Boverket 2015; `nybyggnadsandel.csv`);
  transport = Mobilitet och transport, hushållens transport minus flyget.
  Värden i `road2zero/data/budgetandelar.csv` (Konsumtionskompassen 2022 för Malmö, Skåne och Sverige; offentligt och
  investeringar SEI 2026). Standard Malmö (27,8 %); val: Skåne, Sverige, egna andelar, hela budgeten (faktor 1).
  Stadens klimatredovisning (0.13.0, `op/app/stad.js`, `op/projekt/<id>/data/klimatbokforing.json`): sidorna GHG Protocol for
  Cities och Stadens klimatbokföring. Ändrar inte OP:s beräkning. Trafiken alltid territoriellt (Vägvis A, bara avgaser = scope 1);
  fjärrvärmen som i klimatkontraktet (produktionen i scope 1, energiindustri, ingår i summan); el i scope 2 = SCB:s el utom
  transporter × den valda elfaktorn; industri, sjöfart/järnväg/flyg, arbetsmaskiner, produktanvändning, avfall och jordbruk börjar
  på Miljöbarometerns 2024 och förändras med egen takt (standard 0 %); energisektorn följer fjärrvärmens index. Speglas mot
  Miljöbarometern och klimatkontraktet, kalibreras inte. Mål 2030 mot 1990: −70 % (staden), −80 % (EU-missionen); budget 6 600 kt.
  Resultaten redovisas i de officiella kategorierna (0.13.1): klimatkontraktets fem kategorier × scope, GPC:s undersektorer med IE/NE,
  Miljöbarometerns åtta sektorer; skillnaderna förklaras per kategori och en brygga går från OP:s klimatavtryck till territoriellt och GPC.
  Jämför räknesätten (0.15.0, vy `jamfor` i `stad.js`, sida 05): `jamforelse(res, j)` summerar utsläppskällorna (`KALLOR`) per
  räknesätt för en period (standard 2027–2050) eller ett år, GPC som BASIC+ (standard) eller BASIC. Klimatavtrycket med perspektiv A
  och alla kategorier; per invånare = medel av årens värden. Kolumnen om vad översiktsplanen kan påverka är en bedömning (modellval).
  Datakällor (0.15.1, användarens val): standard egen källa per räknesätt, valbart samma trafikmodell (Vägvis A, som 0.15.0).
  Klimatavtrycket följer sidomenyn (A eller B, `mobDelar`); bokföringens vägtrafik på Miljöbarometerns nivå; GPC valbart Miljöbarometern,
  klimatkontraktets transport (SMED, standard) eller hela klimatkontraktet. Källfaktorer ur underlaget (`kallfaktorer` i `berakna`):
  källans nivå samma år delat med modellens eller Miljöbarometerns; utvecklingen följer modellen. Sidorna 03 och 04 räknar som förut.
  Energi i byggnader valbar (0.16.0, `energiVal` 'med' (standard) | 'utan'): `aktiva(P)` i `model.js` styr vilka komponenter som ingår i
  `view().total`, `exploatering` och `cityByYear().total`; `totalAlla` tar alltid med alla. Komponenterna beräknas alltid. Lokaliseringskartan
  visas utan energi (användarens förslag till Malmö stad); laddelen ligger kvar i mobiliteten; sidorna 03–05 tar alltid med energin.
  Fordonsflottan (0.16.1, `flottaVal` 'nv2026' (standard) | 'oforandrad' | 'egen'): mobiliteten delas i bränslekedja (ttw + wtt − el),
  laddel och tillverkning ur Vägvis underlag. Bränslekedjan följer `UTV.flotta_nv2026` (Naturvårdsverket 2026, tabell 4, inrikes transporter
  med beslutade styrmedel, delat med trafikarbetet +0,87 %/år enligt Trafikverket 2026; 2046–2050 som 2041–2045), laddelen elvalet och
  tillverkningen `UTV.bilprod` (global el, IEA). 'oforandrad' och 'egen' skalar hela livscykelfaktorn som i 1.3. Standard 2050: 180,0 kt (A).
  Lokaliseringskartan (0.16.2, `R.tillkommande`, `tillkommande()` i `model.js`): per DeSO klimatpåverkan per ny bostad och arbetsplats
  2030–2050 (trafik, bygg, mark, energi; energin i summan bara med `energiVal` 'med'); kartans nyckeltal `ny_bostad` och `ny_arbetsplats`
  (alltid per enhet, enhetsvalet avstängt), flaggor T och M (`flaggor()`, `FLAGG_T` 1,25). Parametrar `nyTyp`, `btaSmahus`, `byggSmahusFaktor`,
  `tathetFbh`, `tathetSmahus`, `nyArbTyp`, `tathetArb`, `nyMark` ('op' = ÖP-områdenas marktäcke i DeSO:n, annars bebyggd). Arbetsplatstrafik saknas ännu.

## Kända osäkerheter

- Fullständig referens till Dodoo m.fl. 2026 saknas.
- Boverkets rapport 2026:16 är inte genomläst.
- Riksgenomsnitt för markkol 0–50 cm saknas; gräsmark och urban grönyta använder SLU:s länsvärde för Uppsala.
- DeSO för Malmöfallen och standardprojektet är förslag som användaren ska kontrollera på kartan.
- Road2Zero-OP har text som gäller Malmö i `op/app/app.js`; en ny stad kräver att texterna läses igenom.

## Arbetsgång vid ändringar

1. Större ändringar: börja i planläge och beskriv vad som ändras innan filer ändras.
2. Ändra data i `road2zero/data/`, logik i `road2zero/`, gränssnitt i `gemensamt/`, `plan/` och `cityscenario/`; OP i `op/`.
3. Uppdatera `algoritmer.py` när en formel ändras och `README.md` när ett modellbeslut ändras.
4. Kör `python -m pytest -q`. Justera förväntade värden i testerna bara när ändringen är avsiktlig, och säg vilka som ändrades och varför.
5. Starta apparna och titta på de sidor som berörs.
6. Höj `__version__` i `road2zero/__init__.py` (0.x.y) och skriv commit-meddelandet på svenska.
