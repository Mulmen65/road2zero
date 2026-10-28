"""Fasta listor och namn som motorn och gränssnittet delar."""

# Klimatkategorier i redovisningsordning: (namn, redovisningsnivå, färg)
KATEGORIER = [
    # Färgerna följer en validerad kategoripalett (åtta kulörer, ordningen klarar CVD- och normalseende-kontrollen för
    # intilliggande staplar) plus två neutrala toner för Övrig konsumtion och Offentliga investeringar.
    ("Byggnad", 1, "#2a78d6"),
    ("Energi", 1, "#eb6834"),
    ("Anläggning", 1, "#1baf7a"),
    ("Förändrad markanvändning", 1, "#eda100"),
    ("Mobilitet och transport", 2, "#e87ba4"),
    ("Flygresor", 2, "#6250d6"),
    ("Matkonsumtion", 2, "#e34948"),
    ("Övrig konsumtion", 2, "#52514e"),
    ("Offentliga investeringar", 3, "#a8a69e"),
    ("Negativa utsläpp", 1, "#008300"),
]
KATEGORI_NAMN = [k[0] for k in KATEGORIER]
NIVA = {k[0]: k[1] for k in KATEGORIER}
FARG = {k[0]: k[2] for k in KATEGORIER}
NIVA_NAMN = {1: "Nivå 1 · exploateringen", 2: "Nivå 2 · med invånarna", 3: "Nivå 3 · med offentlig sektor"}
NIVA_INNEHALL = {
    1: "Byggnad, Energi, Anläggning, Förändrad markanvändning, minus Negativa utsläpp",
    2: "Nivå 1 plus Mobilitet och transport, Flygresor, Matkonsumtion och Övrig konsumtion",
    3: "Nivå 2 plus Offentliga investeringar",
}

MODULER = [
    ("0", "Projekt och inställningar"),
    ("U", "Emissionsfaktorer över tid"),
    ("1", "Byggnader"),
    ("2", "Anläggning"),
    ("3", "Förändrad markanvändning"),
    ("4", "Mobilitet och transport"),
    ("5", "Matkonsumtion"),
    ("6", "Övrig konsumtion och flygresor"),
    ("7", "Offentlig sektor"),
    ("8", "Negativa utsläpp"),
    ("B", "Klimatbudget"),
]

# Byggnadstyper: intern nyckel -> visningsnamn, bostad?, reduktionsgrupp, energiklasser
BYGGNADSTYPER = {
    "flerbostadshus": ("Flerbostadshus", True, "flerbostad_kontor_skola"),
    "småhus": ("Småhus", True, "smahus"),
    "kontor": ("Kontor", False, "flerbostad_kontor_skola"),
    "lokaler": ("Lokaler", False, "flerbostad_kontor_skola"),
    "handel": ("Handelshus", False, "logistik"),
    "skola": ("Skola", False, "flerbostad_kontor_skola"),
    "vård": ("Vårdbyggnad", False, "ovriga"),
    "industribyggnad": ("Industribyggnad", False, "logistik"),
    "mobilitetshus": ("Mobilitetshus", False, "logistik"),
    "underjordisk_parkering": ("Underjordisk parkering", False, "ovriga"),
    "övriga_byggnader": ("Övriga byggnader", False, "ovriga"),
}
TYP_FRAN_NAMN = {v[0]: k for k, v in BYGGNADSTYPER.items()}

# Energikategori i tabellen energiklasser per byggnadstyp. Boverkets byggregler skiljer på småhus, flerbostadshus och
# lokaler; kontor, skola, vård och handel är lokaler. Garage, industri och övriga byggnader räknas som uppvärmda eller ouppvärmda.
ENERGIKATEGORI = {
    "flerbostadshus": "flerbostadshus", "småhus": "småhus", "kontor": "lokaler", "lokaler": "lokaler", "handel": "lokaler",
    "skola": "lokaler", "vård": "lokaler", "industribyggnad": "industribyggnad", "mobilitetshus": "mobilitetshus",
    "underjordisk_parkering": "underjordisk_parkering", "övriga_byggnader": "övriga_byggnader",
}
ENERGIKATEGORI_NAMN = {"flerbostadshus": "Flerbostadshus (BBR)", "småhus": "Småhus (BBR)", "lokaler": "Lokaler (BBR)",
                       "industribyggnad": "Industri", "mobilitetshus": "Garage", "underjordisk_parkering": "Garage",
                       "övriga_byggnader": "Övriga byggnader", "övrig_byggnation": "Övrig byggnation"}
# Förvald energiklass: C motsvarar nybyggnadskravet i BBR (primärenergital 75–100 % av kravet).
STANDARDKLASS = {"industribyggnad": "Uppvärmt", "övriga_byggnader": "Uppvärmt", "mobilitetshus": "Ouppvärmt",
                 "underjordisk_parkering": "Ouppvärmt"}
