# Faktorer och äldre Jägersroindata

Modellen innehåller separata lager för numeriska värden, indata, metoder och bibliografi. En generisk metodkälla, exempelvis IPCC eller Boverket, intygar inte modellens lokala koltäthet eller ett projekts emissionsfaktor.

## Medföljande värden

- Två proportioneringsfaktorer hämtas från hela FÖP:s tabell på sidan 14: 440 000/4 300 m² BTA per bostad och 8 900/4 300 personer per bostad. Att använda dessa genomsnitt för SMT är ett markerat arbetsantagande.
- BTA, byggperiod och programandelar matas in samlat. Granskningen behöver därför säkerställa representativa faktorer för den aktuella mixen av byggnadstyper och material.
- Äldre grundläggnings- och anläggningsfaktorer kommer från Oceanhamnens `Schablonvärden`, med exakta radangivelser. Tonvärden är omräknade till kg. Dessa ligger tillgängliga i registret utan att automatiskt väljas på alla aktivitetsrader.
- Äldre generell byggnadsfaktor 375 är markerad Ej verifierad. Den ursprungliga schablonraden saknar enhet och källa; dess tänkta omfattning måste styrkas före beslutsanvändning.
- Numeriska faktorer för energi, markens kolpooler/flöden, mat, övrig konsumtion, offentliga investeringar och kolsänkor har inte fyllts med påhittade värden.
- `data/legacy_oceanhamnen_factors.csv` innehåller samtliga 123 råparametrar från schablonbladet för fortsatt granskning. Alla är inte implementerade eller aktiverade faktorer i den nya modellen.
- `data/legacy_jagersro_parameters.csv` innehåller 141 råvariabler/ekvationer från Mat, SEI_Konsumtionskompassen och Scarborough_modell i den tillhandahållna äldre modellen. Ekvationer och ursprungliga enhetsnamn bevaras. De exekveras eller importeras inte automatiskt som nya numeriska faktorer.
- `data/source_provenance.json` anger filnamn och SHA-256 för de ursprungliga modeller som råtabellerna hämtats från.

## Innan en faktor märks Projektverifierad

Dokumentera originalkälla, version, sida/tabell/datapost, enhet, mängddefinition, geografisk och tidsmässig representativitet, livscykelomfattning, GWP-metod och eventuell osäkerhet. För prognoser behövs numeriska årsvärden eller en dokumenterad årlig förändring.

Kontrollera särskilt följande avgränsningar: byggnadsfaktor mot pålning/spontning, Vägvis mot byggtransporter och byggnaders laddel, offentlig investeringsfaktor mot redan inkluderade offentliga anläggningar, konsumtion mot mat/energi/resor samt negativa utsläpp mot EPD och markens upptag.

Ändringar av faktorvärden och källor görs i samma formulär. Användaren ansvarar för att källan faktiskt styrker det ändrade värdet. Modellens källstatus är ett redigerbart granskningsfält, inte en automatisk kvalitetskontroll av dokumentinnehållet.
