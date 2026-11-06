/* Tester för stadens klimatredovisning i Road2Zero-OP (GHG Protocol for Cities och Malmös klimatbokföring).
   Kör: node op/tests/test_stad.js */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('assert');
const OP = path.resolve(__dirname, '..'), ROOT = path.join(OP, 'projekt', 'malmo_op');
const M = require(path.join(OP, 'app/model.js')), Z = require(path.join(OP, 'app/stad.js'));
const read = p => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const D = {deso: read('data/kalla/deso_2025_malmo.geojson'), energi: read('data/energi_deklarationer.json'), mob: read('data/mobilitet_vagvis.json'), expl: read('data/exploatering_op2023.json')};
const B = read('data/klimatbokforing.json');
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, (msg || '') + ' ' + a + ' ≠ ' + b);
let passed = 0; const test = (n, f) => { f(); passed++; console.log('✓ ' + n); };
const S = M.prepare(D), R = M.compute(S, {}), res = Z.berakna(M, S, R, B);
const rad = (r, y) => r.rader.find(x => x.ar === y);
// elbilarnas laddel i Vägvis wtt räknas om från Vägvis elfaktor till modellens (Boverkets 37 g 2024)
const elOm = x => x.el * (R.faktorer[0].el * 1000 / D.mob.elFaktor.A - 1);
const T = B.territoriell, i24 = T.ar.indexOf(2024);

test('underlaget: sektorerna summerar till den publicerade totalen och varje källa finns', () => {
  for (let i = 0; i < T.ar.length; i++) {
    const s = Object.values(T.sektorer).reduce((a, v) => a + v[i], 0);
    near(s, T.totalt[i], Math.max(6, 0.005 * T.totalt[i]), 'år ' + T.ar[i] + ' (totalen är avrundad)');
  }
  for (const id of Object.keys(T.sektorer)) assert.ok(Z.SEKTORER.some(s => s.id === id), id);
  const anv = JSON.stringify(B).match(/"kalla": ?"[^"]+"/g).map(x => x.split('"')[3]);
  for (const k of anv) assert.ok(B.kallor[k], 'källa ' + k);
  const c = B.gpc_klimatkontrakt; near(c.rader.reduce((a, r) => a + r.s1 + r.s2, 0), c.totalt, 1, 'klimatkontraktets total');
  near(Object.values(B.el_scb.kategorier).reduce((a, v) => a + v, 0), B.el_scb.totalt, 2, 'SCB:s el');
});

test('startåret: officiella sektorer lika Miljöbarometern, vägtrafiken = Vägvis modell A, avgaser', () => {
  const r = rad(res, 2024);
  for (const id of ['energi', 'industri', 'jordbruk', 'sjofart', 'arbetsmaskiner', 'produkt', 'avfall']) near(r.sek[id], T.sektorer[id][i24] * 1000, 1e-6, id);
  near(r.sek.vagtrafik, D.mob.stad.A.ttw, 1e-3, 'vägtrafik 2024');
  near(r.terr, Object.values(r.sek).reduce((a, v) => a + v, 0), 1e-6);
  near(r.terr / 1000, 848.3, 0.05, 'territoriellt 2024');
});

test('standard 0 %: officiella sektorer konstanta; energin följer fjärrvärmens index', () => {
  for (const y of [2030, 2050]) {
    const r = rad(res, y), f = R.faktorer[R.years.indexOf(y)];
    for (const id of ['industri', 'jordbruk', 'sjofart', 'arbetsmaskiner', 'produkt', 'avfall']) near(r.sek[id], T.sektorer[id][i24] * 1000, 1e-6, id + ' ' + y);
    near(r.sek.energi, T.sektorer.energi[i24] * 1000 * f.iFv, 1e-6, 'energi ' + y);
  }
  near(rad(res, 2026).sek.energi, T.sektorer.energi[i24] * 1000, 1e-6, 'startvärdet gäller till och med 2026');
});

