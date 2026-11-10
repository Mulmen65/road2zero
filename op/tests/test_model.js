/* Beräkningstester för MalmoOP. Kör: node tests/test_model.js */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('assert');
const OP = path.resolve(__dirname, '..'), ROOT = path.join(OP, 'projekt', 'malmo_op');
const M = require(path.join(OP, 'app/model.js'));
const read = p => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const D = {deso: read('data/kalla/deso_2025_malmo.geojson'), energi: read('data/energi_deklarationer.json'), mob: read('data/mobilitet_vagvis.json'), expl: read('data/exploatering_op2023.json')};
const S = M.prepare(D);
const sum = a => Array.from(a).reduce((x, y) => x + y, 0);
const near = (a, b, tol = 1e-6, msg = '') => assert.ok(Math.abs(a - b) <= tol * Math.max(1, Math.abs(a), Math.abs(b)), msg + ' ' + a + ' ≠ ' + b);
let passed = 0;
function test(name, fn) { fn(); passed++; console.log('✓ ' + name); }

test('209 DeSO och samma ordning i energi och geometri', () => { assert.strictEqual(S.n, 209); assert.deepStrictEqual(D.energi.deso, S.ids); });

test('DeSO-summor = Malmö-summor för varje år och komponent', () => {
  const R = M.compute(S, {});
  for (const ar of [...M.YEARS, 'ack']) {
    const v = M.view(S, R, ar);
    for (const c of [...M.COMPONENTS, 'total']) near(v.rows.reduce((s, r) => s + r[c], 0), v.city[c], 1e-9, ar + ' ' + c);
    near(v.city.total, M.COMPONENTS.reduce((s, c) => s + v.city[c], 0), 1e-9, 'total ' + ar);
  }
});

test('Energins massbalans: kartlagt + ej kartlagt = alla deklarationer (bara deklarerade, okalibrerat)', () => {
  const P = M.params({bestand: 'deklarerade'}), eb = M.energyBase(S, P), E = D.energi.kolumner;
  let all = 0;
  for (let i = 0; i < E.id.length; i++) {
    const a = E.bta[i] > 0 ? E.bta[i] * P.atempFaktor : S.btaMedian * P.atempFaktor;
    all += E.se[i] * a * (E.el[i] * P.efEl + (1 - E.el[i]) * P.efFv) / 1000;
  }
  near(sum(eb.t) + eb.unmappedT, all, 1e-9, 'massbalans');
  assert.strictEqual(eb.unmapped, D.energi.urval.ej_kartlagda);
  assert.strictEqual(eb.k, 1); assert.strictEqual(eb.kalibrering, 'ingen');
});

test('Hela beståndet: massbalans med kalibreringsfaktor per post', () => {
  const P = M.params({}), eb = M.energyBase(S, P), it = M.energyItems(S, P);
  assert.strictEqual(it.m, D.energi.kolumner.id.length + D.energi.bestand.bta.length);
  let all = 0;
  for (let i = 0; i < it.m; i++) all += eb.kG[it.grp[i]] * it.se[i] * it.a[i] * (it.el[i] * P.efEl + (1 - it.el[i]) * P.efFv) / 1000;
  near(sum(eb.t) + eb.unmappedT, all, 1e-9, 'massbalans hela');
  near(sum(eb.skattadT), D.energi.bestand.bta.reduce((s, b, j) => { const kl = D.energi.bestand.kl[j], a = b * P.atempFaktor * (kl === S.IND ? P.industriAndel : 1), el = D.energi.bestand.el[j];
    return s + eb.kG[S.GRP[kl]] * D.energi.bestand.se[j] * a * (el * P.efEl + (1 - el) * P.efFv) / 1000; }, 0), 1e-9, 'skattade byggnader');
  assert.ok(sum(eb.t) > sum(M.energyBase(S, M.params({bestand: 'deklarerade', kalibrering: 'ingen'})).t), 'hela beståndet ger mer än bara deklarerade');
});

