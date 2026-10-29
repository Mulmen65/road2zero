# Road2Zero

Klimatberäkning för stadsdelar utan karta. Modellen räknar tio klimatkategorier år för år och jämför nettoutsläppen med en vetenskapligt baserad koldioxidbudget (Forster m.fl. 2026), fördelad lika per person på de invånare som faktiskt bor i området.

Appen startar med standardprojektet Jägersro (Svensk Travsports del, utbyggnad 2030–2045); sidopanelen kan också börja med ett tomt projekt. Alla schabloner är förifyllda och varje värde hänvisar till en publicerad källa eller är tydligt markerat som modellval.

## Flikar

| Flik | Innehåll |
|---|---|
| Indata | Moduler 0–8 och klimatbudget. Byggbeståndet anges som andelar med egen byggnadstyp, stomme och egna energival. |
| Emissionsfaktorer över tid | Startvärden 2026 och årlig förändring i procent per period 2027–2100 för byggpåverkan per stomme, anläggning, el, fjärrvärme, bilproduktion, förbränningsbilar, el- och laddhybridbilar, bilinnehav, körsträcka, mat, övrig konsumtion, flyg och offentlig sektor. |
| Resultat | Välj vilka klimatkategorier som ska ingå (förvalt efter redovisningsnivå) och om flygets höghöjdseffekt ska räknas med. Nyckeltal och underflikar: Översikt (summa per kategori, vattenfall, trädkarta med delposter, bland annat kosten per kostprofil), Över tid (per år, ackumulerat, en panel per kategori), Per person (t CO2e per person och år, ackumulerat per person och snitt för en valbar analysperiod, standard 2027–2050, jämfört med budgetandelen), Klimatbudget (snitt per person mot budgetutrymmet per person för valfri temperatur 1,5–2,0 °C och sannolikhet, inklusive andra växthusgaser, samt ackumulerat mot stadsdelens budget), Tabeller och export (t CO2e, t per person och år eller kg per m² BTA; CSV och Excel) samt Källor och beräkning för de valda kategorierna. |
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
app/                      gränssnittet, en fil per flik
road2zero/                beräkningsmotorn (oberoende av Streamlit)
  engine.py               berakna(indata) -> Resultat
  scenario.py             indatamodell, standardvärden, validering, JSON
  modules/                en modul per indatamodul och klimatbudget
  algoritmer.py           formler och text för fliken Beräkningar
  data/                   faktabiblioteket (CSV och JSON)
tests/                    regressionstester
verktyg/                  skript som läser underlag till faktabiblioteket
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

Indata sparas som JSON från sidopanelen och kan öppnas igen. Filen innehåller modellversionen. Nycklar som saknas fylls med standardvärden när filen öppnas.
