"""Beskrivning av alla beräkningar: formler (LaTeX), steg och vilka parametrar och tabeller som används.

Texten här är den som visas i fliken Beräkningar. Den ska spegla koden i road2zero/modules.
"""

ALGORITMER = [
    {
        "modul": "Tidsmodell och invånare",
        "kod": "road2zero/modules/byggnader.py: i_drift()",
        "text": "Motorn räknar i hela år från startår till slutår. Byggbeståndet anges som andelar: byggnadstyp, stomme och energival per andel. "
                "Utbyggnadstakten anges som färdigställd BTA per år och andel. "
                "Byggskedet bokförs det år BTA:n blir klar. Drift och invånare räknas med halvårsregel: hälften det år BTA:n blir klar och helt därefter.",
        "formler": [
            r"A_{\mathrm{drift}}(t) = \sum_{\tau \le t} a_\tau \cdot \begin{cases} 0{,}5 & \tau = t \\ 1 & \tau < t \end{cases}",
            r"N(t) = \sum_{\text{bostäder}} \frac{A_{\mathrm{drift}}(t)}{\mathrm{BTA/hushåll}} \cdot \mathrm{personer/hushåll}",
        ],
        "steg": ["Fördela andelens BTA på år: jämnt, framtungt, baktungt eller egen tabell.", "Räkna BTA i drift med halvårsregeln.",
                 "Räkna invånare i bostäder (flerbostadshus och småhus)."],
        "parametrar": ["allm.personer_per_hushall", "allm.bta_per_hushall"],
        "tabeller": [],
    },
    {
        "modul": "1 Byggnader: byggskede",
        "kod": "road2zero/modules/byggnader.py",
        "text": "Varje andel av byggbeståndet har en stomme. Schablonen för byggnadstypen och stommen (A1–A5, nivå 2025) multipliceras "
                "med reduktionskurvan för året då BTA:n blir klar. Ett manuellt värde ersätter schablonen och reduceras inte.",
        "formler": [
            r"E_{\mathrm{bygg},i}(\tau) = a_{i,\tau} \cdot S_{\mathrm{typ}_i,\,s_i} \cdot R_{g_i,\,s_i}(\tau) \;/\; 1000 \quad [\mathrm{t\,CO_2e}]",
            r"E_{\mathrm{påln}}(\tau) = a_\tau \cdot 0{,}026 \cdot \mathrm{andel\ pålad} \qquad E_{\mathrm{spont}} = A_{\mathrm{spont}} \cdot 0{,}2805",
        ],
        "steg": ["Slå upp schablon S (kg CO2e/m² BTA) för andelens typ och stomme.", "Multiplicera med reduktionsfaktor R för byggnadsgruppen, stommen och året.",
                 "Pålning och spont bokförs under Anläggning samma år."],
        "parametrar": ["bygg.paln", "bygg.spont"],
        "tabeller": ["byggschabloner", "reduktionskurvor"],
    },
    {
        "modul": "1 Byggnader: energi i drift",
        "kod": "road2zero/modules/byggnader.py",
        "text": "Varje andel har egna energival. Energiklassen ger köpt energi per m² Atemp för byggnadstypens kategori i Boverkets byggregler "
                "(småhus, flerbostadshus eller lokaler). Med fjärrvärme räknas köpt fjärrvärme och fastighetsel, med eluppvärmning all köpt el. "
                "Garage, industri och övriga byggnader är uppvärmda eller ouppvärmda och har bara el. Egen solel ersätter köpt el; "
                "överskott redovisas som undvikna utsläpp utanför nettot.",
        "formler": [
            r"\text{fjärrvärme: } Q_{\mathrm{fjv}} = A_{\mathrm{temp}} \cdot q_{\mathrm{fjv}},\ Q_{\mathrm{el}} = A_{\mathrm{temp}} \cdot q_{\mathrm{fel}} \qquad \text{el: } Q_{\mathrm{fjv}} = 0,\ Q_{\mathrm{el}} = A_{\mathrm{temp}} \cdot q_{\mathrm{eluppv}}",
            r"E_{\mathrm{energi}}(t) = \left(Q_{\mathrm{fjv}} \cdot f_{\mathrm{fjv}}(t) + \max(0, Q_{\mathrm{el}} - Q_{\mathrm{sol}}) \cdot f_{\mathrm{el}}(t)\right) / 10^6",
            r"f_{\mathrm{el}}(t) = 37 \cdot \frac{\mathrm{EU_{ref}}(t)}{\mathrm{EU_{ref}}(2025)} \ \mathrm{g\,CO_2e/kWh}",
            r"E_{\mathrm{undviket}}(t) = -\max(0, Q_{\mathrm{sol}} - Q_{\mathrm{el}}) \cdot (f_{\mathrm{el}}(t) - f_{\mathrm{panel}}) / 10^6",
        ],
        "steg": ["Atemp = 0,9 × andelens BTA i drift.", "Slå upp andelens energiklass och uppvärmning.", "Elens kurva gäller i hela modellen."],
        "parametrar": ["allm.atemp_andel", "el.startvarde", "el.kurva", "fjv.startvarde", "sol.produktion", "sol.panel"],
        "tabeller": ["energiklasser", "kurvor"],
    },
    {
        "modul": "2 Anläggning",
        "kod": "road2zero/modules/anlaggning.py",
        "text": "Ytor per anläggningstyp gånger ytschablon, fördelat jämnt över angivna år. Masshantering: volym gånger schakt- eller saneringsfaktor plus masstransport.",
        "formler": [
            r"E_{\mathrm{yta}} = A \cdot e_{\mathrm{typ,utförande}}",
            r"E_{\mathrm{massor}} = V \cdot e_{\mathrm{schakt}} + V \cdot \rho \cdot d \cdot e_{\mathrm{transport}}",
            r"E_{\mathrm{ledning}} = L \cdot 0{,}0391 \qquad E_{\mathrm{betong}} = V \cdot e_{\mathrm{betong}}",
        ],
        "steg": ["Summera ytor, betong, massor, ledningar och engångsvärden.", "Fördela jämnt mellan första och sista år."],
        "parametrar": ["anl.schakt", "anl.sanering", "anl.jorddensitet", "anl.transport", "anl.betong_standard", "anl.betong_klimatforbattrad", "anl.ledning"],
        "tabeller": ["ytschabloner"],
    },
    {
        "modul": "3 Förändrad markanvändning",
        "kod": "road2zero/modules/mark.py",
        "text": "Kolförlust per pool när mark tas i anspråk. Skog räknas med Skogskolmodellen 10.4: kolförråd i befintlig skog per trädslag och ålder, "
                "förlorat framtida upptag över 50 år och upptag i ny skog. Öppen mark har förifyllda kolförråd per pool med källa: åker enligt Mark- och grödoinventeringen, gräsmark och urban grönyta enligt SLU. Användaren kan ändra alla värden.",
        "formler": [
            r"E_{\mathrm{förlust}} = \mathrm{ha} \cdot \sum_{p \in \{SOC, DOM, bio\}} C_p \cdot (1 - b_p) \cdot \tfrac{44}{12}",
            r"E_{\mathrm{förlorat}} = \mathrm{ha} \cdot (1-b_{\mathrm{bio}}) \cdot \Delta C^{\mathrm{Skogskol}}_{50\,\mathrm{år}}",
            r"U_{\mathrm{ny\,skog}}(t) = -\mathrm{ha} \cdot u^{\mathrm{Skogskol}}(t - t_0 + 1)",
            r"U_{\mathrm{förgröning}}(t) = -A \cdot 0{,}07 \cdot \left(1 - 0{,}9 \cdot \tfrac{\min(t-t_0, 40)}{40}\right) / 1000",
        ],
        "steg": ["Slå upp kolförråd per pool (eget värde, Skogskolmodellen eller förifyllt värde).", "Bevarad andel per pool enligt markanvändning.",
                 "Ny skog och förgröning bokförs som negativa utsläpp."],
        "parametrar": ["allm.c_till_co2", "mark.horisont", "mark.skog_andel_soc", "mark.skog_andel_dom", "mark.skog_andel_bio",
                       "mark.forgroning_start", "mark.forgroning_mattnad", "mark.forgroning_ar"],
        "tabeller": ["markpooler", "bevarande", "skogskol_kurvbibliotek"],
    },
    {
        "modul": "4 Mobilitet och transport",
        "kod": "road2zero/modules/mobilitet.py: faktorer()",
        "text": "De boendes bilar (hushållsmodell B). Fordonskilometer = hushåll × bilar per hushåll × körsträcka per bil. "
                "Livscykelfaktorn per drivlina består av förbränning, bränslets tidigare led, el till laddning, tillverkning av fordon och batteri "
                "fördelad på livslängden samt underhåll (ICCT 2025). Elbilarnas andel av körsträckan följer Trafikverkets basprognos 2024; "
                "andra drivlinor minskar proportionellt.",
        "formler": [
            r"\mathrm{fkm}(t) = \frac{N(t)}{\mathrm{pers/hh}} \cdot \mathrm{bilar/hh} \cdot \mathrm{km/bil}",
            r"f_d = \underbrace{\left(MJ_d \cdot (\phi\, e_{\mathrm{ttw}} + \phi\, e_{\mathrm{wtt}} + (1-\phi)\, e_{\mathrm{bio}}) + o\right)(1-\eta)^{t-2024}}_{\text{bränsle}} + \underbrace{\epsilon_d \frac{kWh_d}{0{,}9} f_{\mathrm{el}}(t)}_{\text{el}} + \underbrace{\frac{(K_d + B_d \cdot 72{,}8) \cdot 1000}{240\,000}}_{\text{fordon och batteri}} + u_d",
            r"E_{\mathrm{mob}}(t) = \mathrm{fkm}(t) \cdot \sum_d m_d(t) \cdot f_d(t) / 10^6",
        ],
        "steg": ["Bilar per hushåll och körsträcka från kommunen (SCB och RUS) eller eget värde.", "Drivlinemix 2024 från Trafikanalys, elbilsandel enligt Trafikverkets basprognos.",
                 "Faktor per drivlina med modellens elkurva."],
        "parametrar": ["mob.mj_per_km", "mob.kwh_per_km", "mob.laddverkningsgrad", "mob.ovrigt", "mob.livslangd", "mob.kaross", "mob.batteri_kwh",
                       "mob.batteri_ef", "mob.underhall", "mob.bensin.ttw", "mob.bensin.wtt", "mob.bensin.fossil", "mob.bensin.bio", "mob.diesel.ttw",
                       "mob.diesel.wtt", "mob.diesel.fossil", "mob.diesel.bio", "mob.biogas.ttw", "mob.biogas.bio", "mob.phev_eldrift", "mob.effektivisering",
                       "mob.km_riket", "mob.elbilskurva"],
        "tabeller": ["kommuner", "kurvor"],
    },
    {
        "modul": "5 Matkonsumtion",
        "kod": "road2zero/modules/konsumtion.py: mat_per_inv()",
        "text": "Kostprofilmodell: andel per profil gånger klimatavtryck per profil och dag. Valfri kalibrering mot Konsumtionskompassens livsmedel och valfri kostomställning mot målandelar.",
        "formler": [
            r"m(t) = \sum_p w_p(t) \cdot c_p \cdot 365 / 1000 \cdot (1+g)^{t-t_0} \quad [\mathrm{t/inv,\,år}]",
            r"E_{\mathrm{mat}}(t) = N(t) \cdot m(t)",
        ],
        "steg": ["Andelar summerar till 100 %.", "Kalibrering skalar så att snittet blir 1,08 t (SEI 2026)."],
        "parametrar": ["mat.dagar", "mat.kalibrering_mal"],
        "tabeller": ["kostprofiler"],
    },
    {
        "modul": "6 Övrig konsumtion och flygresor",
        "kod": "road2zero/modules/konsumtion.py",
        "text": "Sju hushållskategorier ur Konsumtionskompassen 2.1 (30 % av 5,39 t). Flygresor är en egen klimatkategori med riksgenomsnitt per invånare.",
        "formler": [r"E_{\mathrm{övrig}}(t) = N(t) \cdot \sum_k o_k \cdot (1+g)^{t-t_0}", r"E_{\mathrm{flyg}}(t) = N(t) \cdot 1{,}1 \cdot (1+g)^{t-t_0}"],
        "steg": ["Varje kategori kan ändras.", "Flygresor redovisas på nivå 2."],
        "parametrar": ["ovr.hushall_total", "flyg.per_inv"],
        "tabeller": ["ovrig_konsumtion"],
    },
    {
        "modul": "7 Offentlig sektor",
        "kod": "road2zero/modules/konsumtion.py",
        "text": "Offentlig konsumtion plus den offentliga andelen av investeringarna. Projektets egna byggnader och anläggningar ingår inte här.",
        "formler": [r"E_{\mathrm{off}}(t) = N(t) \cdot \left(0{,}83 + 2{,}09 \cdot 0{,}18\right) \cdot (1+g)^{t-t_0}"],
        "steg": ["Offentlig andel = offentliga myndigheters bruttoinvesteringar / totala bruttoinvesteringar."],
        "parametrar": ["off.konsumtion", "off.investeringar", "off.andel"],
        "tabeller": [],
    },
    {
        "modul": "8 Negativa utsläpp",
        "kod": "road2zero/modules/negativa.py, byggnader.py, mark.py",
        "text": "Inbyggt virke (bara med CCF-certifikat för dubbel volym), biokol (bara EBC C-sink), stadsträd med tillväxtkurva, ny skog och förgröning.",
        "formler": [
            r"U_{\mathrm{virke},i} = -a_{i,\tau} \cdot v_i \cdot c_{\mathrm{produkt}} / 1000 \cdot \mathrm{CCF}_i \quad (v_i = 0{,}15 \text{ för trästomme, annars } 0)",
            r"U_{\mathrm{biokol}} = -n_{\mathrm{gropar}} \cdot 0{,}3 \qquad U_{\mathrm{träd}}(t) = -n \cdot 21{,}77 \cdot g(t-t_p) / 1000",
        ],
        "steg": ["En post som inte uppfyller sitt krav visas men räknas inte."],
        "parametrar": ["bygg.virke_m3_m2", "bygg.virke.stomvirke", "bygg.virke.kl_tra", "bygg.virke.limtra", "neg.biokol_per_grop", "neg.trad_upptag"],
        "tabeller": ["kurvor"],
    },
    {
        "modul": "Redovisningsnivåer",
        "kod": "road2zero/engine.py: netto_per_niva()",
        "text": "Nivå 1 är exploateringen, nivå 2 lägger till invånarnas mobilitet, flyg, mat och övrig konsumtion, nivå 3 lägger till offentlig sektor. Negativa utsläpp dras av på alla nivåer.",
        "formler": [r"\mathrm{Netto}_L(t) = \sum_{c\,:\,\mathrm{nivå}(c) \le L} E_c(t)"],
        "steg": [],
        "parametrar": [],
        "tabeller": [],
    },
    {
        "modul": "Klimatbudget (Forster m.fl. 2026)",
        "kod": "road2zero/modules/budget.py",
        "text": "Global budget B väljs per temperaturgräns och sannolikhet. En bana som exakt förbrukar B räknas om till CO2e och fördelas lika per person och år på de invånare som faktiskt bor i området. "
                "Byggskedet bokförs när BTA:n blir klar och får ingen egen budget.",
        "formler": [
            r"E(t) = E_0 (1-r)^{t-2026}, \quad r = E_0 / B \quad (B > E_0)",
            r"E(t) = E_0 \cdot \text{linjärt till noll på } T = 2B/E_0 \text{ år} \quad (B \le E_0)",
            r"b(t) = k \cdot E(t) / P(t), \quad k = 56{,}8 / 43{,}2",
            r"B_{\mathrm{stadsdel}} = \sum_t N(t) \cdot b(t)",
        ],
        "steg": ["Budgeten är förbrukad det första år då kumulativa nettoutsläpp överstiger stadsdelens hela budget."],
        "parametrar": ["budget.e0", "budget.k"],
        "tabeller": ["budget_forster2026", "befolkning_unwpp2024"],
    },
]