test('Kalibrering: fjärrvärmen möter SCB per sektor eller totalt', () => {
  const kal = D.energi.kalibrering, sek = M.energyBase(S, M.params({kalibrering: 'sektor'}));
  assert.strictEqual(sek.kalibrering, 'sektor'); assert.strictEqual(sek.kG[0], 1, 'småhus kalibreras inte');
  near(sek.grupper[1].modell * sek.kG[1], kal.sektor_mal_mwh.flerbostadshus * 1000, 1e-9, 'flerbostadshus');
  near(sek.grupper[2].modell * sek.kG[2], kal.sektor_mal_mwh.lokal_industri * 1000, 1e-9, 'lokaler och industri');
  near(sek.dhKalibrerad, sek.grupper[0].modell + (kal.sektor_mal_mwh.flerbostadshus + kal.sektor_mal_mwh.lokal_industri) * 1000, 1e-9, 'summa sektor');
  const tot = M.energyBase(S, M.params({kalibrering: 'total'}));
  near(tot.dhKalibrerad, kal.mal_fjarrvarme_mwh * 1000, 1e-9, 'total');
  near(tot.k, kal.mal_fjarrvarme_mwh * 1000 / tot.dhModell, 1e-12, 'k total');
  const ingen = M.energyBase(S, M.params({kalibrering: 'ingen'}));
  near(ingen.dhKalibrerad, ingen.dhModell, 1e-12); near(ingen.dhModell, tot.dhModell, 1e-12, 'samma okalibrerade modell');
  near(kal.sektor_mal_mwh.smahus + kal.sektor_mal_mwh.flerbostadshus + kal.sektor_mal_mwh.lokal_industri, kal.mal_fjarrvarme_mwh, 1e-5, 'sektorer = total');
  assert.strictEqual(M.params({kalibrering: 'scb'}).kalibrering, 'total', 'äldre värde scb tolkas som total');
});

test('Räkneexempel energi: 100 kWh/m², 1 000 m², 10 % el = 5,41 t', () => {
  const t = 100 * 1000 * (0.1 * 0.037 + 0.9 * 0.056) / 1000;
  near(t, 5.41, 1e-12);
  const P = M.params({atempLage: 'fast', atempFast: 1000, elLage: 'fast', elFast: 0.1, bestand: 'deklarerade'}), eb = M.energyBase(S, P), E = D.energi.kolumner;
  let mapped = 0; for (let i = 0; i < E.id.length; i++) if (E.alloc[i].length) mapped += E.se[i] * 1000 * (0.1 * 0.037 + 0.9 * 0.056) / 1000;
  near(sum(eb.t), mapped, 1e-9, 'fast läge');
});

test('Mobilitet 2024 = Vägvis Malmö-summor, med elbilarnas el räknad med modellens elfaktor (A och B)', () => {
  const om = (x, ef) => x.total - x.el + x.el * ef / D.mob.elFaktor.A;
  for (const [namn, p, x] of [['A', {perspektiv: 'A'}, D.mob.stad.A], ['B', {perspektiv: 'B'}, D.mob.stad.B_local], ['B gtfs', {perspektiv: 'B', bLage: 'gtfs'}, D.mob.stad.B_gtfs]]) {
    assert.ok(x.el > 0 && x.el < 0.02 * x.total, namn + ': laddelen är en liten del');
    near(M.view(S, M.compute(S, p), 2024).city.mobilitet, om(x, 37), 1, namn + ', Boverket 37 g');
    near(M.view(S, M.compute(S, {...p, elVal: 'iea'}), 2024).city.mobilitet, om(x, 26), 1, namn + ', IEA 26 g');
    near(M.view(S, M.compute(S, {...p, elVal: 'egen', efElEgen: D.mob.elFaktor.A / 1000}), 2024).city.mobilitet, x.total, 1e-6, namn + ', Vägvis egen elfaktor');
  }
});

