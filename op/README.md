# Road2Zero-OP – stadens klimatavtryck per DeSO

Road2Zero-OP är Road2Zero-modellen för hela staden. Den bygger på MalmoOP 1.2 och har samma logotyp, meny och förklaringssidor
som Road2Zero-Plan och Road2Zero-CityScenario. Varje stad eller plan är ett projekt i `projekt/<id>/`; det första är **Malmö_ÖP**
(`projekt/malmo_op/`). Huvudfilen på Streamlit Community Cloud är `op/streamlit_app.py` i repot `Mulmen65/road2zero`.
Se också repots README för hur en ny stad läggs till.

Appen räknar på tre delar:

1. **Energi i befintliga byggnader** utgår från användarens energideklarationer (*Energikarta filer.csv*). Adresserna kopplas till DeSO med Malmö stads adresstjänst. Byggnader utan deklaration skattas från deklarerade byggnader av samma typ, så att hela beståndet i varje DeSO ingår. Ytorna kalibreras mot SCB:s fjärrvärmestatistik 2024. Energin räknas om till ton CO₂e med Boverkets emissionsfaktorer för el och fjärrvärme. En Monte Carlo-beräkning ger 95-procentsintervall per DeSO och för Malmö.
2. **Mobilitet** kommer från Vägvis 2.3.1 och följer samma A/B-växel. Modell A avser trafiken på vägar i området; modell B avser hushållens bilar. A och B adderas aldrig.
3. **Exploatering 2030–2050** bygger på de 36 utbyggnadsområdena i Översiktsplan för Malmö 2023. Delen omfattar tillkommande BTA, nybyggnation (A1–A5), förändrad markanvändning (kolförråd), energi i nya byggnader och nya invånares mobilitet.

Resultaten visas i **ton CO₂e/år**, **ton eller kg CO₂e per hektar och år** (landyta utan hav) och **ton CO₂e per invånare och år**. De finns för åren 2024, 2030, 2035, 2040, 2045 och 2050 samt som summa för 2030–2050. Beräkningen körs i webbläsaren och uppdateras direkt när antagandena ändras.

## Starta i Streamlit Community Cloud

