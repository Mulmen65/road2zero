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

console.log('\n' + passed + ' tester för stadens redovisning godkända.');