test('Elens klimatfaktor: tre val med startvärde och takt; äldre lägen behåller sitt resultat', () => {
  assert.strictEqual(M.params({}).elVal, 'boverket'); near(M.params({}).efEl, 0.037, 1e-15);
  const iea = M.params({elVal: 'iea'}), egen = M.params({elVal: 'egen', efElEgen: 0.05});
  near(iea.efEl, 0.026, 1e-15); assert.deepStrictEqual([1, 2, 3, 4, 5].map(k => iea['elR' + k]), M.UTV.el_iea);
  near(egen.efEl, 0.05, 1e-15); assert.deepStrictEqual([1, 2, 3, 4, 5].map(k => egen['elR' + k]), M.UTV.el_wem);
  near(M.faktorer(iea, 2030).el, 0.026 * Math.pow(1 + M.UTV.el_iea[0] / 100, 4), 1e-15);
  assert.strictEqual(M.params({elVal: 'okänd'}).elVal, 'boverket');
  const gammal = M.params({efEl: 0.05});   // äldre läge: eget startvärde utan val, Boverkets takt
  assert.strictEqual(gammal.elVal, 'egen'); near(gammal.efEl, 0.05, 1e-15);
  assert.deepStrictEqual([1, 2, 3, 4, 5].map(k => gammal['elR' + k]), M.UTV.el);
  assert.strictEqual(M.params({elVal: 'iea', elR1: -1}).elR1, -1, 'egen takt går före valets standard');
});

test('Utan exploatering är exploateringsposterna noll', () => {
  const v = M.view(S, M.compute(S, {exploatering: false}), 'ack');
  for (const c of ['bygg', 'mark', 'nydrift', 'nymob']) assert.strictEqual(v.city[c], 0, c);
});

test('Nybyggnation 2030–2050 = Σ BTA × gränsvärde / 1 000', () => {
  const P = M.params({}), v = M.view(S, M.compute(S, P), 'ack');
  let exp = 0;
  for (const a of D.expl.omraden) {
    const lok = a.kategori === 'Verksamhetsområde' ? ['hall', P.btaArbVerks] : ['lokal', P.btaArbBlandad];
    exp += (a.bostader * P.btaBostad * M.BYGG.gransvarde2030.bostad + a.arbetsplatser * lok[1] * M.BYGG.gransvarde2030[lok[0]] + (a.forskola + a.grundskola + a.gymnasie) * P.btaSkolplats * M.BYGG.gransvarde2030.skola) / 1000;
  }
  near(v.city.bygg, exp, 1e-9, 'bygg');
});

test('Markförlust = Σ ha × hårdgörandel × (C före − C efter) × 44/12', () => {
  const P = M.params({}), v = M.view(S, M.compute(S, P), 'ack'), C = {aker: P.kolAker, oppen: P.kolOppen, skog: P.kolSkog, vatten: 0, bebyggd: P.kolBebyggd, okand: P.kolBebyggd};
  let exp = 0;
  for (const a of D.expl.omraden) for (const d of a.delar) for (const [k, ha] of Object.entries(d.mark)) exp += ha * P.hardgorandel * Math.max(0, C[k] - P.kolBebyggd) * 44 / 12;
  near(v.city.mark, exp, 1e-9, 'mark');
});

test('Tidsplan: ingen nybyggnation 2024 eller 2050; Fokus 1 klar 2040', () => {
  const R = M.compute(S, {});
  assert.strictEqual(M.view(S, R, 2024).city.bygg, 0);
  assert.strictEqual(M.view(S, R, 2050).city.bygg, 0);
  const f1 = D.expl.omraden.filter(a => a.fokus === 1).reduce((s, a) => s + a.bostader, 0);
  near(M.view(S, R, 2040).city.nyaInv, f1 * M.DEFAULTS.personerPerBostad, 1e-9, 'nya invånare 2040');
});

test('Nya invånare 2050 = alla bostäder × invånare per bostad', () => {
  const v = M.view(S, M.compute(S, {}), 2050), b = D.expl.omraden.reduce((s, a) => s + a.bostader, 0);
  near(v.city.nyaInv, b * M.DEFAULTS.personerPerBostad, 1e-9);
  near(v.city.bef, sum(S.hh.map(h => h.bef)) + b * M.DEFAULTS.personerPerBostad, 1e-9);
});

