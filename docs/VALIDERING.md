# Validering av Road2Zero 1.0

Leveransdatum: 2026-10-27. Modellens beräkningar är nya Python-funktioner, separerade från Streamlit-gränssnittet.

## Kontroller som har körts i leveransmiljön

- 34 automatiska motortester passerade med `python -m unittest discover -s tests -v`.
- Ett oberoende räkneexempel kontrollerades kategori för kategori mot uttryckliga mängder och faktorer.
- Demots total är **353 926,6667 kg CO₂e** inom den specificerade femårsperioden. Detta är ett syntetiskt räkneexempel, inte en klimatprognos för Jägersro.
- SMT:s startscenario innehåller 4 000 bostäder, preliminär BTA/invånarskattning och identifierade dataluckor. Det ger **ingen beräknad projekttotal**.
- Testerna täcker total BTA, fördelning mellan programandelar och etapper, egna nollvärden, saknade värden, enheter, faktorkurvor, solel, grundläggning, markareor, kolpooler, skogens kapacitet, referensmark, transportperspektiv, årsserier, konsumtion, kolavdrag, återföring och serialisering.
- Kommandoradskörning av det kompletta demot producerade scenario och beräkningspaket utan blockerande dataluckor.
- Python-filerna kompilerades utan syntaxfel.
- 18 strukturella gränssnittsflöden kördes: nio inmatningsmoduler vardera för SMT och demo. Streamlit och diagramrendering ersattes där med testsubstitut. Detta kontrollerar Python-flödet, inte webbgränssnittets verkliga beteende eller utseende.

## Kontroller som inte kunde köras här

Streamlit och Plotly finns inte installerade i leveransmiljön. Paketinstallationen stoppades av miljöns nätverksbegränsning. Därför hoppades **tre riktiga Streamlit AppTest-tester över** här: appstart med sex flikar, samtliga inmatningsmoduler och ändring av total BTA.

Dessa tester ingår i projektet och körs via GitHub Actions efter att `requirements-dev.txt` har installerats. Ett faktiskt GitHub Actions-resultat har inte hämtats eller påståtts. En riktig webbläsargranskning och en Streamlit Cloud-publicering återstår.

## Praktisk kontroll vid första start

1. Starta appen och kontrollera att SMT med 4 000 bostäder öppnas och att projekttotalen är ofullständig.
2. Välj demo i sidopanelen. Kontrollera totalen cirka **353,927 ton CO₂e**.
3. Öppna `Indata → Byggd BTA och energi`, ändra total BTA och byggperiod och spara. Kontrollera att årsserierna uppdateras.
4. Aktivera etapper och kontrollera andelssumman samt att etappernas perioder ligger inom vald byggperiod.
5. Spara JSON och beräkningspaket. Läs tillbaka JSON och kontrollera att mängder, faktorer och referenser följer med.

## Vetenskaplig och projektspecifik granskning

Motortester verifierar beräkningslogik mot angivna antaganden. De verifierar inte att en äldre emissionsfaktor är aktuell, representativ eller korrekt avgränsad. Sådan granskning behövs före beslutsanvändning, särskilt för markens kolpooler/nettoflöden, offentliga investeringar, konsumtionsfaktorer, tillgodoräknade kolsänkor och underlag från Vägvis.

Modellen gör ingen fullständig osäkerhetssimulering, dynamisk klimatmetrik eller fullständig skogs-, jord- eller våtmarksmodell. Faktornas uppgivna osäkerhet sparas som metadata. Avvikelser mot ursprunglig Klimatanalys eller Stella bör testas med avgränsade gemensamma räknefall innan resultat jämförs som likvärdiga.
