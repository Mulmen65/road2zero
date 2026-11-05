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
        "modul": "Emissionsfaktorer över tid",
        "kod": "road2zero/utveckling.py: Utveckling.index()",
        "text": "Varje emissionsfaktor har ett startvärde som gäller 2026 och en årlig procentuell förändring per period från 2027 till 2100 "
                "(negativt värde = minskning). Indexet multipliceras med startvärdet det år utsläppet uppstår: byggskedet det år BTA:n blir klar, "
                "drift, mobilitet och konsumtion varje år. Elbilarnas och laddhybridernas andel av körsträckan ändras i procentenheter per år "
                "och kan tillsammans bli högst 100 %.",
        "formler": [
            r"I_f(2026) = 1, \qquad I_f(t) = I_f(t-1) \cdot \left(1 + \tfrac{r_{f,p(t)}}{100}\right) \quad (t = 2027 \ldots 2100)",
            r"e_f(t) = e_f(2026) \cdot I_f(t)",
            r"a_{\mathrm{el}}(t) = \min\!\left(1,\ a_{\mathrm{el}}(2025) + \sum_{\tau=2027}^{t} \tfrac{\Delta_{\mathrm{el},p(\tau)}}{100}\right)",
        ],
        "steg": ["Perioder: 2027–2030, 2031–2035, 2036–2040, 2041–2045, 2046–2050, 2051–2060, 2061–2070 och 2071–2100.",
                 "Anläggning följer betongstommens kurva och övrig konsumtion bilproduktionens kurva, om inte annat väljs.",
                 "Index efter 2100 hålls konstant.",
                 "År före 2026 (befintliga stadsdelar med tidigt startår) får index 1: startvärdena gäller bakåt och skrivs inte om "
                 "till historiska nivåer. Utsläppen före 2026 blir därför en undre skattning."],
        "parametrar": ["el.startvarde", "fjv.startvarde"],
        "tabeller": ["utveckling"],
    },
    {
        "modul": "1 Byggnader: byggskede",
        "kod": "road2zero/modules/byggnader.py",
        "text": "Varje andel av byggbeståndet har en stomme: Generisk (= Betong BAU), Betong BAU/BÄST, Stål BAU/BÄST eller Trä BAU/BÄST. "
                "Startvärdet för byggnadstypen och stommen (A1–A5, Tabell A utökad; gäller 2026) multipliceras med stommens index för året då BTA:n blir klar. Ett manuellt värde ersätter schablonen och ändras inte över tid. "
                "Pålning och spont följer anläggningens index.",
        "formler": [
            r"E_{\mathrm{bygg},i}(\tau) = a_{i,\tau} \cdot S_{\mathrm{typ}_i,\,s_i}(2026) \cdot I_{s_i}(\tau) \;/\; 1000 \quad [\mathrm{t\,CO_2e}]",
            r"E_{\mathrm{påln}}(\tau) = a_\tau \cdot 0{,}026 \cdot \mathrm{andel\ pålad} \cdot I_{\mathrm{anl}}(\tau) \qquad E_{\mathrm{spont}} = A_{\mathrm{spont}} \cdot 0{,}2805 \cdot I_{\mathrm{anl}}(\tau)",
        ],
        "steg": ["Slå upp startvärde S (kg CO2e/m² BTA, nivå 2026) för andelens typ och stomme.", "Multiplicera med stommens index I för året då BTA:n blir klar.",
                 "Pålning och spont bokförs under Anläggning samma år."],
        "parametrar": ["bygg.paln", "bygg.spont"],
        "tabeller": ["byggschabloner", "reduktionskurvor", "utveckling"],
    },
    {
        "modul": "1 Byggnader: energi i drift",
        "kod": "road2zero/modules/byggnader.py",
        "text": "Varje andel har egna energival. Energiklassen ger köpt energi per m² Atemp för byggnadstypens kategori i Boverkets byggregler "
                "(småhus, flerbostadshus eller lokaler). Fastighetsvärmen fördelas mellan fjärrvärme (andel s) och värmepump (1 − s): "
                "fjärrvärmedelen ger köpt fjärrvärme och fastighetsel, värmepumpsdelen all köpt el för eluppvärmda byggnader. "
                "Egen köpt el och egen köpt fjärrvärme anges per m² BTA och ersätter klassens värden. "
                "Garage, industri och övriga byggnader är uppvärmda eller ouppvärmda och har bara el. Egen solel ersätter köpt el; "
                "överskott redovisas som undvikna utsläpp utanför nettot.",
        "formler": [
            r"Q_{\mathrm{fjv}} = A_{\mathrm{temp}} \cdot s \cdot q_{\mathrm{fjv}}, \qquad Q_{\mathrm{el}} = A_{\mathrm{temp}} \cdot \left(s \cdot q_{\mathrm{fel}} + (1-s) \cdot q_{\mathrm{eluppv}}\right) \quad \text{eller eget värde} \cdot \mathrm{BTA}",
            r"E_{\mathrm{energi}}(t) = \left(Q_{\mathrm{fjv}} \cdot f_{\mathrm{fjv}}(t) + \max(0, Q_{\mathrm{el}} - Q_{\mathrm{sol}}) \cdot f_{\mathrm{el}}(t)\right) / 10^6",
            r"f_{\mathrm{el}}(t) = 37 \cdot I_{\mathrm{el}}(t), \qquad f_{\mathrm{fjv}}(t) = f_{\mathrm{fjv}}(2026) \cdot I_{\mathrm{fjv}}(t) \ \ [\mathrm{g\,CO_2e/kWh}]",
            r"E_{\mathrm{undviket}}(t) = -\max(0, Q_{\mathrm{sol}} - Q_{\mathrm{el}}) \cdot (f_{\mathrm{el}}(t) - f_{\mathrm{panel}}) / 10^6",
        ],
        "steg": ["Atemp = 0,9 × andelens BTA i drift.", "Slå upp andelens energiklass och andel fjärrvärme, eller använd egna värden per m² BTA.",
                 "Elens index gäller i hela modellen: byggnader, elbilar och solel."],
        "parametrar": ["allm.atemp_andel", "el.startvarde", "fjv.startvarde", "sol.produktion", "sol.panel"],
        "tabeller": ["energiklasser", "utveckling"],
    },
    {
        "modul": "2 Anläggning",
        "kod": "road2zero/modules/anlaggning.py",
        "text": "Ytor per anläggningstyp gånger ytschablon, fördelat jämnt över angivna år. Masshantering: volym gånger schakt- eller saneringsfaktor plus masstransport. "
                "Schablonerna gäller 2026 och följer anläggningens index, som standard betongstommens kurva. Engångsvärden räknas som angivna.",
        "formler": [
            r"E_{\mathrm{yta}}(t) = A \cdot e_{\mathrm{typ,utförande}} \cdot I_{\mathrm{anl}}(t)",
            r"E_{\mathrm{massor}} = V \cdot e_{\mathrm{schakt}} + V \cdot \rho \cdot d \cdot e_{\mathrm{transport}}",
            r"E_{\mathrm{ledning}} = L \cdot 0{,}0391 \qquad E_{\mathrm{betong}} = V \cdot e_{\mathrm{betong}}",
        ],
        "steg": ["Summera ytor, betong, massor, ledningar och engångsvärden.", "Fördela jämnt mellan första och sista år."],
        "parametrar": ["anl.schakt", "anl.sanering", "anl.jorddensitet", "anl.transport", "anl.betong_standard", "anl.betong_klimatforbattrad", "anl.ledning"],
        "tabeller": ["ytschabloner", "utveckling"],
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
                "fördelad på livslängden samt underhåll (ICCT 2025). Fordon och batteri följer bilproduktionens index (globalt elsnitt), "
                "bränsledelen förbränningsbilarnas index och el till laddning den svenska elens index. Elbilar och laddhybrider ökar med "
                "procentenheter per år; andra drivlinor minskar proportionellt. Bilar per hushåll och körsträcka har egna index.",
        "formler": [
            r"\mathrm{fkm}(t) = \frac{N(t)}{\mathrm{pers/hh}} \cdot \mathrm{bilar/hh} \cdot I_{\mathrm{bilar}}(t) \cdot \mathrm{km/bil} \cdot I_{\mathrm{km}}(t)",
            r"f_d = \underbrace{\left(MJ_d \cdot (\phi\, e_{\mathrm{ttw}} + \phi\, e_{\mathrm{wtt}} + (1-\phi)\, e_{\mathrm{bio}}) + o\right) I_{\mathrm{förbr}}(t)}_{\text{bränsle}} + \underbrace{\epsilon_d \frac{kWh_d}{0{,}9} f_{\mathrm{el}}(t)}_{\text{el}} + \underbrace{\frac{(K_d + B_d \cdot 72{,}8) \cdot 1000}{240\,000} I_{\mathrm{bilprod}}(t)}_{\text{fordon och batteri}} + u_d",
            r"E_{\mathrm{mob}}(t) = \mathrm{fkm}(t) \cdot \sum_d m_d(t) \cdot f_d(t) / 10^6",
        ],
        "steg": ["Bilar per hushåll och körsträcka från kommunen (SCB och RUS) eller eget värde.", "Drivlinemix 2025 från Trafikanalys; elbilar och laddhybrider ökar enligt fliken Emissionsfaktorer över tid.",
                 "Faktor per drivlina med modellens elkurva."],
        "parametrar": ["mob.mj_per_km", "mob.kwh_per_km", "mob.laddverkningsgrad", "mob.ovrigt", "mob.livslangd", "mob.kaross", "mob.batteri_kwh",
                       "mob.batteri_ef", "mob.underhall", "mob.bensin.ttw", "mob.bensin.wtt", "mob.bensin.fossil", "mob.bensin.bio", "mob.diesel.ttw",
                       "mob.diesel.wtt", "mob.diesel.fossil", "mob.diesel.bio", "mob.biogas.ttw", "mob.biogas.bio", "mob.phev_eldrift",
                       "mob.km_riket"],
        "tabeller": ["kommuner", "utveckling", "personbil_livscykel"],
    },
    {
        "modul": "5 Matkonsumtion",
        "kod": "road2zero/modules/konsumtion.py: mat_per_inv()",
        "text": "Kostprofilmodell: andel per profil gånger klimatavtryck per profil och dag. Valfri kalibrering mot Konsumtionskompassens livsmedel och valfri kostomställning mot målandelar.",
        "formler": [
            r"m(t) = \sum_p w_p(t) \cdot c_p \cdot 365 / 1000 \cdot I_{\mathrm{mat}}(t) \quad [\mathrm{t/inv,\,år}]",
            r"E_{\mathrm{mat}}(t) = N(t) \cdot m(t)",
        ],
        "steg": ["Andelar summerar till 100 %.", "Kalibrering skalar så att snittet blir 1,08 t (SEI 2026)."],
        "parametrar": ["mat.dagar", "mat.kalibrering_mal"],
        "tabeller": ["kostprofiler", "utveckling"],
    },
    {
        "modul": "6 Övrig konsumtion och flygresor",
        "kod": "road2zero/modules/konsumtion.py",
        "text": "Sju hushållskategorier ur Konsumtionskompassen 2.1 (30 % av 5,39 t). Flygresor är en egen klimatkategori med riksgenomsnitt per invånare.",
        "formler": [r"E_{\mathrm{övrig}}(t) = N(t) \cdot \sum_k o_k \cdot I_{\mathrm{övrig}}(t)", r"E_{\mathrm{flyg}}(t) = N(t) \cdot 1{,}1 \cdot I_{\mathrm{flyg}}(t)"],
        "steg": ["Varje kategori kan ändras.", "Flygresor redovisas på nivå 2."],
        "parametrar": ["ovr.hushall_total", "flyg.per_inv"],
        "tabeller": ["ovrig_konsumtion", "utveckling"],
    },
    {
        "modul": "7 Offentlig sektor",
        "kod": "road2zero/modules/konsumtion.py",
        "text": "Offentlig konsumtion plus den offentliga andelen av investeringarna. Projektets egna byggnader och anläggningar ingår inte här.",
        "formler": [r"E_{\mathrm{off}}(t) = N(t) \cdot \left(0{,}83 + 2{,}09 \cdot 0{,}18\right) \cdot I_{\mathrm{off}}(t)"],
        "steg": ["Offentlig andel = offentliga myndigheters bruttoinvesteringar / totala bruttoinvesteringar.",
                 "Index enligt EU:s klimatmål: −55 % 2030 och −90 % 2040 jämfört med 1990."],
        "parametrar": ["off.konsumtion", "off.investeringar", "off.andel"],
        "tabeller": [],
    },
    {
        "modul": "8 Negativa utsläpp",
        "kod": "road2zero/modules/negativa.py, byggnader.py, mark.py",
        "text": "Kolinlagring i trästomme (Trä BAU och Trä BÄST, balanserande), biokol (bara EBC C-sink), stadsträd med tillväxtkurva, ny skog och förgröning. "
                "Kolinlagringen = −(BTA × v × F_produkt) med bundet kol per m³ enligt EN 16449: stomvirke 720,7, limträ 786,0 och KL-trä 680,7 kg CO2/m³. "
                "Schablon: stomvirke för Trä BAU och limträ för Trä BÄST, v = 0,15 m³ per m² BTA. Fördelas över byggtiden som BTA:n blir klar.",
        "formler": [
            r"U_{\mathrm{trä},i}(\tau) = -a_{i,\tau} \cdot v_i \cdot F_{\mathrm{produkt}} / 1000 \quad [\mathrm{t\,CO_2}], \quad v_i = 0{,}15 \text{ som schablon för Trä BAU och Trä BÄST}",
            r"U_{\mathrm{biokol}} = -n_{\mathrm{gropar}} \cdot 0{,}3 \qquad U_{\mathrm{träd}}(t) = -n \cdot 21{,}77 \cdot g(t-t_p) / 1000",
        ],
        "steg": ["En post som inte uppfyller sitt krav visas men räknas inte."],
        "parametrar": ["bygg.virke_m3_m2", "bygg.virke.stomvirke", "bygg.virke.limtra", "bygg.virke.kl_tra", "neg.biokol_per_grop", "neg.trad_upptag"],
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
        "steg": ["Budgeten är förbrukad det första år då kumulativa nettoutsläpp överstiger stadsdelens hela budget.",
                 "Banan börjar 2026. År före 2026 får ingen budgetandel men deras utsläpp räknas in i den kumulativa summan."],
        "parametrar": ["budget.e0", "budget.k"],
        "tabeller": ["budget_forster2026", "befolkning_unwpp2024"],
    },
]

