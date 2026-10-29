# Road2Zero – instruktioner för Claude

Road2Zero är en evidensbaserad klimatberäkning för stadsdelar utan karta. Python-paketet `road2zero/` räknar tio klimatkategorier år
för år och jämför nettoutsläppen med en koldioxidbudget. `streamlit_app.py` och `app/` är gränssnittet. Användaren är klimatforskare
och skriver svenska; svara och skriv all text i gränssnittet på svenska.

## Kör och testa

```bash
pip install -r requirements.txt
python -m pytest -q                                   # ska alltid vara grönt innan commit
python -m streamlit run streamlit_app.py --server.port 8501
python verktyg/las_tabell_a.py                        # läser underlag/tabell_a_utokad.xlsx till faktabiblioteket
python verktyg/jagersro.py                            # bygger standardprojektet ur underlag/jagersro_*
```

Efter en ändring i gränssnittet: starta appen, öppna den i webbläsaren och titta på fliken du ändrat. Testerna fångar inte layoutfel.

## Struktur

- `road2zero/engine.py` – `berakna(indata) -> Resultat`. Beroende av Streamlit får inte införas i `road2zero/`.
- `road2zero/scenario.py` – indatamodell, standardvärden (`tomt()`), validering, JSON och migrering av äldre sparade filer.
- `road2zero/utveckling.py` – index per emissionsfaktor och år (fliken Emissionsfaktorer över tid).
- `road2zero/modules/` – en modul per indatamodul och klimatbudget.
- `road2zero/algoritmer.py` – formler och text i fliken Beräkningar. Uppdatera den när en formel ändras.
- `road2zero/data/` – faktabiblioteket (CSV med `;`, JSON). Varje värde har kolumnen `kalla` med id i `referenser.csv`.
- `app/` – en fil per flik. `common.py` har `fmt()` (svenskt talformat), `editor()` och `senare()`.
- `verktyg/las_tabell_a.py` – läser Tabell A utökad till `byggschabloner.csv`, `reduktionskurvor.csv` och byggraderna i `utveckling.csv`.
- `verktyg/jagersro.py` – bygger `road2zero/data/standardprojekt_jagersro.json` ur Excel-underlaget och planskissen i `underlag/`.
- `underlag/` – källfiler som skripten läser. Visas aldrig i gränssnittet.
- `tests/test_motor.py` – regressionstester, källkonsistens och test för rent gränssnitt.

## Grundregler

1. **Inga siffror i beräkningskoden.** Alla faktorer ligger i `road2zero/data/` med källa. Ny källa läggs in i `referenser.csv`.
   Värden utan extern källa får källan `MODELLVAL` och statusen Modellval eller Antagande.
2. **Rent gränssnitt.** Gränssnittet, faktabiblioteket och koden får inte hänvisa till internt eller tidigare bilagt underlag
   (Klimatanalys 3.0, Jägersro, Vägvis, Oceanhamnen, QA-underlag). Hänvisa till de publicerade källorna. `test_rent_granssnitt` kontrollerar.
   Undantag: standardprojektets JSON-fil får bära projektets namn; koden och gränssnittet läser namnet ur filen.
3. **Appen startar med standardprojektet** (`scenario.standardprojekt()`, Jägersro, Svensk Travsports del). Sidopanelen kan ladda det
   igen eller börja med ett tomt projekt. `scenario.exempel()` är ett påhittat testfall och används bara av testerna.
4. **Allt indata som påverkar resultatet har ett förifyllt värde med källa** som användaren kan ändra.
5. **Svenskt talformat** i gränssnittet: mellanslag som tusentalsavgränsare och decimalkomma (`fmt()`).
6. **Indataflikar som visar resultat** använder `senare()` så att tabeller och diagram fylls efter att alla indata lästs.
7. **Diagram**: använd den dova färgskalan i `road2zero/konstanter.py` (kategorier) och `app/diagram.py` (layout och övriga linjer);
   aldrig två y-axlar.
8. **Sparade indata** ska fortsätta gå att öppna. Ändras datamodellen: lägg migrering i `scenario.fran_json()` och ett test.

## Modellbeslut (ändras bara om användaren ber om det)

- **Kategorier och nivåer:** Byggnad, Energi, Anläggning, Förändrad markanvändning (nivå 1); Mobilitet och transport, Flygresor,
  Matkonsumtion, Övrig konsumtion (nivå 2); Offentliga investeringar (nivå 3); Negativa utsläpp dras av på alla nivåer.
  Undvikna utsläpp från exporterad solel redovisas utanför nettot.
- **Tid:** hela år, standard 2026–2076. Byggskedet bokförs det år BTA:n blir klar. Drift och invånare med halvårsregel.
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
- **El:** Boverkets 37 g CO2e/kWh, förändring enligt EU:s referensscenario 2020. Samma elfaktor i hela modellen (byggnader, elbilar, solel).
- **Fjärrvärme:** ortens värde (användaren anger), förändring enligt EU:s referensscenario 2020.
- **Mobilitet:** de boendes bilar: hushåll × bilar per hushåll × körsträcka; livscykelfaktor per drivlina (ICCT 2025, direktiv 2015/652).
  Drivlinemix 2025 (Trafikanalys). Bilproduktionen följer den globala elens klimatfaktor (IEA).
- **Mat:** kostprofiler med andelar ur EPIC-Oxford-kohorten (Scarborough m.fl. 2023), redovisade som en delpost per kostprofil;
  utveckling enligt FAO:s globala utsläppsintensitet.
- **Övrig konsumtion:** sju kategorier ur Konsumtionskompassen 2.1, ändringsbara; följer bilproduktionens kurva (globalt elsnitt).
- **Flygresor:** egen kategori, 1,1 t per invånare (Kamb och Larsson 2018, år 2017 med höghöjdseffekt); redovisas som två delposter,
  koldioxid från bränslet och höghöjdseffekt (faktor 170/90 ≈ 1,89). Utveckling enligt globalt snitt för flygbränsle (IATA).
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

## Kända osäkerheter

- Fiskätarnas klimatavtryck (2,74 kg CO2e per dag, Scarborough m.fl. 2023) bryter ordningen mellan grupperna; ska kontrolleras.
- Fullständig referens till Dodoo m.fl. 2026 saknas.
- Boverkets rapport 2026:16 är inte genomläst.
- Riksgenomsnitt för markkol 0–50 cm saknas; gräsmark och urban grönyta använder SLU:s länsvärde för Uppsala.

## Arbetsgång vid ändringar

1. Större ändringar: börja i planläge och beskriv vad som ändras innan filer ändras.
2. Ändra data i `road2zero/data/`, logik i `road2zero/`, gränssnitt i `app/`.
3. Uppdatera `algoritmer.py` när en formel ändras och `README.md` när ett modellbeslut ändras.
4. Kör `python -m pytest -q`. Justera förväntade värden i testerna bara när ändringen är avsiktlig, och säg vilka som ändrades och varför.
5. Starta appen och titta på de flikar som berörs.
6. Höj `__version__` i `road2zero/__init__.py` (0.x.y) och skriv commit-meddelandet på svenska.
