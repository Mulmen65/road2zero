# Road2Zero

Klimatberäkning för stadsdelar utan karta. Modellen räknar tio klimatkategorier år för år och jämför nettoutsläppen med en vetenskapligt baserad koldioxidbudget (Forster m.fl. 2026), fördelad lika per person på de invånare som faktiskt bor i området.

Appen startar med ett tomt projekt. Alla schabloner är förifyllda och varje värde hänvisar till en publicerad källa eller är tydligt markerat som modellval.

## Flikar

| Flik | Innehåll |
|---|---|
| Indata | Moduler 0–8 och klimatbudget. Byggbeståndet anges som andelar med egen byggnadstyp, stomme och egna energival. |
| Emissionsfaktorer över tid | Startvärden 2026 och årlig förändring i procent per period 2027–2100 för byggpåverkan per stomme, anläggning, el, fjärrvärme, bilproduktion, förbränningsbilar, el- och laddhybridbilar, bilinnehav, körsträcka, mat, övrig konsumtion, flyg och offentlig sektor. |
| Resultat | Nyckeltal, tabell per klimatkategori, delposter, tabell per år, klimatbudget, export till CSV och Excel. |
| Illustration | Utsläpp per år, vägen mot noll mot budgeten, summa per kategori, vattenfall, per invånare och flöden från modul till kategori. |
| Beräkningar | Formler, steg, parametrar och mellanled för varje modul. |
| Faktorer och parametrar | Hela faktabiblioteket med värde, enhet, statusklass och källa. Egna värden kan anges per parameter. |
| Referenser | Alla källor, grupperade, med länk och var de används. |

## Byggbeståndet

Varje rad är en andel av byggbeståndet: en byggnadstyp, en stomme och en BTA, med egen energiklass, andel fjärrvärme och värmepump för fastighetsvärmen, valfri egen köpt el och fjärrvärme per m² BTA, och solceller. Byggpåverkan och energi hör alltså alltid till samma BTA.

- **Stomme:** Generisk (= Betong BAU), Betong BAU, Betong BÄST, Stål BAU, Stål BÄST, Trä BAU eller Trä BÄST. Rullistan visar förifylld byggpåverkan i kg CO2e/m² BTA för den valda byggnadstypen (A1–A5) ur Tabell A utökad, med SBUF-kategori/proxy och startankare (BAU = SBUF 14381 Insteg, BÄST = SBUF 14381 Färdplan; startvärden enligt Malmqvist m.fl. 2023). Tabellens värde gäller 2026 och följer stommens index i fliken Emissionsfaktorer över tid för året då BTA:n blir klar.
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
| El | EU:s referensscenario 2020 till 2050, därefter samma takt | EU Reference Scenario 2020 |
| Fjärrvärme | EU:s referensscenario 2020 till 2050, därefter oförändrad | EU Reference Scenario 2020 |
| Bilproduktion och övrig konsumtion | Global elens klimatfaktor −3,7 % per år | IEA Electricity 2026 |
| Elbilar och laddhybrider | +3,0 respektive +1,7 procentenheter per år | Trafikanalys, körsträckor 2024 och 2025 |
| Bilar per hushåll, körsträcka, förbränningsbilar | 0 % | Användarval |
| Matproduktion | −1,30 % per år | FAO 2025 (utsläppsintensitet −25 % 2001–2023) |
| Flyg | −1,8 % per år | IATA: bränsleeffektivitet och hållbart flygbränsle |
| Offentlig sektor | −5,74 % per år 2027–2030, −13,96 % per år 2031–2050, därefter 0 % | EU:s klimatlag: −55 % 2030, −90 % 2040; EEA 2025 |

## Arbeta med Claude Code

- `CLAUDE.md` innehåller modellbesluten och arbetsreglerna. Claude Code läser filen i början av varje session.
- `.claude/skills/uppdatera-tabell-a/` är en projekt-skill: skriv `/uppdatera-tabell-a` i Claude Code när en ny version av
  Tabell A utökad ska läsas in.
- `verktyg/las_tabell_a.py` läser `underlag/tabell_a_utokad.xlsx` till faktabiblioteket.
- Varje push till grenen `main` på GitHub uppdaterar appen på Streamlit Community Cloud.

## Kör lokalt

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Publicera på Streamlit Community Cloud

1. Lägg mappen i ett GitHub-repo.
2. Gå till share.streamlit.io, välj **Create app** och sedan repot och grenen.
3. Ange `streamlit_app.py` som huvudfil. Python 3.12 eller senare fungerar; appen är testad med Python 3.13 och Streamlit 1.66.

## Struktur