test('egen takt: −5 % per år från 2027 för industrin', () => {
  const u = Z.standard(); u.r.industri = -5;
  const r = Z.berakna(M, S, R, B, u);
  near(rad(r, 2026).sek.industri, 96200, 1e-6); near(rad(r, 2030).sek.industri, 96200 * Math.pow(0.95, 4), 1e-6);
  near(rad(r, 2030).sek.avfall, rad(res, 2030).sek.avfall, 1e-9, 'andra sektorer opåverkade');
});

test('Sysavs koldioxidavskiljning sänker energisektorn från 2030', () => {
  const Rb = M.compute(S, {beccs: 'ja'}), rb = Z.berakna(M, S, Rb, B);
  near(rad(rb, 2030).sek.energi, rad(res, 2030).sek.energi * (1 - M.DEFAULTS.beccsMinskning / 100), 1e-6);
  near(rad(rb, 2029).sek.energi, rad(res, 2029).sek.energi, 1e-9);
});

test('GPC: scope 2 = el × elfaktor, sektorernas summor och BASIC', () => {
  const r = rad(res, 2024), f = R.faktorer[0];
  near(r.s2.stat, (B.el_scb.totalt - B.el_scb.kategorier.transporter) * 1000 * f.el / 1000, 1e-6, 'el 2024 = SCB:s el utom transporter');
  near(r.s2.jvg, B.el_scb.kategorier.transporter * 1000 * f.el / 1000, 1e-6);
  near(r.gpc.I.s1, r.sek.energi + r.sek.industri, 1e-9);
  near(r.gpc.II.s1, r.sek.vagtrafik + r.sek.sjofart + r.sek.arbetsmaskiner, 1e-9);
  near(r.basic, r.gpc.I.s1 + r.gpc.I.s2 + r.gpc.II.s1 + r.gpc.II.s2 + r.gpc.III.s1, 1e-9);
  near(r.basicPlus, r.terr + r.s2.stat + r.s2.jvg + r.mark, 1e-6, 'BASIC+ = territoriellt + scope 2 + mark');
  near(r.gpc.II.s3, D.mob.stad.A.wtt + elOm(D.mob.stad.A) + D.mob.stad.A.fordon, 1, 'scope 3 för trafiken 2024, laddelen med 37 g');
  const re = Z.berakna(M, S, M.compute(S, {effektivisering2050: 20}), B);
  near(rad(res, 2050).elKwh - rad(re, 2050).elKwh, 0.2 * res.el.byggKwh, 1, 'effektiviseringen gäller byggnadselen');
});

test('perspektiv B i sidomenyn påverkar inte redovisningen; modell A krävs', () => {
  assert.throws(() => Z.berakna(M, S, M.compute(S, {perspektiv: 'B'}), B));
  const rA = Z.berakna(M, S, M.compute(S, {...M.compute(S, {perspektiv: 'B'}).P, perspektiv: 'A'}), B);
  near(rad(rA, 2040).terr, rad(res, 2040).terr, 1e-6);
});

test('mål och koldioxidbudget', () => {
  near(res.mal.mal70, 1660e3 * 0.3, 1e-6); near(res.mal.mal80, 1660e3 * 0.2, 1e-6);
  near(res.mal.prognos, rad(res, 2030).terr, 1e-9);
  const b = res.budget, utfall = [2021, 2022, 2023, 2024, 2025].reduce((a, y) => a + T.totalt[T.ar.indexOf(y)] * 1000, 0);
  near(b.utfall, utfall, 1e-6, 'utfall 2021–2025');
  near(b.kum, utfall + [2026, 2027, 2028, 2029, 2030].reduce((a, y) => a + rad(res, y).terr, 0), 1e-6);
  assert.strictEqual(b.slutAr, 2028, 'förbrukad 2028 med oförändrade utsläpp, som i Malmö stads uppföljning');
  assert.strictEqual(b.ar.length, 10);
});

