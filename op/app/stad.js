/* Road2Zero-OP – stadens klimatredovisning: GHG Protocol for Cities och Malmös klimatbokföring.
   Två sidor som visar stadens utsläpp som staden själv redovisar dem, med prognos 2024–2050:
     gpc        GHG Protocol for Cities (WRI, C40 och ICLEI, 2021) per sektor och scope, speglad mot klimatkontraktets
                inventering med EU-missionen (GPC BASIC, data för 2022).
     bokforing  territoriella utsläpp per sektor som i Miljöbarometern, med målen −70 % (Malmö) och −80 % (EU-missionen)
                och koldioxidbudgeten 2021–2030.
   Modulen ändrar inte Road2Zero-OP:s beräkning. Den läser resultatet från MalmoOP.compute (alltid modell A för trafiken)
   och lägger till de sektorer som OP inte räknar med Malmö stads officiella startvärden. Resultaten speglas mot de officiella
   siffrorna, de kalibreras inte. Beräkningsdelen är ren JavaScript och testas i Node (op/tests/test_stad.js). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.R2ZStad = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const START = 2024;            // startår: OP:s basår och senaste helår i den officiella statistiken
  const FORANDRING_FRAN = 2027;  // som för emissionsfaktorerna i OP: startvärdet gäller till och med 2026
  /* Territoriella sektorer som i Miljöbarometern. grund: 'egen' = Road2Zero-OP:s egen beräkning, 'fjarrvarme' = officiellt
     startvärde som följer fjärrvärmens klimatfaktor i OP, 'officiell' = officiellt startvärde med egen årlig förändring.
     Ordningen är diagrammens staplingsordning (färgerna ur paletten, valda så att grannar skiljer sig). */
  const SEKTORER = [
    {id: 'energi', namn: 'Energi', gpc: 'I', grund: 'fjarrvarme', farg: '#4fa8a0'},
    {id: 'industri', namn: 'Industri', gpc: 'I', grund: 'officiell', farg: '#1f5a6e'},
    {id: 'vagtrafik', namn: 'Vägtrafik', gpc: 'II', grund: 'egen', farg: '#5a86b8'},
    {id: 'avfall', namn: 'Avfall och avlopp', gpc: 'III', grund: 'officiell', farg: '#7aa65a'},
    {id: 'sjofart', namn: 'Sjöfart, järnväg och flyg', gpc: 'II', grund: 'officiell', farg: '#1d4e74'},
    {id: 'jordbruk', namn: 'Jordbruk', gpc: 'V', grund: 'officiell', farg: '#a3c27a'},
    {id: 'arbetsmaskiner', namn: 'Arbetsmaskiner', gpc: 'II', grund: 'officiell', farg: '#7d939d'},
    {id: 'produkt', namn: 'Produktanvändning', gpc: 'IV', grund: 'officiell', farg: '#bcd3db'}
  ];
  const TABELL = ['energi', 'industri', 'jordbruk', 'vagtrafik', 'sjofart', 'arbetsmaskiner', 'produkt', 'avfall']; // Miljöbarometerns ordning
  const GPC = [
    {id: 'I', namn: 'Stationär energi', kort: 'Stationär energi', farg: '#1f5a6e', ccc: 'stationar'},
    {id: 'II', namn: 'Transport', kort: 'Transport', farg: '#5a86b8', ccc: 'transport'},
    {id: 'III', namn: 'Avfall', kort: 'Avfall', farg: '#7aa65a', ccc: 'avfall'},
    {id: 'IV', namn: 'Industriprocesser och produktanvändning (IPPU)', kort: 'IPPU', farg: '#1d4e74', ccc: 'ippu'},
    {id: 'V', namn: 'Jordbruk, skogsbruk och annan markanvändning (AFOLU)', kort: 'AFOLU', farg: '#a3c27a', ccc: 'afolu'}
  ];
  /* Sektorer med egen årlig förändring (% per år från 2027). Standard 0 %: oförändrad nivå från 2024 (modellval). */
  const TAKTER = [
    ['industri', 'Industri'], ['sjofart', 'Sjöfart, järnväg och flyg'], ['arbetsmaskiner', 'Arbetsmaskiner'],
    ['produkt', 'Produktanvändning'], ['avfall', 'Avfall och avlopp'], ['jordbruk', 'Jordbruk'],
    ['ovrigEl', 'Övrig elanvändning (scope 2)']];

  const summa = a => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i]; return s; };
  function standard() { return {r: Object.fromEntries(TAKTER.map(([k]) => [k, 0])), ar: 2030, v: 1}; }

  /* ---------- beräkning ---------- */
  /* M = MalmoOP, S = M.prepare(D), R = M.compute(S, P) med perspektiv A, B = klimatbokforing.json, u = urval (takter, år).
     Returnerar t CO2e per år för båda redovisningarna. */
  function berakna(M, S, R, B, u = standard()) {
    if (R.P.perspektiv !== 'A') throw new Error('Stadens redovisning räknar trafiken territoriellt och kräver modell A.');
    const T = B.territoriell, iStart = T.ar.indexOf(START);
    if (iStart < 0) throw new Error('Officiella värden för ' + START + ' saknas.');
    const start = {}; for (const [id, v] of Object.entries(T.sektorer)) start[id] = v[iStart] * 1000;
    const P = R.P, mob = S.D.mob.A, n = S.n;
    const ttw = new Float64Array(n), s3 = new Float64Array(n);       // avgasernas och uppströmsledets andel av Vägvis modell A
    S.ids.forEach((id, i) => { const a = mob[id]; if (a && a.total > 0) { ttw[i] = a.ttw / a.total; s3[i] = (a.wtt + a.fordon) / a.total; } });
    const elByggKwh = P.efEl > 0 ? summa(R.energyBase.tEl) * 1000 / P.efEl : 0;   // byggnadsel ur energideklarationerna
    const elK = B.el_scb.kategorier, elStatKwh = (B.el_scb.totalt - (elK.transporter || 0)) * 1000, elJvgKwh = (elK.transporter || 0) * 1000;
    const ovrigElKwh = Math.max(0, elStatKwh - elByggKwh);           // hushålls-, verksamhets- och industriel
    const r = id => Number(u.r && u.r[id]) || 0;
    const kf = (id, y) => Math.pow(1 + r(id) / 100, Math.max(0, y - (FORANDRING_FRAN - 1)));
    const rader = R.years.map((y, yi) => {
      const f = R.faktorer[yi];
      let vag = 0, mobS3 = 0;
      for (let i = 0; i < n; i++) { const m = R.comp.mobilitet[yi][i] + R.comp.nymob[yi][i]; vag += m * ttw[i]; mobS3 += m * s3[i]; }
      const sek = {energi: start.energi * f.iFv, vagtrafik: vag};
      for (const id of ['industri', 'sjofart', 'arbetsmaskiner', 'produkt', 'avfall', 'jordbruk']) sek[id] = start[id] * kf(id, y);
      const terr = SEKTORER.reduce((s, x) => s + sek[x.id], 0);
      // scope 2: el i byggnader och verksamheter (byggnadsel med effektivisering + nya byggnaders el + övrig el) och järnvägens el
      const eff = 1 - P.effektivisering2050 / 100 * M.ramp(y), efMix = P.elandelNy * f.el + (1 - P.elandelNy) * f.fv;
      const nyElKwh = efMix > 0 ? summa(R.comp.nydrift[yi]) * 1000 / efMix * P.elandelNy : 0;
      const elKwh = elByggKwh * eff + nyElKwh + ovrigElKwh * kf('ovrigEl', y);
      const s2 = {stat: elKwh * f.el / 1000, jvg: elJvgKwh * f.el / 1000};
      const mark = summa(R.comp.mark[yi]), bygg = summa(R.comp.bygg[yi]);
      const gpc = {
        I: {s1: sek.energi + sek.industri, s2: s2.stat, s3: 0},
        II: {s1: sek.vagtrafik + sek.sjofart + sek.arbetsmaskiner, s2: s2.jvg, s3: mobS3},
        III: {s1: sek.avfall, s2: 0, s3: 0},
        IV: {s1: sek.produkt, s2: 0, s3: 0},
        V: {s1: sek.jordbruk + mark, s2: 0, s3: 0}};
      const basic = gpc.I.s1 + gpc.I.s2 + gpc.II.s1 + gpc.II.s2 + gpc.III.s1;
      return {ar: y, sek, terr, s2, mark, bygg, mobS3, elKwh, gpc, basic, basicPlus: basic + gpc.IV.s1 + gpc.V.s1, scope3: mobS3 + bygg};
    });
    const rad = y => rader.find(x => x.ar === y);
    // mål: −70 % (Malmö) och −80 % (EU-missionen) mot 1990
    const i90 = T.ar.indexOf(B.mal.territoriellt.basar), bas = T.totalt[i90] * 1000;
    const ar2030 = rad(B.mal.territoriellt.ar);
    const mal = {bas, basar: B.mal.territoriellt.basar, ar: B.mal.territoriellt.ar,
      mal70: bas * (1 - B.mal.territoriellt.minskning_pct / 100), mal80: bas * (1 - B.mal.mission.minskning_pct / 100),
      prognos: ar2030 ? ar2030.terr : null, minskning: ar2030 ? 1 - ar2030.terr / bas : null};
    mal.kvarvarandeMax = bas * B.mal.mission.kvarvarande_max_pct / 100;
    // koldioxidbudget: officiellt utfall till och med senaste år, därefter prognos
    const K = B.mal.koldioxidbudget, sistaOff = Math.max(...T.ar.filter(y => y <= K.slut));
    const budgetAr = []; let kum = 0, slut = null;
    for (let y = K.start; y <= K.slut; y++) {
      const io = T.ar.indexOf(y), off = io >= 0 && y <= sistaOff, v = off ? T.totalt[io] * 1000 : (rad(y) ? rad(y).terr : null);
      if (v == null) continue;
      kum += v; if (slut == null && kum > K.kt * 1000) slut = y;
      budgetAr.push({ar: y, t: v, kum, officiell: off});
    }
    const utfall = budgetAr.filter(x => x.officiell).reduce((s, x) => s + x.t, 0);
    const budget = {kt: K.kt, start: K.start, slut: K.slut, ar: budgetAr, kum, slutAr: slut, sistaOfficiella: sistaOff,
      utfall, kvarEfterUtfall: K.kt * 1000 - utfall, kvarVidSlut: K.kt * 1000 - kum};
    // spegling mot den officiella statistiken (startåret) och mot klimatkontraktet
    const r0 = rad(START), i25 = T.ar.indexOf(START + 1);
    const speglingTerr = TABELL.map(id => {
      const s = SEKTORER.find(x => x.id === id);
      return {id, namn: s.namn, grund: s.grund, officiell: start[id], officiellNasta: i25 >= 0 ? T.sektorer[id][i25] * 1000 : null,
        modell: r0.sek[id], skillnad: r0.sek[id] - start[id]};
    });
    const ccc = B.gpc_klimatkontrakt, speglingGpc = GPC.map(g => {
      const c = ccc.rader.find(x => x.id === g.ccc) || {s1: 0, s2: 0};
      return {id: g.id, namn: g.namn, modellS1: r0.gpc[g.id].s1, modellS2: r0.gpc[g.id].s2, cccS1: c.s1 || 0, cccS2: c.s2 || 0,
        skillnad: r0.gpc[g.id].s1 + r0.gpc[g.id].s2 - (c.s1 || 0) - (c.s2 || 0)};
    });
    return {rader, start, mal, budget, speglingTerr, speglingGpc, el: {byggKwh: elByggKwh, ovrigKwh: ovrigElKwh, jvgKwh: elJvgKwh, statKwh: elStatKwh},
      officiellTotal: T.totalt[iStart] * 1000, cccTotal: ccc.totalt, cccAr: ccc.dataar};
  }

  /* ---------- gränssnitt (bara i webbläsaren) ---------- */
  const INK = '#15211d', INK2 = '#56635e', GRID = '#e3e9e6', SURF = '#fbfcfb', LINJE = '#c9d4cf', VARNING = '#a4442c', BUDGET = '#2f6b3f';
  const nf = (x, d = 0) => x == null || !Number.isFinite(x) ? '–' : new Intl.NumberFormat('sv-SE', {maximumFractionDigits: d, minimumFractionDigits: d}).format(x);
  const kt = (t, d = 1) => nf(t / 1000, d);
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const rgba = (h, a) => 'rgba(' + parseInt(h.slice(1, 3), 16) + ',' + parseInt(h.slice(3, 5), 16) + ',' + parseInt(h.slice(5, 7), 16) + ',' + a + ')';
  const CONF = {displaylogo: false, responsive: true, toImageButtonOptions: {format: 'png', scale: 2}};
  const STORE = 'r2z-op-stad';
  const GRUND = {egen: 'Egen beräkning: Vägvis modell A, avgaser', fjarrvarme: 'Officiellt startvärde × fjärrvärmens klimatfaktor', officiell: 'Officiellt startvärde × egen förändring'};

  let st = null;
  function urvalStart() {
    let s = null; try { s = JSON.parse(localStorage.getItem(STORE) || 'null'); } catch (e) { s = null; }
    const u = standard();
    if (s && typeof s === 'object') {
      if (s.r && typeof s.r === 'object') for (const [k] of TAKTER) { const v = Number(s.r[k]); if (Number.isFinite(v)) u.r[k] = Math.max(-50, Math.min(50, v)); }
      if (Number.isFinite(Number(s.ar))) u.ar = Number(s.ar);
    }
    return u;
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
  const kort = (l, v, f, huvud) => '<div class="card' + (huvud ? ' kpi-main' : '') + '"><div class="kpi-label">' + l + '</div><div class="kpi-value">' + v + '</div><div class="kpi-foot">' + f + '</div></div>';
  const cccS = (B, id) => { const c = B.gpc_klimatkontrakt.rader.find(x => x.id === id) || {}; return (c.s1 || 0) + (c.s2 || 0); };
  const kalibrering = ctx => { const m = ctx.S.D.mob.A_metadata || {}, ref = m.reference && m.reference.reference; return (ref && ref.source ? ref.source : 'Miljöbarometerns vägtrafik ' + START).replace(/\.\s*$/, ''); };
  const utanPunkt = t => String(t || '').replace(/\.\s*$/, '');
  const kalla = (B, id) => B.kallor[id] ? esc(B.kallor[id].kort) : esc(id);

  function panel(ctx, B, vy) {
    const P = ctx.P, ar = ctx.R.years;
    const takter = TAKTER.filter(([k]) => vy === 'gpc' || k !== 'ovrigEl').map(([k, l]) =>
      '<label class="field">' + esc(l) + ', % per år<input class="input" type="number" step="0.1" min="-50" max="50" data-r2zs-takt="' + k + '" value="' + st.r[k] + '"></label>').join('');
    const fl = [P.flotta2030, P.flotta2040, P.flotta2050].map(v => nf(v, 2)).join(' / ');
    return '<article class="card r2zr-urval"><div class="r2zr-rad r2zr-val" style="margin-top:0">' +
      '<label class="field">Visa år i tabellerna<select data-r2zs="ar">' + ar.map(y => '<option value="' + y + '"' + (y === st.ar ? ' selected' : '') + '>' + y + '</option>').join('') + '</select></label>' + takter + '</div>' +
      '<p class="small">Sektorerna som Road2Zero-OP inte räknar själv börjar på Malmö stads officiella värden för ' + START + ' (' + kalla(B, B.territoriell.kalla) + ') och förändras med den årliga takten från ' + FORANDRING_FRAN + '. Standard är 0 %, oförändrad nivå. ' +
      'Energisektorn följer fjärrvärmens klimatfaktor (' + (P.beccs === 'ja' ? 'med Sysavs koldioxidavskiljning från ' + P.beccsAr + ', −' + nf(P.beccsMinskning) + ' %' : 'utan Sysavs koldioxidavskiljning') + '), vägtrafiken fordonsflottans klimatfaktor ' + fl + ' för 2030 / 2040 / 2050 och trafikförändringen ' + nf(P.trafikForandring2050) + ' % till 2050, och elen elens klimatfaktor. ' +
      'De ändras under <button type="button" class="link-btn" data-go="parameters">Antaganden &amp; scenario</button>. Trafiken räknas alltid territoriellt med Vägvis modell A, oavsett perspektivet i sidomenyn.</p></article>';
  }

  /* ----- sidan GHG Protocol for Cities ----- */
  function gpcHtml(ctx, B, res) {
    const r0 = res.rader[0], rv = res.rader.find(x => x.ar === st.ar) || r0;
    const h = '<section class="r2zr-kpis">' +
      kort('BASIC+ ' + r0.ar, kt(r0.basicPlus, 0) + '<small> kt CO₂e</small>', 'Scope 1 + 2 i alla sektorer, som klimatkontraktet räknar', true) +
      kort('BASIC ' + r0.ar, kt(r0.basic, 0) + '<small> kt</small>', 'Stationär energi och transport (scope 1 + 2) och avfall (scope 1)') +
      kort('Klimatkontraktet ' + res.cccAr, kt(res.cccTotal, 0) + '<small> kt</small>', 'GPC BASIC beräknad i CIRIS (' + kalla(B, 'CCC') + ')') +
      kort('BASIC+ ' + rv.ar, kt(rv.basicPlus, 0) + '<small> kt</small>', nf(100 * (rv.basicPlus / r0.basicPlus - 1), 0) + ' % mot ' + r0.ar) +
      kort('Scope 3 ' + rv.ar, kt(rv.scope3, 0) + '<small> kt</small>', 'Utanför summorna: trafikens bränsleproduktion och fordon, nybyggnation') + '</section>';
    const cell = v => '<td class="numeric">' + (v ? kt(v) : '–') + '</td>';
    const del = (namn, s1, s2, s3, sub) => '<tr' + (sub ? ' class="r2zs-sub"' : '') + '><td>' + (sub ? '&nbsp;&nbsp;' : '') + namn + '</td>' + cell(s1) + cell(s2) + cell(s3) + cell((s1 || 0) + (s2 || 0)) + '</tr>';
    const g = rv.gpc, s = rv.sek;
    let t = '<article class="card"><h2>Utsläpp per sektor och scope ' + rv.ar + ' (kt CO₂e)</h2><div class="table-wrap"><table class="r2zs-tab"><thead><tr><th>Sektor enligt GPC</th><th class="numeric">Scope 1</th><th class="numeric">Scope 2</th><th class="numeric">Scope 3</th><th class="numeric">Scope 1 + 2</th></tr></thead><tbody>' +
      del('<b>I Stationär energi</b>', g.I.s1, g.I.s2, 0) + del('Energiindustri: el, fjärrvärme och egen uppvärmning', s.energi, 0, 0, 1) + del('Industri, energi och processer', s.industri, 0, 0, 1) + del('El i byggnader och verksamheter', 0, rv.s2.stat, 0, 1) +
      del('<b>II Transport</b>', g.II.s1, g.II.s2, g.II.s3) + del('Vägtrafik (Road2Zero-OP)', s.vagtrafik, 0, rv.mobS3, 1) + del('Sjöfart, järnväg och flyg', s.sjofart, rv.s2.jvg, 0, 1) + del('Arbetsmaskiner', s.arbetsmaskiner, 0, 0, 1) +
      del('<b>III Avfall</b>', g.III.s1, 0, 0) + del('<b>IV Industriprocesser och produktanvändning</b>', g.IV.s1, 0, 0) +
      del('<b>V Jordbruk, skogsbruk och annan markanvändning</b>', g.V.s1, 0, 0) + del('Jordbruk', s.jordbruk, 0, 0, 1) + del('Förändrad markanvändning i utbyggnaden (Road2Zero-OP)', rv.mark, 0, 0, 1) +
      del('Övrigt scope 3: nybyggnation A1–A5 (Road2Zero-OP)', 0, 0, rv.bygg) +
      '<tr class="r2zs-sum"><td>BASIC</td><td></td><td></td><td></td>' + cell(rv.basic) + '</tr><tr class="r2zs-sum"><td>BASIC+ (= klimatkontraktets avgränsning)</td><td></td><td></td><td></td>' + cell(rv.basicPlus) + '</tr>' +
      '</tbody></table></div><p class="small">Scope 3 ingår inte i BASIC eller BASIC+ här: trafikens bränsleproduktion och fordonstillverkning (Vägvis) och nybyggnationens material (A1–A5) redovisas bara som information. El i scope 2: ' +
      nf(rv.elKwh / 1e6, 0) + ' GWh × ' + nf(1000 * ctx.R.faktorer[ctx.R.years.indexOf(rv.ar)].el, 1) + ' g CO₂e/kWh.</p></article>';
    const sp = res.speglingGpc;
    t += '<article class="card"><h2>Spegling mot klimatkontraktet</h2><p class="small">Road2Zero-OP ' + START + ' mot Malmö stads inventering i klimatkontraktet med EU-missionen (data för ' + res.cccAr + '). Siffrorna korrigeras inte mot varandra.</p><div class="table-wrap"><table class="r2zs-tab"><thead><tr><th>Sektor</th><th class="numeric">OP scope 1</th><th class="numeric">OP scope 2</th><th class="numeric">Kontraktet scope 1</th><th class="numeric">Kontraktet scope 2</th><th class="numeric">Skillnad scope 1 + 2</th></tr></thead><tbody>' +
      sp.map(x => '<tr><td>' + esc(x.id + ' ' + x.namn) + '</td><td class="numeric">' + kt(x.modellS1) + '</td><td class="numeric">' + kt(x.modellS2) + '</td><td class="numeric">' + kt(x.cccS1) + '</td><td class="numeric">' + kt(x.cccS2) + '</td><td class="numeric">' + (x.skillnad > 0 ? '+' : '') + kt(x.skillnad) + '</td></tr>').join('') +
      '<tr class="r2zs-sum"><td>Summa</td><td class="numeric">' + kt(sp.reduce((a, x) => a + x.modellS1, 0)) + '</td><td class="numeric">' + kt(sp.reduce((a, x) => a + x.modellS2, 0)) + '</td><td class="numeric">' + kt(sp.reduce((a, x) => a + x.cccS1, 0)) + '</td><td class="numeric">' + kt(sp.reduce((a, x) => a + x.cccS2, 0)) + '</td><td class="numeric">' + kt(r0.basicPlus - res.cccTotal) + '</td></tr></tbody></table></div>' +
      '<p class="small">Klimatkontraktets transport, ' + kt(cccS(B, 'transport'), 0) + ' kt, är ' + nf(cccS(B, 'transport') / (r0.gpc.II.s1 + r0.gpc.II.s2), 1) + ' gånger Road2Zero-OP:s, som bygger på Miljöbarometerns vägtrafik, sjöfart, järnväg, flyg och arbetsmaskiner, och byggnaderna, ' + kt(cccS(B, 'stationar'), 0) + ' kt, är ' + nf(cccS(B, 'stationar') / (r0.gpc.I.s1 + r0.gpc.I.s2), 1) + ' gånger. Kontraktet anger att siffrorna steg när staden bytte beräkningsmetod (CIRIS) och att stadens egna beräkningar visar en minskning. Road2Zero-OP följer Miljöbarometerns sektorer för scope 1.</p></article>';
    return h + '<article class="card r2zr-fig" id="r2zs-gpc-tid"></article><article class="card r2zr-fig" id="r2zs-gpc-spegel"></article>' + t + metodGpc(ctx, B, res);
  }
  function metodGpc(ctx, B, res) {
    return '<article class="card method-text"><h2>Så räknas GHG Protocol for Cities här</h2>' +
      '<p>GHG Protocol for Cities (GPC) delar stadens utsläpp i fem sektorer och tre scope (' + kalla(B, 'GPC2021') + '). Scope 1 är utsläpp inom stadens gräns, scope 2 kommer från el, värme och kyla från nätet som används i staden, och scope 3 är övriga utsläpp utanför gränsen som staden orsakar. Nivån BASIC omfattar scope 1 och 2 för stationär energi och transport och scope 1 för avfall; BASIC+ lägger till industriprocesser och produktanvändning (IPPU) och jordbruk och mark (AFOLU).</p>' +
      '<p><b>Fjärrvärmen räknas som i klimatkontraktet:</b> utsläppen där värmen produceras, i scope 1 under energiindustrin, främst förbränningen av plast i avfallet hos Sysav. I strikt GPC redovisas produktion som levereras till nätet i scope 1 men räknas inte i BASIC-summan; klimatkontraktet räknar in den, och det gör Road2Zero-OP också. Fjärrvärmen räknas därför inte en gång till i scope 2.</p>' +
      '<p><b>El i scope 2</b> är elanvändningen 2024 utom transporter enligt SCB, ' + nf(res.el.statKwh / 1e6, 0) + ' GWh (' + kalla(B, 'SCB2026EN') + '): byggnadsel ur energideklarationerna, ' + nf(res.el.byggKwh / 1e6, 0) + ' GWh, som följer effektiviseringen i OP, el i nya byggnader och övrig el, ' + nf(res.el.ovrigKwh / 1e6, 0) + ' GWh, med egen årlig förändring. Elfaktorn är Boverkets ' + nf(1000 * ctx.P.efEl, 0) + ' g CO₂e/kWh med samma utveckling som i övriga Road2Zero. Järnvägens el (' + nf(res.el.jvgKwh / 1e6, 0) + ' GWh) är transportens scope 2.</p>' +
      '<p><b>Vägtrafiken</b> är Road2Zero-OP:s egen beräkning: Vägvis modell A, trafiken på vägarna i Malmö, och bara avgaserna (scope 1). Vägvis modell A är kalibrerad mot ' + esc(kalibrering(ctx)) + '. Bränsleproduktion och fordonstillverkning hamnar i scope 3. <b>Övriga sektorer</b> börjar på Miljöbarometerns värden för 2024. Hela sektorn Industri redovisas under stationär energi, eftersom energi och processer inte går att dela upp i statistiken. Förändrad markanvändning i utbyggnaden är Road2Zero-OP:s egen beräkning och ingår i AFOLU; klimatkontraktets AFOLU omfattar bara jordbruket.</p></article>';
  }

  /* ----- sidan Malmös klimatbokföring ----- */
  function bokfHtml(ctx, B, res) {
    const T = B.territoriell, sista = T.ar[T.ar.length - 1], prel = (T.preliminara_ar || []).includes(sista);
    const m = res.mal, bu = res.budget, rv = res.rader.find(x => x.ar === st.ar) || res.rader[0];
    const h = '<section class="r2zr-kpis">' +
      kort('Utfall ' + sista + (prel ? ', preliminärt' : ''), nf(T.totalt[T.ar.length - 1], 0) + '<small> kt CO₂e</small>', nf(100 * (1 - T.totalt[T.ar.length - 1] * 1000 / m.bas), 0) + ' % lägre än ' + m.basar + ' (' + kalla(B, T.kalla) + ')', true) +
      kort('Prognos ' + m.ar, kt(m.prognos, 0) + '<small> kt</small>', nf(100 * m.minskning, 0) + ' % lägre än ' + m.basar) +
      kort('Malmös mål ' + m.ar + ': −' + B.mal.territoriellt.minskning_pct + ' %', kt(m.mal70, 0) + '<small> kt</small>', m.prognos <= m.mal70 ? 'Prognosen når målet' : 'Prognosen är ' + kt(m.prognos - m.mal70, 0) + ' kt över målet') +
      kort('EU-missionen: −' + B.mal.mission.minskning_pct + ' %', kt(m.mal80, 0) + '<small> kt</small>', 'Högst ' + B.mal.mission.kvarvarande_max_pct + ' % kvarvarande, som neutraliseras. ' + (m.prognos <= m.mal80 ? 'Prognosen når nivån' : kt(m.prognos - m.mal80, 0) + ' kt över')) +
      kort('Koldioxidbudget ' + bu.start + '–' + bu.slut, nf(bu.kt) + '<small> kt</small>', bu.slutAr ? 'Förbrukad ' + bu.slutAr : 'Räcker till och med ' + bu.slut + ', ' + kt(bu.kvarVidSlut, 0) + ' kt kvar') + '</section>';
    const sp = res.speglingTerr, tot = k => sp.reduce((a, x) => a + (x[k] || 0), 0);
    let t = '<article class="card"><h2>Spegling mot Miljöbarometern ' + START + '</h2><p class="small">Road2Zero-OP mot Malmö stads officiella territoriella utsläpp (' + kalla(B, T.kalla) + ', uppdaterad ' + esc(T.uppdaterad) + '). Siffrorna korrigeras inte mot varandra.</p><div class="table-wrap"><table class="r2zs-tab"><thead><tr><th>Sektor</th><th class="numeric">Officiellt ' + START + '</th><th class="numeric">Officiellt ' + (START + 1) + (prel ? ' (prel.)' : '') + '</th><th class="numeric">Road2Zero-OP ' + START + '</th><th class="numeric">Skillnad</th><th>Underlag i Road2Zero-OP</th></tr></thead><tbody>' +
      sp.map(x => '<tr><td>' + esc(x.namn) + '</td><td class="numeric">' + kt(x.officiell) + '</td><td class="numeric">' + kt(x.officiellNasta) + '</td><td class="numeric">' + kt(x.modell) + '</td><td class="numeric">' + (Math.abs(x.skillnad) < 0.5 ? '0' : (x.skillnad > 0 ? '+' : '') + kt(x.skillnad)) + '</td><td>' + esc(GRUND[x.grund]) + '</td></tr>').join('') +
      '<tr class="r2zs-sum"><td>Summa</td><td class="numeric">' + kt(tot('officiell')) + '</td><td class="numeric">' + kt(tot('officiellNasta')) + '</td><td class="numeric">' + kt(tot('modell')) + '</td><td class="numeric">' + kt(tot('modell') - tot('officiell')) + '</td><td>Publicerad total ' + START + ': ' + kt(res.officiellTotal, 0) + ' kt</td></tr></tbody></table></div>' +
      '<p class="small">Vägtrafiken är Road2Zero-OP:s egen beräkning och skiljer sig därför från den officiella. Vägvis modell A är kalibrerad mot ' + esc(kalibrering(ctx)) + '. Övriga sektorer är officiella startvärden och därför lika ' + START + '.</p></article>';
    const visa = [2024, 2025, 2030, 2035, 2040, 2045, 2050].filter(y => res.rader.some(x => x.ar === y));
    if (!visa.includes(rv.ar)) visa.push(rv.ar), visa.sort((a, b) => a - b);
    t += '<article class="card"><h2>Prognos per sektor (kt CO₂e)</h2><div class="table-wrap"><table class="r2zs-tab"><thead><tr><th>Sektor</th>' + visa.map(y => '<th class="numeric">' + y + '</th>').join('') + '</tr></thead><tbody>' +
      TABELL.map(id => '<tr><td>' + esc(SEKTORER.find(x => x.id === id).namn) + '</td>' + visa.map(y => '<td class="numeric">' + kt(res.rader.find(x => x.ar === y).sek[id]) + '</td>').join('') + '</tr>').join('') +
      '<tr class="r2zs-sum"><td>Summa</td>' + visa.map(y => '<td class="numeric">' + kt(res.rader.find(x => x.ar === y).terr) + '</td>').join('') + '</tr>' +
      '<tr><td>Minskning mot ' + m.basar + '</td>' + visa.map(y => '<td class="numeric">' + nf(100 * (1 - res.rader.find(x => x.ar === y).terr / m.bas), 0) + ' %</td>').join('') + '</tr></tbody></table></div>' +
      '<p class="small"><button type="button" class="secondary" id="r2zs-csv">Prognos per sektor och år · CSV</button></p></article>';
    t += '<article class="card"><h2>Koldioxidbudget ' + bu.start + '–' + bu.slut + '</h2><div class="table-wrap"><table class="r2zs-tab"><thead><tr><th>År</th><th class="numeric">Utsläpp, kt</th><th class="numeric">Ackumulerat, kt</th><th class="numeric">Kvar av ' + nf(bu.kt) + ' kt</th><th>Källa</th></tr></thead><tbody>' +
      bu.ar.map(x => '<tr><td>' + x.ar + '</td><td class="numeric">' + kt(x.t) + '</td><td class="numeric">' + kt(x.kum) + '</td><td class="numeric">' + kt(bu.kt * 1000 - x.kum) + '</td><td>' + (x.officiell ? 'Officiellt utfall' + ((T.preliminara_ar || []).includes(x.ar) ? ', preliminärt' : '') : 'Prognos, Road2Zero-OP') + '</td></tr>').join('') +
      '</tbody></table></div><p class="small">' + esc(utanPunkt(B.mal.koldioxidbudget.text)) + ' (' + kalla(B, B.mal.koldioxidbudget.kalla) + '). Med den senaste statistiken återstår ' + kt(bu.kvarEfterUtfall, 0) + ' kt efter ' + bu.sistaOfficiella + ' (' + kalla(B, B.territoriell.kalla) + ').</p></article>';
    return h + '<article class="card r2zr-fig" id="r2zs-terr-tid"></article><article class="card r2zr-fig" id="r2zs-budget"></article>' + t + metodBokf(ctx, B, res);
  }
  function metodBokf(ctx, B, res) {
    return '<article class="card method-text"><h2>Så räknas klimatbokföringen här</h2>' +
      '<p>Malmö stad redovisar de territoriella utsläppen, alltså utsläppen inom Malmös geografiska område på land och vatten, i Miljöbarometern. Det motsvarar scope 1 i GHG Protocol for Cities. Importerad el och konsumtionens utsläpp utanför Malmö ingår inte (' + kalla(B, B.territoriell.kalla) + ').</p>' +
      '<p><b>Mål.</b> ' + esc(utanPunkt(B.mal.territoriellt.text)) + ' (' + kalla(B, B.mal.territoriellt.kalla) + '). ' + esc(utanPunkt(B.mal.mission.text)) + ' (' + kalla(B, B.mal.mission.kalla) + '). Med ' + res.mal.basar + ' som bas, ' + kt(res.mal.bas, 0) + ' kt, blir nivåerna ' + kt(res.mal.mal70, 0) + ' kt (−70 %) och ' + kt(res.mal.mal80, 0) + ' kt (−80 %).</p>' +
      '<p><b>Prognos.</b> Energisektorn börjar på 2024 års värde och följer fjärrvärmens klimatfaktor i Road2Zero-OP, med Sysavs koldioxidavskiljning om den är vald. Den följer alltså inte Malmös värmebehov, eftersom avfallet bränns oavsett. Vägtrafiken är Road2Zero-OP:s egen beräkning (Vägvis modell A, avgaser) med fordonsflottans klimatfaktor, trafikförändringen och de nya invånarnas trafik. Övriga sektorer börjar på 2024 års värde och förändras med en egen takt per år från 2027. Negativa utsläpp räknas inte, som i Malmös koldioxidbudget.</p></article>';
  }

  function html(ctx, B, vy) {
    if (!st) st = urvalStart();
    if (!ctx.R.years.includes(st.ar)) st.ar = 2030;
    const res = berakna(ctx.M, ctx.S, ctx.R, B, st);
    return panel(ctx, B, vy) + (vy === 'gpc' ? gpcHtml(ctx, B, res) : bokfHtml(ctx, B, res));
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
      const l = layout('Utsläpp enligt GHG Protocol for Cities, scope 1 och 2', ar[0] + '–' + ar[ar.length - 1] + ' · prognos med Road2Zero-OP:s antaganden · klimatkontraktet ' + res.cccAr + ': ' + kt(res.cccTotal, 0) + ' kt', 480);
      l.barmode = 'stack'; l.bargap = 0.25;
      l.shapes = [{type: 'line', xref: 'paper', x0: 0, x1: 1, y0: res.cccTotal / 1000, y1: res.cccTotal / 1000, line: {color: INK2, width: 1.5, dash: 'dot'}}];
      l.annotations = [{xref: 'paper', x: 1, y: res.cccTotal / 1000, text: 'Klimatkontraktet ' + res.cccAr + ': ' + kt(res.cccTotal, 0) + ' kt', showarrow: false, xanchor: 'right', yanchor: 'bottom', font: {color: INK2, size: 12}}];
      plot('r2zs-gpc-tid', sp, l);
      const y = res.speglingGpc.map(x => x.id + ' ' + GPC.find(g => g.id === x.id).kort).reverse();
      const s = res.speglingGpc.slice().reverse();
      const l2 = layout('Spegling per sektor: Road2Zero-OP ' + START + ' och klimatkontraktet ' + res.cccAr, 'Scope 1 + 2, kt CO₂e', 380, '');
      l2.barmode = 'group'; l2.hovermode = 'closest'; l2.xaxis = {...l2.xaxis, showgrid: true, gridcolor: GRID, title: {text: 'kt CO2e'}, tickformat: ',.0f'}; l2.yaxis = {...l2.yaxis, gridcolor: 'rgba(0,0,0,0)', title: {text: ''}, tickformat: ''}; l2.margin = {l: 10, r: 70, t: 72, b: 10};
      plot('r2zs-gpc-spegel', [
        {type: 'bar', orientation: 'h', name: 'Road2Zero-OP ' + START, y, x: s.map(x => (x.modellS1 + x.modellS2) / 1000), marker: {color: '#1f5a6e'}, text: s.map(x => kt(x.modellS1 + x.modellS2, 0)), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}: %{x:,.1f} kt<extra>Road2Zero-OP</extra>'},
        {type: 'bar', orientation: 'h', name: 'Klimatkontraktet ' + res.cccAr, y, x: s.map(x => (x.cccS1 + x.cccS2) / 1000), marker: {color: '#bcd3db', line: {color: '#7d939d', width: 1}}, text: s.map(x => kt(x.cccS1 + x.cccS2, 0)), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}: %{x:,.1f} kt<extra>Klimatkontraktet</extra>'}], l2);
    } else {
      const T = B.territoriell, m = res.mal;
      const data = SEKTORER.map(s => ({type: 'scatter', mode: 'lines', stackgroup: 'p', name: s.namn, x: ar, y: res.rader.map(x => x.sek[s.id] / 1000), line: {width: 0.5, color: s.farg}, fillcolor: rgba(s.farg, 0.85), hovertemplate: s.namn + ': %{y:,.1f} kt<extra></extra>'}));
      data.push({type: 'scatter', mode: 'lines+markers', name: 'Officiellt utfall (Miljöbarometern)', x: T.ar, y: T.totalt, line: {color: INK, width: 2}, marker: {size: 8, color: INK, line: {color: SURF, width: 2}}, hovertemplate: 'Officiellt %{x}: %{y:,.0f} kt<extra></extra>'});
      const l = layout('Territoriella utsläpp: utfall ' + T.ar[0] + '–' + T.ar[T.ar.length - 1] + ' och prognos ' + ar[0] + '–' + ar[ar.length - 1], 'Ytor: Road2Zero-OP:s prognos per sektor · linje: Malmö stads utfall · mål ' + m.ar + ': −70 % och −80 % mot ' + m.basar, 500);
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
    const huvud = ['ar', ...TABELL.map(id => 'terr_' + id + '_t'), 'territoriellt_t', ...GPC.flatMap(g => ['gpc_' + g.id + '_s1_t', 'gpc_' + g.id + '_s2_t']), 'gpc_basic_t', 'gpc_basic_plus_t', 'scope3_t', 'el_kwh'];
    const tal = v => String(Math.round(v * 10) / 10).replace('.', ',');
    const rader = res.rader.map(x => [x.ar, ...TABELL.map(id => tal(x.sek[id])), tal(x.terr), ...GPC.flatMap(g => [tal(x.gpc[g.id].s1), tal(x.gpc[g.id].s2)]), tal(x.basic), tal(x.basicPlus), tal(x.scope3), tal(x.elKwh)].join(';'));
    return '﻿' + [huvud.join(';'), ...rader].join('\n') + '\n';
  }

  function bind(ctx, B, vy, rerender) {
    if (!st) st = urvalStart();
    const om = () => { spara(); rerender(); };
    document.querySelectorAll('[data-r2zs-takt]').forEach(el => el.onchange = () => { const v = Number(String(el.value).replace(',', '.')); st.r[el.dataset.r2zsTakt] = Number.isFinite(v) ? Math.max(-50, Math.min(50, v)) : 0; om(); });
    document.querySelectorAll('[data-r2zs]').forEach(el => el.onchange = () => { if (el.dataset.r2zs === 'ar') st.ar = Number(el.value); om(); });
    const c = document.getElementById('r2zs-csv');
    if (c) c.onclick = () => { const b = new Blob([csv(ctx, B)], {type: 'text/csv'}), a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'road2zero_op_stadens_redovisning.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
    rita(ctx, B, vy);
    const omMat = () => document.querySelectorAll('.r2zr-fig.js-plotly-plot').forEach(el => { try { Plotly.Plots.resize(el); } catch (e) { /* diagrammet är borta */ } });
    if (typeof Plotly !== 'undefined') { requestAnimationFrame(omMat); setTimeout(omMat, 250); }
  }

  return {START, FORANDRING_FRAN, SEKTORER, GPC, TAKTER, TABELL, standard, berakna, html, bind, csv};
});
