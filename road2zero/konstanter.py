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
    "handel": ("Handel", False, "logistik"),
    "skola": ("Skola", False, "flerbostad_kontor_skola"),
    "vård": ("Vård", False, "flerbostad_kontor_skola"),
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
TRASTOMMAR = {"trä", "klimatförbättrat_trä"}

STOMMAR = {
    "generisk": "Generisk",
    "betong": "Betong",
    "stål": "Stål",
    "trä": "Trä",
    "klimatförbättrad_generisk": "Klimatförbättrad generisk",
    "klimatförbättrad_betong": "Klimatförbättrad betong",
    "klimatförbättrat_stål": "Klimatförbättrat stål",
    "klimatförbättrat_trä": "Klimatförbättrat trä",
    "lfm30": "LFM30",
}
STOMME_FRAN_NAMN = {v: k for k, v in STOMMAR.items()}
# LFM30 saknar egen reduktionskurva; den följer klimatförbättrad betong (modellval).
REDUKTIONSKURVA_FOR_STOMME = {"lfm30": "klimatförbättrad_betong"}

VIRKESPRODUKTER = {"Stomvirke": "bygg.virke.stomvirke", "KL-trä": "bygg.virke.kl_tra", "Limträ": "bygg.virke.limtra"}

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

EL_KURVOR = {
    "boverket_eu_referens": "Boverket 37 g, EU:s referensscenario (standard)",
    "boverket_konstant": "Boverket 37 g, konstant",
    "boverket_eu_wam": "Boverket 37 g, EU:s scenario med ytterligare åtgärder",
    "egen": "Egen kurva (start, mål och målår)",
}
FJV_KURVOR = {
    "eu_referens": "Ortens värde med EU:s referensscenario (standard)",
    "konstant": "Ortens värde, konstant",
}

# Uppvärmning per andel av byggbeståndet
UPPVARMNING = {
    "fjärrvärme": "Fjärrvärme",
    "el": "Eluppvärmd (värmepump)",
}

STATUS_FARG = {
    "Officiell statistik": "#1D6B45", "Lagstiftning": "#1D6B45", "Officiellt scenario": "#1F4E7A",
    "Litteraturvärde": "#1F4E7A", "Litteraturvärde, ska kontrolleras": "#7A4E00", "Branschschablon": "#0D5C4D",
    "Modellvärde": "#5C4A8A", "Härlett": "#3E4B46",
    "Modellantagande": "#7A4E00", "Antagande": "#8E2B1E", "Modellval": "#7A4E00", "Litteraturvärde (länsvärde)": "#1F4E7A", "Användarval": "#3E4B46", "Källa ska verifieras": "#8E2B1E",
}