test('officiella kategorier: Miljöbarometerns sektorer i dess ordning, klimatkontraktets fem kategorier', () => {
  assert.deepStrictEqual(Z.TABELL, ['energi', 'industri', 'jordbruk', 'vagtrafik', 'sjofart', 'arbetsmaskiner', 'produkt', 'avfall']);
  assert.deepStrictEqual(Object.keys(T.sektorer).sort(), Z.TABELL.slice().sort());
  assert.deepStrictEqual(Z.GPC.map(g => g.ccc), B.gpc_klimatkontrakt.rader.map(r => r.id));
});

test('GPC:s undersektorer summerar till klimatkontraktets kategorier; elen fördelas efter SCB', () => {
  for (const y of [2024, 2040]) {
    const r = rad(res, y);
    for (const g of Z.GPC) {
      const d = r.detalj.filter(x => x.grupp === g.id), s = k => d.reduce((a, x) => a + (typeof x[k] === 'number' ? x[k] : 0), 0);
      near(s('s1'), r.gpc[g.id].s1, 1e-6, g.id + ' scope 1 ' + y); near(s('s2'), r.gpc[g.id].s2, 1e-6, g.id + ' scope 2 ' + y); near(s('s3'), r.gpc[g.id].s3, 1e-6, g.id + ' scope 3 ' + y);
    }
    near(r.detalj.find(x => x.grupp === null).s3, r.bygg, 1e-9, 'övrigt scope 3 = nybyggnation');
  }
  const k = B.el_scb.kategorier, stat = B.el_scb.totalt - k.transporter;
  near(res.elAndel.bostader, (k.smahus + k.flerbostadshus + k.fritidshus) / stat, 1e-6);
  near(Object.values(res.elAndel).reduce((a, v) => a + v, 0), 1, 1e-6, 'andelarna täcker all el utom transporter');
});

test('bryggan: klimatavtrycket → territoriellt → GPC BASIC+', () => {
  const b = res.brygga, rows = M.cityByYear(R), r = rad(res, 2024);
  near(b[0].t, rows[0].total, 1e-6, 'start = sidan Resultat & klimatbudget, perspektiv A');
  const steg = (i, j) => b.slice(i, j).reduce((a, x) => a + x.t, 0);
  near(b[0].t + steg(1, 7), b[7].t, 1e-6, 'till territoriellt'); near(b[7].t, r.terr, 1e-6);
  near(b[7].t + steg(8, 10), b[10].t, 1e-6, 'till BASIC+'); near(b[10].t, r.basicPlus, 1e-6);
  near(-(b[1].t + b[2].t), D.mob.stad.A.wtt + elOm(D.mob.stad.A) + D.mob.stad.A.fordon, 1, 'Vägvis uppströms och fordon, laddelen med 37 g');
});

test('förklaringarna bygger på underlaget', () => {
  const t = Z.forklaringGpc(B, res, 'II');
  assert.ok(t.includes('Nationella emissionsdatabasen') && t.includes('ENVIMAN'), 'transportens källor');
  assert.ok(Z.forklaringGpc(B, res, 'I').includes('55 g/kWh'), 'kontraktets implicita elfaktor');
  assert.ok(Z.forklaringTerr(S, B, res, 'vagtrafik').includes('3,9 %'), 'vägtrafikens skillnad');
});

test('Road2Zero-OP:s egen beräkning: oförändrad utom elbilarnas laddel, som räknas med modellens elfaktor (0.14.0)', () => {
  const rows = M.cityByYear(R);
  near(rows[0].total, 560111.05, 0.05, 'OP 2024'); near(rows.find(r => r.year === 2050).total, 566623.49, 0.05, 'OP 2050');
});

test('elvalet ändrar inte avgaserna: territoriellt och scope 1 är desamma för alla tre val', () => {
  for (const p of [{elVal: 'iea'}, {elVal: 'egen', efElEgen: 0.09}]) {
    const rx = Z.berakna(M, S, M.compute(S, p), B);
    for (const y of [2024, 2035, 2050]) near(rad(rx, y).terr, rad(res, y).terr, 1e-6, JSON.stringify(p) + ' ' + y);
  }
});

