# Road2Zero

<img src="gemensamt/logo.svg" width="72" align="right" alt="Road2Zero">

Road2Zero är en familj av evidensbaserade klimatmodeller för staden. Alla tre har samma logotyp, samma mörkgröna meny och samma
förklaringssidor (**Karta & områden, Så räknas resultatet, Antaganden & scenario, Trafik & geodata, Metod & källor**), och alla visar
kartor med DeSO-områden och OpenStreetMap i bakgrunden.

| Modell | Huvudfil | Använd när du vill … |
|---|---|---|
| **Road2Zero-OP** | `op/streamlit_app.py` | se hela stadens klimatavtryck per DeSO enligt översiktsplanen: energi i befintliga byggnader, mobilitet och utbyggnaden 2030–2050. Ett projekt per stad i `op/projekt/`; först **Malmö_ÖP**. |
| **Road2Zero-Plan** | `plan/streamlit_app.py` | analysera en plan i detalj (till exempel Jägersro): tio klimatkategorier år för år mot en koldioxidbudget. |
| **Road2Zero-CityScenario** | `cityscenario/streamlit_app.py` | testa planer mot varandra, i samma eller olika stadsdelar, med rättvis jämförelse. Indata från JSON eller Excel. |

Plan och CityScenario räknar med samma motor (`road2zero/`) och jämför nettoutsläppen med en vetenskapligt baserad
koldioxidbudget (Forster m.fl. 2026), fördelad lika per person på de invånare som faktiskt bor i området. Alla schabloner är
förifyllda och varje värde hänvisar till en publicerad källa eller är tydligt markerat som modellval. Road2Zero-OP bygger på
MalmoOP 1.2 och räknar i webbläsaren.