```
CLAUDE.md                 instruktioner och modellbeslut för Claude Code
streamlit_app.py          start och flikar
scenario_app.py           road2zero-scenario: tre scenarier mot varandra
app/                      gränssnittet, en fil per flik
road2zero/                beräkningsmotorn (oberoende av Streamlit)
  engine.py               berakna(indata) -> Resultat
  jamforelse.py           rättvis jämförelse av scenarier
  scenario.py             indatamodell, standardvärden, validering, JSON
  modules/                en modul per indatamodul och klimatbudget
  algoritmer.py           formler och text för fliken Beräkningar
  data/                   faktabiblioteket (CSV och JSON)
tests/                    regressionstester
verktyg/                  skript som läser underlag till faktabiblioteket och bygger färdiga fall
fall/                     färdiga fall att öppna i appen (Västra hamnen, Varvsstaden och Jägersro SMT i Malmö)
underlag/                 källfiler (Tabell A utökad), visas inte i appen
```

Faktabiblioteket ligger i `road2zero/data/`. Varje rad har en kolumn `kalla` med id i `referenser.csv`. Byt eller lägg till ett värde genom att ändra CSV-filen; testerna kontrollerar att varje käll-id finns.

## Tester

```bash
pip install pytest
python -m pytest -q
```

Testerna kontrollerar ett påhittat testfall, att andelar med olika stommar och energival räknas var för sig, att äldre sparade indata med två stommar per rad läses in som andelar, att faktabiblioteket är konsistent och att gränssnittet bara hänvisar till publicerade källor.

## Spara och öppna indata

Indata sparas som JSON från sidopanelen och kan öppnas igen. Filen innehåller modellversionen. Nycklar som saknas fylls med standardvärden när filen öppnas. Egna nycklar, till exempel en `dokumentation` med källor och antaganden, behålls när filen sparas igen. Excel-exporten har indata i bladet Indata, en JSON-rad per rad (`fortsatter` = 1 betyder att raden fortsätter på nästa).

## Färdiga fall

`fall/vastra_hamnen.json` (2000–2050), `fall/varvsstaden.json` (2020–2050) och `fall/jagersro_smt.json` (2030–2050) öppnas från sidopanelen; i road2zero-scenario finns de i rullistan **Färdigt fall**, och knappen **Hämta Malmöfallen till A, B och C** läser `fall/malmofallen.json` med alla tre på en gång. Alla tre har samma schabloner för arbetsplatser, närservice, mobilitetshus, gator och fjärrvärme, så att de kan jämföras. Varje fil har en `dokumentation` med källor, kalibrering och status per andel (Uppgift, Kalibrerat eller Antagande). Filerna byggs av `python verktyg/bygg_malmofall.py`; ändra skriptet och kör det igen för att uppdatera fallen.

## road2zero-scenario: tre scenarier mot varandra

```bash
streamlit run scenario_app.py
```

Ett eget verktyg i samma repo. Välj överst vilket av scenario A, B och C du ändrar; alla indataflikar, emissionsfaktorer över tid och egna parametrar från Road2Zero gäller det valda scenariot. Flikarna **Jämförelse** och **Rättvis jämförelse** visar alla tre sida vid sida och uppdateras direkt när indata ändras. I sidopanelen läser **Öppna fil** en fil med alla tre scenarier till A, B och C, eller en fil med ett scenario (samma JSON-format som Road2Zero) till det valda scenariot. Där sparar du också alla tre eller ett scenario i taget, kopierar ett scenario till ett annat och hämtar ett färdigt fall ur `fall/`. En fil med tre scenarier kan inte öppnas i Road2Zero, som bara har ett scenario; appen säger då till. På Streamlit Community Cloud skapar du en ny app från samma repo med huvudfilen `scenario_app.py`.

## Jämföra stadsdelar

```bash
python verktyg/jamfor_stadsdelar.py fall/a.json fall/b.json fall/c.json --referens 3 --ut jamforelse.xlsx
```

Samma beräkning som fliken Rättvis jämförelse i road2zero-scenario. Verktyget delar nivå 1 på funktion: bostäder och närservice (skolor) per invånare, verksamheter per arbetsplats (20 m² BTA per arbetsplats); parkering, anläggning, mark och stadsträd fördelas efter BTA. Det räknar både med lika förutsättningar (alla emissionsfaktorer på 2026 års nivå, så att bara utformningen skiljer) och med faktisk tidpunkt. Engångsutsläpp fördelas på 50 år och läggs till ett års drift vid full utbyggnad. Den standardiserade stadsdelen väger varje stadsdels intensitet per m² med referensfallets fördelning mellan bostäder och verksamheter.

## Befintliga stadsdelar

Startåret kan sättas från 1990, så att en stadsdel kan räknas från första spadtaget. År före 2026 använder startvärdena 2026 för alla emissionsfaktorer (ingen bakåtskrivning), så utsläppen före 2026 blir en undre skattning. Klimatbudgeten börjar 2026; jämför därför också perioden från 2026 när fall med olika startår jämförs.
