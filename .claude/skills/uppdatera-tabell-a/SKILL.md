---
name: uppdatera-tabell-a
description: Uppdatera byggpåverkan per byggnadstyp och stomme från en ny version av Tabell A utökad (Excel). Använd när användaren lägger in eller pekar på en ny Excel med startvärden eller reduktionskurvor för stommar.
---

# Uppdatera Tabell A utökad

1. Ta reda på var den nya Excel-filen finns. Den kan vara bifogad, ligga i användarens Google Drive eller redan i `underlag/`.
   Från Google Drive: ladda ned filen som .xlsx; Drive-kopplingen läser bara text och räcker inte för formler och flera blad.
2. Spara filen som `underlag/tabell_a_utokad.xlsx` (ersätt den gamla) och behåll bladnamnen
   `Startvarden och proxy` och `Reduktionskurvor`.
3. Kör `python verktyg/las_tabell_a.py`. Skriptet skriver `road2zero/data/byggschabloner.csv`, `reduktionskurvor.csv`
   och byggraderna i `utveckling.csv`, och skriver ut den nya årliga förändringen per stomme.
4. Jämför med förra versionen: `git diff --stat road2zero/data/` och visa användaren vilka startvärden och takter som ändrats,
   i en kort tabell (byggnadstyp × stomme). Kontrollera att Generisk fortfarande är lika med Betong BAU.
5. Kör `python -m pytest -q`. `test_startvarden_som_tabellen` och `test_kategorier` innehåller förväntade värden; uppdatera dem
   bara efter att användaren bekräftat att de nya värdena är avsiktliga.
6. Starta appen och kontrollera rullistan för stomme under Indata → Byggnader och diagrammet Byggpåverkan per stomme i fliken
   Emissionsfaktorer över tid.
7. Höj versionen i `road2zero/__init__.py`, gör en commit med meddelandet "Uppdatera Tabell A utökad: <vad som ändrats>" och
   fråga om du ska pusha.
