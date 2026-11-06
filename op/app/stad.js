/* Road2Zero-OP – stadens klimatredovisning: GHG Protocol for Cities och Malmös klimatbokföring.
   Två sidor som visar stadens utsläpp i de officiella kategorierna för respektive räknemetod, med prognos 2024–2050:
     gpc        GHG Protocol for Cities (WRI, C40 och ICLEI, 2021): klimatkontraktets kategorier (Byggnader, Transport, Avfall,
                IPPU, AFOLU × scope 1, 2 och 3) och GPC:s undersektorer med notationsnycklar (IE, NE), speglade mot klimatkontraktets
                inventering med EU-missionen (GPC BASIC, data för 2022).
     bokforing  territoriella utsläpp i Miljöbarometerns åtta sektorer, med målen −70 % (Malmö) och −80 % (EU-missionen),
                koldioxidbudgeten 2021–2030 och en brygga från Road2Zero-OP:s eget klimatavtryck.
   Modulen ändrar inte Road2Zero-OP:s beräkning. Den läser resultatet från MalmoOP.compute (alltid modell A för trafiken)
   och lägger till de sektorer som OP inte räknar med Malmö stads officiella startvärden. Resultaten speglas mot de officiella
   siffrorna och skillnaderna förklaras, men de kalibreras inte. Beräkningsdelen testas i Node (op/tests/test_stad.js). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.R2ZStad = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const START = 2024;            // startår: OP:s basår och senaste helår i den officiella statistiken
  const FORANDRING_FRAN = 2027;  // som för emissionsfaktorerna i OP: startvärdet gäller till och med 2026
  /* Miljöbarometerns åtta sektorer i Miljöbarometerns ordning (också diagrammens staplingsordning; färgerna ur paletten,
     valda så att grannar skiljer sig). grund: 'egen' = Road2Zero-OP:s egen beräkning, 'fjarrvarme' = officiellt startvärde som
     följer fjärrvärmens klimatfaktor i OP, 'officiell' = officiellt startvärde med egen årlig förändring. */
  const SEKTORER = [
    {id: 'energi', namn: 'Energi', grund: 'fjarrvarme', farg: '#4fa8a0'},
    {id: 'industri', namn: 'Industri', grund: 'officiell', farg: '#1f5a6e'},
    {id: 'jordbruk', namn: 'Jordbruk', grund: 'officiell', farg: '#a3c27a'},
    {id: 'vagtrafik', namn: 'Vägtrafik', grund: 'egen', farg: '#5a86b8'},
    {id: 'sjofart', namn: 'Sjöfart, järnväg och flyg', grund: 'officiell', farg: '#1d4e74'},
    {id: 'arbetsmaskiner', namn: 'Arbetsmaskiner', grund: 'officiell', farg: '#7d939d'},
    {id: 'produkt', namn: 'Produktanvändning', grund: 'officiell', farg: '#bcd3db'},
    {id: 'avfall', namn: 'Avfall och avlopp', grund: 'officiell', farg: '#7aa65a'}
  ];
  const TABELL = SEKTORER.map(s => s.id);
  /* Klimatkontraktets kategorier (GPC-sektorer I–V) i kontraktets ordning. */
  const GPC = [
    {id: 'I', namn: 'Byggnader (stationär energi)', kort: 'Byggnader', farg: '#1f5a6e', ccc: 'stationar'},
    {id: 'II', namn: 'Transport', kort: 'Transport', farg: '#5a86b8', ccc: 'transport'},
    {id: 'III', namn: 'Avfall', kort: 'Avfall', farg: '#7aa65a', ccc: 'avfall'},
    {id: 'IV', namn: 'Industriprocesser och produktanvändning (IPPU)', kort: 'IPPU', farg: '#1d4e74', ccc: 'ippu'},
    {id: 'V', namn: 'Jordbruk, skogsbruk och annan markanvändning (AFOLU)', kort: 'AFOLU', farg: '#a3c27a', ccc: 'afolu'}
  ];
  /* SCB:s förbrukarkategorier för el (TAB3654) fördelade på GPC:s undersektorer för scope 2. */
  const ELKAT = {bostader: ['smahus', 'flerbostadshus', 'fritidshus'], lokaler: ['offentlig', 'ovriga_tjanster'], industri: ['industri'], jordbruk: ['jordbruk']};
  /* GPC:s undersektorer (WRI, C40 och ICLEI, 2021, kapitel 6–10). Ett tal är en funktion av årsraden x; en sträng är en
     notationsnyckel: IE = ingår i annan rad, NE = inte uppskattad. */
  const DETALJ = [
    {kod: 'I.1', grupp: 'I', namn: 'Bostäder', s1: 'IE', s2: x => x.s2kat.bostader, not: 'Egen uppvärmning ingår i I.4 (Miljöbarometerns Energi). El: SCB:s småhus, flerbostadshus och fritidshus.'},
    {kod: 'I.2', grupp: 'I', namn: 'Lokaler och verksamheter', s1: 'IE', s2: x => x.s2kat.lokaler, not: 'Egen uppvärmning ingår i I.4. El: SCB:s offentlig verksamhet och övriga tjänster.'},
    {kod: 'I.3', grupp: 'I', namn: 'Tillverkningsindustri och byggverksamhet', s1: x => x.sek.industri, s2: x => x.s2kat.industri, not: 'Miljöbarometerns Industri, inklusive industriprocesserna (IV.1). El: SCB:s industri och byggverksamhet.'},
    {kod: 'I.4', grupp: 'I', namn: 'Energiindustri', s1: x => x.sek.energi, s2: 'IE', not: 'Miljöbarometerns Energi: el- och värmeproduktion, avfallsförbränningen hos Sysav och egen uppvärmning av bostäder och lokaler.'},
    {kod: 'I.5', grupp: 'I', namn: 'Jordbruk, skogsbruk och fiske', s1: 'IE', s2: x => x.s2kat.jordbruk, not: 'Jordbrukets maskiner ingår i V (Miljöbarometerns Jordbruk), fiskebåtar i II.2–II.4. El: SCB:s jordbruk, skogsbruk och fiske.'},
    {kod: 'I.6–I.8', grupp: 'I', namn: 'Ej specificerat och flyktiga utsläpp', s1: 'NE', s2: 'NE', not: 'Redovisas inte i Miljöbarometern.'},
    {kod: 'II.1', grupp: 'II', namn: 'Vägtrafik', s1: x => x.sek.vagtrafik, s2: 'IE', s3: x => x.mobS3, not: 'Road2Zero-OP: Vägvis modell A, avgaser. Laddel ingår i SCB:s el. Scope 3: bränsleproduktion och fordonstillverkning.'},
    {kod: 'II.2–II.4', grupp: 'II', namn: 'Järnväg, sjöfart och flyg', s1: x => x.sek.sjofart, s2: x => x.s2.jvg, not: 'Miljöbarometern redovisar dem tillsammans: fiskebåtar, inrikes och utrikes sjöfart, järnväg och inrikes flyg. El: SCB:s transporter.'},
    {kod: 'II.5', grupp: 'II', namn: 'Arbetsmaskiner och terrängfordon', s1: x => x.sek.arbetsmaskiner, s2: 'IE', not: 'Miljöbarometerns Arbetsmaskiner: hushåll, verksamheter, industri, byggande och hamnar.'},
    {kod: 'III.1–III.4', grupp: 'III', namn: 'Deponering, biologisk behandling, förbränning och avlopp', s1: x => x.sek.avfall, not: 'Miljöbarometerns Avfall och avlopp. Förbränning med energiåtervinning ingår i I.4.'},
    {kod: 'IV.1', grupp: 'IV', namn: 'Industriprocesser', s1: 'IE', not: 'Ingår i I.3 (Miljöbarometerns Industri).'},
    {kod: 'IV.2', grupp: 'IV', namn: 'Produktanvändning', s1: x => x.sek.produkt, not: 'Miljöbarometerns Produktanvändning: smörjmedel, urea, fluorerade gaser, färg och lösningsmedel.'},
    {kod: 'V.1, V.3', grupp: 'V', namn: 'Boskap och övriga källor på mark', s1: x => x.sek.jordbruk, not: 'Miljöbarometerns Jordbruk, inklusive jordbrukets maskiner.'},
    {kod: 'V.2', grupp: 'V', namn: 'Mark', s1: x => x.mark, not: 'Road2Zero-OP: förändrad markanvändning i utbyggnaden. Ingår inte i klimatkontraktet eller Miljöbarometern.'},
    {kod: 'Scope 3', grupp: null, namn: 'Övrigt: nybyggnation A1–A5', s3: x => x.bygg, not: 'Road2Zero-OP: materialen i nybyggnationen. Utanför BASIC och BASIC+.'}
  ];
  /* Sektorer med egen årlig förändring (% per år från 2027). Standard 0 %: oförändrad nivå från 2024 (modellval). */
  const TAKTER = [
    ['industri', 'Industri'], ['sjofart', 'Sjöfart, järnväg och flyg'], ['arbetsmaskiner', 'Arbetsmaskiner'],
    ['produkt', 'Produktanvändning'], ['avfall', 'Avfall och avlopp'], ['jordbruk', 'Jordbruk'],
    ['ovrigEl', 'Övrig elanvändning (scope 2)']];

  const summa = a => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i]; return s; };
  const varde = (v, x) => typeof v === 'function' ? v(x) : (v || null);   // tal eller notationsnyckel
  const detalj = x => DETALJ.map(d => ({kod: d.kod, grupp: d.grupp, namn: d.namn, not: d.not, s1: varde(d.s1, x), s2: varde(d.s2, x), s3: varde(d.s3, x)}));
  function standard() { return {r: Object.fromEntries(TAKTER.map(([k]) => [k, 0])), ar: 2030, v: 1}; }

  /* ---------- beräkning ---------- */
  /* M = MalmoOP, S = M.prepare(D), R = M.compute(S, P) med perspektiv A, B = klimatbokforing.json, u = urval (takter, år).
     Returnerar t CO2e per år för båda redovisningarna, speglingen mot de officiella siffrorna och bryggan från OP:s klimatavtryck. */
  function berakna(M, S, R, B, u = standard()) {
    if (R.P.perspektiv !== 'A') throw new Error('Stadens redovisning räknar trafiken territoriellt och kräver modell A.');
    const T = B.territoriell, iStart = T.ar.indexOf(START);
    if (iStart < 0) throw new Error('Officiella värden för ' + START + ' saknas.');
    const officiellt = (id, y) => { const i = T.ar.indexOf(y); return i >= 0 ? (id ? T.sektorer[id][i] : T.totalt[i]) * 1000 : null; };
    const start = {}; for (const id of Object.keys(T.sektorer)) start[id] = officiellt(id, START);
    const P = R.P, mob = S.D.mob.A, n = S.n;
    const ttw = new Float64Array(n), wtt = new Float64Array(n), fordon = new Float64Array(n), el = new Float64Array(n);  // andelar av Vägvis modell A
    S.ids.forEach((id, i) => { const a = mob[id]; if (a && a.total > 0) { ttw[i] = a.ttw / a.total; wtt[i] = a.wtt / a.total; fordon[i] = a.fordon / a.total; el[i] = (a.el || 0) / a.total; } });
    // Mobiliteten i R räknar elbilarnas laddel (del av wtt) med modellens elfaktor; avgaserna (ttw) påverkas inte av elvalet.
    const efVagvis = (S.D.mob.elFaktor || {}).A || 0;
    const elByggKwh = P.efEl > 0 ? summa(R.energyBase.tEl) * 1000 / P.efEl : 0;   // byggnadsel ur energideklarationerna
    const elK = B.el_scb.kategorier, elStatKwh = (B.el_scb.totalt - (elK.transporter || 0)) * 1000, elJvgKwh = (elK.transporter || 0) * 1000;
    const ovrigElKwh = Math.max(0, elStatKwh - elByggKwh);           // hushålls-, verksamhets- och industriel
    // andelar av elen utom transporter per GPC-undersektor; normerade så att de summerar till 1 (SCB:s kategorier är avrundade)
    const elKat = {}; for (const [k, kat] of Object.entries(ELKAT)) elKat[k] = kat.reduce((s, c) => s + (elK[c] || 0), 0);
    const elKatSumma = Object.values(elKat).reduce((s, v) => s + v, 0), elAndel = {};
    for (const k of Object.keys(ELKAT)) elAndel[k] = elKatSumma > 0 ? elKat[k] / elKatSumma : 0;
    const r = id => Number(u.r && u.r[id]) || 0;
    const kf = (id, y) => Math.pow(1 + r(id) / 100, Math.max(0, y - (FORANDRING_FRAN - 1)));
    const rader = R.years.map((y, yi) => {
      const f = R.faktorer[yi];
      let vag = 0, mobWtt = 0, mobFordon = 0, mobTot = 0;
      const kEl = efVagvis > 0 ? f.el * 1000 / efVagvis : 1;
      for (let i = 0; i < n; i++) {
        const m = R.comp.mobilitet[yi][i] + R.comp.nymob[yi][i], s = 1 - el[i] + el[i] * kEl, raw = s > 0 ? m / s : 0;
        mobTot += m; vag += raw * ttw[i]; mobWtt += raw * (wtt[i] - el[i] + el[i] * kEl); mobFordon += raw * fordon[i];
      }
      const sek = {energi: start.energi * f.iFv, vagtrafik: vag};
      for (const id of ['industri', 'sjofart', 'arbetsmaskiner', 'produkt', 'avfall', 'jordbruk']) sek[id] = start[id] * kf(id, y);
      const terr = TABELL.reduce((s, id) => s + sek[id], 0);
      // scope 2: el i byggnader och verksamheter (byggnadsel med effektivisering + nya byggnaders el + övrig el) och transporternas el
      const eff = 1 - P.effektivisering2050 / 100 * M.ramp(y), efMix = P.elandelNy * f.el + (1 - P.elandelNy) * f.fv;
      const nyElKwh = efMix > 0 ? summa(R.comp.nydrift[yi]) * 1000 / efMix * P.elandelNy : 0;
      const elKwh = elByggKwh * eff + nyElKwh + ovrigElKwh * kf('ovrigEl', y);
      const s2 = {stat: elKwh * f.el / 1000, jvg: elJvgKwh * f.el / 1000};
      const s2kat = Object.fromEntries(Object.keys(ELKAT).map(k => [k, s2.stat * elAndel[k]]));
      const mark = summa(R.comp.mark[yi]), bygg = summa(R.comp.bygg[yi]), mobS3 = mobWtt + mobFordon;
      const gpc = {
        I: {s1: sek.energi + sek.industri, s2: s2.stat, s3: 0},
        II: {s1: sek.vagtrafik + sek.sjofart + sek.arbetsmaskiner, s2: s2.jvg, s3: mobS3},
        III: {s1: sek.avfall, s2: 0, s3: 0},
        IV: {s1: sek.produkt, s2: 0, s3: 0},
        V: {s1: sek.jordbruk + mark, s2: 0, s3: 0}};
      const basic = gpc.I.s1 + gpc.I.s2 + gpc.II.s1 + gpc.II.s2 + gpc.III.s1;
      // Road2Zero-OP:s eget klimatavtryck samma år (sidan Resultat & klimatbudget, perspektiv A)
      const op = {energi: summa(R.comp.energi[yi]) + summa(R.comp.nydrift[yi]), mobilitet: mobTot, bygg, mark};
      op.total = op.energi + op.mobilitet + op.bygg + op.mark;
      // energin uppdelad på använd el och fjärrvärme: befintliga byggnader ur energyBase, nya byggnader med elandelen
      const opEl = summa(R.energyBase.tEl) * f.iEl * eff + (efMix > 0 ? summa(R.comp.nydrift[yi]) * P.elandelNy * f.el / efMix : 0);
      return {ar: y, inv: summa(R.pop[yi]), sek, terr, s2, s2kat, mark, bygg, mobS3, mobWtt, mobFordon, elKwh, gpc, basic, basicPlus: basic + gpc.IV.s1 + gpc.V.s1, scope3: mobS3 + bygg, op,
        opEl, opFv: op.energi - opEl, detalj: detalj({sek, s2, s2kat, mark, bygg, mobS3})};
    });
    const rad = y => rader.find(x => x.ar === y);
    // mål: −70 % (Malmö) och −80 % (EU-missionen) mot 1990
    const bas = officiellt(null, B.mal.territoriellt.basar), ar2030 = rad(B.mal.territoriellt.ar);
    const mal = {bas, basar: B.mal.territoriellt.basar, ar: B.mal.territoriellt.ar,
      mal70: bas * (1 - B.mal.territoriellt.minskning_pct / 100), mal80: bas * (1 - B.mal.mission.minskning_pct / 100),
      prognos: ar2030 ? ar2030.terr : null, minskning: ar2030 ? 1 - ar2030.terr / bas : null, kvarvarandeMax: bas * B.mal.mission.kvarvarande_max_pct / 100};
    // koldioxidbudget: officiellt utfall till och med senaste år, därefter prognos
    const K = B.mal.koldioxidbudget, sistaOff = Math.max(...T.ar.filter(y => y <= K.slut));
    const budgetAr = []; let kum = 0, slut = null;
    for (let y = K.start; y <= K.slut; y++) {
      const off = T.ar.includes(y) && y <= sistaOff, v = off ? officiellt(null, y) : (rad(y) ? rad(y).terr : null);
      if (v == null) continue;
      kum += v; if (slut == null && kum > K.kt * 1000) slut = y;
      budgetAr.push({ar: y, t: v, kum, officiell: off});
    }
    const utfall = budgetAr.filter(x => x.officiell).reduce((s, x) => s + x.t, 0);
    const budget = {kt: K.kt, start: K.start, slut: K.slut, ar: budgetAr, kum, slutAr: slut, sistaOfficiella: sistaOff,
      utfall, kvarEfterUtfall: K.kt * 1000 - utfall, kvarVidSlut: K.kt * 1000 - kum};
    // spegling mot Miljöbarometern (startåret) och mot klimatkontraktet (dess dataår)
    const r0 = rad(START), ccc = B.gpc_klimatkontrakt, cAr = ccc.dataar;
    const speglingTerr = TABELL.map(id => ({id, namn: SEKTORER.find(x => x.id === id).namn, grund: SEKTORER.find(x => x.id === id).grund,
      officiell: start[id], officiellNasta: officiellt(id, START + 1), modell: r0.sek[id], skillnad: r0.sek[id] - start[id]}));
    const mbAr = id => officiellt(id, cAr);   // Miljöbarometern samma år som klimatkontraktet
    const mbGpc = {I: mbAr('energi') + mbAr('industri'), II: mbAr('vagtrafik') + mbAr('sjofart') + mbAr('arbetsmaskiner'), III: mbAr('avfall'), IV: mbAr('produkt'), V: mbAr('jordbruk')};
    const speglingGpc = GPC.map(g => {
      const c = ccc.rader.find(x => x.id === g.ccc) || {s1: 0, s2: 0};
      return {id: g.id, namn: g.namn, modellS1: r0.gpc[g.id].s1, modellS2: r0.gpc[g.id].s2, cccS1: c.s1 || 0, cccS2: c.s2 || 0, mbS1: mbGpc[g.id],
        skillnad: r0.gpc[g.id].s1 + r0.gpc[g.id].s2 - (c.s1 || 0) - (c.s2 || 0)};
    });
    // brygga: Road2Zero-OP:s klimatavtryck → territoriellt → GPC BASIC+ (startåret)
    const ovriga = ['industri', 'jordbruk', 'sjofart', 'arbetsmaskiner', 'produkt', 'avfall'].reduce((s, id) => s + r0.sek[id], 0);
    const brygga = [
      {text: 'Road2Zero-OP:s klimatavtryck, perspektiv A (sidan Resultat & klimatbudget)', t: r0.op.total, summa: true},
      {text: 'Mobilitet: bränslets produktion och transport och elbilarnas laddel (Vägvis, uppströms; laddelen med vald elfaktor)', t: -r0.mobWtt},
      {text: 'Mobilitet: fordonstillverkning (Vägvis)', t: -r0.mobFordon},
      {text: 'Energi i befintliga och nya byggnader med faktorerna för använd el och fjärrvärme', t: -r0.op.energi},
      {text: 'Nybyggnation A1–A5 och förändrad markanvändning', t: -(r0.bygg + r0.mark)},
      {text: 'Miljöbarometerns Energi: utsläppen vid el- och värmeproduktionen i Malmö och egen uppvärmning', t: r0.sek.energi},
      {text: 'Miljöbarometerns Industri, Jordbruk, Sjöfart/järnväg/flyg, Arbetsmaskiner, Produktanvändning och Avfall och avlopp', t: ovriga},
      {text: 'Stadens klimatbokföring, territoriellt (scope 1)', t: r0.terr, summa: true},
      {text: 'El i scope 2: byggnader, verksamheter och transporter (SCB:s elanvändning × vald elfaktor)', t: r0.s2.stat + r0.s2.jvg},
      {text: 'Förändrad markanvändning (AFOLU, V.2)', t: r0.mark},
      {text: 'GHG Protocol for Cities, BASIC+ (scope 1 + 2)', t: r0.basicPlus, summa: true}];
    const fvKwh = P.efFv > 0 ? summa(R.energyBase.tFv) * 1000 / P.efFv : 0;
    return {rader, start, mal, budget, speglingTerr, speglingGpc, mbGpc, brygga, elAndel,
      el: {byggKwh: elByggKwh, ovrigKwh: ovrigElKwh, jvgKwh: elJvgKwh, statKwh: elStatKwh, fvKwh},
      officiellTotal: officiellt(null, START), officiellTotalCcc: officiellt(null, cAr), cccTotal: ccc.totalt, cccAr: cAr};
  }

  /* ---------- jämförelse av de tre räknesätten ---------- */
  /* Räknesätten i jämförelsen, med färg och linjetyp för diagrammen över tid och sidan där de redovisas. */
  const METODER = [
    {id: 'op', namn: 'Road2Zero-OP:s klimatavtryck', kort: 'Klimatavtryck', farg: '#1f5a6e', dash: 'solid', sida: 'results', sidnamn: 'Resultat & klimatbudget'},
    {id: 'terr', namn: 'Stadens klimatbokföring, territoriellt', kort: 'Territoriellt', farg: '#7aa65a', dash: 'dash', sida: 'bokforing', sidnamn: 'Stadens klimatbokföring'},
    {id: 'gpc', namn: 'GHG Protocol for Cities', kort: 'GPC', farg: '#5a86b8', dash: 'dot', sida: 'gpc', sidnamn: 'GHG Protocol for Cities'}];
  /* Delarna i stapeldiagrammet i staplingsordning: det som ingår i alla tre först, sedan det som bokföringen och GPC delar.
     Färgerna ur paletten, valda så att delar som ligger intill varandra i någon stapel skiljer sig minst ΔE 15 (OKLab). */
  const DELAR = [
    {id: 'avgaser', namn: 'Vägtrafikens avgaser', farg: '#5a86b8'},
    {id: 'produktion', namn: 'El- och värmeproduktion och egen uppvärmning', farg: '#a76019'},
    {id: 'ovriga', namn: 'Industri, sjöfart, arbetsmaskiner, avfall och jordbruk', farg: '#7d939d'},
    {id: 'elScope2', namn: 'El i scope 2', farg: '#2c6e9e'},
    {id: 'trafikLc', namn: 'Trafikens bränsle, laddel och fordon', farg: '#bcd3db'},
    {id: 'energiAnv', namn: 'Använd el och fjärrvärme i byggnaderna', farg: '#4fa8a0'},
    {id: 'bygg', namn: 'Nybyggnation A1–A5', farg: '#1f5a6e'},
    {id: 'mark', namn: 'Förändrad markanvändning', farg: '#a3c27a'}];
  /* Utsläppskällor: v = t CO2e ur årsraden, med = om källan ingår (gpc: 'basic' = i BASIC och BASIC+, 'plus' = bara BASIC+),
     ute = var källan hamnar i ett räknesätt där den inte ingår, op = vad en översiktsplan kan påverka (bedömning, modellval). */
  const KALLOR = [
    {id: 'avgaser', del: 'avgaser', namn: 'Vägtrafikens avgaser på stadens vägar', v: x => x.sek.vagtrafik, med: {op: true, terr: true, gpc: 'basic'}, gpcKod: 'II.1, scope 1', ute: {},
      op: 'Stor: lokalisering, täthet, gatunät, parkering och kollektivtrafik påverkar hur mycket som körs.'},
    {id: 'bransle', del: 'trafikLc', namn: 'Bränslets produktion och transport, elbilarnas laddel', v: x => x.mobWtt, med: {op: true, terr: false, gpc: false},
      ute: {terr: 'Utanför gränsen: bränslet och elen produceras i regel utanför staden.', gpc: 'Scope 3, utanför summan; laddelen ingår i elen i scope 2.'},
      op: 'Som avgaserna: följer hur mycket som körs.'},
    {id: 'fordon', del: 'trafikLc', namn: 'Tillverkning av fordon och batterier', v: x => x.mobFordon, med: {op: true, terr: false, gpc: false},
      ute: {terr: 'Utanför gränsen: fordonen tillverkas utanför staden.', gpc: 'Scope 3, utanför summan.'},
      op: 'Viss: bilinnehavet följer täthet, parkering och närhet till kollektivtrafik.'},
    {id: 'anvEl', del: 'energiAnv', namn: 'Använd el i befintliga och nya byggnader', v: x => x.opEl, med: {op: true, terr: false, gpc: false},
      ute: {terr: 'Utanför gränsen: importerad el ingår inte; elproduktion i staden ingår i el- och värmeproduktionen.', gpc: 'I stället el i scope 2 med SCB:s elanvändning.'},
      op: 'Viss: täthet, byggnadstyper och lokal elproduktion. Energikraven på byggnaderna är nationella.'},
    {id: 'anvFv', del: 'energiAnv', namn: 'Använd fjärrvärme i befintliga och nya byggnader', v: x => x.opFv, med: {op: true, terr: false, gpc: false},
      ute: {terr: 'Räknas vid produktionen (el- och värmeproduktionen).', gpc: 'Räknas vid produktionen i scope 1 (I.4).'},
      op: 'Viss: fjärrvärmenätets utbyggnad och täthet. Produktionen styrs av energibolaget.'},
    {id: 'elScope2', del: 'elScope2', namn: 'El i scope 2: stadens elanvändning enligt SCB × elfaktorn', v: x => x.s2.stat + x.s2.jvg, med: {op: false, terr: false, gpc: 'basic'}, gpcKod: 'I.1–I.5 och II.2–II.4, scope 2',
      ute: {op: 'Byggnadernas el ingår i stället som använd el, ur energideklarationerna.', terr: 'Utanför gränsen: importerad el ingår inte.'},
      op: 'Viss: som använd el i byggnaderna.'},
    {id: 'produktion', del: 'produktion', namn: 'El- och värmeproduktion i staden och egen uppvärmning', v: x => x.sek.energi, med: {op: false, terr: true, gpc: 'basic'}, gpcKod: 'I.4, scope 1',
      ute: {op: 'I stället använd el och fjärrvärme i byggnaderna.'},
      op: 'Liten: produktionen och avfallsmängderna styrs av energibolaget och avfallsplaneringen. ÖP kan reservera mark för anläggningar.'},
    {id: 'industri', del: 'ovriga', namn: 'Industri, inklusive industriprocesser', v: x => x.sek.industri, med: {op: false, terr: true, gpc: 'basic'}, gpcKod: 'I.3, scope 1',
      ute: {op: 'Ingår inte: verksamheternas egen förbränning och processer räknas inte.'}, op: 'Liten: mark för verksamheter.'},
    {id: 'produkt', del: 'ovriga', namn: 'Produktanvändning', v: x => x.sek.produkt, med: {op: false, terr: true, gpc: 'plus'}, gpcKod: 'IV.2, scope 1', ute: {op: 'Ingår inte.', gpc: 'Ingår inte i BASIC.'},
      op: 'Liten.'},
    {id: 'sjofart', del: 'ovriga', namn: 'Sjöfart, järnväg och inrikes flyg', v: x => x.sek.sjofart, med: {op: false, terr: true, gpc: 'basic'}, gpcKod: 'II.2–II.4, scope 1', ute: {op: 'Ingår inte: OP räknar vägtrafiken.'},
      op: 'Liten: hamnens och spårens lokalisering.'},
    {id: 'arbetsmaskiner', del: 'ovriga', namn: 'Arbetsmaskiner', v: x => x.sek.arbetsmaskiner, med: {op: false, terr: true, gpc: 'basic'}, gpcKod: 'II.5, scope 1',
      ute: {op: 'Ingår inte; byggarbetsplatsens maskiner ingår i nybyggnationens A5.'}, op: 'Liten.'},
    {id: 'avfall', del: 'ovriga', namn: 'Avfall och avlopp', v: x => x.sek.avfall, med: {op: false, terr: true, gpc: 'basic'}, gpcKod: 'III, scope 1', ute: {op: 'Ingår inte.'},
      op: 'Liten: mark för avfallsanläggningar och avloppsrening.'},
    {id: 'jordbruk', del: 'ovriga', namn: 'Jordbruk', v: x => x.sek.jordbruk, med: {op: false, terr: true, gpc: 'plus'}, gpcKod: 'V.1 och V.3, scope 1',
      ute: {op: 'Ingår inte; den mark som bebyggs ingår i förändrad markanvändning.', gpc: 'Ingår inte i BASIC.'}, op: 'Viss: hur mycket jordbruksmark som bebyggs.'},
    {id: 'bygg', del: 'bygg', namn: 'Nybyggnation, material och byggskede A1–A5', v: x => x.bygg, med: {op: true, terr: false, gpc: false},
      ute: {terr: 'Utanför gränsen: materialen tillverkas i regel utanför staden.', gpc: 'Scope 3, utanför summan.'},
      op: 'Stor: hur mycket, var och hur det byggs, och om befintliga byggnader kan användas i stället.'},
    {id: 'mark', del: 'mark', namn: 'Förändrad markanvändning: kolförråd i mark och växtlighet', v: x => x.mark, med: {op: true, terr: false, gpc: 'plus'}, gpcKod: 'V.2',
      ute: {terr: 'Ingår inte i Miljöbarometern.', gpc: 'Ingår inte i BASIC.'}, op: 'Stor: var det byggs och hur mycket åker och grönyta som bevaras.'}];
  const NIVAER = {plus: 'BASIC+', basic: 'BASIC'};
  function jamforStandard() { return {lage: 'period', p0: 2027, p1: 2050, ar: 2030, niva: 'plus'}; }
  const ingar = (k, m, niva) => m === 'gpc' ? (k.med.gpc === 'basic' || (k.med.gpc === 'plus' && niva === 'plus')) : k.med[m] === true;

  /* Jämför räknesätten för valda år. res = berakna(…), j = {lage: 'period' | 'ar', p0, p1, ar, niva: 'plus' | 'basic'}.
     Ackumulerat = summan av årsvärdena; per invånare = medel av årens utsläpp per invånare (som på sidan Resultat). */
  function jamforelse(res, jIn) {
    const j = {...jamforStandard(), ...(jIn || {})}, alla = res.rader.map(x => x.ar);
    const fran = j.lage === 'ar' ? j.ar : Math.min(j.p0, j.p1), till = j.lage === 'ar' ? j.ar : Math.max(j.p0, j.p1);
    const sel = res.rader.filter(x => x.ar >= fran && x.ar <= till);
    if (!sel.length) throw new Error('Inga år mellan ' + fran + ' och ' + till + '.');
    const kallor = KALLOR.map(k => ({id: k.id, del: k.del, namn: k.namn, gpcKod: k.gpcKod, ute: k.ute, op: k.op,
      t: sel.reduce((s, x) => s + k.v(x), 0), ingar: Object.fromEntries(METODER.map(m => [m.id, ingar(k, m.id, j.niva)]))}));
    const metoder = METODER.map(m => {
      const delar = Object.fromEntries(DELAR.map(d => [d.id, 0]));
      for (const k of kallor) if (k.ingar[m.id]) delar[k.del] += k.t;
      const arsvarde = x => KALLOR.reduce((s, k) => s + (ingar(k, m.id, j.niva) ? k.v(x) : 0), 0);
      const perAr = res.rader.map(arsvarde);
      const perPerson = sel.reduce((s, x) => s + (x.inv > 0 ? arsvarde(x) / x.inv : 0), 0) / sel.length;
      return {...m, namn: m.id === 'gpc' ? m.namn + ', ' + NIVAER[j.niva] : m.namn, kort: m.id === 'gpc' ? 'GPC ' + NIVAER[j.niva] : m.kort,
        delar, total: Object.values(delar).reduce((s, v) => s + v, 0), perAr, perPerson};
    });
    // brygga: klimatavtrycket → territoriellt → GPC, en rad per del som skiljer
    const steg = (fore, efter, plus, minus) => DELAR.map(d => {
      const v = efter.delar[d.id] - fore.delar[d.id];
      if (Math.abs(v) < 1e-6) return null;
      const k = KALLOR.filter(x => x.del === d.id), diff = k.filter(x => ingar(x, fore.id, j.niva) !== ingar(x, efter.id, j.niva));
      const lc = s => s.charAt(0).toLowerCase() + s.slice(1);
      const namn = diff.length === k.length ? [d.namn] : diff.map(x => x.namn.split(':')[0]);
      const vad = namn.length === 1 ? lc(namn[0]) : namn.slice(0, -1).map(lc).join(', ') + ' och ' + lc(namn[namn.length - 1]);
      return {del: d.id, text: (v > 0 ? plus : minus) + vad, t: v};
    }).filter(Boolean).sort((a, b) => (a.t > 0) - (b.t > 0));   // först det som tas bort, sedan det som läggs till
    const [op, terr, gpc] = metoder;
    const brygga = [{text: op.namn, t: op.total, summa: true, metod: 'op'},
      ...steg(op, terr, 'Läggs till i bokföringen: ', 'Ingår inte i bokföringen: '), {text: terr.namn, t: terr.total, summa: true, metod: 'terr'},
      ...steg(terr, gpc, 'Läggs till i GPC: ', 'Ingår inte i ' + NIVAER[j.niva] + ': '), {text: gpc.namn, t: gpc.total, summa: true, metod: 'gpc'}];
    const gemensamma = kallor.filter(k => METODER.every(m => k.ingar[m.id]));
    return {j, lage: j.lage, fran, till, ar: sel.map(x => x.ar), alla, kallor, metoder, brygga,
      gemensamt: {t: gemensamma.reduce((s, k) => s + k.t, 0), kallor: gemensamma.map(k => k.namn)}};
  }

  /* ---------- förklaringar av skillnaderna (text med siffror ur underlaget) ---------- */
  const nf = (x, d = 0) => x == null || !Number.isFinite(x) ? '–' : new Intl.NumberFormat('sv-SE', {maximumFractionDigits: d, minimumFractionDigits: d}).format(x);
  const kt = (t, d = 1) => nf(t / 1000, d);
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const utanPunkt = t => String(t || '').replace(/\.\s*$/, '');
  const kalla = (B, id) => B.kallor[id] ? esc(B.kallor[id].kort) : esc(id);
  const kalibrering = S => { const m = S.D.mob.A_metadata || {}, ref = m.reference && m.reference.reference; return utanPunkt(ref && ref.source ? ref.source : 'Miljöbarometerns vägtrafik ' + START); };
  const pm = v => (v > 0 ? '+' : v < 0 ? '−' : '') + kt(Math.abs(v));

  function forklaringTerr(S, B, res, id) {
    const x = res.speglingTerr.find(s => s.id === id), r0 = res.rader.find(y => y.ar === START);
    if (id === 'vagtrafik') return 'Road2Zero-OP:s egen beräkning: Vägvis modell A, trafiken på vägarna i varje DeSO gånger emissionsfaktorer, bara avgaserna. ' +
      'Vägvis är kalibrerad mot ' + esc(kalibrering(S)) + '. Miljöbarometern räknar vägtrafiken i ENVIMAN med fordonsflöden per väg och visar i den senaste uppdateringen ' +
      kt(x.officiell) + ' kt. Därför är OP ' + kt(Math.abs(x.skillnad)) + ' kt (' + nf(100 * Math.abs(x.skillnad) / x.officiell, 1) + ' %) ' + (x.skillnad < 0 ? 'lägre' : 'högre') + '.';
    if (id === 'energi') return 'Startvärdet är Miljöbarometerns värde för ' + START + ', så skillnaden är 0 per definition. OP:s egen energi på resultatsidan (' + kt(r0.op.energi) +
      ' kt) används inte här: den räknar använd el och fjärrvärme med Boverkets faktorer, medan Miljöbarometern räknar utsläppen där värmen och elen produceras (se bryggan nedan).';
    return 'Startvärdet är Miljöbarometerns värde för ' + START + ', så skillnaden är 0 per definition. Det är ingen oberoende kontroll; OP räknar inte sektorn själv.';
  }
  function forklaringGpc(B, res, id) {
    const x = res.speglingGpc.find(s => s.id === id), r0 = res.rader.find(y => y.ar === START), cAr = res.cccAr, mbS = id => kt(res.mbGpc[id]);
    const MB = k => B.territoriell.sektorer[k][B.territoriell.ar.indexOf(cAr)];
    switch (id) {
      case 'I': return 'Scope 1: OP = Miljöbarometerns Energi (' + kt(r0.sek.energi) + ') + Industri (' + kt(r0.sek.industri) + ') ' + START + '. Samma sektorer ' + cAr + ': ' + mbS('I') +
        ' kt, alltså ' + kt(x.cccS1 - res.mbGpc.I) + ' kt mindre än kontraktets ' + kt(x.cccS1) + ' kt. Kontraktet räknar i CIRIS från energianvändning och emissionsfaktorer och tar med cirka 500 000 ton avfall i fjärrvärmesystemet; ' +
        'Miljöbarometern räknar anläggningarnas egna utsläpp i ENVIMAN och utesluter biogen koldioxid. Vilka bränslen och faktorer CIRIS använt går inte att se i kontraktet. ' +
        'Scope 2: OP = ' + nf(r0.elKwh / 1e6, 0) + ' GWh × ' + nf(r0.s2.stat * 1e6 / r0.elKwh, 0) + ' g/kWh = ' + kt(x.modellS2) + ' kt; kontraktets ' + kt(x.cccS2) +
        ' kt motsvarar ' + nf(x.cccS2 * 1e6 / res.el.statKwh, 0) + ' g/kWh på samma elanvändning, alltså en högre elfaktor.';
      case 'II': return 'Scope 1: OP = vägtrafik ' + kt(r0.sek.vagtrafik) + ' (Vägvis) + sjöfart, järnväg och flyg ' + kt(r0.sek.sjofart) + ' + arbetsmaskiner ' + kt(r0.sek.arbetsmaskiner) +
        '. Miljöbarometerns samma sektorer ' + cAr + ': ' + mbS('II') + ' kt. Kontraktets ' + kt(x.cccS1) + ' kt är ' + nf(x.cccS1 / res.mbGpc.II, 1) + ' gånger så mycket. ' +
        'Kontraktet hämtade transportens scope 1 ur Nationella emissionsdatabasen (SMED), som fördelar Sveriges utsläpp uppifrån och ned till kommunerna med vägnät och annan statistik. ' +
        'Miljöbarometern räknar trafiken nerifrån och upp i ENVIMAN med fordonsflöden per väg, eftersom staden bedömer det som säkrare. Skillnaden är alltså två olika källor, inte ett räknefel. ' +
        'Scope 2: OP = SCB:s el för transporter, ' + nf(res.el.jvgKwh / 1e6, 0) + ' GWh × elfaktorn = ' + kt(x.modellS2) + ' kt; kontraktet ' + kt(x.cccS2) + ' kt, bara järnvägens el.';
      case 'III': return 'OP = Miljöbarometerns Avfall och avlopp (deponier, avloppsrening, biologisk behandling, krematorier, farligt avfall) ' + START + '; ' + cAr + ': ' + kt(MB('avfall') * 1000) +
        ' kt. Kontraktets ' + kt(x.cccS1) + ' kt bygger på avfallsmängder och SMED och är ' + kt(MB('avfall') * 1000 - x.cccS1) + ' kt lägre än Miljöbarometern samma år; kontraktet anger inte vilka delar som ingår, till exempel avloppsreningen. ' +
        'Förbränning med energiåtervinning ligger i båda under byggnader.';
      case 'IV': return 'OP = Miljöbarometerns Produktanvändning ' + START + '; ' + cAr + ': ' + kt(MB('produkt') * 1000) + ' kt. Kontraktets ' + kt(x.cccS1) +
        ' kt kommer från SMED. Industriprocesserna ligger i Miljöbarometerns Industri och därmed under byggnader i OP; i kontraktet kan en del av dem ligga här.';
      case 'V': return 'OP = Miljöbarometerns Jordbruk ' + kt(r0.sek.jordbruk) + ' kt (' + cAr + ': ' + kt(MB('jordbruk') * 1000) + ') + förändrad markanvändning ' + kt(r0.mark) +
        ' kt. Miljöbarometerns jordbruk omfattar också jordbrukets maskiner; kontraktets ' + kt(x.cccS1) + ' kt kommer från SMED och omfattar inte marken.';
    }
    return '';
  }

  /* ---------- gränssnitt (bara i webbläsaren) ---------- */
  const INK = '#15211d', INK2 = '#56635e', GRID = '#e3e9e6', SURF = '#fbfcfb', LINJE = '#c9d4cf', VARNING = '#a4442c', BUDGET = '#2f6b3f';
  const rgba = (h, a) => 'rgba(' + parseInt(h.slice(1, 3), 16) + ',' + parseInt(h.slice(3, 5), 16) + ',' + parseInt(h.slice(5, 7), 16) + ',' + a + ')';
  const CONF = {displaylogo: false, responsive: true, toImageButtonOptions: {format: 'png', scale: 2}};
  const STORE = 'r2z-op-stad';
  const GRUND = {egen: 'Egen beräkning (Vägvis modell A, avgaser)', fjarrvarme: 'Officiellt startvärde × fjärrvärmens klimatfaktor', officiell: 'Officiellt startvärde × egen förändring'};

  let st = null;
  function urvalStart() {
    let s = null; try { s = JSON.parse(localStorage.getItem(STORE) || 'null'); } catch (e) { s = null; }
    const u = standard(); u.j = jamforStandard();
    if (s && typeof s === 'object') {
      if (s.r && typeof s.r === 'object') for (const [k] of TAKTER) { const v = Number(s.r[k]); if (Number.isFinite(v)) u.r[k] = Math.max(-50, Math.min(50, v)); }
      if (Number.isFinite(Number(s.ar))) u.ar = Number(s.ar);
      if (s.j && typeof s.j === 'object') {
        if (['period', 'ar'].includes(s.j.lage)) u.j.lage = s.j.lage;
        if (NIVAER[s.j.niva]) u.j.niva = s.j.niva;
        for (const k of ['p0', 'p1', 'ar']) if (Number.isInteger(Number(s.j[k]))) u.j[k] = Number(s.j[k]);
      }
    }
    return u;
  }
  /* Håll jämförelsens år inom modellens år (2024–2050). */
  function jamforUrval(ar) {
    const j = st.j, inom = y => Math.max(ar[0], Math.min(ar[ar.length - 1], y)), std = jamforStandard();
    for (const k of ['p0', 'p1', 'ar']) j[k] = ar.includes(j[k]) ? j[k] : inom(std[k]);
    if (j.p0 > j.p1) [j.p0, j.p1] = [j.p1, j.p0];
    return j;
  }
  function spara() { try { localStorage.setItem(STORE, JSON.stringify(st)); } catch (e) { /* lagring ej tillgänglig */ } }
  function layout(titel, undertitel, hojd, yt) {
    return {title: {text: '<b>' + titel + '</b>' + (undertitel ? '<br><span style="font-size:12px;color:' + INK2 + '">' + undertitel + '</span>' : ''), x: 0, xanchor: 'left', font: {size: 16, color: INK}},
      font: {family: 'Inter, system-ui, sans-serif', size: 13, color: INK}, height: hojd || 440, plot_bgcolor: SURF, paper_bgcolor: SURF,
      margin: {l: 10, r: 10, t: 72, b: 10}, legend: {orientation: 'h', yanchor: 'top', y: -0.16, x: 0, font: {size: 12}, traceorder: 'normal'},
      hoverlabel: {bgcolor: 'white', bordercolor: LINJE, font: {size: 12, color: INK}}, separators: ', ', hovermode: 'x unified',
      xaxis: {showgrid: false, linecolor: LINJE, tickcolor: LINJE, automargin: true},
      yaxis: {gridcolor: GRID, zerolinecolor: INK2, zerolinewidth: 1, title: {text: yt || 'kt CO2e'}, tickformat: ',.0f', automargin: true, rangemode: 'tozero'}};
  }
  const lum = h => { const c = [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16) / 255).map(v => v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
  const textfarg = h => 1.05 / (lum(h) + 0.05) >= (lum(h) + 0.05) / (lum(INK) + 0.05) ? '#ffffff' : INK;   // vit eller mörk text, den som kontrasterar mest
  const radbryt = (t, n) => { const ord = esc(t).split(' '), rader = ['']; for (const o of ord) { const r = rader[rader.length - 1]; if (r && (r + ' ' + o).length > n) rader.push(o); else rader[rader.length - 1] = r ? r + ' ' + o : o; } return rader.join('<br>'); };
  const kort = (l, v, f, huvud) => '<div class="card' + (huvud ? ' kpi-main' : '') + '"><div class="kpi-label">' + l + '</div><div class="kpi-value">' + v + '</div><div class="kpi-foot">' + f + '</div></div>';
  const cell = v => '<td class="numeric">' + (typeof v === 'string' ? '<span class="r2zs-nyckel">' + esc(v) + '</span>' : v ? kt(v) : '–') + '</td>';
  const num = v => typeof v === 'number' ? v : 0;

  function panel(ctx, B, vy) {
    const P = ctx.P, ar = ctx.R.years, opt = (v, l, val) => '<option value="' + v + '"' + (v === val ? ' selected' : '') + '>' + l + '</option>';
    const takter = TAKTER.filter(([k]) => vy !== 'bokforing' || k !== 'ovrigEl').map(([k, l]) =>
      '<label class="field">' + esc(l) + ', % per år<input class="input" type="number" step="0.1" min="-50" max="50" data-r2zs-takt="' + k + '" value="' + st.r[k] + '"></label>').join('');
    const fl = [P.flotta2030, P.flotta2040, P.flotta2050].map(v => nf(v, 2)).join(' / ');
    let forsta;
    if (vy === 'jamfor') {
      const j = st.j, val = (k, a) => '<select data-r2zs-j="' + k + '">' + a.map(y => opt(y, y, j[k])).join('') + '</select>';
      forsta = '<div class="r2zr-rad r2zr-val" style="margin-top:0"><div><div class="r2zr-etikett">Jämför</div><div class="toggle" style="margin:0">' +
        [['period', 'Ackumulerat'], ['ar', 'Ett år']].map(([v, l]) => '<button type="button" data-r2zs-lage="' + v + '" class="' + (j.lage === v ? 'active' : '') + '">' + l + '</button>').join('') + '</div></div>' +
        (j.lage === 'period' ? '<label class="field">Från' + val('p0', ar) + '</label><label class="field">Till och med' + val('p1', ar) + '</label>'
          : '<label class="field">År' + val('ar', ar) + '</label>') +
        '<label class="field">Nivå i GHG Protocol for Cities<select data-r2zs-j="niva">' + opt('plus', 'BASIC+ (som klimatkontraktet)', j.niva) + opt('basic', 'BASIC', j.niva) + '</select></label></div>' +
        '<div class="r2zr-etikett" style="margin-top:16px">Årlig förändring från ' + FORANDRING_FRAN + ' för de sektorer som Road2Zero-OP inte räknar själv</div><div class="r2zr-rad r2zr-val" style="margin-top:0">' + takter + '</div>';
    } else forsta = '<div class="r2zr-rad r2zr-val" style="margin-top:0">' +
      '<label class="field">Visa år i tabellerna<select data-r2zs="ar">' + ar.map(y => opt(y, y, st.ar)).join('') + '</select></label>' + takter + '</div>';
    return '<article class="card r2zr-urval">' + forsta +
      '<p class="small">Sektorerna som Road2Zero-OP inte räknar själv börjar på Malmö stads officiella värden för ' + START + ' (' + kalla(B, B.territoriell.kalla) + ') och förändras med den årliga takten från ' + FORANDRING_FRAN + '. Standard är 0 %, oförändrad nivå. ' +
      'Energisektorn följer fjärrvärmens klimatfaktor (' + (P.beccs === 'ja' ? 'med Sysavs koldioxidavskiljning från ' + P.beccsAr + ', −' + nf(P.beccsMinskning) + ' %' : 'utan Sysavs koldioxidavskiljning') + '), vägtrafiken fordonsflottans klimatfaktor ' + fl + ' för 2030 / 2040 / 2050 och trafikförändringen ' + nf(P.trafikForandring2050) + ' % till 2050, och elen elens klimatfaktor. ' +
      'De ändras under <button type="button" class="link-btn" data-go="parameters">Antaganden &amp; scenario</button>. Trafiken räknas alltid territoriellt med Vägvis modell A, oavsett perspektivet i sidomenyn.' +
      (vy === 'jamfor' ? '' : ' Jämför med de andra räknesätten under <button type="button" class="link-btn" data-go="jamfor">Jämför räknesätten</button>.') + '</p></article>';
  }

  /* ----- sidan GHG Protocol for Cities ----- */
  function gpcHtml(ctx, B, res) {
    const r0 = res.rader[0], rv = res.rader.find(x => x.ar === st.ar) || r0, ccc = B.gpc_klimatkontrakt;
    let h = '<section class="r2zr-kpis">' +
      kort('BASIC+ ' + r0.ar, kt(r0.basicPlus, 0) + '<small> kt CO₂e</small>', 'Scope 1 + 2 i alla fem kategorier, som klimatkontraktet räknar', true) +
      kort('BASIC ' + r0.ar, kt(r0.basic, 0) + '<small> kt</small>', 'Byggnader och transport (scope 1 + 2) och avfall (scope 1)') +
      kort('Klimatkontraktet ' + res.cccAr, kt(res.cccTotal, 0) + '<small> kt</small>', 'GPC BASIC beräknad i CIRIS (' + kalla(B, 'CCC') + ')') +
      kort('BASIC+ ' + rv.ar, kt(rv.basicPlus, 0) + '<small> kt</small>', nf(100 * (rv.basicPlus / r0.basicPlus - 1), 0) + ' % mot ' + r0.ar) +
      kort('Scope 3 ' + rv.ar, kt(rv.scope3, 0) + '<small> kt</small>', 'Utanför summorna: trafikens bränsleproduktion och fordon, nybyggnation') + '</section>';
    // 1. klimatkontraktets kategorier
    h += '<article class="card"><h2>Utsläpp ' + rv.ar + ' i klimatkontraktets kategorier (kt CO₂e)</h2><p class="small">Samma kategorier och scope som Malmö stads inventering i klimatkontraktet (avsnitt A-1.4).</p><div class="table-wrap r2zs-full"><table class="r2zs-tab"><thead><tr><th>Kategori</th><th class="numeric">Scope 1</th><th class="numeric">Scope 2</th><th class="numeric">Scope 3</th><th class="numeric">Totalt (scope 1 + 2)</th></tr></thead><tbody>' +
      GPC.map(g => { const v = rv.gpc[g.id]; return '<tr><td>' + esc(g.namn) + '</td>' + cell(v.s1) + cell(v.s2) + cell(v.s3) + cell(v.s1 + v.s2) + '</tr>'; }).join('') +
      '<tr class="r2zs-sum"><td>Totalt</td>' + cell(GPC.reduce((s, g) => s + rv.gpc[g.id].s1, 0)) + cell(GPC.reduce((s, g) => s + rv.gpc[g.id].s2, 0)) + cell(rv.scope3 - rv.bygg) + cell(rv.basicPlus) + '</tr></tbody></table></div>' +
      '<p class="small">Scope 3 är information och ingår inte i totalen: trafikens bränsleproduktion och fordonstillverkning (Vägvis). Nybyggnationens material, ' + kt(rv.bygg) + ' kt, redovisas som övrigt scope 3 i tabellen över undersektorer.</p></article>';
    // 2. spegling med förklaring
    const sp = res.speglingGpc;
    h += '<article class="card"><h2>Spegling mot klimatkontraktet och förklaring</h2><p class="small">Road2Zero-OP ' + START + ' mot klimatkontraktets inventering (data för ' + res.cccAr + ') och Miljöbarometerns samma sektorer för ' + res.cccAr + '. Siffrorna korrigeras inte mot varandra.</p><div class="table-wrap r2zs-full"><table class="r2zs-tab r2zs-forklaring"><thead><tr><th>Kategori</th><th class="numeric">OP ' + START + ' scope 1</th><th class="numeric">OP ' + START + ' scope 2</th><th class="numeric">Kontraktet ' + res.cccAr + ' scope 1</th><th class="numeric">Kontraktet ' + res.cccAr + ' scope 2</th><th class="numeric">Miljöbarometern ' + res.cccAr + ' scope 1</th><th class="numeric">Skillnad OP − kontraktet</th></tr></thead><tbody>' +
      sp.map(x => '<tr class="r2zs-datarad"><td>' + esc(x.namn) + '</td>' + cell(x.modellS1) + cell(x.modellS2) + cell(x.cccS1) + cell(x.cccS2) + cell(x.mbS1) + '<td class="numeric">' + pm(x.skillnad) + '</td></tr>' +
        '<tr class="r2zs-whyrow"><td colspan="7"><b>Varför:</b> ' + forklaringGpc(B, res, x.id) + '</td></tr>').join('') +
      '<tr class="r2zs-sum"><td>Totalt</td>' + cell(sp.reduce((a, x) => a + x.modellS1, 0)) + cell(sp.reduce((a, x) => a + x.modellS2, 0)) + cell(sp.reduce((a, x) => a + x.cccS1, 0)) + cell(sp.reduce((a, x) => a + x.cccS2, 0)) + cell(sp.reduce((a, x) => a + x.mbS1, 0)) + '<td class="numeric">' + pm(r0.basicPlus - res.cccTotal) + '</td></tr>' +
      '<tr class="r2zs-whyrow"><td colspan="7"><b>Varför:</b> Året förklarar lite: Miljöbarometerns total var ' + kt(res.officiellTotalCcc, 0) + ' kt ' + res.cccAr + ' och ' + kt(res.officiellTotal, 0) + ' kt ' + START + '. Nästan hela skillnaden ligger i transport och byggnader, där kontraktet använder andra källor och metoder (CIRIS och SMED) än Miljöbarometern (ENVIMAN).</td></tr></tbody></table></div></article>';
    // 3. GPC:s undersektorer
    const grupper = GPC.map(g => {
      const rows = rv.detalj.filter(d => d.grupp === g.id);
      return '<tr class="r2zs-grupp"><td><b>' + g.id + ' ' + esc(g.namn) + '</b></td>' + cell(rv.gpc[g.id].s1) + cell(rv.gpc[g.id].s2) + cell(rv.gpc[g.id].s3) + '<td></td></tr>' +
        rows.map(d => '<tr class="r2zs-sub"><td>' + esc(d.kod) + ' ' + esc(d.namn) + '</td>' + cell(d.s1) + cell(d.s2) + cell(d.s3) + '<td class="r2zs-not">' + esc(d.not) + '</td></tr>').join('');
    }).join('');
    const ov = rv.detalj.find(d => d.grupp === null);
    h += '<article class="card"><h2>GPC:s undersektorer ' + rv.ar + ' (kt CO₂e)</h2><div class="table-wrap r2zs-full"><table class="r2zs-tab"><thead><tr><th>Undersektor enligt GPC</th><th class="numeric">Scope 1</th><th class="numeric">Scope 2</th><th class="numeric">Scope 3</th><th>Underlag och avgränsning</th></tr></thead><tbody>' + grupper +
      '<tr class="r2zs-sub"><td>' + esc(ov.kod) + ': ' + esc(ov.namn) + '</td>' + cell(null) + cell(null) + cell(ov.s3) + '<td class="r2zs-not">' + esc(ov.not) + '</td></tr>' +
      '<tr class="r2zs-sum"><td>BASIC</td><td></td><td></td><td></td><td class="numeric r2zs-v">' + kt(rv.basic) + '</td></tr><tr class="r2zs-sum"><td>BASIC+ (klimatkontraktets avgränsning)</td><td></td><td></td><td></td><td class="numeric r2zs-v">' + kt(rv.basicPlus) + '</td></tr></tbody></table></div>' +
      '<p class="small">Notationsnycklar enligt GPC: IE = ingår i en annan rad (included elsewhere), NE = inte uppskattad (not estimated). El i scope 2 fördelas på undersektorerna med SCB:s förbrukarkategorier ' + B.el_scb.ar + ' (' + kalla(B, B.el_scb.kalla) + ').</p></article>';
    return h + '<article class="card r2zr-fig" id="r2zs-gpc-tid"></article><article class="card r2zr-fig" id="r2zs-gpc-spegel"></article>' + metodGpc(ctx, B, res);
  }
  function metodGpc(ctx, B, res) {
    return '<article class="card method-text"><h2>Så räknas GHG Protocol for Cities här</h2>' +
      '<p>GHG Protocol for Cities (GPC) delar stadens utsläpp i fem sektorer och tre scope (' + kalla(B, 'GPC2021') + '). Scope 1 är utsläpp inom stadens gräns, scope 2 kommer från el, värme och kyla från nätet som används i staden, och scope 3 är övriga utsläpp utanför gränsen som staden orsakar. Nivån BASIC omfattar scope 1 och 2 för stationär energi och transport och scope 1 för avfall; BASIC+ lägger till IPPU och AFOLU. Malmö stad redovisar inventeringen i klimatkontraktet i fem kategorier: byggnader (stationär energi), transport, avfall, IPPU och AFOLU (' + kalla(B, 'CCC') + ').</p>' +
      '<p><b>Fjärrvärmen räknas som i klimatkontraktet:</b> utsläppen där värmen produceras, i scope 1 under energiindustrin, främst förbränningen av plast i avfallet hos Sysav. I strikt GPC redovisas produktion som levereras till nätet i scope 1 men räknas inte i BASIC-summan; klimatkontraktet räknar in den, och det gör Road2Zero-OP också. Fjärrvärmen räknas därför inte en gång till i scope 2.</p>' +
      '<p><b>El i scope 2</b> är elanvändningen ' + B.el_scb.ar + ' utom transporter enligt SCB, ' + nf(res.el.statKwh / 1e6, 0) + ' GWh: byggnadsel ur energideklarationerna, ' + nf(res.el.byggKwh / 1e6, 0) + ' GWh, som följer effektiviseringen i OP, el i nya byggnader och övrig el, ' + nf(res.el.ovrigKwh / 1e6, 0) + ' GWh, med egen årlig förändring. Elfaktorn är den som valts under Antaganden & scenario, ' + esc(ctx.M.EL_ALT[ctx.P.elVal].namn.toLowerCase()) + ', ' + nf(1000 * ctx.P.efEl, 0) + ' g CO₂e/kWh ' + START + ', med valets utveckling över tid. Elbilarnas laddning ingår i SCB:s el och räknas med samma faktor.</p>' +
      '<p><b>Vägtrafiken</b> är Road2Zero-OP:s egen beräkning: Vägvis modell A och bara avgaserna (scope 1). <b>Övriga sektorer</b> börjar på Miljöbarometerns värden för ' + START + '. ' + esc(utanPunkt(B.territoriell.metod)) + ' (' + kalla(B, B.territoriell.kalla) + '). ' +
      'Klimatkontraktets inventering: ' + esc(utanPunkt(B.gpc_klimatkontrakt.metod)) + ' (' + kalla(B, 'CCC') + ').</p></article>';
  }

  /* ----- sidan Malmös klimatbokföring ----- */
  function bokfHtml(ctx, B, res) {
    const T = B.territoriell, sista = T.ar[T.ar.length - 1], prel = (T.preliminara_ar || []).includes(sista);
    const m = res.mal, bu = res.budget, rv = res.rader.find(x => x.ar === st.ar) || res.rader[0], r0 = res.rader[0];
    let h = '<section class="r2zr-kpis">' +
      kort('Utfall ' + sista + (prel ? ', preliminärt' : ''), nf(T.totalt[T.ar.length - 1], 0) + '<small> kt CO₂e</small>', nf(100 * (1 - T.totalt[T.ar.length - 1] * 1000 / m.bas), 0) + ' % lägre än ' + m.basar + ' (' + kalla(B, T.kalla) + ')', true) +
      kort('Prognos ' + m.ar, kt(m.prognos, 0) + '<small> kt</small>', nf(100 * m.minskning, 0) + ' % lägre än ' + m.basar) +
      kort('Malmös mål ' + m.ar + ': −' + B.mal.territoriellt.minskning_pct + ' %', kt(m.mal70, 0) + '<small> kt</small>', m.prognos <= m.mal70 ? 'Prognosen når målet' : 'Prognosen är ' + kt(m.prognos - m.mal70, 0) + ' kt över målet') +
      kort('EU-missionen: −' + B.mal.mission.minskning_pct + ' %', kt(m.mal80, 0) + '<small> kt</small>', 'Högst ' + B.mal.mission.kvarvarande_max_pct + ' % kvarvarande, som neutraliseras. ' + (m.prognos <= m.mal80 ? 'Prognosen når nivån' : kt(m.prognos - m.mal80, 0) + ' kt över')) +
      kort('Koldioxidbudget ' + bu.start + '–' + bu.slut, nf(bu.kt) + '<small> kt</small>', bu.slutAr ? 'Förbrukad ' + bu.slutAr : 'Räcker till och med ' + bu.slut + ', ' + kt(bu.kvarVidSlut, 0) + ' kt kvar') + '</section>';
    h += '<article class="card r2zr-fig" id="r2zs-terr-tid"></article>';
    // 1. Miljöbarometerns sektorer valt år
    h += '<article class="card"><h2>Utsläpp ' + rv.ar + ' i Miljöbarometerns sektorer (kt CO₂e)</h2><div class="table-wrap r2zs-full"><table class="r2zs-tab"><thead><tr><th>Sektor</th><th>Vad sektorn omfattar (Miljöbarometern)</th><th class="numeric">' + rv.ar + '</th><th>Underlag i Road2Zero-OP</th></tr></thead><tbody>' +
      TABELL.map(id => { const s = SEKTORER.find(x => x.id === id); return '<tr><td>' + esc(s.namn) + '</td><td class="r2zs-def">' + esc((T.definitioner || {})[id] || '') + '</td>' + cell(rv.sek[id]) + '<td>' + esc(GRUND[s.grund]) + '</td></tr>'; }).join('') +
      '<tr class="r2zs-sum"><td>Summa</td><td></td>' + cell(rv.terr) + '<td>' + nf(100 * (1 - rv.terr / m.bas), 0) + ' % lägre än ' + m.basar + '</td></tr></tbody></table></div></article>';
    // 2. spegling med förklaring
    const sp = res.speglingTerr, tot = k => sp.reduce((a, x) => a + (x[k] || 0), 0);
    h += '<article class="card"><h2>Spegling mot Miljöbarometern ' + START + ' och förklaring</h2><p class="small">Road2Zero-OP mot Malmö stads officiella territoriella utsläpp (' + kalla(B, T.kalla) + ', uppdaterad ' + esc(T.uppdaterad) + '). Siffrorna korrigeras inte mot varandra.</p><div class="table-wrap r2zs-full"><table class="r2zs-tab r2zs-forklaring"><thead><tr><th>Sektor</th><th class="numeric">Officiellt ' + START + '</th><th class="numeric">Officiellt ' + (START + 1) + (prel ? ' (prel.)' : '') + '</th><th class="numeric">Road2Zero-OP ' + START + '</th><th class="numeric">Skillnad</th></tr></thead><tbody>' +
      sp.map(x => '<tr class="r2zs-datarad"><td>' + esc(x.namn) + '</td>' + cell(x.officiell) + cell(x.officiellNasta) + cell(x.modell) + '<td class="numeric">' + (Math.abs(x.skillnad) < 0.5 ? '0' : pm(x.skillnad)) + '</td></tr>' +
        '<tr class="r2zs-whyrow"><td colspan="5"><b>Varför:</b> ' + forklaringTerr(ctx.S, B, res, x.id) + '</td></tr>').join('') +
      '<tr class="r2zs-sum"><td>Summa</td>' + cell(tot('officiell')) + cell(tot('officiellNasta')) + cell(tot('modell')) + '<td class="numeric">' + pm(tot('modell') - tot('officiell')) + '</td></tr><tr class="r2zs-whyrow"><td colspan="5"><b>Varför:</b> Publicerad total ' + START + ': ' + kt(res.officiellTotal, 0) + ' kt (avrundad till tre värdesiffror). Hela skillnaden är vägtrafiken; övriga sektorer är officiella startvärden.</td></tr></tbody></table></div></article>';
    // 3. brygga från OP:s klimatavtryck
    const fv = B.fjarrvarme_malmo;
    h += '<article class="card"><h2>Från Road2Zero-OP:s klimatavtryck till stadens redovisning, ' + START + '</h2><p class="small">Road2Zero-OP har tre räknesätt. Bryggan visar steg för steg vad som skiljer klimatavtrycket på sidan Resultat &amp; klimatbudget från den territoriella bokföringen och från GHG Protocol for Cities.</p><div class="table-wrap r2zs-full"><table class="r2zs-tab"><thead><tr><th>Steg</th><th class="numeric">kt CO₂e</th></tr></thead><tbody>' +
      res.brygga.map((b, i) => '<tr' + (b.summa ? ' class="r2zs-sum"' : '') + '><td>' + (b.summa && i > 0 ? '= ' : '') + esc(b.text) + '</td><td class="numeric">' + (b.summa ? kt(b.t) : pm(b.t)) + '</td></tr>').join('') + '</tbody></table></div>' +
      '<p class="small"><b>Varför energin skiljer:</b> klimatavtrycket räknar den el och fjärrvärme som används i byggnaderna med den valda elfaktorn och Boverkets medelvärde för fjärrvärme, ' + nf(1000 * ctx.P.efEl, 0) + ' och ' + nf(1000 * ctx.P.efFv, 0) + ' g CO₂e/kWh, ' + kt(r0.op.energi) + ' kt. ' +
      (fv ? 'Malmös fjärrvärme har enligt Energiföretagen ' + nf(fv.g_per_kwh, 1) + ' g CO₂e/kWh (' + fv.ar + ', med bränslets transport och produktion; ' + kalla(B, fv.kalla) + '); med den faktorn skulle OP:s fjärrvärme, ' + nf(res.el.fvKwh / 1e6, 0) + ' GWh, ge ' + kt(res.el.fvKwh * fv.g_per_kwh / 1e6) + ' kt. ' : '') +
      'Den territoriella bokföringen räknar i stället alla fossila utsläpp vid produktionen i Malmö, ' + kt(r0.sek.energi) + ' kt, även värme och el som levereras utanför Malmö och egen uppvärmning, men inte den importerade elen. ' +
      '<b>Varför mobiliteten skiljer:</b> klimatavtrycket räknar trafikens livscykel (avgaser, bränsleproduktion och fordonstillverkning), bokföringen och GPC:s scope 1 bara avgaserna.</p></article>';
    // 4. prognos och budget
    const visa = [2024, 2025, 2030, 2035, 2040, 2045, 2050].filter(y => res.rader.some(x => x.ar === y));
    if (!visa.includes(rv.ar)) visa.push(rv.ar), visa.sort((a, b) => a - b);
    h += '<article class="card"><h2>Prognos per sektor (kt CO₂e)</h2><div class="table-wrap r2zs-full"><table class="r2zs-tab"><thead><tr><th>Sektor</th>' + visa.map(y => '<th class="numeric">' + y + '</th>').join('') + '</tr></thead><tbody>' +
      TABELL.map(id => '<tr><td>' + esc(SEKTORER.find(x => x.id === id).namn) + '</td>' + visa.map(y => cell(res.rader.find(x => x.ar === y).sek[id])).join('') + '</tr>').join('') +
      '<tr class="r2zs-sum"><td>Summa</td>' + visa.map(y => cell(res.rader.find(x => x.ar === y).terr)).join('') + '</tr>' +
      '<tr><td>Minskning mot ' + m.basar + '</td>' + visa.map(y => '<td class="numeric">' + nf(100 * (1 - res.rader.find(x => x.ar === y).terr / m.bas), 0) + ' %</td>').join('') + '</tr></tbody></table></div>' +
      '<p class="small"><button type="button" class="secondary" id="r2zs-csv">Prognos per sektor och år · CSV</button></p></article>';
    h += '<article class="card r2zr-fig" id="r2zs-budget"></article>';
    h += '<article class="card"><h2>Koldioxidbudget ' + bu.start + '–' + bu.slut + '</h2><div class="table-wrap r2zs-full"><table class="r2zs-tab"><thead><tr><th>År</th><th class="numeric">Utsläpp, kt</th><th class="numeric">Ackumulerat, kt</th><th class="numeric">Kvar av ' + nf(bu.kt) + ' kt</th><th>Källa</th></tr></thead><tbody>' +
      bu.ar.map(x => '<tr><td>' + x.ar + '</td>' + cell(x.t) + cell(x.kum) + '<td class="numeric">' + kt(bu.kt * 1000 - x.kum) + '</td><td>' + (x.officiell ? 'Officiellt utfall' + ((T.preliminara_ar || []).includes(x.ar) ? ', preliminärt' : '') : 'Prognos, Road2Zero-OP') + '</td></tr>').join('') +
      '</tbody></table></div><p class="small">' + esc(utanPunkt(B.mal.koldioxidbudget.text)) + ' (' + kalla(B, B.mal.koldioxidbudget.kalla) + '). Med den senaste statistiken återstår ' + kt(bu.kvarEfterUtfall, 0) + ' kt efter ' + bu.sistaOfficiella + ' (' + kalla(B, T.kalla) + ').</p></article>';
    return h + metodBokf(ctx, B, res);
  }
  function metodBokf(ctx, B, res) {
    return '<article class="card method-text"><h2>Så räknas klimatbokföringen här</h2>' +
      '<p>Malmö stad redovisar de territoriella utsläppen, alltså utsläppen inom Malmös geografiska område på land och vatten, i Miljöbarometern i åtta sektorer. Det motsvarar scope 1 i GHG Protocol for Cities. Importerad el och konsumtionens utsläpp utanför Malmö ingår inte. ' + esc(utanPunkt(B.territoriell.metod)) + ' (' + kalla(B, B.territoriell.kalla) + ').</p>' +
      '<p><b>Mål.</b> ' + esc(utanPunkt(B.mal.territoriellt.text)) + ' (' + kalla(B, B.mal.territoriellt.kalla) + '). ' + esc(utanPunkt(B.mal.mission.text)) + ' (' + kalla(B, B.mal.mission.kalla) + '). Med ' + res.mal.basar + ' som bas, ' + kt(res.mal.bas, 0) + ' kt, blir nivåerna ' + kt(res.mal.mal70, 0) + ' kt (−70 %) och ' + kt(res.mal.mal80, 0) + ' kt (−80 %).</p>' +
      '<p><b>Prognos.</b> Energisektorn börjar på ' + START + ' års värde och följer fjärrvärmens klimatfaktor i Road2Zero-OP, med Sysavs koldioxidavskiljning om den är vald. Den följer alltså inte Malmös värmebehov, eftersom avfallet bränns oavsett. Vägtrafiken är Road2Zero-OP:s egen beräkning (Vägvis modell A, avgaser) med fordonsflottans klimatfaktor, trafikförändringen och de nya invånarnas trafik. Övriga sektorer börjar på ' + START + ' års värde och förändras med en egen takt per år från ' + FORANDRING_FRAN + '. Negativa utsläpp räknas inte, som i Malmös koldioxidbudget.</p></article>';
  }

  /* ----- sidan Jämför räknesätten ----- */
  const period = J => J.fran === J.till ? String(J.fran) : J.fran + '–' + J.till;
  const pct = (a, b) => b > 0 ? nf(100 * a / b, 0) + ' %' : '–';
  const AV = {op: 'klimatavtrycket', terr: 'det territoriella', gpc: 'GPC'};
  function jamforHtml(ctx, B, res) {
    const J = jamforelse(res, jamforUrval(ctx.R.years)), per = period(J), ack = J.lage === 'period', niva = NIVAER[J.j.niva];
    const omf = {op: 'Energi i byggnaderna, trafikens livscykel, nybyggnation och mark',
      terr: 'Utsläpp inom stadens gräns (scope 1)',
      gpc: J.j.niva === 'plus' ? 'Scope 1 och el i scope 2 i alla fem kategorier' : 'Byggnader och transport (scope 1 + 2) och avfall (scope 1)'};
    const tot = J.metoder.map(m => m.total), hogst = Math.max(...tot), lagst = Math.min(...tot);
    let h = '<section class="r2zr-kpis r2zs-kpis4">' +
      J.metoder.map(m => kort(esc(m.kort) + ' ' + per, kt(m.total, 0) + '<small> kt CO₂e</small>', nf(m.perPerson, 2) + (ack ? ' t per invånare och år i snitt. ' : ' t per invånare. ') + omf[m.id])).join('') +
      kort('Gemensamt för alla tre', kt(J.gemensamt.t, 0) + '<small> kt CO₂e</small>', esc(J.gemensamt.kallor.join(', ')) + ': ' + J.metoder.map(m => pct(J.gemensamt.t, m.total) + ' av ' + AV[m.id]).join(', ').replace(/, ([^,]*)$/, ' och $1'), true) + '</section>';
    if (ctx.P.perspektiv === 'B' && ctx.Rvald) {
      const b = ctx.M.cityByYear(ctx.Rvald).filter(r => r.year >= J.fran && r.year <= J.till).reduce((s, r) => s + r.total, 0);
      h += '<div class="notice info">Sidomenyn visar perspektiv B, hushållens bilar. Här räknas klimatavtrycket med perspektiv A, trafiken på stadens vägar, så att avgaserna avser samma trafik i alla tre räknesätten. Med perspektiv B är klimatavtrycket ' + kt(b, 0) + ' kt ' + per + '.</div>';
    }
    h += '<article class="card r2zr-paris"><h2>Samma stad, samma antaganden, tre svar</h2><p>Räknesätten bygger på samma beräkning av ' + esc(B.stad || 'staden') + ' med samma antaganden. De skiljer sig i <b>systemgränsen</b>, alltså vilka utsläpp som räknas och var. ' +
      'Klimatavtrycket följer det som stadens byggnader, trafik och utbyggnad orsakar, även utanför staden. Den territoriella bokföringen räknar det som släpps ut inom stadens gräns, oavsett vem som orsakar det. GHG Protocol for Cities lägger till den el som används i staden. ' +
      (ack ? 'Ackumulerat ' : 'År ') + per + ' skiljer det ' + kt(hogst - lagst, 0) + ' kt mellan högsta och lägsta, och bara ' + kt(J.gemensamt.t, 0) + ' kt ingår i alla tre.</p></article>';
    h += '<article class="card r2zr-fig" id="r2zs-jmf-staplar"></article>';
    // vad som ingår i vilket räknesätt
    const farg = id => DELAR.find(d => d.id === id).farg;
    const d = ack ? 0 : 1, cellJ = (k, m) => k.ingar[m] ? '<td class="numeric">' + kt(k.t, d) + (m === 'gpc' && k.gpcKod ? '<span class="r2zs-kod">' + esc(k.gpcKod) + '</span>' : '') + '</td>'
      : '<td class="r2zs-ute">' + esc(k.ute[m] || 'Ingår inte.') + '</td>';
    h += '<article class="card"><h2>Vad som ingår i vilket räknesätt, ' + (ack ? 'ackumulerat ' : '') + per + ' (kt CO₂e)</h2><p class="small">Ett värde betyder att utsläppskällan ingår; annars står var den hamnar i stället. Färgen visar delen i stapeldiagrammet.</p>' +
      '<div class="table-wrap r2zs-full"><table class="r2zs-tab r2zs-jmf"><thead><tr><th>Utsläppskälla</th>' + J.metoder.map(m => '<th class="numeric">' + esc(m.namn) + '</th>').join('') + '<th>Vad översiktsplanen kan påverka (bedömning)</th></tr></thead><tbody>' +
      J.kallor.map(k => '<tr><td><i class="r2zs-farg" style="background:' + farg(k.del) + '"></i>' + esc(k.namn) + '</td>' + METODER.map(m => cellJ(k, m.id)).join('') + '<td class="r2zs-not">' + esc(k.op) + '</td></tr>').join('') +
      '<tr class="r2zs-sum"><td>Summa</td>' + J.metoder.map(m => '<td class="numeric">' + kt(m.total, d) + '</td>').join('') + '<td></td></tr>' +
      '<tr><td>Per invånare' + (ack ? ' och år, snitt' : '') + ', t CO₂e</td>' + J.metoder.map(m => '<td class="numeric">' + nf(m.perPerson, 2) + '</td>').join('') + '<td></td></tr>' +
      '<tr><td>Ingår inte i något av räknesätten</td><td colspan="3" class="r2zs-ute">Mat, varor och tjänster, flygresor, offentlig konsumtion och investeringar utöver nybyggnationen. De ingår i det konsumtionsbaserade fotavtrycket per invånare (Konsumtionskompassen), som sidan Resultat &amp; klimatbudget använder för att fördela budgeten.</td><td class="r2zs-not">Liten direkt.</td></tr>' +
      '</tbody></table></div></article>';
    h += '<article class="card r2zr-fig" id="r2zs-jmf-brygga"></article>';
    h += ack ? '<section class="grid2 grid-even"><article class="card r2zr-fig" id="r2zs-jmf-tid"></article><article class="card r2zr-fig" id="r2zs-jmf-kum"></article></section>'
      : '<article class="card r2zr-fig" id="r2zs-jmf-tid"></article>';
    // vilket mål hör till vilket räknesätt
    const mt = B.mal.territoriellt, mm = B.mal.mission, K = B.mal.koldioxidbudget;
    const fraga = {op: 'Vilka utsläpp orsakar stadens byggnader, trafik och utbyggnad, var de än uppstår?',
      terr: 'Hur mycket släpps ut inom stadens gräns?',
      gpc: 'Hur mycket släpps ut inom stadens gräns, och hur mycket orsakar den el som används i staden?'};
    const mal = {op: 'Parisavtalets koldioxidbudget för 1,5–2,0 °C, lika per invånare (Forster m.fl. 2026) och fördelad på kategorierna enligt Konsumtionskompassen.',
      terr: esc(B.stad || 'Stadens') + 's mål: −' + mt.minskning_pct + '\u00a0% till ' + mt.ar + ' jämfört med ' + mt.basar + ' (' + kalla(B, mt.kalla) + '), och koldioxidbudgeten ' + nf(K.kt) + ' kt för ' + K.start + '–' + K.slut + ' (' + kalla(B, K.kalla) + ').',
      gpc: 'EU-missionen 100 klimatneutrala och smarta städer: minst −' + mm.minskning_pct + '\u00a0% till ' + mm.ar + ' och högst ' + mm.kvarvarande_max_pct + '\u00a0% kvarvarande utsläpp, som neutraliseras (' + kalla(B, mm.kalla) + ').'};
    h += '<article class="card"><h2>Räknesätten svarar på olika frågor och följs upp mot olika mål</h2><div class="table-wrap r2zs-full"><table class="r2zs-tab"><thead><tr><th>Räknesätt</th><th>Frågan det svarar på</th><th>Mål och budget som hör till</th><th>Mer på sidan</th></tr></thead><tbody>' +
      J.metoder.map(m => '<tr><td>' + esc(m.namn) + '</td><td class="r2zs-not">' + fraga[m.id] + '</td><td class="r2zs-not">' + mal[m.id] + '</td><td><button type="button" class="link-btn" data-go="' + m.sida + '">' + esc(m.sidnamn) + '</button></td></tr>').join('') +
      '</tbody></table></div></article>';
    return h + metodJmf(ctx, B, J, niva);
  }
  function metodJmf(ctx, B, J, niva) {
    return '<article class="card method-text"><h2>Systemgränser i en översiktsplan</h2>' +
      '<p>En översiktsplan påverkar framför allt var och hur mycket som byggs, hur marken används och hur mycket trafik staden får. Det syns främst i klimatavtrycket: nybyggnationen, marken och trafikens bränsle och fordon ingår bara där. ' +
      'Den territoriella bokföringen domineras i stället av utsläpp som planen påverkar lite: el- och värmeproduktionen, främst förbränningen av avfall, och industrin, sjöfarten och arbetsmaskinerna. GHG Protocol for Cities lägger till elen som används i staden, men inte byggmaterialen, bränslets produktion eller fordonen.</p>' +
      '<p>Ett enda räknesätt ger därför en ofullständig bild. Den territoriella siffran visar inte det mesta av det planen påverkar, och klimatavtrycket kan inte följas upp direkt mot stadens mål, som gäller de territoriella utsläppen. Sidan ställer de tre bredvid varandra med samma antaganden, och bryggan visar steg för steg vad som skiljer dem.</p>' +
      '<h3>Så räknas jämförelsen</h3><p>Alla tre räknas år för år med antagandena under <button type="button" class="link-btn" data-go="parameters">Antaganden &amp; scenario</button> och samma trafik: Vägvis modell A, trafiken på stadens vägar, även när sidomenyn visar perspektiv B. ' +
      'Klimatavtrycket omfattar alla fyra kategorier och både befintlig stad och exploateringen, oavsett urvalet på sidan Resultat &amp; klimatbudget. GHG Protocol for Cities visas som ' + niva + (J.j.niva === 'plus' ? ', med IPPU och AFOLU som i klimatkontraktet' : ', utan IPPU och AFOLU') + '. ' +
      'Ackumulerat är summan av årens utsläpp. Per invånare är medelvärdet av årens utsläpp per invånare, med stadens invånare och de nya invånarna år för år, som på sidan Resultat &amp; klimatbudget. ' +
      'Alla år är modellvärden, även ' + START + ' och ' + (START + 1) + '; skillnaden mot Miljöbarometerns utfall förklaras på sidan Stadens klimatbokföring. Kolumnen om översiktsplanen är en kvalitativ bedömning (modellval).</p>' +
      '<p class="small"><button type="button" class="secondary" id="r2zs-jmf-csv">De tre räknesätten och utsläppskällorna per år · CSV</button></p></article>';
  }

  function html(ctx, B, vy) {
    if (!st) st = urvalStart();
    if (!ctx.R.years.includes(st.ar)) st.ar = 2030;
    const res = berakna(ctx.M, ctx.S, ctx.R, B, st);
    return panel(ctx, B, vy) + (vy === 'gpc' ? gpcHtml(ctx, B, res) : vy === 'jamfor' ? jamforHtml(ctx, B, res) : bokfHtml(ctx, B, res));
  }

  function rita(ctx, B, vy) {
    if (typeof Plotly === 'undefined') return;
    const res = berakna(ctx.M, ctx.S, ctx.R, B, st), ar = res.rader.map(x => x.ar);
    const plot = (id, data, lay) => { const el = document.getElementById(id); if (!el) return; el.style.height = (lay.height || 440) + 'px'; Plotly.newPlot(el, data, lay, CONF); };
    if (vy === 'gpc') {
      const sp = [];
      for (const g of GPC) {
        sp.push({type: 'bar', name: g.kort + ', scope 1', x: ar, y: res.rader.map(x => x.gpc[g.id].s1 / 1000), marker: {color: g.farg, line: {color: SURF, width: 1}}, hovertemplate: g.kort + ', scope 1: %{y:,.1f} kt<extra></extra>'});
        if (res.rader.some(x => x.gpc[g.id].s2 > 0)) sp.push({type: 'bar', name: g.kort + ', scope 2', x: ar, y: res.rader.map(x => x.gpc[g.id].s2 / 1000), marker: {color: rgba(g.farg, 0.45), line: {color: SURF, width: 1}}, hovertemplate: g.kort + ', scope 2: %{y:,.1f} kt<extra></extra>'});
      }
      const l = layout('Utsläpp i klimatkontraktets kategorier, scope 1 och 2', ar[0] + '–' + ar[ar.length - 1] + ' · prognos med Road2Zero-OP:s antaganden · klimatkontraktet ' + res.cccAr + ': ' + kt(res.cccTotal, 0) + ' kt', 480);
      l.barmode = 'stack'; l.bargap = 0.25;
      l.shapes = [{type: 'line', xref: 'paper', x0: 0, x1: 1, y0: res.cccTotal / 1000, y1: res.cccTotal / 1000, line: {color: INK2, width: 1.5, dash: 'dot'}}];
      l.annotations = [{xref: 'paper', x: 1, y: res.cccTotal / 1000, text: 'Klimatkontraktet ' + res.cccAr + ': ' + kt(res.cccTotal, 0) + ' kt', showarrow: false, xanchor: 'right', yanchor: 'bottom', font: {color: INK2, size: 12}}];
      plot('r2zs-gpc-tid', sp, l);
      const s = res.speglingGpc.slice().reverse(), y = s.map(x => x.id + ' ' + GPC.find(g => g.id === x.id).kort);
      const l2 = layout('Spegling per kategori: Road2Zero-OP ' + START + ', klimatkontraktet ' + res.cccAr + ' och Miljöbarometern ' + res.cccAr, 'Scope 1 + 2 (Miljöbarometern: scope 1), kt CO₂e', 420, '');
      l2.barmode = 'group'; l2.hovermode = 'closest'; l2.xaxis = {...l2.xaxis, showgrid: true, gridcolor: GRID, title: {text: 'kt CO2e'}, tickformat: ',.0f'}; l2.yaxis = {...l2.yaxis, gridcolor: 'rgba(0,0,0,0)', title: {text: ''}, tickformat: ''}; l2.margin = {l: 10, r: 70, t: 72, b: 10};
      plot('r2zs-gpc-spegel', [
        {type: 'bar', orientation: 'h', name: 'Road2Zero-OP ' + START, y, x: s.map(x => (x.modellS1 + x.modellS2) / 1000), marker: {color: '#1f5a6e'}, text: s.map(x => kt(x.modellS1 + x.modellS2, 0)), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}: %{x:,.1f} kt<extra>Road2Zero-OP</extra>'},
        {type: 'bar', orientation: 'h', name: 'Klimatkontraktet ' + res.cccAr, y, x: s.map(x => (x.cccS1 + x.cccS2) / 1000), marker: {color: '#bcd3db', line: {color: '#7d939d', width: 1}}, text: s.map(x => kt(x.cccS1 + x.cccS2, 0)), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}: %{x:,.1f} kt<extra>Klimatkontraktet</extra>'},
        {type: 'bar', orientation: 'h', name: 'Miljöbarometern ' + res.cccAr + ' (scope 1)', y, x: s.map(x => x.mbS1 / 1000), marker: {color: '#a3c27a'}, text: s.map(x => kt(x.mbS1, 0)), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}: %{x:,.1f} kt<extra>Miljöbarometern</extra>'}], l2);
    } else if (vy === 'jamfor') {
      const J = jamforelse(res, jamforUrval(ctx.R.years)), per = period(J), ack = J.lage === 'period', namn = J.metoder.map(m => m.kort);
      // 1. staplar: tre räknesätt, uppdelade på delarna
      const maxT = Math.max(...J.metoder.map(m => m.total));
      const data = DELAR.filter(d => J.metoder.some(m => m.delar[d.id] > 0)).map(d => ({type: 'bar', orientation: 'h', name: d.namn, y: namn, x: J.metoder.map(m => m.delar[d.id] / 1000),
        marker: {color: d.farg, line: {color: SURF, width: 2}}, text: J.metoder.map(m => m.delar[d.id] >= 0.08 * maxT ? kt(m.delar[d.id], 0) : ''),
        textposition: 'inside', insidetextanchor: 'middle', textfont: {color: textfarg(d.farg), size: 12}, hovertemplate: '%{y} · ' + d.namn + ': %{x:,.0f} kt<extra></extra>'}));
      const l = layout('Samma stad, tre systemgränser', (ack ? 'Ackumulerat ' : '') + per + ', kt CO₂e · samma färg är samma utsläpp i flera räknesätt', 400, '');
      l.barmode = 'stack'; l.bargap = 0.3; l.hovermode = 'closest'; l.margin = {l: 10, r: 20, t: 72, b: 10};
      l.yaxis = {gridcolor: 'rgba(0,0,0,0)', autorange: 'reversed', automargin: true, ticks: '', tickfont: {size: 13, color: INK}};
      l.xaxis = {...l.xaxis, showgrid: true, gridcolor: GRID, title: {text: ''}, tickformat: ',.0f', range: [0, maxT / 1000 * 1.13]};   // enheten står i undertiteln
      l.annotations = J.metoder.map(m => ({x: m.total / 1000, y: m.kort, text: '<b>' + kt(m.total, 0) + ' kt</b>', showarrow: false, xanchor: 'left', xshift: 6, font: {color: INK, size: 13}}));
      l.legend = {...l.legend, y: -0.2};
      plot('r2zs-jmf-staplar', data, l);
      // 2. brygga (vattenfall)
      const b = J.brygga, etikett = s => s.summa ? '<b>' + esc(J.metoder.find(m => m.id === s.metod).kort) + '</b>' : radbryt(s.text, 46);
      const lb = layout('Från klimatavtrycket till ' + esc(J.metoder[2].kort) + ', ' + (ack ? 'ackumulerat ' : '') + per, 'Steg för steg: vad som tas bort och läggs till när systemgränsen ändras, kt CO₂e', 90 + 44 * b.length, '');
      lb.hovermode = 'closest'; lb.showlegend = false; lb.margin = {l: 10, r: 70, t: 72, b: 10};
      lb.yaxis = {gridcolor: 'rgba(0,0,0,0)', autorange: 'reversed', automargin: true, ticks: '', tickfont: {size: 12, color: INK}};
      lb.xaxis = {...lb.xaxis, showgrid: true, gridcolor: GRID, title: {text: 'kt CO2e'}, tickformat: ',.0f', rangemode: 'tozero'};
      plot('r2zs-jmf-brygga', [{type: 'waterfall', orientation: 'h', y: b.map(etikett), x: b.map(s => s.summa ? 0 : s.t / 1000).map((v, i) => i === 0 ? b[0].t / 1000 : v),
        measure: b.map((s, i) => i === 0 ? 'absolute' : s.summa ? 'total' : 'relative'), text: b.map(s => s.summa ? kt(s.t, 0) : (s.t > 0 ? '+' : '−') + kt(Math.abs(s.t), 0)),
        textposition: 'outside', cliponaxis: false, increasing: {marker: {color: '#5c6f78'}}, decreasing: {marker: {color: '#bcd3db'}}, totals: {marker: {color: '#1f5a6e'}},
        connector: {line: {color: LINJE, width: 1}}, hovertemplate: '%{text} kt<extra></extra>'}], lb);
      // 3. per år och 4. ackumulerat
      const ar = res.rader.map(x => x.ar), linje = m => ({type: 'scatter', mode: 'lines', name: m.kort, line: {color: m.farg, width: 2.5, dash: m.dash}, hovertemplate: m.kort + ': %{y:,.0f} kt<extra></extra>'});
      const lt = layout('Utsläpp per år', ar[0] + '–' + ar[ar.length - 1] + ', kt CO₂e per år · ' + (ack ? 'skuggat: ' : 'markerat: ') + per, 420);
      lt.xaxis = {...lt.xaxis, dtick: 5, range: [ar[0] - 0.5, ar[ar.length - 1] + 0.5]};
      lt.shapes = [ack ? {type: 'rect', x0: J.fran - 0.5, x1: J.till + 0.5, yref: 'paper', y0: 0, y1: 1, fillcolor: rgba(GRID, 0.55), line: {width: 0}, layer: 'below'}
        : {type: 'line', x0: J.fran, x1: J.fran, yref: 'paper', y0: 0, y1: 1, line: {color: INK2, width: 1.5, dash: 'dot'}}];
      plot('r2zs-jmf-tid', J.metoder.map(m => ({...linje(m), x: ar, y: m.perAr.map(v => v / 1000)})), lt);
      if (ack) {
        const kum = m => { let s = 0; return J.ar.map(a => (s += m.perAr[ar.indexOf(a)]) / 1000); };
        const lk = layout('Ackumulerade utsläpp ' + per, 'kt CO₂e från ' + J.fran, 420);
        lk.margin = {l: 10, r: 80, t: 72, b: 10};
        lk.annotations = J.metoder.map(m => ({x: J.till, y: m.total / 1000, text: kt(m.total, 0), showarrow: false, xanchor: 'left', xshift: 6, font: {color: m.farg, size: 12}}));
        plot('r2zs-jmf-kum', J.metoder.map(m => ({...linje(m), x: J.ar, y: kum(m)})), lk);
      }
    } else {
      const T = B.territoriell, m = res.mal;
      const data = SEKTORER.map(s => ({type: 'scatter', mode: 'lines', stackgroup: 'p', name: s.namn, x: ar, y: res.rader.map(x => x.sek[s.id] / 1000), line: {width: 0.5, color: s.farg}, fillcolor: rgba(s.farg, 0.85), hovertemplate: s.namn + ': %{y:,.1f} kt<extra></extra>'}));
      data.push({type: 'scatter', mode: 'lines+markers', name: 'Officiellt utfall (Miljöbarometern)', x: T.ar, y: T.totalt, line: {color: INK, width: 2}, marker: {size: 8, color: INK, line: {color: SURF, width: 2}}, hovertemplate: 'Officiellt %{x}: %{y:,.0f} kt<extra></extra>'});
      const l = layout('Territoriella utsläpp i Miljöbarometerns sektorer: utfall ' + T.ar[0] + '–' + T.ar[T.ar.length - 1] + ' och prognos ' + ar[0] + '–' + ar[ar.length - 1], 'Ytor: Road2Zero-OP:s prognos per sektor · linje: Malmö stads utfall · mål ' + m.ar + ': −70 % och −80 % mot ' + m.basar, 500);
      l.xaxis = {...l.xaxis, range: [T.ar[0] - 1, ar[ar.length - 1] + 1], dtick: 5};
      l.shapes = [[m.mal70, VARNING, 'dash'], [m.mal80, BUDGET, 'dot']].map(([v, c, d]) => ({type: 'line', x0: T.ar[0], x1: ar[ar.length - 1], y0: v / 1000, y1: v / 1000, line: {color: c, width: 1.5, dash: d}}))
        .concat([{type: 'line', x0: m.ar, x1: m.ar, yref: 'paper', y0: 0, y1: 1, line: {color: LINJE, width: 1}}]);
      l.annotations = [[m.mal70, VARNING, 'Malmös mål ' + m.ar + ', −70 %: ' + kt(m.mal70, 0) + ' kt'], [m.mal80, BUDGET, 'EU-missionen, −80 %: ' + kt(m.mal80, 0) + ' kt']].map(([v, c, txt]) => ({x: T.ar[0], y: v / 1000, text: txt, showarrow: false, xanchor: 'left', yanchor: 'bottom', font: {color: c, size: 12}}));
      plot('r2zs-terr-tid', data, l);
      const bu = res.budget;
      const l2 = layout('Koldioxidbudget ' + bu.start + '–' + bu.slut + ': ackumulerade utsläpp', 'Officiellt utfall till och med ' + bu.sistaOfficiella + ', därefter Road2Zero-OP:s prognos · budget ' + nf(bu.kt) + ' kt (Malmö stad)', 400);
      l2.xaxis = {...l2.xaxis, dtick: 1};
      const off = bu.ar.filter(x => x.officiell), prog = bu.ar.filter((x, i) => !x.officiell || (bu.ar[i + 1] && !bu.ar[i + 1].officiell));
      l2.shapes = [{type: 'line', xref: 'paper', x0: 0, x1: 1, y0: bu.kt, y1: bu.kt, line: {color: BUDGET, width: 2}}];
      l2.annotations = [{xref: 'paper', x: 0, y: bu.kt, text: 'Budget ' + nf(bu.kt) + ' kt', showarrow: false, xanchor: 'left', yanchor: 'bottom', font: {color: BUDGET, size: 12}}];
      if (bu.slutAr) { l2.shapes.push({type: 'line', x0: bu.slutAr, x1: bu.slutAr, yref: 'paper', y0: 0, y1: 1, line: {color: VARNING, width: 1.5, dash: 'dot'}}); l2.annotations.push({x: bu.slutAr, yref: 'paper', y: 1, text: 'Förbrukad ' + bu.slutAr, showarrow: false, xanchor: 'left', yanchor: 'top', font: {color: VARNING, size: 12}}); }
      plot('r2zs-budget', [
        {type: 'scatter', mode: 'lines+markers', name: 'Officiellt utfall, ackumulerat', x: off.map(x => x.ar), y: off.map(x => x.kum / 1000), line: {color: INK, width: 2}, marker: {size: 8, color: INK, line: {color: SURF, width: 2}}, hovertemplate: '%{x}: %{y:,.0f} kt<extra>Utfall</extra>'},
        {type: 'scatter', mode: 'lines+markers', name: 'Prognos, ackumulerat', x: prog.map(x => x.ar), y: prog.map(x => x.kum / 1000), line: {color: '#5a86b8', width: 2, dash: 'dash'}, marker: {size: 8, color: '#5a86b8', line: {color: SURF, width: 2}}, hovertemplate: '%{x}: %{y:,.0f} kt<extra>Prognos</extra>'}], l2);
    }
  }

  function csv(ctx, B) {
    const res = berakna(ctx.M, ctx.S, ctx.R, B, st);
    const koder = DETALJ.map(d => d.kod);
    const huvud = ['ar', ...TABELL.map(id => 'miljobarometern_' + id + '_t'), 'territoriellt_t', ...GPC.flatMap(g => ['gpc_' + g.id + '_s1_t', 'gpc_' + g.id + '_s2_t', 'gpc_' + g.id + '_s3_t']),
      ...koder.flatMap(k => ['s1', 's2', 's3'].map(s => 'gpc_' + k.replace(/[^0-9A-Za-zÅÄÖåäö.]+/g, '_') + '_' + s)), 'gpc_basic_t', 'gpc_basic_plus_t', 'el_kwh'];
    const tal1 = v => typeof v === 'string' ? v : v == null ? '' : String(Math.round(v * 10) / 10).replace('.', ',');
    const rader = res.rader.map(x => [x.ar, ...TABELL.map(id => tal1(x.sek[id])), tal1(x.terr), ...GPC.flatMap(g => [tal1(x.gpc[g.id].s1), tal1(x.gpc[g.id].s2), tal1(x.gpc[g.id].s3)]),
      ...x.detalj.flatMap(d => [tal1(d.s1), tal1(d.s2), tal1(d.s3)]), tal1(x.basic), tal1(x.basicPlus), tal1(x.elKwh)].join(';'));
    return '﻿' + [huvud.join(';'), ...rader].join('\n') + '\n';
  }

  /* De tre räknesätten och utsläppskällorna per år, i t CO2e. */
  function csvJamfor(ctx, B) {
    const res = berakna(ctx.M, ctx.S, ctx.R, B, st), tal1 = v => String(Math.round(v * 10) / 10).replace('.', ',');
    const m = niva => jamforelse(res, {lage: 'period', p0: res.rader[0].ar, p1: res.rader[res.rader.length - 1].ar, niva}).metoder;
    const plus = m('plus'), basic = m('basic');
    const huvud = ['ar', 'invanare', 'klimatavtryck_t', 'territoriellt_t', 'gpc_basic_t', 'gpc_basic_plus_t', ...KALLOR.map(k => k.id + '_t')];
    const rader = res.rader.map((x, i) => [x.ar, Math.round(x.inv), tal1(plus[0].perAr[i]), tal1(plus[1].perAr[i]), tal1(basic[2].perAr[i]), tal1(plus[2].perAr[i]), ...KALLOR.map(k => tal1(k.v(x)))].join(';'));
    return '\ufeff' + [huvud.join(';'), ...rader].join('\n') + '\n';
  }
  const ladda = (text, fil) => { const b = new Blob([text], {type: 'text/csv'}), a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = fil; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };

  function bind(ctx, B, vy, rerender) {
    if (!st) st = urvalStart();
    const om = () => { spara(); rerender(); };
    document.querySelectorAll('[data-r2zs-takt]').forEach(el => el.onchange = () => { const v = Number(String(el.value).replace(',', '.')); st.r[el.dataset.r2zsTakt] = Number.isFinite(v) ? Math.max(-50, Math.min(50, v)) : 0; om(); });
    document.querySelectorAll('[data-r2zs]').forEach(el => el.onchange = () => { if (el.dataset.r2zs === 'ar') st.ar = Number(el.value); om(); });
    document.querySelectorAll('[data-r2zs-lage]').forEach(el => el.onclick = () => { st.j.lage = el.dataset.r2zsLage; om(); });
    document.querySelectorAll('[data-r2zs-j]').forEach(el => el.onchange = () => { const k = el.dataset.r2zsJ; st.j[k] = k === 'niva' ? el.value : Number(el.value); om(); });
    const c = document.getElementById('r2zs-csv');
    if (c) c.onclick = () => ladda(csv(ctx, B), 'road2zero_op_stadens_redovisning.csv');
    const cj = document.getElementById('r2zs-jmf-csv');
    if (cj) cj.onclick = () => ladda(csvJamfor(ctx, B), 'road2zero_op_tre_raknesatt.csv');
    rita(ctx, B, vy);
    const omMat = () => document.querySelectorAll('.r2zr-fig.js-plotly-plot').forEach(el => { try { Plotly.Plots.resize(el); } catch (e) { /* diagrammet är borta */ } });
    if (typeof Plotly !== 'undefined') { requestAnimationFrame(omMat); setTimeout(omMat, 250); }
  }

  return {START, FORANDRING_FRAN, SEKTORER, GPC, DETALJ, ELKAT, TAKTER, TABELL, METODER, DELAR, KALLOR, NIVAER, standard, berakna, jamforStandard, jamforelse,
    forklaringTerr, forklaringGpc, html, bind, csv, csvJamfor};
});