TABELLKALLOR = {
    "byggschabloner": ("Byggskedets startvärden per byggnadstyp och stomme (Tabell A utökad)", "TABELL_A_UTOKAD,MALMQVIST2023,SBUF14381"),
    "reduktionskurvor": ("Reduktionskurvor per byggnadskategori och stomme (Tabell A utökad)", "TABELL_A_UTOKAD,SBUF14381,HEIDELBERG_SLITE,STEGRA_SSAB"),
    "energiklasser": ("Energiklasser per byggnadstyp", "BOVERKET_BBR,MODELLVAL"),
    "ytschabloner": ("Ytschabloner per anläggningstyp", "SBUF_SCHABLON"),
    "kurvor": ("Tidskurvor: el och fjärrvärme (underlag för standardtakten) och trädtillväxt", "EU_REF2020,ITREE"),
    "utveckling": ("Emissionsfaktorer över tid: årlig förändring per period", "TABELL_A_UTOKAD,EU_REF2020,IEA_EL2026,TRAFA_KM_2025,FAO2025,IATA_EFF2024,IATA_SAF2025,EU_KLIMATLAG2026,EEA_TP2025"),
    "markpooler": ("Kolförråd per marktyp och pool", "KSLA2025,SLU2025"),
    "bevarande": ("Bevarad andel per markanvändning", "MODELLVAL"),
    "skogskol_kurvbibliotek": ("Skogskolmodellens kurvbibliotek per hektar", "SKOGSKOL104"),
    "kommuner": ("Bilar per hushåll och körsträcka per kommun", "SCB_TAB6589,SCB_TAB6568,RUS_KORSTRACKA,TRAFA_KM_2024"),
    "kostprofiler": ("Kostprofiler: andelar och klimatavtryck", "SCARBOROUGH2023"),
    "ovrig_konsumtion": ("Övrig konsumtion per hushållskategori", "SEI2026"),
    "budget_forster2026": ("Kvarvarande koldioxidbudget från 2026", "FORSTER2026"),
    "befolkning_unwpp2024": ("Världsbefolkning, medelvariant", "UNWPP2024"),
    "personbil_livscykel": ("Personbil: fordon, batteri, förbrukning och bränslen", "ICCT2025,FQD2015,PHEV_ICCT2022,TRAFA_KM_2025"),
}
