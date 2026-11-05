/* Tester för Resultat & klimatbudget i Road2Zero-OP. Kör: node op/tests/test_resultat.js
   Förväntade värden för klimatbudgeten är räknade med road2zero/modules/budget.py (samma bana och fördelning). */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('assert'), {execFileSync} = require('child_process');
const OP = path.resolve(__dirname, '..'), ROOT = path.join(OP, 'projekt', 'malmo_op');
const M = require(path.join(OP, 'app/model.js')), RZ = require(path.join(OP, 'app/resultat.js'));
const read = p => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const csv = f => fs.readFileSync(path.join(OP, '..', 'road2zero', 'data', f), 'utf8').trim().split(/\r?\n/).slice(1).map(l => l.split(';'));
const B = {budget: csv('budget_forster2026.csv').map(([t, s, g]) => ({temperatur: t, sannolikhet: Number(s), gt_co2: Number(g)})),
  befolkning: csv('befolkning_unwpp2024.csv').map(([a, m]) => ({ar: Number(a), miljarder: Number(m)})), e0: 43.0, k: 1.314815, farg: {},
  andelar: csv('budgetandelar.csv').map(([o, ar, h, bo, tr, fl, off, inv]) => ({omrade: o, ar: Number(ar), hushall_kg: Number(h), boende_kg: Number(bo), transport_kg: Number(tr), flyg_kg: Number(fl), offentlig_kg: Number(off), investeringar_kg: Number(inv)})),
  nybyggnad: Object.fromEntries(csv('nybyggnadsandel.csv').map(([post, , v]) => [post, Number(v)]))};
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, (msg || '') + ' ' + a + ' ≠ ' + b);
let passed = 0; const test = (n, f) => { f(); passed++; console.log('✓ ' + n); };
const D = {deso: read('data/kalla/deso_2025_malmo.geojson'), energi: read('data/energi_deklarationer.json'), mob: read('data/mobilitet_vagvis.json'), expl: read('data/exploatering_op2023.json')};
const S = M.prepare(D), R = M.compute(S, {}), rows = M.cityByYear(R);
const alla = {kat: RZ.KATEGORIER.slice(), grupper: ['befintlig', 'ny'], period: [2027, 2050], temp: '1,5', sann: 50};

