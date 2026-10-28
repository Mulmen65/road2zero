# Road2Zero

Klimatberäkning för stadsdelar utan karta. Modellen räknar tio klimatkategorier år för år och jämför nettoutsläppen med en vetenskapligt baserad koldioxidbudget (Forster m.fl. 2026), fördelad lika per person på de invånare som faktiskt bor i området.

Appen startar med ett tomt projekt. Alla schabloner är förifyllda och varje värde hänvisar till en publicerad källa eller är tydligt markerat som modellval.

## Flikar

| Flik | Innehåll |
|---|---|
| Indata | Moduler 0–8 och klimatbudget. Byggbeståndet anges som andelar med egen byggnadstyp, stomme och egna energival. |
| Resultat | Nyckeltal, tabell per klimatkategori, delposter, tabell per år, klimatbudget, export till CSV och Excel. |
| Illustration | Utsläpp per år, vägen mot noll mot budgeten, summa per kategori, vattenfall, per invånare och flöden från modul till kategori. |
| Beräkningar | Formler, steg, parametrar och mellanled för varje modul. |
| Faktorer och parametrar | Hela faktabiblioteket med värde, enhet, statusklass och källa. Egna värden kan anges per parameter. |
| Referenser | Alla källor, grupperade, med länk och var de används. |

## Byggbeståndet

Varje rad är en andel av byggbeståndet: en byggnadstyp, en stomme och en BTA, med egen energiklass, uppvärmning (fjärrvärme eller el) och solceller. Byggpåverkan och energi hör alltså alltid till samma BTA.

- **Stomme:** rullistan visar förifylld byggpåverkan i kg CO2e/m² BTA för den valda byggnadstypen (A1–A5, nivå 2025; Malmqvist m.fl. 2023 och SBUF 14381). Värdet reduceras med SBUF:s kurva för året då BTA:n blir klar.
- **Energi:** energiklassen ger köpt fjärrvärme och el per m² Atemp för byggnadstypens kategori i Boverkets byggregler. Klass C motsvarar nybyggnadskravet och är förvald. Garage, industri och övriga byggnader är uppvärmda eller ouppvärmda och har bara el.
- **Utbyggnadstakt:** färdigställd BTA per år och andel; jämn, framtung, baktung eller egen tabell.

Formuläret *Lägg till byggbestånd* fördelar en byggnadstyps BTA på flera stommar, och varje rad blir en egen andel med egna energival.

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
streamlit_app.py          start och flikar
app/                      gränssnittet, en fil per flik
road2zero/                beräkningsmotorn (oberoende av Streamlit)
  engine.py               berakna(indata) -> Resultat
  scenario.py             indatamodell, standardvärden, validering, JSON
  modules/                en modul per indatamodul och klimatbudget
  algoritmer.py           formler och text för fliken Beräkningar
  data/                   faktabiblioteket (CSV och JSON)
tests/                    regressionstester
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