test('Ny mobilitet: B i värd-DeSO, A fördelad efter trafik; egen flottfaktor skalar hela livscykeln (som 1.3)', () => {
  const vB = M.view(S, M.compute(S, {perspektiv: 'B', flottaVal: 'oforandrad'}), 2050), vA = M.view(S, M.compute(S, {perspektiv: 'A'}), 2050);
  const host = new Set(D.expl.omraden.flatMap(a => a.delar.map(d => d.deso)));
  assert.ok(vB.rows.every(r => host.has(r.id) || r.nymob === 0), 'B utanför värd-DeSO');
  assert.ok(vA.rows.filter(r => r.mobilitet > 0).every(r => r.nymob > 0), 'A fördelas till alla med trafik');
  const half = M.view(S, M.compute(S, {perspektiv: 'B', flotta2050: 0.5}), 2050);   // utan flottaVal: äldre läge, blir 'egen'
  assert.strictEqual(M.params({flotta2050: 0.5}).flottaVal, 'egen'); assert.strictEqual(M.params({}).flottaVal, 'nv2026');
  near(half.city.nymob, vB.city.nymob * 0.5, 1e-9, 'flotta');
  near(half.city.mobilitet, vB.city.mobilitet * 0.5, 1e-9, 'flotta befintlig');
});

test('Enheter: kg/ha = 1 000 × t/ha; per invånare', () => {
  const v = M.view(S, M.compute(S, {}), 2030), r = v.rows.find(x => x.land_ha > 0 && x.bef > 0);
  near(M.metric(r, 'total', 'kg_ha'), 1000 * M.metric(r, 'total', 't_ha'), 1e-12);
  near(M.metric(r, 'total', 't_inv'), r.total / r.bef, 1e-12);
});

const NOLL = Object.fromEntries(['elR', 'fvR', 'byggR'].flatMap(p => [1, 2, 3, 4, 5].map(k => [p + k, 0])));
test('Effektivisering verkar linjärt till 2050; utan förändrade faktorer är energin densamma som 2024', () => {
  const base = M.view(S, M.compute(S, NOLL), 2050).city.energi;
  near(base, M.view(S, M.compute(S, NOLL), 2024).city.energi, 1e-12, 'oförändrade faktorer');
  near(M.view(S, M.compute(S, {...NOLL, effektivisering2050: 30}), 2050).city.energi, base * 0.7, 1e-9, 'eff');
  near(M.view(S, M.compute(S, {effektivisering2050: 30}), 2024).city.energi, base, 1e-9, '2024 oförändrat');
});

test('Standardtakterna för el, fjärrvärme och klimattrappor = Road2Zero-Plans faktabibliotek (utveckling.csv)', () => {
  const rader = fs.readFileSync(path.join(OP, '..', 'road2zero', 'data', 'utveckling.csv'), 'utf8').trim().split(/\r?\n/).map(r => r.split(';'));
  const hdr = rader[0], kol = ['p2027_2030', 'p2031_2035', 'p2036_2040', 'p2041_2045', 'p2046_2050'].map(c => hdr.indexOf(c));
  const rad = id => rader.find(r => r[0] === id);
  for (const [nyckel, id] of [['el', 'el'], ['el_iea', 'el_iea'], ['el_wem', 'el_wem'], ['fv', 'fjv'], ['insteg', 'bygg.betong_bau'], ['fardplan', 'bygg.betong_bast']])
    assert.deepStrictEqual(M.UTV[nyckel], kol.map(c => Number(rad(id)[c])), nyckel);
  // elens startvärden = Road2Zero-Plans parametrar (g CO2e/kWh)
  const par = Object.fromEntries(fs.readFileSync(path.join(OP, '..', 'road2zero', 'data', 'parametrar.csv'), 'utf8').trim().split(/\r?\n/).map(r => r.split(';')).map(r => [r[0], Number(r[3])]));
  near(M.EL_ALT.boverket.ef * 1000, par['el.startvarde'], 1e-9, 'Boverket'); near(M.EL_ALT.iea.ef * 1000, par['el.startvarde_iea'], 1e-9, 'IEA');
  near(M.DEFAULTS.efElEgen * 1000, par['el.startvarde_egen'], 1e-9, 'eget startvärde');
  assert.deepStrictEqual(M.PERIODER.map(([a, b]) => 'p' + a + '_' + b), hdr.filter(h => /^p20(2|3|4)/.test(h)).slice(0, 5));
});