/* ---------- jämförelse av räknesätten (0.15.0) ---------- */
test('jämförelse: delarna summerar till varje räknesätt varje år, energin = el + fjärrvärme', () => {
  const op = Z.KALLOR.filter(k => k.med.op), terr = Z.KALLOR.filter(k => k.med.terr);
  const gpc = niva => Z.KALLOR.filter(k => k.med.gpc === 'basic' || (niva === 'plus' && k.med.gpc === 'plus'));
  const s = (ks, x) => ks.reduce((a, k) => a + k.v(x), 0);
  for (const x of res.rader) {
    near(s(op, x), x.op.total, 1e-6, 'klimatavtryck ' + x.ar); near(s(terr, x), x.terr, 1e-6, 'territoriellt ' + x.ar);
    near(s(gpc('plus'), x), x.basicPlus, 1e-6, 'BASIC+ ' + x.ar); near(s(gpc('basic'), x), x.basic, 1e-6, 'BASIC ' + x.ar);
    near(x.opEl + x.opFv, x.op.energi, 1e-6, 'energi ' + x.ar); assert.ok(x.opEl > 0 && x.opFv > 0);
  }
  near(rad(res, 2024).opEl, R.energyBase.tEl.reduce((a, v) => a + v, 0), 1e-6, 'el i befintliga byggnader 2024');
  for (const k of Z.KALLOR) assert.ok(Z.DELAR.some(d => d.id === k.del) && k.op, k.id);
});

test('jämförelse med samma trafikmodell, ackumulerat 2027–2050: samma summor som sidorna, avgaserna gemensamma', () => {
  const J = Z.jamforelse(res, {trafik: 'samma'}), [op, terr, gpc] = J.metoder, sel = res.rader.filter(x => x.ar >= 2027 && x.ar <= 2050);
  assert.deepStrictEqual([J.fran, J.till, J.j.niva], [2027, 2050, 'plus']);
  near(op.total, M.cityByYear(R).filter(r => r.year >= 2027 && r.year <= 2050).reduce((a, r) => a + r.total, 0), 1e-4, 'klimatavtrycket = Resultat, alla kategorier');
  near(terr.total, sel.reduce((a, x) => a + x.terr, 0), 1e-4); near(gpc.total, sel.reduce((a, x) => a + x.basicPlus, 0), 1e-4);
  near(J.gemensamt.t, sel.reduce((a, x) => a + x.sek.vagtrafik, 0), 1e-4, 'gemensamt = vägtrafikens avgaser');
  for (const m of J.metoder) { near(m.delar.avgaser, J.gemensamt.t, 1e-6, m.id); near(m.perAr.reduce((a, v, i) => a + (res.rader[i].ar >= 2027 ? v : 0), 0), m.total, 1e-4); }
  near(op.perPerson, sel.reduce((a, x) => a + x.op.total / x.inv, 0) / sel.length, 1e-9, 'snitt per invånare');
  near(op.total / 1000, 14766.0, 0.5, 'klimatavtryck 2027–2050'); near(terr.total / 1000, 19150.1, 0.5); near(gpc.total / 1000, 20658.3, 0.5);
});

test('jämförelse: bryggan går från klimatavtrycket via territoriellt till GPC', () => {
  for (const niva of ['plus', 'basic']) {
    const J = Z.jamforelse(res, {niva, trafik: 'samma'}), b = J.brygga, iT = b.findIndex(x => x.metod === 'terr');
    assert.strictEqual(b[0].metod, 'op'); assert.strictEqual(b[b.length - 1].metod, 'gpc');
    near(b[0].t + b.slice(1, iT).reduce((a, x) => a + x.t, 0), b[iT].t, 1e-4, niva + ' till territoriellt');
    near(b[iT].t + b.slice(iT + 1, -1).reduce((a, x) => a + x.t, 0), b[b.length - 1].t, 1e-4, niva + ' till GPC');
    near(b[b.length - 1].t, J.metoder[2].total, 1e-6);
    assert.ok(b.some(x => x.text === 'Läggs till i bokföringen: industri, sjöfart, arbetsmaskiner, avfall och jordbruk'), 'hel del med sitt namn');
    assert.ok(b.slice(1, iT).findIndex(x => x.t > 0) > b.slice(1, iT).findLastIndex(x => x.t < 0), 'först det som tas bort');
  }
  const t = Z.jamforelse(res, {niva: 'basic', trafik: 'samma'}).brygga.map(x => x.text).join(' | ');
  assert.ok(t.includes('Ingår inte i BASIC: produktanvändning och jordbruk'), t);
});