test('andel per person följer budget.py (1,5 °C, 50 %)', () => {
  const a = RZ.andelPerPerson(B, '1,5', 50, [2025, 2026, 2030, 2050]);
  assert.strictEqual(a[2025], undefined);
  near(a[2026], 43.0 * 1.314815 / 8.3007, 1e-9, '2026');
  near(a[2030], 43.0 * Math.pow(1 - 43 / 130, 4) * 1.314815 / 8.5691, 1e-9, '2030');
});
test('linjär bana när budgeten är mindre än ett års utsläpp (1,5 °C, 90 %)', () => {
  const E = RZ.bana(10, 43, 5);
  near(E.reduce((s, x) => s + x, 0), 10, 1e-9, 'summan av banan är budgeten');
});
test('kategorierna summerar till modellens totala utsläpp', () => {
  const p = RZ.perAr(rows, alla);
  p.forEach((r, i) => near(r.summa, rows[i].total, 1e-6, 'år ' + r.ar));
});
test('befintlig stad och exploateringen delar upp summan', () => {
  const b = RZ.berakna(rows, B, {...alla, grupper: ['befintlig']}), n = RZ.berakna(rows, B, {...alla, grupper: ['ny']}), h = RZ.berakna(rows, B, alla);
  near(b.summa + n.summa, h.summa, 1e-6);
  assert.ok(n.summa > 0 && b.summa > n.summa);
});
test('stadens budget = invånare × andel per person från 2026', () => {
  const h = RZ.berakna(rows, B, alla), a = RZ.andelPerPerson(B, '1,5', 50, rows.map(r => r.year));
  near(h.stadBudget, rows.filter(r => r.year >= 2026).reduce((s, r) => s + r.bef * a[r.year], 0), 1e-6);
  assert.ok(h.slut === null || (h.slut >= 2026 && h.slut <= 2050));
});
test('högre temperaturgräns ger större budget', () => {
  const lag = RZ.berakna(rows, B, alla).stadBudget, hog = RZ.berakna(rows, B, {...alla, temp: '2,0'}).stadBudget;
  assert.ok(hog > lag * 3);
});
test('budget.py ger samma andel per person', () => {
  let py;
  try {
    py = execFileSync('python3', ['-c', "import sys,json; sys.path.insert(0, sys.argv[1]); from road2zero.factlib import ladda; from road2zero.modules.budget import andel_per_person, global_gt; fb=ladda(); a,_=andel_per_person(fb, global_gt(fb,'1,7',67), 43.0, 1.314815, list(range(2024,2051))); print(json.dumps(a))", path.join(OP, '..')], {encoding: 'utf8'});
  } catch (e) { console.log('  (Python saknas, jämförelsen hoppas över)'); return; }
  const a = JSON.parse(py), j = RZ.andelPerPerson(B, '1,7', 67, Array.from({length: 27}, (_, i) => 2024 + i));
  for (const [y, v] of Object.entries(a)) near(j[y], v, 1e-9, 'år ' + y);
});
test('budgetandelar enligt Konsumtionskompassen (Malmö 2022) mot hela fotavtrycket', () => {
  const a1 = RZ.standardAndelar(B, 'Malmö', 1), F = 5754.14 + 830 + 2090;
  near(a1.boende, 1066.46 / F, 1e-12); near(a1.investeringar, 2090 / F, 1e-12); near(a1.transport, (1749.27 - 848) / F, 1e-12);
  near(100 * a1.boende, 12.3, 0.05); near(100 * a1.investeringar, 24.1, 0.05); near(100 * a1.transport, 10.4, 0.05);
  near(RZ.standardAndelar(B, 'Malmö', 0.5).investeringar, 0.5 * 2090 / F, 1e-12);
  const n = RZ.standardByggandel(B), a = RZ.standardAndelar(B, 'Malmö');
  near(a.investeringar, n * 2090 / F, 1e-12, 'standard: nybyggnationens andel av investeringarna');
  near(100 * a.investeringar, 5.1, 0.05); near(100 * (a.boende + a.investeringar + a.transport), 27.8, 0.05);
  assert.deepStrictEqual(B.andelar.map(r => r.omrade), ['Malmö', 'Skåne', 'Sverige']);
  assert.deepStrictEqual(RZ.BUDGETGRUPPER.flatMap(g => g.kat).sort(), RZ.KATEGORIER.slice().sort(), 'varje kategori i exakt en grupp');
});
test('nybyggnationens andel av investeringarna ur SCB, Byggföretagen och Boverket', () => {
  const d = RZ.nybyggnadsdelar(B);
  near(d.bygg, 9507646 / 22451346, 1e-12, 'byggprodukter F41–F43 / fasta bruttoinvesteringar 2023');
  near(d.hus, (235.9 + 273.6) / (235.9 + 273.6 + 143.2), 1e-12, 'bostäder + lokaler / bygginvesteringar 2023');
  near(d.ny, 7240 / (7240 + 4129), 1e-12, 'nybyggnad / (nybyggnad + ombyggnad) 2015');
  near(d.n, d.bygg * d.hus * d.ny, 1e-15); near(100 * d.n, 21.1, 0.05);
  assert.strictEqual(RZ.standardByggandel({}), 1, 'utan underlag: hela investeringsandelen');
  near(RZ.budgetFaktor(B, {...alla, tilldelning: 'Malmö', byggandel: null}), RZ.budgetFaktor(B, {...alla, tilldelning: 'Malmö'}), 1e-15);
});
test('budgetfaktorn är summan av andelarna för grupper med valda kategorier', () => {
  const a = RZ.standardAndelar(B, 'Malmö'), u = {...alla, tilldelning: 'Malmö'};
  near(RZ.budgetFaktor(B, u), a.boende + a.investeringar + a.transport, 1e-12);
  near(RZ.budgetFaktor(B, {...u, kat: ['Energi']}), a.boende, 1e-12);
  near(RZ.budgetFaktor(B, {...u, kat: ['Byggnad']}), a.investeringar, 1e-12);
  near(RZ.budgetFaktor(B, {...u, kat: ['Byggnad', 'Förändrad markanvändning', 'Mobilitet och transport']}), a.investeringar + a.transport, 1e-12);
  near(RZ.budgetFaktor(B, {...u, byggandel: 40}), a.boende + 0.4 * RZ.standardAndelar(B, 'Malmö', 1).investeringar + a.transport, 1e-12);
  assert.strictEqual(RZ.budgetFaktor(B, alla), 1, 'utan tilldelning: hela budgeten');
  near(RZ.budgetFaktor(B, {...alla, tilldelning: 'egen', andelar: {boende: 10, investeringar: 5, transport: 20}}), 0.35, 1e-12);
});
test('stadens budget och budgetåret med tilldelning', () => {
  const hel = RZ.berakna(rows, B, alla), u = {...alla, tilldelning: 'Malmö'}, r = RZ.berakna(rows, B, u);
  near(r.stadBudget, hel.stadBudget * r.faktor, 1e-6); near(r.snittBudget, hel.snittBudget * r.faktor, 1e-12);
  assert.ok(r.slut <= hel.slut, 'mindre budget förbrukas tidigare');
  assert.strictEqual(r.grupper.length, 3);
  for (const g of r.grupper) near(g.snittBudget, r.snittHel * g.andel, 1e-12);
  near(r.grupper.reduce((s, g) => s + g.snitt, 0), r.snitt, 1e-9, 'grupperna summerar till snittet');
  near(RZ.budgetSnitt(rows, B, u, '1,5', 50), r.snittBudget, 1e-12);
});
console.log('\n' + passed + ' tester för resultatvyn godkända.');