test('Emissionsfaktorer över tid: index 1 till 2026, sedan (1 + r/100) per år och period', () => {
  const P = M.params({}), r = M.UTV.el;
  near(M.faktorer(P, 2026).el, P.efEl, 1e-15); near(M.faktorer(P, 2024).fv, P.efFv, 1e-15);
  near(M.indexAr(r, 2030), Math.pow(1 + r[0] / 100, 4), 1e-12);
  near(M.indexAr(r, 2032), Math.pow(1 + r[0] / 100, 4) * Math.pow(1 + r[1] / 100, 2), 1e-12);
  const v = M.view(S, M.compute(S, {}), 2050).city.energi, eb = M.energyBase(S, P), fk = M.faktorer(P, 2050);
  near(v, sum(eb.tEl) * fk.iEl + sum(eb.tFv) * fk.iFv, 1e-9, 'energi 2050 = el- och fjärrvärmedelen var för sig');
  near(sum(eb.tEl) + sum(eb.tFv), sum(eb.t), 1e-9, 'el + fjärrvärme = summa');
});

test('Sysavs koldioxidavskiljning sänker fjärrvärmens faktor från valt år, i befintliga och nya byggnader', () => {
  const nej = M.compute(S, {}), ja = M.compute(S, {beccs: 'ja'}), eb = nej.energyBase, P = M.params({});
  assert.strictEqual(M.DEFAULTS.beccs, 'nej'); assert.strictEqual(M.DEFAULTS.beccsAr, 2030); assert.strictEqual(M.DEFAULTS.beccsMinskning, 43);
  near(M.view(S, ja, 2024).city.energi, M.view(S, nej, 2024).city.energi, 1e-12);
  const y = nej.years.indexOf(2029), y30 = nej.years.indexOf(2030);
  near(sum(ja.comp.energi[y]), sum(nej.comp.energi[y]), 1e-12, '2029 oförändrat');
  near(sum(nej.comp.energi[y30]) - sum(ja.comp.energi[y30]), sum(eb.tFv) * M.faktorer(P, 2030).iFv * 0.43, 1e-9, '43 % av fjärrvärmedelen 2030');
  assert.ok(M.view(S, ja, 2050).city.nydrift < M.view(S, nej, 2050).city.nydrift, 'nya byggnader');
  near(M.faktorer(M.params({beccs: 'ja', beccsAr: 2035, beccsMinskning: 100}), 2035).fv, 0, 1e-15);
});

test('Klimattrappor för nybyggnation', () => {
  const f = (k, y, x = {}) => M.byggFaktor(M.params({klimatBygg: k, ...x}), 'bostad', y), m2040 = 0.1 * 358 * M.P75_PROXY;
  near(f('trappa', 2034), 235, 1e-12); near(f('trappa', 2035), (235 + m2040) / 2, 1e-12); near(f('trappa', 2040), m2040, 1e-12);
  near(f('insteg', 2026), 358, 1e-12); near(f('insteg', 2030), 358 * Math.pow(1 - 0.0571, 4), 1e-9);
  near(f('fardplan', 2031), 358 * Math.pow(1 - 0.0924, 4) * (1 - 0.0592), 1e-9);
  near(f('egen', 2045, NOLL), 358, 1e-12); near(f('referens', 2045), 358, 1e-12); near(f('gransvarde2030', 2045), 235, 1e-12);
  const ref = M.view(S, M.compute(S, {klimatBygg: 'referens'}), 'ack').city.bygg, ins = M.view(S, M.compute(S, {klimatBygg: 'insteg'}), 'ack').city.bygg;
  assert.ok(ins < ref, 'Insteg lägre än oförändrade referensvärden');
});

test('Ogiltiga antaganden avvisas eller begränsas', () => {
  const P = M.params({efEl: -5, atempFaktor: 'abc', perspektiv: 'C', ar: 2033, f1Start: 2035, f1Slut: 2030, okänd: 1});
  assert.strictEqual(P.efEl, 0); assert.strictEqual(P.atempFaktor, M.DEFAULTS.atempFaktor); assert.strictEqual(P.perspektiv, 'A');
  assert.strictEqual(P.ar, M.DEFAULTS.ar); assert.ok(P.f1Slut > P.f1Start); assert.ok(!('okänd' in P));
});

test('Indikativ bana: gränsvärde 2030, −90 % mot 75-percentilproxy 2040', () => {
  const P = M.params({klimatBygg: 'bana'});
  near(M.byggFaktor(P, 'bostad', 2030), 235, 1e-12);
  near(M.byggFaktor(P, 'bostad', 2040), 0.1 * 358 * M.P75_PROXY, 1e-12);
  near(M.byggFaktor(P, 'bostad', 2035), (235 + 0.1 * 358 * M.P75_PROXY) / 2, 1e-12);
});