test('jämförelse ett år: samma värden som årsraden', () => {
  for (const y of [2024, 2030, 2050]) {
    const J = Z.jamforelse(res, {lage: 'ar', ar: y, niva: 'basic', trafik: 'samma'}), r = rad(res, y);
    assert.deepStrictEqual(J.ar, [y]);
    near(J.metoder[0].total, r.op.total, 1e-6); near(J.metoder[1].total, r.terr, 1e-6); near(J.metoder[2].total, r.basic, 1e-6);
    near(J.metoder[1].perPerson, r.terr / r.inv, 1e-12);
  }
  assert.throws(() => Z.jamforelse(res, {lage: 'ar', ar: 2060}));
});

/* ---------- egen datakälla per räknesätt (0.15.1) ---------- */
const sum = (a, f) => a.reduce((s, x) => s + f(x), 0), period = r => r.rader.filter(x => x.ar >= 2027 && x.ar <= 2050);
test('mobDelar: perspektiv A som berakna; perspektiv B summerar till Resultat med B', () => {
  const a = Z.mobDelar(S, R);
  res.rader.forEach((x, i) => { near(a[i].ttw, x.sek.vagtrafik, 1e-6); near(a[i].wtt, x.mobWtt, 1e-6); near(a[i].fordon, x.mobFordon, 1e-6); near(a[i].tot, x.op.mobilitet, 1e-6); });
  const RB = M.compute(S, {perspektiv: 'B'}), b = Z.mobDelar(S, RB), rows = M.cityByYear(RB);
  b.forEach((x, i) => { near(x.ttw + x.wtt + x.fordon, x.tot, 1e-6, 'delar ' + rows[i].year); near(x.tot, rows[i].mobilitet + rows[i].nymob, 1e-6, 'B ' + rows[i].year); });
  near(b[0].ttw, D.mob.stad[RB.bKey].ttw, 1, 'B:s avgaser 2024 = Vägvis B');
});

test('källfaktorerna räknas ur underlaget', () => {
  const K = res.kallfaktorer, r0 = rad(res, 2024), c = id => B.gpc_klimatkontrakt.rader.find(x => x.id === id), mb = (id, y) => T.sektorer[id][T.ar.indexOf(y)] * 1000;
  near(K.vag, mb('vagtrafik', 2024) / D.mob.stad.A.ttw, 1e-9, 'Miljöbarometern / Vägvis A 2024');
  near(K.transport, c('transport').s1 / (mb('vagtrafik', 2022) + mb('sjofart', 2022) + mb('arbetsmaskiner', 2022)), 1e-9, 'SMED / ENVIMAN 2022');
  near(K.byggnader, c('stationar').s1 / (mb('energi', 2022) + mb('industri', 2022)), 1e-9);
  near(K.scope2, (c('stationar').s2 + c('transport').s2) / (r0.s2.stat + r0.s2.jvg), 1e-9);
  near(K.vag, 1.0406, 0.0001); near(K.transport, 1.922, 0.001);
});