TABELLKALLOR = {
    "byggschabloner": ("Byggskedets schabloner per byggnadstyp och stomme", "MALMQVIST2023,SBUF14381"),
    "reduktionskurvor": ("Reduktionskurvor per byggnadsgrupp och stomme", "SBUF14381"),
    "energiklasser": ("Energiklasser per byggnadstyp", "BOVERKET_BBR,MODELLVAL"),
    "ytschabloner": ("Ytschabloner per anläggningstyp", "SBUF_SCHABLON"),
    "kurvor": ("Tidskurvor: el, fjärrvärme, elbilsandel och trädtillväxt", "EU_REF2020,TV_BASPROGNOS2024,TRAFA_KM_2024,ITREE"),
    "markpooler": ("Kolförråd per marktyp och pool", "KSLA2025,SLU2025"),
    "bevarande": ("Bevarad andel per markanvändning", "MODELLVAL"),
    "skogskol_kurvbibliotek": ("Skogskolmodellens kurvbibliotek per hektar", "SKOGSKOL104"),
    "kommuner": ("Bilar per hushåll och körsträcka per kommun", "SCB_TAB6589,SCB_TAB6568,RUS_KORSTRACKA,TRAFA_KM_2024"),
    "kostprofiler": ("Kostprofiler: andelar och klimatavtryck", "SCARBOROUGH2023"),
    "ovrig_konsumtion": ("Övrig konsumtion per hushållskategori", "SEI2026"),
    "budget_forster2026": ("Kvarvarande koldioxidbudget från 2026", "FORSTER2026"),
    "befolkning_unwpp2024": ("Världsbefolkning, medelvariant", "UNWPP2024"),
    "personbil_livscykel": ("Personbil: fordon, batteri, förbrukning och bränslen", "ICCT2025,FQD2015,PHEV_ICCT2022"),
}