OUPPVARMDA_KLASSER = {"Uppvärmt", "Ouppvärmt"}   # el för belysning, ventilation och eventuell temperering, ingen fjärrvärme
TRASTOMMAR = {"tra_bau", "tra_bast"}

STOMMAR = {
    "generisk": "Generisk (= Betong BAU)",
    "betong_bau": "Betong BAU",
    "betong_bast": "Betong BÄST",
    "stal_bau": "Stål BAU",
    "stal_bast": "Stål BÄST",
    "tra_bau": "Trä BAU",
    "tra_bast": "Trä BÄST",
}
STOMME_FRAN_NAMN = {v: k for k, v in STOMMAR.items()}
# Äldre stomnycklar i sparade indata -> nya. LFM30 och klimatförbättrad generisk finns inte i Tabell A utökad.
STOMME_MIGRERING = {
    "betong": "betong_bau", "klimatförbättrad_betong": "betong_bast", "stål": "stal_bau", "klimatförbättrat_stål": "stal_bast",
    "trä": "tra_bau", "klimatförbättrat_trä": "tra_bast", "klimatförbättrad_generisk": "betong_bast", "lfm30": "betong_bast",
}
# Generisk är Betong BAU (samma startvärde och samma utveckling över tid). BAU = SBUF 14381 Insteg, BÄST = SBUF 14381 Färdplan.

# Kolinlagring i trästomme: bundet kol per m³ enligt EN 16449. "Använd schablon" ger stomvirke för Trä BAU och limträ för Trä BÄST.
VIRKESPRODUKTER = {"Stomvirke": "bygg.virke.stomvirke", "Limträ/glulam": "bygg.virke.limtra", "KL-trä": "bygg.virke.kl_tra"}
SCHABLON_PRODUKT = "Använd schablon"
STANDARD_VIRKESPRODUKT = {"tra_bau": "Stomvirke", "tra_bast": "Limträ/glulam"}

ANLAGGNINGSTYPER = {
    "huvudgata": "Huvudgata", "lokalgata": "Lokalgata", "gc_vag": "GC-väg", "torg": "Torg",
    "markparkering": "Markparkering", "park": "Park", "bostadsgard": "Bostadsgård", "lekplats": "Lekplats",
    "skolgard": "Skolgård", "trafik": "Trafikyta", "kaj": "Kaj", "bro": "Bro", "gc_bro": "GC-bro",
}
ANLAGGNING_FRAN_NAMN = {v: k for k, v in ANLAGGNINGSTYPER.items()}

MARKTYPER = ["Åkermark", "Betes- och gräsmark", "Urban grönyta", "Hårdgjord mark", "Barrskog", "Lövskog", "Blandskog"]
SKOGSTYPER = {"Barrskog": "spruce", "Lövskog": "mixed", "Blandskog": "mixed"}  # Lövskog saknar egen kurva för befintlig skog
TILL_MARK = ["Bebyggd kvartersmark", "Gata och torg", "Kvartersmark gård", "Park", "Bevarad", "Nyplanterad skog", "Avhårdgjord yta"]
TRADSLAG = {"Gran": "spruce", "Tall": "pine", "Blandskog (gran/bok)": "mixed", "Bok": "beech"}
SKOTSEL = {"Fri utveckling": "natural", "Kontinuitetsskogsbruk": "continuous"}
TIDIGARE_MARK_FOR_SKOG = {"Åkermark": "cropland", "Betes- och gräsmark": "grassland", "Urban grönyta": "grassland",
                          "Hårdgjord mark": "sealed", "Barrskog": "grassland", "Lövskog": "grassland", "Blandskog": "grassland"}
FORGRONING_FRAN = {"Hårdgjord mark"}
FORGRONING_TILL = {"Park", "Kvartersmark gård", "Avhårdgjord yta"}

DRIVLINOR = {"petrol": "Bensin", "diesel": "Diesel", "hev": "Elhybrid", "bev": "Elbil", "phev": "Laddhybrid", "biogas": "Biogas"}

# Fastighetsvärme: andel fjärrvärme anges per andel av byggbeståndet; resten är el till värmepump.

STATUS_FARG = {
    "Officiell statistik": "#1D6B45", "Lagstiftning": "#1D6B45", "Officiellt scenario": "#1F4E7A",
    "Litteraturvärde": "#1F4E7A", "Litteraturvärde, ska kontrolleras": "#7A4E00", "Branschschablon": "#0D5C4D",
    "Modellvärde": "#5C4A8A", "Härlett": "#3E4B46",
    "Modellantagande": "#7A4E00", "Antagande": "#8E2B1E", "Modellval": "#7A4E00", "Litteraturvärde (länsvärde)": "#1F4E7A", "Användarval": "#3E4B46", "Källa ska verifieras": "#8E2B1E",
}