test('Varje utbyggnadsområde fördelas fullt ut på DeSO', () => {
  for (const a of D.expl.omraden) near(a.delar.reduce((s, d) => s + d.andel, 0), 1, 1e-4, a.namn);
});

test('Kontrollsiffror (perspektiv A, el Boverket): 560,1 kt 2024; 2050 566,6 kt med oförändrad flotta (1.3) och 180,0 kt med beslutade styrmedel', () => {
  const R = M.compute(S, {}), R1 = M.compute(S, {flottaVal: 'oforandrad'});
  near(M.view(S, R, 2024).city.total / 1000, 560.1, 2e-4); near(M.view(S, R1, 2024).city.total / 1000, 560.1, 2e-4);
  near(M.view(S, R1, 2050).city.total / 1000, 566.6, 2e-4); near(M.view(S, R, 2050).city.total / 1000, 180.0, 1e-3);
});

test('Fordonsflottan: index 1 till 2026; bränslekedjan följer beslutade styrmedel, tillverkningen bilproduktionens kurva; delarna summerar', () => {
  const P = M.params({});
  for (const y of [2024, 2025, 2026]) { near(M.flottaIndex(P, y), 1, 1e-12); near(M.bilprodIndex(P, y), 1, 1e-12); }
  near(M.flottaIndex(P, 2030), Math.pow(1 - 0.0458, 4), 1e-12); near(M.bilprodIndex(P, 2030), Math.pow(1 - 0.037, 4), 1e-12);
  const R = M.compute(S, {});
  R.years.forEach((y, yi) => {
    const m = R.comp.mobilitet[yi].reduce((a, b) => a + b, 0) + R.comp.nymob[yi].reduce((a, b) => a + b, 0), d = R.mobDelar[yi];
    near(d.ttw + d.wtt + d.fordon, m, 1e-9, 'delar ' + y); near(d.tot, m, 1e-9);
    near(R.flotta[yi].bransle, M.flottaIndex(P, y), 1e-12);
  });
  // 2024: delarna = Vägvis A för staden (laddelen omräknad till Boverkets elfaktor)
  const a = D.mob.stad.A, k = P.efEl * 1000 / D.mob.elFaktor.A;
  near(R.mobDelar[0].ttw, a.ttw, 1e-6); near(R.mobDelar[0].wtt, a.wtt - a.el + a.el * k, 1e-6); near(R.mobDelar[0].fordon, a.fordon, 1e-6);
  // B: samma summering med nya invånare
  const RB = M.compute(S, {perspektiv: 'B'}), yi = RB.years.indexOf(2050), dB = RB.mobDelar[yi];
  near(dB.tot, RB.comp.mobilitet[yi].reduce((x, y) => x + y, 0) + RB.comp.nymob[yi].reduce((x, y) => x + y, 0), 1e-9, 'B 2050');
});

test('Energi i byggnader valbar: utan energi = summan minus energi och nya byggnaders energi; komponenterna oförändrade', () => {
  const Rm = M.compute(S, {}), Ru = M.compute(S, {energiVal: 'utan'});
  assert.deepStrictEqual(M.aktiva(Ru.P), ['mobilitet', 'bygg', 'mark', 'nymob']); assert.deepStrictEqual(M.aktiva(Rm.P), M.COMPONENTS);
  for (const ar of [...M.YEARS, 'ack']) {
    const vm = M.view(S, Rm, ar), vu = M.view(S, Ru, ar);
    for (const c of M.COMPONENTS) near(vu.city[c], vm.city[c], 1e-9, ar + ' ' + c);
    near(vu.city.total, vm.city.total - vm.city.energi - vm.city.nydrift, 1e-9, 'total ' + ar);
    near(vu.city.exploatering, vm.city.exploatering - vm.city.nydrift, 1e-9, 'exploatering ' + ar);
    for (let i = 0; i < S.n; i += 17) near(vu.rows[i].total, vu.rows[i].mobilitet + vu.rows[i].bygg + vu.rows[i].mark + vu.rows[i].nymob, 1e-9, 'rad ' + i);
  }
  const bm = M.cityByYear(Rm), bu = M.cityByYear(Ru);
  bu.forEach((r, k) => { near(r.total, bm[k].total - bm[k].energi - bm[k].nydrift, 1e-9, 'år ' + r.year); near(r.totalAlla, bm[k].total, 1e-9); });
  assert.strictEqual(M.params({energiVal: 'x'}).energiVal, 'med');
});