test('egen datakälla (förval): territoriellt 2024 = Miljöbarometerns sektorer; GPC med SMED och hela klimatkontraktet', () => {
  const J = Z.jamforelse(res, {lage: 'ar', ar: 2024}), K = res.kallfaktorer, r0 = rad(res, 2024);
  assert.deepStrictEqual([J.j.trafik, J.j.gpcKalla], ['egen', 'smed']);
  near(J.metoder[1].total, Object.keys(T.sektorer).reduce((s, id) => s + T.sektorer[id][i24] * 1000, 0), 1e-6, 'territoriellt = Miljöbarometern 2024');
  near(J.metoder[0].total, r0.op.total, 1e-6, 'klimatavtrycket med A som förut');
  const tr = r0.sek.vagtrafik * K.vag + r0.sek.sjofart + r0.sek.arbetsmaskiner;
  near(J.metoder[2].total, r0.basicPlus + r0.sek.vagtrafik * (K.vag - 1) + tr * (K.transport - 1), 1e-6, 'BASIC+ med SMED');
  const c = Z.jamforelse(res, {lage: 'ar', ar: 2024, gpcKalla: 'ccc'}).metoder[2].total, kk = B.gpc_klimatkontrakt.rader;
  const mb22 = id => T.sektorer[id][T.ar.indexOf(2022)] * 1000, s = id => r0.sek[id];
  const vantat = (s('energi') + s('industri')) * K.byggnader + (s('vagtrafik') * K.vag + s('sjofart') + s('arbetsmaskiner')) * K.transport + s('avfall') * K.avfall + s('produkt') * K.ippu + s('jordbruk') * K.afolu + (r0.s2.stat + r0.s2.jvg) * K.scope2;
  near(c, vantat, 1e-6, 'hela klimatkontraktet utan marken');
  near(K.byggnader * (mb22('energi') + mb22('industri')), kk.find(x => x.id === 'stationar').s1, 1e-6, 'byggnadernas nivå = kontraktets 2022');
  const m = Z.jamforelse(res, {gpcKalla: 'mb'}), p = period(res);
  near(m.metoder[2].total, sum(p, x => x.basicPlus + x.sek.vagtrafik * (K.vag - 1)), 1e-4, 'GPC med Miljöbarometern');
  near(m.metoder[1].total / 1000, 19440, 1); near(Z.jamforelse(res).metoder[2].total / 1000, 29371, 1); near(Z.jamforelse(res, {gpcKalla: 'ccc'}).metoder[2].total / 1000, 32859, 1);
  assert.ok(!Z.jamforelse(res).gemensamt.lika, 'avgaserna skiljer mellan källorna');
});

test('egen datakälla: klimatavtrycket med B = Resultat med B, och bryggan går ihop i alla lägen', () => {
  const RB = M.compute(S, {perspektiv: 'B'}), opMob = Z.mobDelar(S, RB);
  const JB = Z.jamforelse(res, {}, opMob), rowsB = M.cityByYear(RB).filter(r => r.year >= 2027 && r.year <= 2050);
  near(JB.metoder[0].total, sum(rowsB, r => r.total), 1e-4, 'klimatavtrycket med B'); near(JB.metoder[0].total / 1000, 11341, 1);
  assert.ok(JB.brygga.some(x => x.typ === 'kalla' && x.text.includes('hushållens bilar')));
  for (const j of [{}, {gpcKalla: 'mb'}, {gpcKalla: 'ccc'}, {niva: 'basic'}, {gpcKalla: 'ccc', niva: 'basic'}, {lage: 'ar', ar: 2040}, {trafik: 'samma'}]) for (const om of [null, opMob]) {
    const J = Z.jamforelse(res, j, om), b = J.brygga, iT = b.findIndex(x => x.metod === 'terr');
    near(b[0].t + b.slice(1, iT).reduce((a, x) => a + x.t, 0), J.metoder[1].total, 1e-3, JSON.stringify(j) + ' till territoriellt');
    near(b[iT].t + b.slice(iT + 1, -1).reduce((a, x) => a + x.t, 0), J.metoder[2].total, 1e-3, JSON.stringify(j) + ' till GPC');
    for (const m of J.metoder) near(Object.values(m.delar).reduce((a, v) => a + v, 0), m.total, 1e-6);
    if (j.trafik === 'samma') assert.ok(b.every(x => x.typ !== 'kalla'), 'inga källsteg med samma modell');
  }
});

console.log('\n' + passed + ' tester för stadens redovisning godkända.');