1. Öppna [share.streamlit.io](https://share.streamlit.io) och välj **Create app**.
2. Välj repositoryt **Mulmen65/road2zero**, grenen **main** och **Main file path: `op/streamlit_app.py`**. Python 3.12 rekommenderas.
3. Välj **Deploy**. Inga hemligheter, API-nycklar eller GitHub Actions behövs.

Kör lokalt:

```bash
# från repots rot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run op/streamlit_app.py
```

## Det här är redan gjort i datat

| Steg | Resultat |
|---|---|
| Adresskoppling | 31 028 av 31 356 adresser (99,0 %) har kopplats via Malmö stads `Malmo_adresser_platser/GeocodeServer` och punkt-i-polygon mot SCB DeSO 2025. Hämtat 29 oktober 2026. |
| Energideklarationer | 13 721 av 13 895 beräkningsbara deklarationer (98,7 %) ligger på kartan. 1 534 exakta dubblettrader och 91 ersatta deklarationer är borttagna. |
| Atemp (saknas i CSV) | Skattas ur OpenStreetMap-byggnader: fotavtryck × våningar × 0,9. Våningar från `building:levels`, höjd/3 m eller median i DeSO/RegSO/Malmö. |
| Hela byggnadsbeståndet | Alla 60 757 OSM-byggnader i uttaget klassas. 15 163 har deklaration. 22 527 uppvärmda byggnader utan deklaration skattas med median-energiprestanda och elandel för samma typ i DeSO, RegSO eller Malmö. Av dessa är 716 sammanbyggda med en deklarerad byggnad. 12 678 ouppvärmda byggnader och 10 389 byggnader utanför Malmö ingår inte. |
| Kalibrering | SCB:s fjärrvärme 2024 per sektor: Atemp i flerbostadshus × 0,93 och i lokaler/industri × 0,63. Småhus kalibreras inte; antalet (27 761 mot SCB:s 27 852) och ytan stämmer med SCB:s bostadsstatistik. |
| Osäkerhet | Monte Carlo i webbläsaren (1 000 iterationer, ca 4 s). Energi 2024: 137 kt CO₂e, 95 % 121–154 kt (−11 % / +13 %); per DeSO typiskt ±24 %. Emissionsfaktorerna är Boverkets och hålls fasta. |
| Energibärare (saknas i CSV) | Skattas ur kvoten primärenergital/energiprestanda; regimskifte BBR 29 den 1 september 2020. |
| Mobilitet | Vägvis 2.3.1: A från färdigt resultat; B körs med Vägvis motor (3 000 iterationer). |
| Exploatering | 36 områden i ÖP 2023 med 38 850 bostäder och 37 900 arbetsplatser, uppdelade per DeSO med marktäcke från OSM. |

**Rättelse jämfört med ChatGPT-paketet:** Malmö stads adresstjänst returnerar adresstypen `POI` för alla adresser. ChatGPT-paketet godkände bara `PointAddress` och `Subaddress`, så i praktiken hade *alla* adresser underkänts och kartan blivit grå. MalmoOP godkänner i stället träffar där adress och husnummer stämmer, med flaggor A/B/P/C (se `tools/uppdatera.py`).

## Sidor i appen

| Sida | Innehåll |
|---|---|
| 01 Översikt | Nyckeltal, klimatavtryckets delar, utveckling 2024–2050 och energins osäkerhet (histogram och 95 %-intervall) |
| 02 Resultat & klimatbudget | Samma resultatvy som Road2Zero-Plan: summa per klimatkategori, från brutto till summa, trädkarta, över tid, per person, klimatbudget för 1,5–2,0 °C (Parisavtalet, Forster m.fl. 2026) med budgettilldelning enligt Konsumtionskompassen, tabeller med CSV och källor. Kategorier och befintlig stad/exploatering väljs överst. |
| 03 Karta & områden | Koropletkarta (OSM-bakgrund, havsavskiljning, utbyggnadsområden), områdespanel och tabell över alla 209 DeSO, med 95 %-intervall för energin |
| 04 Så räknas resultatet | Beräkningen steg för steg med siffror för vald DeSO, inklusive deklarationerna och de skattade byggnaderna |
| 05 Antaganden & scenario | Emissionsfaktorer över tid (el, fjärrvärme, Sysavs koldioxidavskiljning och klimattrappa för nybyggnation) och alla övriga antaganden med källor; ändringar sparas i webbläsaren |
| 06 Exploatering 2030–2050 | Utbyggnadsområden, BTA, åkermark, nybyggnation och mark per år |
| 07 Trafik & geodata | Vägvis modell A och B för hela staden, bilinnehav och mobilitet per DeSO |
| 08 Data & kvalitet | Urval, adressflaggor, hela byggnadsbeståndet, kontroll och kalibrering mot SCB, Atemp-källor, energibärarmetod och nedladdningar |
| 09 Metod & källor | Formler, systemgränser och Harvard-referenser |
| Underlag (Streamlit) | Ladda ned adresskopplingen. Läs in en ny CSV eller hämta Malmö stads aktuella energideklarationer. Nya adresser kopplas automatiskt. |

## Beräkning i korthet

```
Energi (t)        = Σ k × energiprestanda × Atemp × (s·EF_el(år) + (1−s)·EF_fv(år)) / 1000 × adressandel × effektivisering(år)
                    (deklarationer + skattade byggnader; k = SCB-fjärrvärme / modellens fjärrvärme per sektor)
Mobilitet (t)     = Vägvis A eller B (2024) × flottfaktor(år) × trafikförändring(år)
EF(år)            = startvärde × Π(1 + r_period/100) från 2027; fjärrvärmen × (1 − minskning) från Sysavs driftår (valbart)
Nybyggnation (t)  = BTA × klimatfaktor(år) enligt vald klimattrappa (kg CO₂e/m² BTA, A1–A5) / 1000, jämnt över byggåren
Mark (t)          = ha × hårdgörandel × (kolförråd före − 22 t C/ha) × 44/12, över byggåren
Nya byggnader (t) = BTA × 0,9 × 50 kWh/m² × EF(år), när de är klara
Ny mobilitet (t)  = nya hushåll × bilar/hushåll × km/bil × t CO₂e/fkm (från Vägvis B för värd-DeSO)
Budget (t)        = Σ(2026–2050) invånare(t) × k · E(t) / världsbefolkning(t) × Σ a_g, E(t) = E₀(1 − E₀/B)^(t−2026)  (Forster m.fl. 2026)
a_g (andel)       = boende U_boende / F; investeringar U_investeringar × n / F; transport (U_transport − U_flyg) / F
                    F = U_hushåll + U_offentlig + U_investeringar per person och år (SEI 2026); summan över grupper i urvalet
Per hektar        = t / landyta utan hav (ha); kg/ha = 1000 × t/ha
```

| Standardantagande | Värde | Källa |
|---|---|---|
| El / fjärrvärme, startvärden | 0,037 / 0,056 kg CO₂e/kWh | Boverket (2026a), klimatdatabasen |
| El / fjärrvärme, förändring per år 2027–2030, 2031–2035, 2036–2040, 2041–2045, 2046–2050 | −3,54 / −2,52 / −2,88 / −2,09 / −2,33 % och −1,63 / −1,75 / −1,92 / −2,13 / −2,38 % | EU:s referensscenario 2020 (Europeiska kommissionen, 2021), samma som Road2Zero-Plan |
| Sysavs koldioxidavskiljning | Av; om på: från 2030, −43 % för fjärrvärmen | Sysav (2024, 2025), Energinyheter (2024), SVT Nyheter (2026); 0,65 × 400/600 härlett |
| Atemp/BTA | 0,9 | Antagande |
| Byggnader som ingår | Hela beståndet (deklarerade + skattade) | OSM-klassning, se Data & kvalitet |
| Kalibrering | Per sektor mot SCB:s fjärrvärme 2024 | SCB (2026a) |
| Uppvärmd andel, odeklarerad industri/lager | 0,5 | Antagande |
| Osäkerhet i kalibreringsmålet (CV) | 0,08 | Antagande, se Metod & källor |
| Emissionsfaktorer i osäkerhetsberäkningen | Fasta (Boverkets värden) | Boverket (2026a) |
| Fokus 1 / Fokus 2 | byggs 2030–2039 / 2040–2049 | Malmö stad: Fokus 1 detaljplaneras före 2030 |
| BTA per bostad / arbetsplats | 90 m² / 25 m² (blandad stad), 100 m² (verksamhet) | Antaganden |
| Uppförande A1–A5 (klimattrappa) | Gränsvärden 2030: 235 (flerbostadshus), 250 (kontor/skola), 190 (hall) kg/m² BTA, oförändrade. Alternativ: Boverkets färdplan (skärpning 2035 och 2040), linjär bana, SBUF Insteg, SBUF Färdplan, referensvärden eller egen takt | Boverket (2026b); Chalmers m.fl. (2025), SBUF 14381 |
| Energi nya byggnader | 50 kWh/m² Atemp, 22 % el | Median i underlaget, klass A–B, ≥ 1 000 m² BTA |
| Kolförråd åker / öppen / skog / bebyggd | 121 / 103 / 146 / 22 t C/ha | Länsstyrelsen i Uppsala län (2025), proxy |
| Hårdgörandel | 0,7 | Antagande |
| Invånare per bostad | 2,11 | SCB 2024 via Vägvis |
| Budgettilldelning | Malmö 2022: boende (Energi) 12,3 %, investeringar (Byggnad och Förändrad markanvändning) 24,1 %, transport utan flyg (Mobilitet och transport) 10,4 % av budgeten; summa 46,8 %. Alternativ: Skåne, Sverige, egna andelar eller hela budgeten | SEI (2026a, 2026b) |
| Nybyggnationens andel av investeringarna (n) | 100 %, en övre gräns (investeringarna omfattar också infrastruktur, maskiner och fordon) | Antagande |

## Uppdatera underlaget

* **I appen:** öppna *Underlag*. Välj en ny CSV med samma kolumner, eller hämta *Malmö stads energikarta*. Klicka på **Läs in och koppla adresser**. Bara nya adresser geokodas, och OSM-byggnader hämtas för dem. Det nya underlaget används direkt i sessionen. Ladda ned ZIP-filen och ersätt filerna i GitHub, eller be Claude pusha dem.
* **Kommandorad:** `python -m tools.uppdatera ny_fil.csv` eller `python -m tools.uppdatera --malmo`. Kör från mappen `op/`; kommandot skriver de uppdaterade filerna i `projekt/malmo_op/data/` (ett annat projekt väljs med miljövariabeln `R2Z_OP_PROJEKT=projekt/<id>`).

Reproducera data från källfilerna i `projekt/malmo_op/data/kalla/` (kör från mappen `op/`):

```bash
python tools/build_adresskoppling.py
python tools/build_energi.py
python tools/build_exploatering.py
node tools/build_mobilitet.js
python tools/build_metadata.py
```

## Osäkerhetsberäkningen

Monte Carlo-beräkningen gäller energi i befintliga byggnader och körs automatiskt i webbläsaren när appen öppnas och när ett antagande som påverkar den ändras. Varje iteration drar:

| Källa | Gemensamt fel (alla byggnader) | Slumpfel per byggnad |
|---|---|---|
| Emissionsfaktor el / fjärrvärme | Ingen: Boverkets 0,037 / 0,056 gäller | – |
| Atemp/BTA | CV 0,06 | – |
| Våningar per våningskälla | CV 0,03–0,20 | CV 0,10–0,60 |
| Energiprestanda, deklarerad / skattad | CV 0,05 / 0,15 per typ | CV 0,10 / 0,30 |
| Elandel | ±4 procentenheter | ±6 (kvot) / ±15 (median) procentenheter |
| Uppvärmd andel i industri och lager | likformig ±25 procentenheter | – |
| Kalibreringsmål (SCB) | CV 0,08 per sektor | – |

Kalibreringen räknas om i varje iteration. Intervallen för framtida år skalas med årets effektivisering och förändrade emissionsfaktorer. Intervallen speglar alltså osäkerheten i aktivitetsdata (Atemp, energiprestanda, elandel och kalibrering), inte valet av emissionsfaktor. Resultatet (2,5-, 50- och 97,5-percentil per DeSO) följer med i CSV- och JSON-exporten.

## Tester

```bash
node tests/test_model.js                 # 28 beräkningstester (massbalans, kalibrering, Monte Carlo, räkneexempel, enheter, tidsplan …)
python -m unittest discover tests        # 12 tester av sidbygge, data, byggnadsbestånd och uppdateringsflöde
```

## Struktur

```
streamlit_app.py           Streamlit-sidor (appen i iframe + sidan Underlag), projektval
app/                       shell.html, model.js (beräkning), app.js (gränssnitt), stilmallar, Leaflet; logotypen läses ur ../gemensamt/
projekt/malmo_op/          projekt.json (namn, kommun, rubriker) och data/ för Malmö_ÖP
  data/                    färdigt beräkningsunderlag (energi, mobilitet, exploatering, adresskoppling, metadata)
  data/kalla/              källfiler: CSV, geokodning, OSM-byggnader (hela beståndet) och grannar, markanvändning, SCB-energistatistik, DeSO, ÖP-lager, Vägvis-data
tools/                     byggskript, uppdateringsflöde och Vägvis beräkningsmotor (MIT)
tests/                     beräknings- och apptester
```

## Tolkning och begränsningar

* Road2Zero-OP (liksom MalmoOP) är en **screening** för översiktlig planering och ingen officiell utsläppsstatistik. Byggnader utan energideklaration ingår som skattningar (kan stängas av). Industriprocesser, sjöfart, flyg och konsumtion ingår inte.
* Atemp och energibärare är **skattningar**. Modellen antar att all energi som inte är el är fjärrvärme. Gas, biobränsle och olja i småhus och industri behandlas därför som fjärrvärme. Detta är troligen förklaringen till att småhusens skattade fjärrvärme ligger över SCB. Boverkets öppna data om energideklarationer med Atemp och energislag kan ersätta skattningen i en senare version.
* Byggnadstypen för odeklarerade byggnader bestäms ur OSM-taggar, markanvändning och storlek. Den kan bli fel för enskilda byggnader. Intervallen per DeSO är därför breda, särskilt i små områden.
* Emissionsfaktorerna är nationella medelvärden ur Boverkets klimatdatabas, inte Malmöspecifika eller marginella. Faktorerna kommer från Boverkets räkneexempel för modul A5. Att använda dem för årlig driftenergi är ett modellval.
* Framtidsåren är scenarier med uttryckliga antaganden. El och fjärrvärme minskar som standard enligt EU:s referensscenario 2020. Flottans klimatfaktor är som standard oförändrad (1,0). Båda kan ändras under *Antaganden & scenario*.
* Budgettilldelningen fördelar budgeten efter dagens utsläpp (grandfathering inom Malmöbornas fotavtryck) och hålls konstant över tid. Nybyggnationen räknas till investeringarna, oavsett om byggherren är offentlig eller privat, och inte till hushållens boende. Hur stor del av investeringarnas utsläpp som är nybyggnation av byggnader saknar källa; standardvärdet 100 % ger därför en för stor andel och en för snäll jämförelse för nybyggnationen.
* Kolförråden kommer från Uppsala län och används som proxy för Skåne. Marktäcket kommer från OpenStreetMap, och oklassad mark räknas som standard som redan bebyggd.
* Energins 95-procentsintervall kommer från MalmoOP:s Monte Carlo och mobilitetens från Vägvis. Modellstruktur och framtidsantaganden ingår inte i intervallen. För exploateringen redovisas inga statistiska intervall.

## Referenser (Harvard)

* Boverket (2026a) *Indata om energianvändning i klimatdeklarationen*. Senast granskad 29 maj 2026. https://www.boverket.se/sv/klimatdeklaration/gor-sa-har/underlag/indata-om-energi/ (Hämtad: 29 oktober 2026).
* Boverket (2026b) *Utkast färdplan för införande av gränsvärden för byggnaders klimatpåverkan*. Rapport 2026:29. https://www.boverket.se/globalassets/publikationer/dokument/2026/rapport-2026-29_utkast-fardplan-gransvarden-klimatpaverkan-byggnader.pdf (Hämtad: 29 oktober 2026).
* Boverket (u.å.) *Vad är primärenergital?* https://www.boverket.se/sv/PBL-kunskapsbanken/regler-om-byggande/boverkets-byggregler/energihushallning/vad-ar-primarenergital/ (Hämtad: 29 oktober 2026).
* Chalmers m.fl. (2025) *Klimatkrav för byggnader – på väg mot netto noll*. Vägledning, SBUF 14381, tabell 5. https://research.chalmers.se/publication/548167/file/548167_Fulltext.pdf
* Energinyheter (2024) *Sysavs planer för koldioxidinfångning fortsätter*, 4 juni 2024. https://www.energinyheter.se/20240604/31443/sysavs-planer-koldioxidinfangning-fortsatter (Hämtad: 5 november 2026).
* Europeiska kommissionen (2021) *EU Reference Scenario 2020*. https://energy.ec.europa.eu/data-and-analysis/energy-modelling/eu-reference-scenario-2020_en
* Länsstyrelsen i Uppsala län (2025) *Kolförråd och kolsänka i skog och mark inom Uppsala län – slutrapport*. (Hämtad: 29 oktober 2026).
* Malmö stad (2023) *Översiktsplan för Malmö*. Antagen av kommunfullmäktige 28 september 2023.
* Malmö stad (2024) *OP2023_Underlag – Utbyggnadsområden*. https://gis.malmo.se/arcgis/rest/services/op/OP2023_Underlag/MapServer/129 (Hämtad: 29 oktober 2026).
* Malmö stad (u.å.) *Malmo_adresser_platser* (GeocodeServer). https://gis.malmo.se/arcgis/rest/services/Malmo_adresser_platser/GeocodeServer (Hämtad: 29 oktober 2026).
* Malmö stad (u.å.) *Malmö Energikarta*. https://stadsatlas.malmo.se/energikarta/ (Hämtad: 29 oktober 2026).
* OpenStreetMap contributors (2026) *OpenStreetMap*, Overpass-uttag 29 oktober 2026. ODbL 1.0. https://www.openstreetmap.org/copyright
* Statistiska centralbyrån (2026a) *Slutanvändning (MWh), efter län och kommun, förbrukarkategori samt bränsletyp*. Tabell EN0203A/SlutAnvSektor. https://www.statistikdatabasen.scb.se (Hämtad: 29 oktober 2026).
* Statistiska centralbyrån (2026b) *Antal lägenheter efter region, hustyp och bostadsarea*. Tabell BO0104T5. https://www.statistikdatabasen.scb.se (Hämtad: 29 oktober 2026).
* Statistiska centralbyrån (2025) *DeSO – Demografiska statistikområden*, 2025_v2. https://www.scb.se/vara-tjanster/oppna-data/oppna-geodata/demografiska-statistikomraden-deso/
* SEI (2026a) *Konsumtionskompassen 2.1: hushållens klimatpåverkan per kommun*, data för 2022 (webbverktyg). https://konsumtionskompassen.pages.dev/skane/malmo (Hämtad: 5 november 2026).
* SEI (2026b) *Konsumtionskompassen i siffror*, version 2.1, data för 2023. https://www.sei.org/wp-content/uploads/2026/05/konsumtionskompassen-siffror-sei2026-013.pdf (Hämtad: 5 november 2026).
* SVT Nyheter (2026) *Kritiken mot Sysavs miljardsatsning: ”För tankarna till Northvolt”*, 6 mars 2026. https://www.svt.se/nyheter/lokalt/skane/kritiken-mot-sysavs-miljardsatsning-for-tankarna-till-northvolt (Hämtad: 5 november 2026).
* Sysav (2024) *Miljörapport 2023*, avfallskraftvärmeverket i Malmö. https://www.sysav.se/media/5ebj4j4n/milj%C3%B6rapport-2023-ema.pdf (Hämtad: 5 november 2026).
* Sysav (2025) *Sysav beviljas stöd för fortsatt satsning på koldioxidavskiljning – ny milstolpe för projekt SkyZero*, 17 april 2025. https://www.sysav.se/om-oss/press-och-media/nyheter/sysav-beviljas-stod-for-fortsatt-satsning-pa-koldioxidavskiljning-ny-milstolpe-for-projekt-skyzero/ (Hämtad: 5 november 2026).
* Vägvis (2026) *Vägvis 2.3.1 – trafikens klimatavtryck*. GitHub: Mulmen65/vagvisa.

## Versioner

| Version | Datum | Innehåll |
|---|---|---|
| 1.3.0 (Road2Zero 0.12.0) | 5 november 2026 | Budgettilldelning: de valda kategorierna jämförs med sin andel av budgeten enligt Konsumtionskompassen (Malmö, Skåne eller Sverige 2022), egna andelar eller hela budgeten. Nybyggnationen hör till investeringarna. Standard Malmö: 46,8 % av budgeten, 1,53 t per person mot 0,26 t, förbrukad 2031. |
| 1.3.0 | 5 november 2026 | Emissionsfaktorer över tid som i Road2Zero-Plan: el och fjärrvärme med årlig förändring per period (standard EU:s referensscenario 2020), Sysavs koldioxidavskiljning som valbart steg för fjärrvärmen och sju klimattrappor för nybyggnation. Standardresultatet 2050 blir 568,8 kt i stället för 628,3 kt (perspektiv A). |
| 1.2.0 | 29 oktober 2026 | Emissionsfaktorerna för el och fjärrvärme är Boverkets värden (0,037 / 0,056 kg CO₂e/kWh) och hålls fasta i osäkerhetsberäkningen. Energins 95 %-intervall 2024: 121–154 kt; per DeSO typiskt ±24 %. |
| 1.1.0 | 29 oktober 2026 | Hela byggnadsbeståndet (odeklarerade byggnader skattas), kalibrering mot SCB:s fjärrvärme 2024 per sektor, Monte Carlo för energin, kort om byggnadsbestånd och SCB-kontroll. |
| 1.0.0 | 29 oktober 2026 | Första versionen: energideklarationer, mobilitet från Vägvis 2.3.1 och exploatering enligt ÖP 2023 per DeSO. |

## Licens

Appkoden har licensen MIT; se `LICENSE`. Där anges även villkoren för tredjepartsdelar (Vägvis, Leaflet, OpenStreetMap, SCB och Malmö stad).