Bilinnehavet per DeSO kommer från **Vägvis 2.3.1** ([Mulmen65/vagvisa](https://github.com/Mulmen65/vagvisa)): hushåll, invånare och
personbilar per DeSO 2024 ur SCB:s register och körsträcka per bil per kommun. I Plan och CityScenario väljer du planens DeSO på
kartan och kan föra över bilinnehavet till mobiliteten (sidan Trafik & geodata). Vägvis ändras inte; underlaget läses in med
`verktyg/hamta_vagvis.py`.

## Mappar

```
road2zero/          beräkningsmotorn för Plan och CityScenario (oberoende av Streamlit)
gemensamt/          gemensamt gränssnitt: logotyp, meny, förklaringssidor, karta, DeSO-underlag, indata- och resultatsidor
plan/               Road2Zero-Plan            (streamlit_app.py)
cityscenario/       Road2Zero-CityScenario    (streamlit_app.py, scenarier.py, ui_jamforelse.py)
op/                 Road2Zero-OP              (streamlit_app.py, app/, projekt/malmo_op/, tools/, tests/)
fall/               färdiga fall för CityScenario (Västra hamnen, Varvsstaden, Jägersro SMT)
verktyg/            skript som bygger faktabibliotek, standardprojekt, fall och DeSO-underlag
underlag/           källfiler som skripten läser; visas inte i apparna
tests/              tester för motorn och gränssnittet
streamlit_app.py    kör Road2Zero-Plan (för äldre publiceringar)
```

## Kör lokalt

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run plan/streamlit_app.py                    # eller cityscenario/streamlit_app.py eller op/streamlit_app.py
```

Startskripten tar appens namn: `./starta_mac_linux.sh cityscenario` eller `starta_windows.bat op` (standard är `plan`).

## Publicera på Streamlit Community Cloud

Skapa en app per modell från samma repo (`Mulmen65/road2zero`, grenen `main`), med huvudfilen `plan/streamlit_app.py`,
`cityscenario/streamlit_app.py` eller `op/streamlit_app.py`. Python 3.12 eller senare; testat med Python 3.13 och Streamlit 1.66.
Varje push till `main` uppdaterar alla tre.

## Road2Zero-Plan

Menyn: **Översikt** (nyckeltal, vägen mot noll, summa per kategori, planområdet på kartan), **Indata** (moduler 0–8 och
klimatbudget), **Resultat** (välj redovisningsnivå, klimatkategorier, analysperiod och flygets höghöjdseffekt; översikt, över tid,
per person, klimatbudget, tabeller och export, källor och beräkning) och förklaringssidorna. Indata sparas och öppnas som JSON eller
Excel från sidopanelen.

## Road2Zero-CityScenario

Välj överst på sidorna vilket av scenario A, B och C du ändrar; alla indata, emissionsfaktorer över tid och egna parametrar gäller
det valda scenariot. **Jämförelse** och **Rättvis jämförelse** visar alla tre sida vid sida. I sidopanelen läser **Öppna fil** en
JSON- eller Excel-fil: en fil med alla tre scenarier läses till A, B och C, en fil med ett scenario till det valda. Spara alla tre
eller ett i taget som JSON eller Excel, kopiera ett scenario till ett annat eller hämta ett färdigt fall ur `fall/`.

**Excel:** arbetsboken har bladet *Värden* (alla enskilda värden, Scenario · Sökväg · Värde), bladet *Utveckling* (årlig förändring
per faktor och period), ett blad per lista (till exempel *byggnader* och *anlaggning.ytor*, en rad per post) och bladet *Läs mig*.
Spara en arbetsbok från appen och använd den som mall. Värden som saknas får standardvärden när filen läses in.

## Road2Zero-OP

Varje stad eller plan är ett projekt i `op/projekt/<id>/` med `projekt.json` (namn, kommun, rubriker) och `data/`. Appen visar en
rullista när det finns fler än ett projekt. Sidan **Underlag** laddar ned underlaget eller läser in nya energideklarationer.

Lägg till en stad:
1. Kopiera `op/projekt/malmo_op/` till `op/projekt/<ny_id>/` och ändra `projekt.json`.
2. Byt filerna i `data/kalla/` (DeSO-gränser, energideklarationer, OSM-byggnader, utbyggnadsområden, Vägvis-underlag för kommunen).
3. Bygg underlaget med projektet valt: `R2Z_OP_PROJEKT=op/projekt/<ny_id> python op/tools/build_energi.py` (och de andra skripten i
   `op/tools/`; `node op/tools/build_mobilitet.js` för mobiliteten).
4. Läs igenom texterna i `op/app/app.js`, som på några ställen gäller Malmö.

## Byggbeståndet

Varje rad är en andel av byggbeståndet: en byggnadstyp, en stomme och en BTA, med egen energiklass, andel fjärrvärme och värmepump för fastighetsvärmen, valfri egen köpt el och fjärrvärme per m² BTA, och solceller. Byggpåverkan och energi hör alltså alltid till samma BTA.

- **Stomme:** Generisk (= Betong BAU), Betong BAU, Betong BÄST, Stål BAU, Stål BÄST, Trä BAU eller Trä BÄST. Rullistan visar förifylld byggpåverkan i kg CO2e/m² BTA för den valda byggnadstypen (A1–A5) ur Tabell A utökad, med SBUF-kategori/proxy och startankare (BAU = SBUF 14381 Insteg, BÄST = SBUF 14381 Färdplan; startvärden enligt Malmqvist m.fl. 2023). Tabellens värde gäller 2026 och följer stommens index under Antaganden & scenario → Emissionsfaktorer över tid för året då BTA:n blir klar.
- **Kolinlagring i trästomme:** för Trä BAU och Trä BÄST räknas −(BTA × v × F_produkt) som negativt utsläpp, fördelat över byggtiden. F_produkt är bundet kol per m³ enligt EN 16449: stomvirke 720,7, limträ 786,0 och KL-trä 680,7 kg CO2/m³. Schablon: stomvirke för Trä BAU, limträ för Trä BÄST och v = 0,15 m³/m² BTA. Både träprodukt och mängd virke kan väljas.
- **Energi:** energiklassen ger köpt fjärrvärme och el per m² Atemp för byggnadstypens kategori i Boverkets byggregler. Klass C motsvarar nybyggnadskravet och är förvald. Fastighetsvärmen delas mellan fjärrvärme och värmepump (el) i procent. Egen köpt el och egen köpt fjärrvärme anges per m² BTA och ersätter klassens värden. Garage, industri och övriga byggnader är uppvärmda eller ouppvärmda och har bara el.
- **Utbyggnadstakt:** färdigställd BTA per år och andel; jämn, framtung, baktung eller egen tabell.

Formuläret *Lägg till byggbestånd* fördelar en byggnadstyps BTA på flera stommar, och varje rad blir en egen andel med egna energival.

## Emissionsfaktorer över tid

Varje faktor har ett startvärde som gäller 2026 och en årlig förändring i procent per period: 2027–2030, 2031–2035, 2036–2040, 2041–2045, 2046–2050, 2051–2060, 2061–2070 och 2071–2100. Negativt värde betyder minskning. Elbilar och laddhybrider ökar i procentenheter av körsträckan per år och kan tillsammans bli högst 100 %.

| Faktor | Standard | Källa |
|---|---|---|
| Byggpåverkan per stomme | Kurvorna i Tabell A utökad (SBUF 14381 till 2035, försiktig extrapolering till 2070, därefter 0 %); Generisk följer Betong BAU | Tabell A utökad, SBUF 14381 |
| Anläggning | Samma som Betong BAU | Modellval enligt beställning |
| El, tre val | **Boverket** (standard): 37 g CO2e/kWh, EU:s referensscenario 2020 till 2050, därefter samma takt. **IEA handelskorrigerad**: 26 g CO2e/kWh med livscykel och nätförluster, −6,68 % per år 2027–2030 och därefter −3,7 %. **Eget startvärde**: användarens värde, Sveriges WEM-prognos (−8,2 % per år 2027–2030, −1,69 %, −0,91 %, därefter 0 %) | Boverket; EU Reference Scenario 2020; IEA timdata 2025/26 och Electricity 2026; Naturvårdsverket 2025 (WEM) |
| Fjärrvärme | EU:s referensscenario 2020 till 2050, därefter oförändrad | EU Reference Scenario 2020 |
| Bilproduktion och övrig konsumtion | Global elens klimatfaktor −3,7 % per år | IEA Electricity 2026 |
| Elbilar och laddhybrider | +3,0 respektive +1,7 procentenheter per år | Trafikanalys, körsträckor 2024 och 2025 |
| Bilar per hushåll, körsträcka, förbränningsbilar | 0 % | Användarval |
| Matkonsumtion | −1,73 % per år | Naturvårdsverket: livsmedel per person −23 % 2008–2023 |
| Flyg | −1,9 till −4,1 % per år till 2050, sedan −1,5 % | ReFuelEU Aviation (hållbart flygbränsle 6–70 %) och bränsleeffektivitet (IATA) |
| Offentlig sektor | −5,74 % per år 2027–2030, −13,96 % per år 2031–2050, därefter 0 % | EU:s klimatlag: −55 % 2030, −90 % 2040; EEA 2025 |

Elvalet görs under Antaganden & scenario → Emissionsfaktorer över tid och gäller hela modellen: byggnadernas el, elbilarnas laddning och solel. Samma tre val finns i Road2Zero-OP och i Vägvis 2.4.0. IEA-värdet bygger på IEA:s handelskorrigerade timvärden för Sverige juli 2025–juni 2026 (9,4 g CO2/kWh vid förbränning, viktat med SCB:s elanvändning) plus livscykel för vatten-, kärn-, vind- och solkraft och nätförluster. Äldre sparade filer med eget startvärde öppnas som Eget startvärde med sin tidigare kurva.

## Arbeta med Claude Code

- `CLAUDE.md` innehåller modellbesluten och arbetsreglerna för alla tre modeller. Claude Code läser filen i början av varje session.
- `.claude/skills/uppdatera-tabell-a/` är en projekt-skill: skriv `/uppdatera-tabell-a` när en ny version av Tabell A utökad ska
  läsas in.
- Claude arbetar på en egen gren och pushar den; du godkänner sammanslagningen till `main`.

## Tester

```bash
pip install -r requirements-dev.txt
python -m pytest -q              # motor, gränssnitt, Excel, DeSO-underlag och Road2Zero-OP:s sidbygge
node op/tests/test_model.js      # Road2Zero-OP:s beräkningar
```

## Spara och öppna indata

Indata sparas som JSON eller Excel från sidopanelen och kan öppnas igen. Filen innehåller modellversionen. Nycklar som saknas fylls
med standardvärden när filen öppnas, så att äldre filer fortsätter att fungera. Egna nycklar, till exempel en `dokumentation` med
källor och antaganden, behålls i JSON. Resultatexporten (Excel) har också indata i bladet Indata, en JSON-rad per rad.

## Färdiga fall

`fall/vastra_hamnen.json` (2000–2050), `fall/varvsstaden.json` (2020–2050) och `fall/jagersro_smt.json` (2030–2050) öppnas från sidopanelen; i Road2Zero-CityScenario finns de i rullistan **Färdigt fall**, och knappen **Hämta Malmöfallen till A, B och C** läser `fall/malmofallen.json` med alla tre på en gång. Alla tre har samma schabloner för arbetsplatser, närservice, mobilitetshus, gator och fjärrvärme, så att de kan jämföras. Varje fil har en `dokumentation` med källor, kalibrering och status per andel (Uppgift, Kalibrerat eller Antagande). Varje fall har också förslag på de DeSO det ligger i (kontrollera på kartan). Filerna byggs av `python verktyg/bygg_malmofall.py`; ändra skriptet och kör det igen för att uppdatera fallen.

## Jämföra stadsdelar

```bash
python verktyg/jamfor_stadsdelar.py fall/a.json fall/b.json fall/c.json --referens 3 --ut jamforelse.xlsx
```

Samma beräkning som sidan Rättvis jämförelse i Road2Zero-CityScenario. Verktyget delar nivå 1 på funktion: bostäder och närservice (skolor) per invånare, verksamheter per arbetsplats (20 m² BTA per arbetsplats); parkering, anläggning, mark och stadsträd fördelas efter BTA. Det räknar både med lika förutsättningar (alla emissionsfaktorer på 2026 års nivå, så att bara utformningen skiljer) och med faktisk tidpunkt. Engångsutsläpp fördelas på 50 år och läggs till ett års drift vid full utbyggnad. Den standardiserade stadsdelen väger varje stadsdels intensitet per m² med referensfallets fördelning mellan bostäder och verksamheter.

## Befintliga stadsdelar

Startåret kan sättas från 1990, så att en stadsdel kan räknas från första spadtaget. År före 2026 använder startvärdena 2026 för alla emissionsfaktorer (ingen bakåtskrivning), så utsläppen före 2026 blir en undre skattning. Klimatbudgeten börjar 2026; jämför därför också perioden från 2026 när fall med olika startår jämförs.
