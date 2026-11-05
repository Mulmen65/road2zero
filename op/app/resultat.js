/* Road2Zero-OP – Resultat & klimatbudget.
   Samma resultatvy som i Road2Zero-Plan (summa per klimatkategori, från brutto till summa, trädkarta, över tid, per person,
   klimatbudget, tabeller och export, källor) för hela staden, med budgeten enligt Forster m.fl. (2026) för 1,5–2,0 °C,
   Parisavtalets temperaturmål. Diagrammen ritas med Plotly, med samma färger och layout som i Road2Zero-Plan.
   Beräkningsdelen (andel per person, stadens budget, urval) är ren JavaScript och testas i Node (op/tests/test_resultat.js).
   Underlaget (budgettabell, världsbefolkning, påslag och kategorifärger) läses in från road2zero/data när sidan byggs. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.R2ZResultat = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  /* OP:s komponenter som klimatkategorier och delposter (samma kategorier som i Road2Zero-Plan). */
  const DELPOSTER = [
    {c: 'bygg', kat: 'Byggnad', del: 'Nybyggnation (A1–A5)', grupp: 'ny'},
    {c: 'energi', kat: 'Energi', del: 'Befintliga byggnader', grupp: 'befintlig'},
    {c: 'nydrift', kat: 'Energi', del: 'Nya byggnader', grupp: 'ny'},
    {c: 'mark', kat: 'Förändrad markanvändning', del: 'Hårdgjord mark', grupp: 'ny'},
    {c: 'mobilitet', kat: 'Mobilitet och transport', del: 'Befintlig stad', grupp: 'befintlig'},
    {c: 'nymob', kat: 'Mobilitet och transport', del: 'Nya invånare', grupp: 'ny'},
  ];
  const KATEGORIER = ['Byggnad', 'Energi', 'Förändrad markanvändning', 'Mobilitet och transport'];
  const BUDGETSTART = 2026, SNITT = [2027, 2050];
  /* Budgetandelar: varje grupp av kategorier får en andel av budgeten per person, räknat mot hela fotavtrycket =
     hushåll + offentlig konsumtion + investeringar (SEI, 2026). Hushållens delar kommer från Konsumtionskompassen (data för
     2022): boende (energi, vatten, hyra) för Energi och transport utan flyg för Mobilitet och transport, eftersom Road2Zero-OP
     inte räknar flygresor. Nybyggnation hör till investeringarna, oavsett byggherre, liksom den mark som tas i anspråk; de får
     investeringarnas andel gånger nybyggnationens andel av investeringarna (standard 100 %, en övre gräns). */
  const BUDGETGRUPPER = [
    {id: 'boende', namn: 'Boende', kat: ['Energi'], text: 'boende (energi, vatten och hyra) i hushållens konsumtion'},
    {id: 'investeringar', namn: 'Investeringar', kat: ['Byggnad', 'Förändrad markanvändning'], text: 'investeringarna'},
    {id: 'transport', namn: 'Mobilitet och transport', kat: ['Mobilitet och transport'], text: 'transport utan flygresor i hushållens konsumtion'}];
  const TILLDELNINGAR = ['Malmö', 'Skåne', 'Sverige', 'egen', 'hela'];

  /* ---------- beräkning (samma som road2zero/modules/budget.py) ---------- */
  function linjar(punkter, x) {               // punkter: [[x, y], …] sorterade på x
    if (x <= punkter[0][0]) return punkter[0][1];
    for (let i = 1; i < punkter.length; i++) {
      const [x0, y0] = punkter[i - 1], [x1, y1] = punkter[i];
      if (x <= x1) return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
    }
    return punkter[punkter.length - 1][1];
  }
  function globalGt(B, temp, sann) {
    const r = B.budget.find(x => x.temperatur === String(temp) && Number(x.sannolikhet) === Number(sann));
    if (!r) throw new Error('Ingen budget för ' + temp + ' °C och ' + sann + ' %');
    return r.gt_co2;
  }
  function bana(Bgt, E0, n) {
    if (Bgt > E0) { const r = E0 / Bgt; return Array.from({length: n}, (_, i) => E0 * Math.pow(1 - r, i)); }
    const T = 2 * Bgt / E0;
    return Array.from({length: n}, (_, i) => { const a = Math.min(i, T), b = Math.min(i + 1, T); return E0 * ((b - a) - (b * b - a * a) / (2 * T)); });
  }
  /* Andel per person och år (t CO2e med andra växthusgaser) från 2026 för åren i ar. */
  function andelPerPerson(B, temp, sann, ar) {
    const pop = B.befolkning.map(r => [r.ar, r.miljarder]);
    const ab = ar.filter(y => y >= BUDGETSTART), n = ab.length ? Math.max(...ab) - BUDGETSTART + 1 : 0;
    const E = bana(globalGt(B, temp, sann), B.e0, n), ut = {};
    ab.forEach(y => { ut[y] = E[y - BUDGETSTART] * B.k / linjar(pop, y); });   // banan räknas från 2026, år för år
    return ut;
  }

  /* Nybyggnationens andel av investeringarnas utsläpp (0–1) ur nybyggnadsandel.csv: byggprodukternas andel av investeringarnas
     utsläpp × byggnadernas andel av bygginvesteringarna × nybyggnadens andel av byggandets utsläpp. Saknas underlaget: 1. */
  function nybyggnadsdelar(B) {
    const d = B.nybyggnad || {}, krav = ['investeringar_ghg', 'byggprodukter_ghg', 'bygginv_bostader', 'bygginv_lokaler', 'bygginv_anlaggningar', 'nybyggnad_ghg', 'ombyggnad_ghg'];
    if (!krav.every(k => Number.isFinite(d[k]) && d[k] > 0)) return null;
    const bygg = d.byggprodukter_ghg / d.investeringar_ghg, hus = (d.bygginv_bostader + d.bygginv_lokaler) / (d.bygginv_bostader + d.bygginv_lokaler + d.bygginv_anlaggningar),
          ny = d.nybyggnad_ghg / (d.nybyggnad_ghg + d.ombyggnad_ghg);
    return {bygg, hus, ny, n: bygg * hus * ny};
  }
  function standardByggandel(B) { const d = nybyggnadsdelar(B); return d ? d.n : 1; }
  /* Andelar per budgetgrupp (0–1) för ett område i budgetandelar.csv; byggandel = nybyggnationens andel av investeringarna. */
  function standardAndelar(B, omrade, byggandel = standardByggandel(B)) {
    const r = (B.andelar || []).find(x => x.omrade === omrade);
    if (!r) return null;
    const tot = r.hushall_kg + r.offentlig_kg + r.investeringar_kg;
    return {boende: r.boende_kg / tot, investeringar: r.investeringar_kg * byggandel / tot, transport: (r.transport_kg - r.flyg_kg) / tot,
            totalKg: tot, hushallAndel: r.hushall_kg / tot, rad: r};
  }
  /* Andelarna som gäller för urvalet: Konsumtionskompassen för ett område, egna andelar eller hela budgeten (1). */
  function andelar(B, urval) {
    const t = urval.tilldelning || 'hela';
    const hela = {hela: true}; for (const g of BUDGETGRUPPER) hela[g.id] = 1;
    if (t === 'hela') return hela;
    if (t === 'egen') { const o = {}; for (const g of BUDGETGRUPPER) o[g.id] = Number((urval.andelar || {})[g.id]) / 100 || 0; return o; }
    return standardAndelar(B, t, urval.byggandel == null ? standardByggandel(B) : urval.byggandel / 100) || hela;
  }
  /* Faktor på budgeten per person: summan av andelarna för de grupper som har minst en vald kategori. Hela budgeten = 1. */
  function budgetFaktor(B, urval) {
    const a = andelar(B, urval);
    if (a.hela) return 1;
    return BUDGETGRUPPER.filter(g => g.kat.some(k => urval.kat.includes(k))).reduce((s, g) => s + a[g.id], 0);
  }

  /* Urval: kategorier och om befintlig stad och exploateringen ingår. rows = MalmoOP.cityByYear(R). */
  function perAr(rows, urval) {
    return rows.map(r => {
      const o = {ar: r.year, inv: r.bef};
      for (const k of KATEGORIER) o[k] = 0;
      for (const d of DELPOSTER) if (urval.kat.includes(d.kat) && urval.grupper.includes(d.grupp)) o[d.kat] += r[d.c];
      o.summa = KATEGORIER.reduce((s, k) => s + o[k], 0);
      return o;
    });
  }
  function delposter(rows, urval) {
    return DELPOSTER.filter(d => urval.kat.includes(d.kat) && urval.grupper.includes(d.grupp))
      .map(d => ({...d, t: rows.reduce((s, r) => s + r[d.c], 0)}));
  }
  function berakna(rows, B, urval) {
    const p = perAr(rows, urval), ar = p.map(r => r.ar);
    const hel = andelPerPerson(B, urval.temp, urval.sann, ar), faktor = budgetFaktor(B, urval), a = andelar(B, urval);
    const andel = {}; for (const y of Object.keys(hel)) andel[y] = hel[y] * faktor;
    let kumB = 0, kum = 0, kumP = 0, kumBP = 0;
    const tab = p.map(r => {
      const bud = r.ar >= BUDGETSTART ? r.inv * (andel[r.ar] || 0) : 0;
      if (r.ar >= BUDGETSTART) { kumB += bud; kum += r.summa; }
      const pp = r.inv > 0 ? r.summa / r.inv : null;
      if (pp != null) { kumP += pp; kumBP += andel[r.ar] || 0; }
      return {...r, andel: andel[r.ar] || 0, budget: bud, budgetKum: kumB, nettoKum: r.ar >= BUDGETSTART ? kum : null,
              perPerson: pp, perPersonKum: kumP, budgetPersonKum: kumBP};
    });
    const total = kumB, slut = (tab.find(r => r.nettoKum != null && r.nettoKum > total) || {}).ar || null;
    const iSnitt = tab.filter(r => r.ar >= urval.period[0] && r.ar <= urval.period[1] && r.inv > 0);
    const medel = f => iSnitt.length ? iSnitt.reduce((s, r) => s + f(r), 0) / iSnitt.length : null;
    const snittKat = {}; for (const k of KATEGORIER) snittKat[k] = medel(r => r[k] / r.inv) || 0;
    const snittHel = iSnitt.length ? iSnitt.reduce((s, r) => s + (hel[r.ar] || 0), 0) / iSnitt.length : null;
    const grupper = BUDGETGRUPPER.filter(g => g.kat.some(k => urval.kat.includes(k))).map(g => {
      const utsl = g.kat.filter(k => urval.kat.includes(k)).reduce((s, k) => s + snittKat[k], 0), bud = snittHel == null ? null : snittHel * (a.hela ? 1 : a[g.id]);
      return {...g, andel: a.hela ? 1 : a[g.id], snitt: utsl, snittBudget: bud, ggr: bud ? utsl / bud : null};
    });
    return {tab, andel, faktor, andelar: a, grupper, snittHel, stadBudget: total, slut, gt: globalGt(B, urval.temp, urval.sann),
            perPersonTotal: Object.values(andel).reduce((s, v) => s + v, 0),
            snitt: medel(r => r.perPerson), snittBudget: medel(r => r.andel), snittKat, snittAr: iSnitt.length ? [iSnitt[0].ar, iSnitt[iSnitt.length - 1].ar] : null,
            delposter: delposter(rows, urval), summa: p.reduce((s, r) => s + r.summa, 0),
            summaBudgetperiod: p.filter(r => r.ar >= BUDGETSTART).reduce((s, r) => s + r.summa, 0)};
  }
  /* Budgetutrymmet per person och år i snitt över analysperioden, för en temperatur och sannolikhet. */
  function budgetSnitt(rows, B, urval, temp, sann) {
    const ar = rows.map(r => r.year), andel = andelPerPerson(B, temp, sann, ar), f = budgetFaktor(B, urval);
    const sel = rows.filter(r => r.year >= urval.period[0] && r.year <= urval.period[1] && r.bef > 0 && r.year >= BUDGETSTART);
    return sel.length ? f * sel.reduce((s, r) => s + (andel[r.year] || 0), 0) / sel.length : null;
  }

  /* ---------- gränssnitt (bara i webbläsaren) ---------- */
  const INK = '#15211d', INK2 = '#56635e', GRID = '#e3e9e6', SURF = '#fbfcfb', LINJE = '#c9d4cf';
  const PETROL = '#1f5a6e', MELLANBLA = '#5a86b8', BUDGET = '#2f6b3f', VARNING = '#a4442c';
  const SANNOLIKHETER = [10, 17, 33, 50, 67, 83, 90];
  const FLIKAR = [['oversikt', 'Översikt'], ['tid', 'Över tid'], ['person', 'Per person'], ['budget', 'Klimatbudget'], ['tabeller', 'Tabeller och export'], ['kallor', 'Källor och beräkning']];
  const nf = (x, d = 0) => x == null || !Number.isFinite(x) ? '–' : new Intl.NumberFormat('sv-SE', {maximumFractionDigits: d, minimumFractionDigits: d}).format(x);
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const rgba = (h, a) => 'rgba(' + parseInt(h.slice(1, 3), 16) + ',' + parseInt(h.slice(3, 5), 16) + ',' + parseInt(h.slice(5, 7), 16) + ',' + a + ')';
  const CONF = {displaylogo: false, responsive: true, toImageButtonOptions: {format: 'png', scale: 2}};
  const STORE = 'r2z-op-resultat';

  let st = null;
  function urvalStart() {
    let s = null; try { s = JSON.parse(localStorage.getItem(STORE) || 'null'); } catch (e) { s = null; }
    const u = {flik: 'oversikt', kat: KATEGORIER.slice(), grupper: ['befintlig', 'ny'], period: SNITT.slice(), temp: '1,5', sann: 50,
               tilldelning: 'Malmö', andelar: null, byggandel: null, v: 2};
    if (s && typeof s === 'object') {
      if (FLIKAR.some(f => f[0] === s.flik)) u.flik = s.flik;
      if (Array.isArray(s.kat)) u.kat = KATEGORIER.filter(k => s.kat.includes(k));
      if (Array.isArray(s.grupper)) u.grupper = ['befintlig', 'ny'].filter(g => s.grupper.includes(g));
      if (Array.isArray(s.period) && s.period.length === 2) u.period = s.period.map(Number);
      if (s.temp) u.temp = String(s.temp);
      if (SANNOLIKHETER.includes(Number(s.sann))) u.sann = Number(s.sann);
      if (TILLDELNINGAR.includes(s.tilldelning)) u.tilldelning = s.tilldelning;
      if (s.andelar && typeof s.andelar === 'object') { u.andelar = {}; for (const g of BUDGETGRUPPER) u.andelar[g.id] = Math.max(0, Math.min(100, Number(s.andelar[g.id]) || 0)); }
      // byggandel sparas från v 2 (0.12.1); i 0.12.0 var standardvärdet 100 % och sparades alltid, så det läses inte in
      if (s.v >= 2 && s.byggandel != null && Number.isFinite(Number(s.byggandel))) u.byggandel = Math.max(0, Math.min(100, Number(s.byggandel)));
    }
    return u;
  }
  function spara() { try { localStorage.setItem(STORE, JSON.stringify(st)); } catch (e) { /* lagring ej tillgänglig */ } }

  function layout(titel, undertitel, hojd, yt) {
    return {title: {text: '<b>' + titel + '</b>' + (undertitel ? '<br><span style="font-size:12px;color:' + INK2 + '">' + undertitel + '</span>' : ''), x: 0, xanchor: 'left', font: {size: 16, color: INK}},
      font: {family: 'Inter, system-ui, sans-serif', size: 13, color: INK}, height: hojd || 420, plot_bgcolor: SURF, paper_bgcolor: SURF,
      margin: {l: 10, r: 10, t: 72, b: 10}, legend: {orientation: 'h', yanchor: 'top', y: -0.2, x: 0, font: {size: 12}},
      hoverlabel: {bgcolor: 'white', bordercolor: LINJE, font: {size: 12, color: INK}}, separators: ', ',
      xaxis: {showgrid: false, linecolor: LINJE, tickcolor: LINJE, automargin: true},
      yaxis: {gridcolor: GRID, zerolinecolor: INK2, zerolinewidth: 1, title: {text: yt === undefined ? 't CO2e' : (yt || '')}, tickformat: ',.0f', automargin: true}};
  }

  function kontroller(ctx, B) {
    const temps = [...new Set(B.budget.map(r => r.temperatur))], ar = ctx.rows.map(r => r.year);
    const opt = (v, l, val) => '<option value="' + esc(v) + '"' + (String(v) === String(val) ? ' selected' : '') + '>' + esc(l) + '</option>';
    return '<article class="card r2zr-urval"><div class="r2zr-rad"><div><div class="r2zr-etikett">Klimatkategorier i diagram och tabeller</div><div class="r2zr-piller">' +
      KATEGORIER.map(k => '<button class="r2zr-pill' + (st.kat.includes(k) ? ' on' : '') + '" data-r2zr-kat="' + esc(k) + '"><i style="background:' + B.farg[k] + '"></i>' + esc(k) + '</button>').join('') +
      '</div></div><div><div class="r2zr-etikett">Ingår</div><div class="r2zr-piller">' +
      [['befintlig', 'Befintlig stad'], ['ny', 'Exploateringen 2030–2050']].map(([g, l]) => '<button class="r2zr-pill' + (st.grupper.includes(g) ? ' on' : '') + '" data-r2zr-grupp="' + g + '">' + l + '</button>').join('') +
      '</div></div></div><div class="r2zr-rad r2zr-val">' +
      '<label class="field">Analysperiod för snitt per person, från<select data-r2zr="p0">' + ar.map(y => opt(y, y, st.period[0])).join('') + '</select></label>' +
      '<label class="field">till<select data-r2zr="p1">' + ar.map(y => opt(y, y, st.period[1])).join('') + '</select></label>' +
      '<label class="field">Temperaturgräns<select data-r2zr="temp">' + temps.map(t => opt(t, t + ' °C', st.temp)).join('') + '</select></label>' +
      '<label class="field">Sannolikhet att hålla gränsen<select data-r2zr="sann">' + SANNOLIKHETER.map(p => opt(p, p + ' %', st.sann)).join('') + '</select></label>' +
      '</div>' + tilldelningRad(B) + '<p class="small">Mobiliteten följer perspektivet i sidomenyn (' + esc(ctx.mobLabel) + '). Klimatbudgeten gäller från 2026; år före 2026 visas men får ingen budgetandel och räknas inte in i jämförelsen med budgeten.</p></article>';
  }

  function byggandelVisad(B) { return st.byggandel == null ? Number((100 * standardByggandel(B)).toFixed(1)) : st.byggandel; }
  function byggandelText(B) {
    const d = nybyggnadsdelar(B), pct = x => nf(100 * x, 1);
    const std = d ? 'byggprodukternas andel av investeringarnas utsläpp ' + pct(d.bygg) + ' % (SCB, 2026) × byggnadernas andel av bygginvesteringarna ' + pct(d.hus) + ' % (Byggföretagen, 2025) × nybyggnadens andel av byggandets utsläpp ' + pct(d.ny) + ' % (Naturvårdsverket och Boverket, 2019)' : '';
    if (st.byggandel == null) return 'Nybyggnationen och marken får ' + pct(standardByggandel(B)) + ' % av investeringarnas andel' + (d ? ': ' + std : '');
    return 'Nybyggnationen och marken får ' + nf(st.byggandel, 1) + ' % av investeringarnas andel (eget värde' + (d ? '; standard ' + pct(d.n) + ' %' : '') + ')';
  }

  function tilldelningRad(B) {
    const opt = (v, l) => '<option value="' + esc(v) + '"' + (st.tilldelning === v ? ' selected' : '') + '>' + esc(l) + '</option>';
    const a = andelar(B, st), fakt = budgetFaktor(B, st), pct = x => nf(100 * x, 1);
    const val = TILLDELNINGAR.filter(t => t === 'egen' || t === 'hela' || standardAndelar(B, t)).map(t => t === 'egen' ? opt(t, 'Egna andelar') : t === 'hela' ? opt(t, 'Hela budgeten') : opt(t, t + ' ' + standardAndelar(B, t).rad.ar)).join('');
    const falt = BUDGETGRUPPER.map(g => '<label class="field">' + esc(g.namn) + ', % av budgeten<input class="input" type="number" min="0" max="100" step="0.1" data-r2zr-andel="' + g.id + '" value="' + (a.hela ? 100 : Number((100 * a[g.id]).toFixed(1))) + '"' + (a.hela ? ' disabled' : '') + '></label>').join('') +
      (st.tilldelning === 'egen' || a.hela ? '' : '<label class="field">Nybyggnationens andel av investeringarna, %<input class="input" type="number" min="0" max="100" step="0.1" data-r2zr-byggandel="1" value="' + byggandelVisad(B) + '"></label>');
    let text;
    if (a.hela) text = 'Hela budgeten per person jämförs med de valda kategorierna, som om de vore stadens enda utsläpp.';
    else {
      const sk = standardAndelar(B, st.tilldelning === 'egen' ? 'Malmö' : st.tilldelning);
      const vald = BUDGETGRUPPER.filter(g => g.kat.some(k => st.kat.includes(k)));
      text = 'Urvalet får <b>' + pct(fakt) + ' %</b> av budgeten per person: ' + vald.map(g => { const kat = g.kat.map(k => k.toLowerCase()).join(' och '); return esc(g.namn.toLowerCase()) + ' ' + pct(a[g.id]) + ' %' + (kat === g.namn.toLowerCase() ? '' : ' (' + kat + ')'); }).join(', ') + '. ' +
        (st.tilldelning === 'egen' ? 'Egna andelar.' : 'Andelarna är dagens utsläpp per person för boende (energi, vatten och hyra) och transport utan flyg i hushållens konsumtion enligt Konsumtionskompassen (' + esc(st.tilldelning) + ' ' + sk.rad.ar + ') och för investeringarna (SEI, 2026), delat med hela fotavtrycket per person: ' + nf(sk.totalKg / 1000, 2) + ' t, varav hushållen ' + nf(sk.rad.hushall_kg / 1000, 2) + ' t, offentlig konsumtion ' + nf(sk.rad.offentlig_kg / 1000, 2) + ' t och investeringar ' + nf(sk.rad.investeringar_kg / 1000, 2) + ' t. ' + byggandelText(B) + '.') +
        ' Resten av budgeten går till det som Road2Zero-OP inte räknar: mat, varor, flygresor, offentlig konsumtion och övriga investeringar.';
    }
    return '<div class="r2zr-rad r2zr-val"><label class="field">Budgettilldelning enligt Konsumtionskompassen<select data-r2zr="tilldelning">' + val + '</select></label>' + falt + '</div><p class="small">' + text + '</p>';
  }

  function nyckeltal(ctx, res) {
    const kort = (l, v, f, huvud) => '<div class="card' + (huvud ? ' kpi-main' : '') + '"><div class="kpi-label">' + l + '</div><div class="kpi-value">' + v + '</div><div class="kpi-foot">' + f + '</div></div>';
    const ar = ctx.rows.map(r => r.year), sn = res.snittAr ? res.snittAr[0] + '–' + res.snittAr[1] : '–';
    const ggr = res.snitt != null && res.snittBudget ? res.snitt / res.snittBudget : null;
    return '<section class="r2zr-kpis">' +
      kort('Summa ' + ar[0] + '–' + ar[ar.length - 1], nf(res.summa / 1000, 0) + '<small> kt CO₂e</small>', 'De valda kategorierna, ' + nf(res.summaBudgetperiod / 1000) + ' kt från 2026', true) +
      kort('Snitt ' + sn, nf(res.snitt, 2) + '<small> t per person och år</small>', 'Budgetandel samma år: ' + nf(res.snittBudget, 2) + ' t') +
      kort('Mot budgeten', ggr == null ? '–' : nf(ggr, 1) + '<small> gånger</small>', st.temp + ' °C, ' + st.sann + ' % sannolikhet (Forster m.fl. 2026)' + (res.andelar.hela ? ', hela budgeten' : ', ' + nf(100 * res.faktor, 1) + ' % av budgeten')) +
      kort('Stadens budget 2026–' + ar[ar.length - 1], nf(res.stadBudget / 1000, 1) + '<small> kt CO₂e</small>', 'Lika per person, faktiska invånare år för år' + (res.andelar.hela ? '' : ', urvalets andel')) +
      kort('Budgeten förbrukad', res.slut ? String(res.slut) : 'Inte före ' + ar[ar.length - 1], 'Första året de ackumulerade utsläppen från 2026 är större än budgeten') +
      '</section>';
  }

  function html(ctx, B) {
    if (!st) st = urvalStart();
    if (typeof Plotly === 'undefined') return '<div class="notice error">Diagrambiblioteket kunde inte läsas in.</div>';
    if (!st.kat.length || !st.grupper.length) return kontroller(ctx, B) + '<div class="notice">Välj minst en klimatkategori och om befintlig stad eller exploateringen ska ingå.</div>';
    const res = berakna(ctx.rows, B, st);
    const flikar = '<div class="toggle r2zr-flikar">' + FLIKAR.map(([id, l]) => '<button data-r2zr-flik="' + id + '" class="' + (st.flik === id ? 'active' : '') + '">' + l + '</button>').join('') + '</div>';
    const div = id => '<div class="card r2zr-fig" id="r2zr-' + id + '"></div>';
    let innehall = '';
    if (st.flik === 'oversikt') innehall = '<section class="grid2 grid-even">' + div('kategori') + div('vattenfall') + '</section>' + div('trad');
    if (st.flik === 'tid') innehall = div('perar') + div('kum');
    if (st.flik === 'person') innehall = div('personar') + div('personkum') + '<p class="small">Per person och år = urvalets utsläpp det året delat med stadens invånare samma år (befintliga och nya). Budgetandelen är andelen per person och år av den globala budgeten.</p>';
    if (st.flik === 'budget') innehall = parisKort() + div('motbudget') + div('personbudget') + (res.andelar.hela ? '' : div('gruppbudget')) + div('persontid') + div('temperatur') + div('ackbudget') + '<p class="small">' + budgetText(B) + '</p>';
    if (st.flik === 'tabeller') innehall = tabeller(ctx, B, res);
    if (st.flik === 'kallor') innehall = kallor(B);
    return kontroller(ctx, B) + nyckeltal(ctx, res) + flikar + innehall;
  }

  function parisKort() {
    return parisKortBas() + (st && st.tilldelning !== 'hela' ? '<article class="card r2zr-paris"><h2>En rättvis andel för det som räknas</h2><p>Budgeten per person ska räcka till allt en invånare orsakar: mat, varor, resor, boende, offentlig service och investeringar. Road2Zero-OP räknar bara nybyggnation, energi, mark och mobilitet utan flyg. Därför jämförs urvalet med <b>den del av budgeten som motsvarar dessa kategorier i dag</b>: boende och transport i hushållens konsumtion enligt Konsumtionskompassen och investeringarna för nybyggnationen, och inte med hela budgeten. Det visar hur långt ifrån Parisavtalet de här delarna är, om resten av konsumtionen ska få plats. Andelarna kan ändras under Budgettilldelning; principen följer WWF:s matbudget, där maten får en fast andel av budgeten.</p></article>' : '');
  }
  function parisKortBas() {
    return '<article class="card r2zr-paris"><h2>Parisavtalet och stadens andel av koldioxidbudgeten</h2><p>Parisavtalet (2015, artikel 2.1 a) innebär att den globala uppvärmningen ska hållas väl under 2 °C jämfört med förindustriell nivå, med ansträngningar att begränsa den till 1,5 °C. Den kvarvarande koldioxidbudgeten för varje temperaturgräns och sannolikhet kommer från Forster m.fl. (2026). Budgeten fördelas lika per person och år på världens befolkning och räknas upp för andra växthusgaser. Stadens budget är summan över stadens faktiska invånare år för år.</p><p class="small">Välj temperaturgräns och sannolikhet överst. Diagrammet <b>Budgetutrymme per person och år för alla temperaturgränser</b> visar hela spannet 1,5–2,0 °C på en gång.</p></article>';
  }
  function budgetText(B) {
    return 'Budgetutrymmet är den globala kvarvarande koldioxidbudgeten från 2026 (Forster m.fl. 2026) som en jämnt minskande bana från ' + nf(B.e0, 1) + ' Gt CO₂ år 2025, räknad upp med ' + nf(B.k, 3) + ' (56,8/43,2) för andra växthusgaser och delad lika per person med världsbefolkningen år för år (UN WPP 2024). Snittet tas över analysperiodens år, för både utsläppen och budgeten. Road2Zero-OP räknar energi i befintliga och nya byggnader, mobilitet, nybyggnation och förändrad markanvändning; konsumtion av mat, varor och flygresor ingår inte, så jämförelsen med budgeten är en undre gräns för stadens påverkan.';
  }

  /* ---------- diagram ---------- */
  function rita(ctx, B) {
    if (typeof Plotly === 'undefined' || !st || !st.kat.length || !st.grupper.length) return;
    const res = berakna(ctx.rows, B, st), F = B.farg, kat = st.kat, ar = res.tab.map(r => r.ar);
    const plot = (id, data, lay) => {
      const el = document.getElementById('r2zr-' + id); if (!el) return;
      el.style.height = (lay.height || 420) + 'px';       // fast höjd: Plotly fyller bredden och behåller höjden när den mäter om
      Plotly.newPlot(el, data, lay, CONF);
    };
    const und = ar[0] + '–' + ar[ar.length - 1] + ' · ' + urvalText();
    if (st.flik === 'oversikt') {
      const tot = kat.map(k => [k, res.tab.reduce((s, r) => s + r[k], 0)]).filter(x => Math.abs(x[1]) > 0).sort((a, b) => a[1] - b[1]);
      const pos = tot.filter(x => x[1] > 0).reduce((s, x) => s + x[1], 0);
      let l = layout('Summa per klimatkategori', und + ' · andel av bruttoutsläppen', 46 * tot.length + 150, null);
      l.xaxis = {...l.xaxis, gridcolor: GRID, showgrid: true, zerolinecolor: INK2, tickformat: ',.0f', title: {text: 't CO2e'}};
      l.yaxis = {...l.yaxis, gridcolor: 'rgba(0,0,0,0)', title: {text: ''}, tickformat: ''}; l.showlegend = false; l.margin = {l: 10, r: 110, t: 72, b: 10};
      plot('kategori', [{type: 'bar', orientation: 'h', y: tot.map(x => x[0]), x: tot.map(x => x[1]), marker: {color: tot.map(x => F[x[0]]), line: {color: SURF, width: 2}},
        text: tot.map(x => x[1] > 0 ? nf(x[1]) + ' t' + (pos ? ' · ' + nf(x[1] / pos * 100) + ' %' : '') : ''), textposition: 'outside', cliponaxis: false, textfont: {color: INK, size: 12},
        hovertemplate: '%{y}: %{x:,.0f} t CO2e<extra></extra>'}], l);
      const ord = KATEGORIER.filter(k => kat.includes(k)).map(k => [k, res.tab.reduce((s, r) => s + r[k], 0)]).filter(x => x[1]);
      const x = ord.map(o => o[0]).concat(['Summa']), y = ord.map(o => o[1]).concat([0]);
      l = layout('Från bruttoutsläpp till summa', 'Kategorierna läggs på varandra', 460); l.showlegend = false; l.xaxis = {...l.xaxis, tickangle: -30};
      plot('vattenfall', [{type: 'waterfall', x, y, measure: ord.map(() => 'relative').concat(['total']), text: ord.map(o => nf(o[1])).concat([nf(res.summa)]), textposition: 'outside',
        connector: {line: {color: GRID}}, increasing: {marker: {color: MELLANBLA}}, decreasing: {marker: {color: BUDGET}}, totals: {marker: {color: PETROL}}, cliponaxis: false,
        hovertemplate: '%{x}: %{y:,.0f} t<extra></extra>'}], l);
      const dp = res.delposter.filter(d => d.t > 0), kk = KATEGORIER.filter(k => dp.some(d => d.kat === k));
      l = layout('Vad utsläppen består av', 'Klimatkategorier och delposter · klicka på en ruta för att zooma', 520, null); l.margin = {l: 4, r: 4, t: 72, b: 4};
      plot('trad', [{type: 'treemap', ids: kk.concat(dp.map(d => d.kat + '/' + d.del)), labels: kk.concat(dp.map(d => d.del)), parents: kk.map(() => '').concat(dp.map(d => d.kat)),
        values: kk.map(k => dp.filter(d => d.kat === k).reduce((s, d) => s + d.t, 0)).concat(dp.map(d => d.t)), branchvalues: 'total',
        marker: {colors: kk.map(k => F[k]).concat(dp.map(d => rgba(F[d.kat], 0.72))), line: {color: SURF, width: 2}},
        texttemplate: '<b>%{label}</b><br>%{value:,.0f} t<br>%{percentRoot:.0%}', hovertemplate: '%{label}<br>%{value:,.0f} t CO2e · %{percentRoot:.1%} av allt<extra></extra>',
        tiling: {pad: 2}, pathbar: {visible: true}, root: {color: SURF}}], l);
    }
    if (st.flik === 'tid') {
      let l = layout('Utsläpp per år och klimatkategori', und + ' · linjen är summan', 480); l.barmode = 'relative'; l.bargap = 0.18; l.hovermode = 'x unified';
      plot('perar', kat.filter(k => res.tab.some(r => r[k])).map(k => ({type: 'bar', x: ar, y: res.tab.map(r => r[k]), name: k, marker: {color: F[k], line: {color: SURF, width: 1}}, hovertemplate: k + ': %{y:,.0f}<extra></extra>'}))
        .concat([{type: 'scatter', mode: 'lines', x: ar, y: res.tab.map(r => r.summa), name: 'Summa', line: {color: INK, width: 2}, hovertemplate: 'Summa: %{y:,.0f}<extra></extra>'}]), l);
      l = layout('Ackumulerade utsläpp', und + ' · summerat från ' + ar[0], 440); l.hovermode = 'x unified';
      const kumK = k => { let s = 0; return res.tab.map(r => (s += r[k])); };
      let s = 0;
      plot('kum', kat.filter(k => res.tab.some(r => r[k])).map(k => ({type: 'scatter', mode: 'lines', x: ar, y: kumK(k), name: k, stackgroup: 'pos', line: {color: F[k], width: 1}, fillcolor: rgba(F[k], 0.85), hovertemplate: k + ': %{y:,.0f} t<extra></extra>'}))
        .concat([{type: 'scatter', mode: 'lines', x: ar, y: res.tab.map(r => (s += r.summa)), name: 'Summa', line: {color: INK, width: 2, dash: 'dot'}, hovertemplate: 'Summa: %{y:,.0f} t<extra></extra>'}]), l);
    }
    const tp = res.tab.filter(r => r.inv > 0), arp = tp.map(r => r.ar);
    const periodform = (l, snitt) => {
      if (!res.snittAr) return;
      const [a0, a1] = res.snittAr;
      l.shapes = [{type: 'rect', xref: 'x', yref: 'paper', x0: a0 - 0.5, x1: a1 + 0.5, y0: 0, y1: 1, fillcolor: rgba(MELLANBLA, 0.07), line: {width: 0}},
        {type: 'line', x0: a0 - 0.5, x1: a1 + 0.5, y0: snitt, y1: snitt, line: {color: PETROL, width: 2, dash: 'dot'}}];
      l.annotations = [{x: a1 + 0.5, y: snitt, text: 'Snitt ' + a0 + '–' + a1 + ': ' + nf(snitt, 2) + ' t', showarrow: false, xanchor: 'right', yanchor: 'bottom', font: {color: PETROL, size: 12}}];
    };
    if (st.flik === 'person') {
      let l = layout('Per person och år', 't CO2e per invånare och år · skuggat: perioden för snittet', 460, 't CO2e per person och år');
      l.barmode = 'relative'; l.bargap = 0.18; l.hovermode = 'x unified'; l.yaxis.tickformat = ',.1f'; periodform(l, res.snitt);
      plot('personar', kat.filter(k => tp.some(r => r[k])).map(k => ({type: 'bar', x: arp, y: tp.map(r => r[k] / r.inv), name: k, marker: {color: F[k], line: {color: SURF, width: 1}}, hovertemplate: k + ': %{y:,.2f} t<extra></extra>'}))
        .concat([{type: 'scatter', mode: 'lines', x: arp, y: tp.map(r => r.perPerson), name: 'Summa per person', line: {color: INK, width: 2}, hovertemplate: 'Summa: %{y:,.2f} t per person<extra></extra>'},
          {type: 'scatter', mode: 'lines', x: arp.filter(y => y >= BUDGETSTART), y: tp.filter(r => r.ar >= BUDGETSTART).map(r => r.andel), name: 'Budgetandel per person och år', line: {color: BUDGET, width: 2, dash: 'dash'}, hovertemplate: 'Budgetandel: %{y:,.2f} t<extra></extra>'}]), l);
      l = layout('Ackumulerat per person', 'Summan av t CO2e per person och år, jämfört med budgetandelen per person', 420, 't CO2e per person'); l.hovermode = 'x unified'; l.yaxis.tickformat = ',.1f';
      plot('personkum', [{type: 'scatter', mode: 'lines', x: arp, y: tp.map(r => r.budgetPersonKum), name: 'Budgetandel per person, ackumulerad', fill: 'tozeroy', fillcolor: rgba(BUDGET, 0.10), line: {color: BUDGET, width: 2, dash: 'dash'}, hovertemplate: 'Budget t.o.m. %{x}: %{y:,.1f} t<extra></extra>'},
        {type: 'scatter', mode: 'lines', x: arp, y: tp.map(r => r.perPersonKum), name: 'Ackumulerat per person', line: {color: INK, width: 2.5}, hovertemplate: 'Ackumulerat t.o.m. %{x}: %{y:,.1f} t<extra></extra>'}], l);
    }
    if (st.flik === 'budget') {
      const tb = res.tab.filter(r => r.ar >= BUDGETSTART), arb = tb.map(r => r.ar);
      let l = layout('Vägen mot noll: ackumulerade utsläpp mot stadens klimatbudget', st.temp + ' °C och ' + st.sann + ' % sannolikhet · Forster m.fl. (2026), lika per person, faktiska invånare · från 2026', 460);
      l.hovermode = 'x unified'; l.shapes = [{type: 'line', xref: 'paper', x0: 0, x1: 1, y0: res.stadBudget, y1: res.stadBudget, line: {color: BUDGET, width: 1}}];
      l.annotations = [{xref: 'paper', x: 1, y: res.stadBudget, text: (res.faktor < 1 ? 'Urvalets budget ' : 'Hela budgeten ') + nf(res.stadBudget) + ' t', showarrow: false, xanchor: 'right', yanchor: 'bottom', font: {color: INK2, size: 12}}];
      if (res.slut) { l.shapes.push({type: 'line', yref: 'paper', x0: res.slut, x1: res.slut, y0: 0, y1: 1, line: {color: VARNING, width: 1.5, dash: 'dot'}}); l.annotations.push({x: res.slut, yref: 'paper', y: 1, text: 'Budgeten förbrukad ' + res.slut, showarrow: false, xanchor: 'left', xshift: 6, font: {color: VARNING, size: 12}}); }
      plot('motbudget', [{type: 'scatter', mode: 'lines', x: arb, y: tb.map(r => r.budgetKum), name: 'Stadens budget, ackumulerad', fill: 'tozeroy', fillcolor: rgba(BUDGET, 0.10), line: {color: BUDGET, width: 2, dash: 'dash'}, hovertemplate: 'Budget t.o.m. %{x}: %{y:,.0f} t<extra></extra>'},
        {type: 'scatter', mode: 'lines', x: arb, y: tb.map(r => r.nettoKum), name: 'Utsläpp, ackumulerade från 2026', line: {color: INK, width: 2.5}, hovertemplate: 'Utsläpp t.o.m. %{x}: %{y:,.0f} t<extra></extra>'}], l);
      // utsläpp per person mot budgetutrymmet (snitt)
      const bud = res.snittBudget, co2 = bud != null ? bud / B.k : null, ru = 'Utsläpp, urvalet', rb = 'Budgetutrymme';
      l = layout('Utsläpp per person mot budgetutrymmet', 'Snitt ' + (res.snittAr ? res.snittAr.join('–') : '') + ', t CO2e per person och år · budget ' + st.temp + ' °C, ' + st.sann + ' % sannolikhet, inklusive andra växthusgaser', 420, null);
      l.barmode = 'relative'; l.bargap = 0.35; l.xaxis = {...l.xaxis, gridcolor: GRID, showgrid: true, zerolinecolor: INK2, tickformat: ',.1f'}; l.yaxis = {...l.yaxis, autorange: 'reversed', tickformat: ''};
      l.margin = {l: 10, r: 80, t: 72, b: 110}; l.legend = {...l.legend, yref: 'container', y: 0.01, yanchor: 'bottom'};
      l.annotations = [{x: res.snitt, y: ru, text: '<b>' + nf(res.snitt, 2) + ' t</b>', showarrow: false, xanchor: 'left', xshift: 8, font: {color: INK, size: 13}},
        {x: bud, y: rb, text: '<b>' + nf(bud, 2) + ' t</b>', showarrow: false, xanchor: 'left', xshift: 8, font: {color: INK, size: 13}}];
      plot('personbudget', kat.filter(k => Math.abs(res.snittKat[k]) > 1e-9).map(k => ({type: 'bar', orientation: 'h', y: [ru], x: [res.snittKat[k]], name: k, marker: {color: F[k], line: {color: SURF, width: 2}}, hovertemplate: k + ': %{x:,.2f} t per person och år<extra></extra>'}))
        .concat(co2 == null ? [] : [{type: 'bar', orientation: 'h', y: [rb], x: [co2], name: 'Budget, koldioxid', marker: {color: rgba(BUDGET, 0.55), line: {color: BUDGET, width: 1.5}}, hovertemplate: 'Koldioxid: %{x:,.2f} t per person och år<extra></extra>'},
          {type: 'bar', orientation: 'h', y: [rb], x: [bud - co2], name: 'Budget, andra växthusgaser', marker: {color: rgba(BUDGET, 0.18), line: {color: BUDGET, width: 1.5}}, hovertemplate: 'Andra växthusgaser: %{x:,.2f} t per person och år<extra></extra>'}]), l);
      // per budgetgrupp: utsläpp per person mot gruppens andel av budgeten
      if (!res.andelar.hela && res.grupper.length) {
        l = layout('Varje del mot sin andel av budgeten', 'Snitt ' + (res.snittAr ? res.snittAr.join('–') : '') + ', t CO2e per person och år · andelarna under Budgettilldelning · ' + st.temp + ' °C, ' + st.sann + ' % sannolikhet', 120 + 90 * res.grupper.length, null);
        l.barmode = 'group'; l.bargap = 0.3; l.xaxis = {...l.xaxis, gridcolor: GRID, showgrid: true, zerolinecolor: INK2, tickformat: ',.2f'}; l.yaxis = {...l.yaxis, autorange: 'reversed', tickformat: ''};
        l.margin = {l: 10, r: 90, t: 72, b: 80}; l.legend = {...l.legend, yref: 'container', y: 0.01, yanchor: 'bottom'};
        const yn = res.grupper.map(g => g.namn + ' (' + nf(100 * g.andel, 1) + ' %)');
        l.annotations = res.grupper.map((g, i) => ({x: Math.max(g.snitt, g.snittBudget || 0), y: yn[i], text: g.ggr == null ? '' : '<b>' + nf(g.ggr, 1) + ' gånger</b>', showarrow: false, xanchor: 'left', xshift: 8, font: {color: g.ggr > 1 ? VARNING : INK, size: 13}}));
        plot('gruppbudget', [{type: 'bar', orientation: 'h', y: yn, x: res.grupper.map(g => g.snitt), name: 'Utsläpp', marker: {color: res.grupper.map(g => F[g.kat.find(k => st.kat.includes(k))] || INK)}, hovertemplate: '%{y}: %{x:,.2f} t per person och år<extra></extra>'},
          {type: 'bar', orientation: 'h', y: yn, x: res.grupper.map(g => g.snittBudget), name: 'Andel av budgeten', marker: {color: rgba(BUDGET, 0.30), line: {color: BUDGET, width: 1.5}}, hovertemplate: 'Budget: %{x:,.2f} t per person och år<extra></extra>'}], l);
      }
      // år för år
      l = layout('Utsläpp och budgetutrymme per person, år för år', 't CO2e per invånare och år · budget ' + st.temp + ' °C, ' + st.sann + ' % sannolikhet · skuggat: analysperioden', 520, 't CO2e per person och år');
      l.barmode = 'relative'; l.bargap = 0.18; l.hovermode = 'x unified'; l.yaxis.tickformat = ',.1f'; l.margin = {l: 10, r: 10, t: 72, b: 120}; l.legend = {...l.legend, yref: 'container', y: 0.01, yanchor: 'bottom'}; periodform(l, res.snitt);
      const tbp = tp.filter(r => r.ar >= BUDGETSTART), arbp = tbp.map(r => r.ar);
      plot('persontid', kat.filter(k => tp.some(r => r[k])).map(k => ({type: 'bar', x: arp, y: tp.map(r => r[k] / r.inv), name: k, marker: {color: F[k], line: {color: SURF, width: 1}}, hovertemplate: k + ': %{y:,.2f} t<extra></extra>'}))
        .concat([{type: 'scatter', mode: 'lines', x: arbp, y: tbp.map(r => r.andel / B.k), name: 'Budget, koldioxid', fill: 'tozeroy', fillcolor: rgba(BUDGET, 0.35), line: {color: BUDGET, width: 1}, hovertemplate: 'Budget, koldioxid: %{y:,.2f} t<extra></extra>'},
          {type: 'scatter', mode: 'lines', x: arbp, y: tbp.map(r => r.andel), name: 'Budget med andra växthusgaser', fill: 'tonexty', fillcolor: rgba(BUDGET, 0.15), line: {color: BUDGET, width: 2, dash: 'dash'}, hovertemplate: 'Budget med andra växthusgaser: %{y:,.2f} t<extra></extra>'},
          {type: 'scatter', mode: 'lines', x: arp, y: tp.map(r => r.perPerson), name: 'Summa per person', line: {color: INK, width: 2}, hovertemplate: 'Summa: %{y:,.2f} t per person<extra></extra>'}]), l);
      // alla temperaturgränser, med Parisavtalets mål markerade
      const temps = [...new Set(B.budget.map(r => r.temperatur))], tx = temps.map(t => Number(t.replace(',', '.')));
      const gron = n => Array.from({length: n}, (_, i) => { const a = [0xb9, 0xd6, 0xa8], b = [0x1d, 0x4a, 0x2a]; return '#' + a.map((v, j) => Math.round(v + (b[j] - v) * i / Math.max(1, n - 1)).toString(16).padStart(2, '0')).join(''); });
      l = layout('Budgetutrymme per person och år för alla temperaturgränser', 'Snitt ' + (res.snittAr ? res.snittAr.join('–') : '') + ' · en linje per sannolikhet · ringen är valet ovan · prickad linje: urvalets utsläpp · Parisavtalet: 1,5 °C och väl under 2 °C', 470, 't CO2e per person och år');
      l.xaxis = {...l.xaxis, tickvals: tx, ticktext: temps.map(t => t + ' °C'), title: {text: 'Temperaturgräns'}}; l.yaxis = {...l.yaxis, tickformat: ',.1f', rangemode: 'tozero'};
      l.legend = {...l.legend, title: {text: 'Sannolikhet '}, y: -0.25};
      l.shapes = [{type: 'line', xref: 'paper', x0: 0, x1: 1, y0: res.snitt, y1: res.snitt, line: {color: INK, width: 2, dash: 'dot'}},
        {type: 'rect', x0: 1.47, x1: 1.53, yref: 'paper', y0: 0, y1: 1, fillcolor: rgba(PETROL, 0.08), line: {width: 0}},
        {type: 'rect', x0: 1.97, x1: 2.03, yref: 'paper', y0: 0, y1: 1, fillcolor: rgba(PETROL, 0.08), line: {width: 0}}];
      l.annotations = [{xref: 'paper', x: 0, y: res.snitt, text: 'Urvalet: ' + nf(res.snitt, 2) + ' t', showarrow: false, xanchor: 'left', yanchor: 'bottom', font: {color: INK, size: 12}},
        {x: 1.5, yref: 'paper', y: 1.02, text: 'Parisavtalets 1,5 °C', showarrow: false, yanchor: 'bottom', font: {color: PETROL, size: 11}},
        {x: 2.0, yref: 'paper', y: 1.02, text: 'väl under 2 °C', showarrow: false, yanchor: 'bottom', xanchor: 'right', font: {color: PETROL, size: 11}}];
      const sp = gron(SANNOLIKHETER.length).map((farg, i) => { const p = SANNOLIKHETER[i], valt = p === Number(st.sann);
        return {type: 'scatter', mode: 'lines+markers', x: tx, y: temps.map(t => budgetSnitt(ctx.rows, B, st, t, p)), name: p + ' %', line: {color: farg, width: valt ? 3 : 1.8},
          marker: {size: valt ? 8 : 6, color: farg, line: {color: SURF, width: 1}}, hovertemplate: p + ' % sannolikhet, %{x:.1f} °C: %{y:,.2f} t per person och år<extra></extra>'}; });
      sp.push({type: 'scatter', mode: 'markers', x: [Number(st.temp.replace(',', '.'))], y: [res.snittBudget], name: 'Valt', showlegend: false, hoverinfo: 'skip', marker: {size: 15, color: 'rgba(0,0,0,0)', line: {color: INK, width: 2}}});
      plot('temperatur', sp, l);
      // stadens budget per temperaturgräns, i kt
      l = layout('Stadens budget 2026–' + ar[ar.length - 1] + ' per temperaturgräns', 'kt CO2e, sannolikhet ' + st.sann + ' % · stapeln längst till höger är stadens utsläpp i urvalet samma år', 400, 'kt CO2e');
      l.showlegend = false;
      const budKt = temps.map(t => { const u = {...st, temp: t}; return berakna(ctx.rows, B, u).stadBudget / 1000; });
      plot('ackbudget', [{type: 'bar', x: temps.map(t => t + ' °C').concat(['Utsläpp']), y: budKt.concat([res.summaBudgetperiod / 1000]),
        marker: {color: temps.map(t => t === st.temp ? BUDGET : rgba(BUDGET, 0.45)).concat([INK])}, text: budKt.concat([res.summaBudgetperiod / 1000]).map(v => nf(v, 0)), textposition: 'outside', cliponaxis: false,
        hovertemplate: '%{x}: %{y:,.0f} kt<extra></extra>'}], l);
    }
  }
  function urvalText() {
    const g = st.grupper.length === 2 ? 'hela staden' : st.grupper[0] === 'ny' ? 'exploateringen' : 'befintlig stad';
    return g + (st.kat.length === KATEGORIER.length ? '' : ' · ' + st.kat.length + ' av ' + KATEGORIER.length + ' kategorier');
  }

  /* ---------- tabeller och export ---------- */
  function tabeller(ctx, B, res) {
    const kat = KATEGORIER.filter(k => st.kat.includes(k)), tot = k => res.tab.reduce((s, r) => s + r[k], 0), brutto = kat.reduce((s, k) => s + Math.max(0, tot(k)), 0);
    const personar = res.tab.reduce((s, r) => s + r.inv, 0);
    let h = '<article class="card"><h2>Per klimatkategori</h2><div class="table-wrap"><table><thead><tr><th>Klimatkategori</th><th class="numeric">t CO₂e</th><th class="numeric">Andel</th><th class="numeric">t per person och år, hela perioden</th><th class="numeric">t per person och år, snitt ' + (res.snittAr || []).join('–') + '</th></tr></thead><tbody>' +
      kat.map(k => '<tr><td>' + esc(k) + '</td><td class="numeric">' + nf(tot(k)) + '</td><td class="numeric">' + nf(brutto ? tot(k) / brutto * 100 : null) + ' %</td><td class="numeric">' + nf(personar ? tot(k) / personar : null, 3) + '</td><td class="numeric">' + nf(res.snittKat[k], 3) + '</td></tr>').join('') +
      '<tr><td>Summa</td><td class="numeric">' + nf(res.summa) + '</td><td></td><td class="numeric">' + nf(personar ? res.summa / personar : null, 3) + '</td><td class="numeric">' + nf(res.snitt, 3) + '</td></tr>' +
      '<tr><td>Budgetandel per person</td><td></td><td></td><td></td><td class="numeric">' + nf(res.snittBudget, 3) + '</td></tr></tbody></table></div></article>';
    h += '<article class="card"><h2>Delposter</h2><div class="table-wrap"><table><thead><tr><th>Klimatkategori</th><th>Delpost</th><th class="numeric">t CO₂e</th></tr></thead><tbody>' +
      res.delposter.map(d => '<tr><td>' + esc(d.kat) + '</td><td>' + esc(d.del) + '</td><td class="numeric">' + nf(d.t) + '</td></tr>').join('') + '</tbody></table></div></article>';
    h += '<article class="card"><h2>Per år</h2><div class="table-wrap"><table><thead><tr><th>År</th>' + kat.map(k => '<th class="numeric">' + esc(k) + '</th>').join('') +
      '<th class="numeric">Summa</th><th class="numeric">Invånare</th><th class="numeric">t per person</th><th class="numeric">Budgetandel per person</th><th class="numeric">Stadens budget</th><th class="numeric">Ackumulerat från 2026</th><th class="numeric">Budget, ackumulerad</th></tr></thead><tbody>' +
      res.tab.map(r => '<tr><td>' + r.ar + '</td>' + kat.map(k => '<td class="numeric">' + nf(r[k]) + '</td>').join('') + '<td class="numeric">' + nf(r.summa) + '</td><td class="numeric">' + nf(r.inv) + '</td><td class="numeric">' + nf(r.perPerson, 2) +
        '</td><td class="numeric">' + (r.ar >= BUDGETSTART ? nf(r.andel, 3) : '–') + '</td><td class="numeric">' + (r.ar >= BUDGETSTART ? nf(r.budget) : '–') + '</td><td class="numeric">' + nf(r.nettoKum) + '</td><td class="numeric">' + (r.ar >= BUDGETSTART ? nf(r.budgetKum) : '–') + '</td></tr>').join('') +
      '</tbody></table></div><div class="button-row" style="margin-top:14px"><button class="secondary" id="r2zr-csv">Tabellen per år · CSV</button></div><p class="small">t CO₂e per år för urvalet (' + esc(urvalText()) + '), budget ' + esc(st.temp) + ' °C och ' + st.sann + ' % sannolikhet.</p></article>';
    return h;
  }
  function csv(ctx, B) {
    const res = berakna(ctx.rows, B, st), kat = KATEGORIER.filter(k => st.kat.includes(k)), d = x => x == null ? '' : String(Math.round(x * 1000) / 1000).replace('.', ',');
    return '﻿' + ['ar', ...kat, 'summa', 'invanare', 't_per_person', 'budgetandel_per_person (' + (res.andelar.hela ? 'hela budgeten' : nf(100 * res.faktor, 1) + ' % av budgeten') + ')', 'stadens_budget_t', 'ackumulerat_fran_2026_t', 'budget_ackumulerad_t'].join(';') + '\n' +
      res.tab.map(r => [r.ar, ...kat.map(k => d(r[k])), d(r.summa), d(r.inv), d(r.perPerson), r.ar >= BUDGETSTART ? d(r.andel) : '', r.ar >= BUDGETSTART ? d(r.budget) : '', d(r.nettoKum), r.ar >= BUDGETSTART ? d(r.budgetKum) : ''].join(';')).join('\n');
  }
  function kallor(B) {
    const d = nybyggnadsdelar(B), pct = x => nf(100 * x, 1);
    const nText = () => d ? ', som standard ' + pct(d.bygg) + ' % × ' + pct(d.hus) + ' % × ' + pct(d.ny) + ' % = ' + pct(d.n) + ' %: byggprodukternas (F41–F43) andel av de konsumtionsbaserade utsläppen från fasta bruttoinvesteringar 2023 (SCB, 2026), byggnadernas andel av bygginvesteringarna 2023 (Byggföretagen, 2025) och nybyggnadens andel av byggandets utsläpp 2015 enligt Boverkets miljöindikatorer (Naturvårdsverket och Boverket, 2019). Andelen kan ändras under Budgettilldelning' : ', som standard 100 %';
    return '<article class="card method-text"><h2>Så räknas resultatvyn</h2>' +
      '<p><b>Klimatkategorier.</b> Road2Zero-OP:s delar redovisas i samma kategorier som Road2Zero-Plan: <i>Byggnad</i> = nybyggnation A1–A5; <i>Energi</i> = energi i befintliga byggnader och i nya byggnader; <i>Förändrad markanvändning</i> = kolförlust när mark hårdgörs; <i>Mobilitet och transport</i> = befintlig stad och nya invånare, enligt perspektiv A eller B. Alla värden är t CO₂e per kalenderår 2024–2050 för hela kommunen.</p>' +
      '<div class="formula">b(t) = k · E(t) / P(t), &nbsp; E(t) = E₀ (1 − r)<sup>t−2026</sup>, &nbsp; r = E₀ / B</div>' +
      '<p>B är den globala kvarvarande koldioxidbudgeten från 2026 för vald temperaturgräns och sannolikhet (Forster m.fl., 2026), E₀ = ' + nf(B.e0, 1) + ' Gt CO₂ är de globala utsläppen 2025, k = ' + nf(B.k, 3) + ' räknar upp koldioxid till alla växthusgaser och P(t) är världsbefolkningen (UN DESA, 2024). Om B är mindre än ett års utsläpp används en linjär bana ned till noll.</p>' +
      '<div class="formula">B<sub>stad</sub> = Σ<sub>t = 2026…2050</sub> N(t) · b(t)</div>' +
      '<p>N(t) är stadens invånare år t, befintliga och nya. Budgeten är förbrukad det första år då stadens ackumulerade utsläpp från 2026 är större än B<sub>stad</sub>. Budgetandelen efter 2050 ingår inte, eftersom modellen slutar 2050.</p>' +
      '<div class="formula">b<sub>urval</sub>(t) = b(t) · Σ<sub>grupper i urvalet</sub> a<sub>g</sub>, &nbsp; a<sub>boende</sub> = U<sub>boende</sub> / F, &nbsp; a<sub>investeringar</sub> = U<sub>investeringar</sub> · n / F, &nbsp; a<sub>transport</sub> = (U<sub>transport</sub> − U<sub>flyg</sub>) / F, &nbsp; F = U<sub>hushåll</sub> + U<sub>offentlig</sub> + U<sub>investeringar</sub></div>' +
      '<div class="formula">n = (U<sub>byggprodukter</sub> / U<sub>investeringar</sub>)<sub>SCB 2023</sub> · ((bostäder + lokaler) / (bostäder + lokaler + anläggningar))<sub>bygginvesteringar 2023</sub> · (nybyggnad / (nybyggnad + ombyggnad))<sub>Boverket 2015</sub></div>' +
      '<p><b>Budgettilldelning.</b> U är utsläpp per person och år. Hushållens delar (boende: energi, vatten och hyra; transport; flygresor) kommer från Konsumtionskompassen för det valda området, data för 2022. Offentlig konsumtion (0,83 t) och investeringar (2,09 t) är riksvärden för 2023 (SEI, 2026). Gruppen boende täcker Energi, gruppen investeringar Byggnad och Förändrad markanvändning och gruppen transport Mobilitet och transport. Nybyggnation hör till investeringarna oavsett om byggherren är offentlig eller privat; n är nybyggnationens andel av investeringarnas utsläpp' + nText() + '. En grupp får hela sin andel när minst en av dess kategorier är vald. Andelarna hålls konstanta över tid. Med <i>Hela budgeten</i> är faktorn 1, som före version 0.12.0.</p>' +
      '<p><b>Avgränsning.</b> Konsumtion (mat, varor, flygresor) och offentlig sektor ingår inte i Road2Zero-OP. Jämförelsen med budgeten visar därför bara en del av stadens klimatpåverkan. För en plan med konsumtionen inräknad: Road2Zero-Plan.</p>' +
      '<h2>Referenser</h2>' +
      '<div class="source"><strong>Forster, P.M. m.fl. (2026)</strong><p>Indicators of Global Climate Change 2025. <i>Earth System Science Data</i>, 18, s. 3889–3933.</p><a href="https://essd.copernicus.org/articles/18/3889/2026/" target="_blank" rel="noopener">essd.copernicus.org/articles/18/3889/2026</a></div>' +
      '<div class="source"><strong>SEI (2026)</strong><p><i>Konsumtionskompassen 2.1</i>: hushållens klimatpåverkan per kommun, data för 2022 (webbverktyg), och <i>Konsumtionskompassen i siffror</i> (data för 2023).</p><a href="https://konsumtionskompassen.pages.dev/skane/malmo" target="_blank" rel="noopener">konsumtionskompassen.pages.dev/skane/malmo</a> · <a href="https://www.sei.org/wp-content/uploads/2026/05/konsumtionskompassen-siffror-sei2026-013.pdf" target="_blank" rel="noopener">sei.org (PDF)</a></div>' +
      '<div class="source"><strong>Byggföretagen (2025)</strong><p><i>Byggkonjunkturen</i>, april 2025. Tabell bygginvesteringar (nationalräkenskaperna).</p><a href="https://byggforetagen.se/app/uploads/2025/04/Byggkonjunkturen.pdf" target="_blank" rel="noopener">byggforetagen.se (PDF)</a></div>' +
      '<div class="source"><strong>Naturvårdsverket och Boverket (2019)</strong><p><i>Klimatscenarier för bygg- och fastighetssektorn: förslag på metod för bättre beslutsunderlag</i>, tabell 6.</p><a href="https://www.naturvardsverket.se/contentassets/8897c1c6a8a44c6e8461443625909c86/klimatscenarier-for-bygg-och-fastighetssektorn.pdf" target="_blank" rel="noopener">naturvardsverket.se (PDF)</a></div>' +
      '<div class="source"><strong>SCB (2026)</strong><p><i>Miljöpåverkan från konsumtion efter produktgrupp SPIN 2007, användning och ämne. År 2008–2024</i>. Miljöräkenskaper, tabell TAB7084.</p><a href="https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__MI__MI1301__MI1301F/MPSPIN/" target="_blank" rel="noopener">statistikdatabasen.scb.se</a></div>' +
      '<div class="source"><strong>Förenta nationerna (2015)</strong><p><i>Parisavtalet</i>. FN:s ramkonvention om klimatförändringar, artikel 2.1 a.</p><a href="https://unfccc.int/sites/default/files/english_paris_agreement.pdf" target="_blank" rel="noopener">unfccc.int/sites/default/files/english_paris_agreement.pdf</a></div>' +
      '<div class="source"><strong>United Nations, Department of Economic and Social Affairs (2024)</strong><p><i>World Population Prospects 2024</i>, medelvariant.</p><a href="https://population.un.org/wpp/" target="_blank" rel="noopener">population.un.org/wpp</a></div>' +
      '</article>';
  }

  function bind(ctx, B, rerender) {
    const om = () => { spara(); rerender(); };
    document.querySelectorAll('[data-r2zr-flik]').forEach(b => b.onclick = () => { st.flik = b.dataset.r2zrFlik; om(); });
    document.querySelectorAll('[data-r2zr-kat]').forEach(b => b.onclick = () => { const k = b.dataset.r2zrKat; st.kat = st.kat.includes(k) ? st.kat.filter(x => x !== k) : KATEGORIER.filter(x => x === k || st.kat.includes(x)); om(); });
    document.querySelectorAll('[data-r2zr-grupp]').forEach(b => b.onclick = () => { const g = b.dataset.r2zrGrupp; st.grupper = st.grupper.includes(g) ? st.grupper.filter(x => x !== g) : ['befintlig', 'ny'].filter(x => x === g || st.grupper.includes(x)); om(); });
    document.querySelectorAll('[data-r2zr]').forEach(el => el.onchange = () => {
      const k = el.dataset.r2zr, v = el.value;
      if (k === 'p0') st.period = [Number(v), Math.max(Number(v), st.period[1])];
      if (k === 'p1') st.period = [Math.min(st.period[0], Number(v)), Number(v)];
      if (k === 'temp') st.temp = v;
      if (k === 'sann') st.sann = Number(v);
      if (k === 'tilldelning') { if (v === 'egen' && !st.andelar) { const a = andelar(B, {...st, tilldelning: st.tilldelning === 'hela' || st.tilldelning === 'egen' ? 'Malmö' : st.tilldelning}); st.andelar = {}; for (const g of BUDGETGRUPPER) st.andelar[g.id] = +(100 * (a[g.id] || 0)).toFixed(1); } st.tilldelning = v; }
      om();
    });
    document.querySelectorAll('[data-r2zr-andel]').forEach(el => el.onchange = () => {
      const a = andelar(B, st), cur = {}; for (const g of BUDGETGRUPPER) cur[g.id] = +(100 * (a[g.id] || 0)).toFixed(1);
      cur[el.dataset.r2zrAndel] = Math.max(0, Math.min(100, Number(el.value) || 0));
      st.andelar = cur; st.tilldelning = 'egen'; om();
    });
    document.querySelectorAll('[data-r2zr-byggandel]').forEach(el => el.onchange = () => { st.byggandel = el.value === '' ? null : Math.max(0, Math.min(100, Number(el.value) || 0)); om(); });
    const c = document.getElementById('r2zr-csv');
    if (c) c.onclick = () => { const b = new Blob([csv(ctx, B)], {type: 'text/csv'}), a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'road2zero_op_resultat_per_ar.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
    rita(ctx, B);
    // Plotly mäter bredden när diagrammet ritas; mät om när sidan har lagt sig (rullningslist, kort i rutnät)
    const omMat = () => document.querySelectorAll('.r2zr-fig.js-plotly-plot').forEach(el => { try { Plotly.Plots.resize(el); } catch (e) { /* diagrammet är borta */ } });
    if (typeof Plotly !== 'undefined') { requestAnimationFrame(omMat); setTimeout(omMat, 250); }
  }

  return {DELPOSTER, KATEGORIER, BUDGETSTART, BUDGETGRUPPER, TILLDELNINGAR, bana, andelPerPerson, globalGt, nybyggnadsdelar, standardByggandel, standardAndelar, andelar, budgetFaktor, perAr, berakna, budgetSnitt, html, bind, csv};
});