test('Deklarationernas DeSO-vikter summerar till 1', () => {
  const E = D.energi.kolumner;
  for (let i = 0; i < E.id.length; i++) if (E.alloc[i].length) near(E.alloc[i].reduce((s, [, w]) => s + w, 0), 1, 1e-3, 'id ' + E.id[i]);
});

(async () => {
  const P = {iterationer: 200, seed: 42};
  const a = await M.simulateEnergy(S, P), b = await M.simulateEnergy(S, P), c = await M.simulateEnergy(S, {...P, seed: 43});
  test('Monte Carlo: samma seed ger samma resultat, annat seed ett annat', () => {
    assert.deepStrictEqual(Array.from(a.deso.p50), Array.from(b.deso.p50));
    assert.strictEqual(a.city.p975, b.city.p975);
    assert.notStrictEqual(a.city.p50, c.city.p50);
    assert.strictEqual(a.nyckel, M.uncertaintyKey(M.params(P)));
  });
  test('Monte Carlo: p2,5 ≤ p50 ≤ p97,5 och beräknat värde inom intervallet', () => {
    for (let d = 0; d < S.n; d++) assert.ok(a.deso.p025[d] <= a.deso.p50[d] + 1e-9 && a.deso.p50[d] <= a.deso.p975[d] + 1e-9, 'DeSO ' + d);
    const det = sum(M.energyBase(S, M.params(P)).t);
    assert.ok(a.city.p025 < det && det < a.city.p975, 'Malmö ' + det);
  });
  const z1 = await M.simulateEnergy(S, {iterationer: 100, seed: 7}), z2 = await M.simulateEnergy(S, {iterationer: 100, seed: 7, efEl: 0.074, efFv: 0.112});
  test('Monte Carlo: emissionsfaktorerna är fasta (Boverket) och skalar dragningarna exakt', () => {
    assert.ok(!('cvEfEl' in M.DEFAULTS) && !('cvEfFv' in M.DEFAULTS), 'ingen osäkerhetsparameter för emissionsfaktorerna');
    assert.strictEqual(M.DEFAULTS.efEl, 0.037); assert.strictEqual(M.DEFAULTS.efFv, 0.056);
    near(z2.city.p025, 2 * z1.city.p025, 1e-9, 'dubbla faktorer ger dubbla värden'); near(z2.deso.p975[10], 2 * z1.deso.p975[10], 1e-9);
  });
  test('Intervall för framtida år skalas med effektivisering och emissionsfaktorer', () => {
    const Q = M.params({effektivisering2050: 30, beccs: 'ja'}), R = M.compute(S, Q), eb = R.energyBase;
    const I24 = M.energyInterval(a, Q, 2024, eb), I50 = M.energyInterval(a, Q, 2050, eb), Iack = M.energyInterval(a, Q, 'ack', eb);
    const fk = M.faktorer(Q, 2050), sEl = sum(eb.tEl) / sum(eb.t), s5 = eb.tEl[5] / eb.t[5];
    near(I24.city.p975, a.city.p975, 1e-12); near(I50.f, 0.7 * (sEl * fk.iEl + (1 - sEl) * fk.iFv), 1e-12);
    near(I50.hi(5), a.deso.p975[5] * 0.7 * (s5 * fk.iEl + (1 - s5) * fk.iFv), 1e-12);
    near(M.view(S, R, 'ack').city.energi, sum(eb.t) * Iack.f, 1e-9, 'ack-faktor');
  });
  const stop = await M.simulateEnergy(S, {iterationer: 500}, p => p < 0.2);
  test('Avbruten Monte Carlo returnerar null', () => assert.strictEqual(stop, null));
  console.log('\n' + passed + ' beräkningstester godkända.');
})().catch(e => { console.error(e); process.exit(1); });
