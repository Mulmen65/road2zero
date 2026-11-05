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
    const andel = andelPerPerson(B, urval.temp, urval.sann, ar);
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
    return {tab, andel, stadBudget: total, slut, gt: globalGt(B, urval.temp, urval.sann),
            perPersonTotal: Object.values(andel).reduce((s, v) => s + v, 0),
            snitt: medel(r => r.perPerson), snittBudget: medel(r => r.andel), snittKat, snittAr: iSnitt.length ? [iSnitt[0].ar, iSnitt[iSnitt.length - 1].ar] : null,
            delposter: delposter(rows, urval), summa: p.reduce((s, r) => s + r.summa, 0),
            summaBudgetperiod: p.filter(r => r.ar >= BUDGETSTART).reduce((s, r) => s + r.summa, 0)};
  }
  /* Budgetutrymmet per person och år i snitt över analysperioden, för en temperatur och sannolikhet. */
  function budgetSnitt(rows, B, urval, temp, sann) {
    const ar = rows.map(r => r.year), andel = andelPerPerson(B, temp, sann, ar);
    const sel = rows.filter(r => r.year >= urval.period[0] && r.year <= urval.period[1] && r.bef > 0 && r.year >= BUDGETSTART);
    return sel.length ? sel.reduce((s, r) => s + (andel[r.year] || 0), 0) / sel.length : null;
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
    const u = {flik: 'oversikt', kat: KATEGORIER.slice(), grupper: ['befintlig', 'ny'], period: SNITT.slice(), temp: '1,5', sann: 50};
    if (s && typeof s === 'object') {
      if (FLIKAR.some(f => f[0] === s.flik)) u.flik = s.flik;
      if (Array.isArray(s.kat)) u.kat = KATEGORIER.filter(k => s.kat.includes(k));
      if (Array.isArray(s.grupper)) u.grupper = ['befintlig', 'ny'].filter(g => s.grupper.includes(g));
      if (Array.isArray(s.period) && s.period.length === 2) u.period = s.period.map(Number);
      if (s.temp) u.temp = String(s.temp);
      if (SANNOLIKHETER.includes(Number(s.sann))) u.sann = Number(s.sann);
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
      '</div><p class="small">Mobiliteten följer perspektivet i sidomenyn (' + esc(ctx.mobLabel) + '). Klimatbudgeten gäller från 2026; år före 2026 visas men får ingen budgetandel och räknas inte in i jämförelsen med budgeten.</p></article>';
  }

  function nyckeltal(ctx, res) {
    const kort = (l, v, f, huvud) => '<div class="card' + (huvud ? ' kpi-main' : '') + '"><div class="kpi-label">' + l + '</div><div class="kpi-value">' + v + '</div><div class="kpi-foot">' + f + '</div></div>';
    const ar = ctx.rows.map(r => r.year), sn = res.snittAr ? res.snittAr[0] + '–' + res.snittAr[1] : '–';
    const ggr = res.snitt != null && res.snittBudget ? res.snitt / res.snittBudget : null;
    return '<section class="r2zr-kpis">' +
      kort('Summa ' + ar[0] + '–' + ar[ar.length - 1], nf(res.summa / 1000, 0) + '<small> kt CO₂e</small>', 'De valda kategorierna, ' + nf(res.summaBudgetperiod / 1000) + ' kt från 2026', true) +
      kort('Snitt ' + sn, nf(res.snitt, 2) + '<small> t per person och år</small>', 'Budgetandel samma år: ' + nf(res.snittBudget, 2) + ' t') +
      kort('Mot budgeten', ggr == null ? '–' : nf(ggr, 1) + '<small> gånger</small>', st.temp + ' °C, ' + st.sann + ' % sannolikhet (Forster m.fl. 2026)') +
      kort('Stadens budget 2026–' + ar[ar.length - 1], nf(res.stadBudget / 1000, 1) + '<small> kt CO₂e</small>', 'Lika per person, faktiska invånare år för år') +
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
    if (st.flik === 'budget') innehall = parisKort() + div('motbudget') + div('personbudget') + div('persontid') + div('temperatur') + div('ackbudget') + '<p class="small">' + budgetText(B) + '</p>';
    if (st.flik === 'tabeller') innehall = tabeller(ctx, B, res);
    if (st.flik === 'kallor') innehall = kallor(B);
    return kontroller(ctx, B) + nyckeltal(ctx, res) + flikar + innehall;
  }

  function parisKort() {
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
      l.annotations = [{xref: 'paper', x: 0, y: res.stadBudget, text: 'Hela budgeten ' + nf(res.stadBudget) + ' t', showarrow: false, xanchor: 'left', yanchor: 'bottom', font: {color: INK2, size: 12}}];
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
    return '﻿' + ['ar', ...kat, 'summa', 'invanare', 't_per_person', 'budgetandel_per_person', 'stadens_budget_t', 'ackumulerat_fran_2026_t', 'budget_ackumulerad_t'].join(';') + '\n' +
      res.tab.map(r => [r.ar, ...kat.map(k => d(r[k])), d(r.summa), d(r.inv), d(r.perPerson), r.ar >= BUDGETSTART ? d(r.andel) : '', r.ar >= BUDGETSTART ? d(r.budget) : '', d(r.nettoKum), r.ar >= BUDGETSTART ? d(r.budgetKum) : ''].join(';')).join('\n');
  }
  function kallor(B) {
    return '<article class="card method-text"><h2>Så räknas resultatvyn</h2>' +
      '<p><b>Klimatkategorier.</b> Road2Zero-OP:s delar redovisas i samma kategorier som Road2Zero-Plan: <i>Byggnad</i> = nybyggnation A1–A5; <i>Energi</i> = energi i befintliga byggnader och i nya byggnader; <i>Förändrad markanvändning</i> = kolförlust när mark hårdgörs; <i>Mobilitet och transport</i> = befintlig stad och nya invånare, enligt perspektiv A eller B. Alla värden är t CO₂e per kalenderår 2024–2050 för hela kommunen.</p>' +
      '<div class="formula">b(t) = k · E(t) / P(t), &nbsp; E(t) = E₀ (1 − r)<sup>t−2026</sup>, &nbsp; r = E₀ / B</div>' +
      '<p>B är den globala kvarvarande koldioxidbudgeten från 2026 för vald temperaturgräns och sannolikhet (Forster m.fl., 2026), E₀ = ' + nf(B.e0, 1) + ' Gt CO₂ är de globala utsläppen 2025, k = ' + nf(B.k, 3) + ' räknar upp koldioxid till alla växthusgaser och P(t) är världsbefolkningen (UN DESA, 2024). Om B är mindre än ett års utsläpp används en linjär bana ned till noll.</p>' +
      '<div class="formula">B<sub>stad</sub> = Σ<sub>t = 2026…2050</sub> N(t) · b(t)</div>' +
      '<p>N(t) är stadens invånare år t, befintliga och nya. Budgeten är förbrukad det första år då stadens ackumulerade utsläpp från 2026 är större än B<sub>stad</sub>. Budgetandelen efter 2050 ingår inte, eftersom modellen slutar 2050.</p>' +
      '<p><b>Avgränsning.</b> Konsumtion (mat, varor, flygresor) och offentlig sektor ingår inte i Road2Zero-OP. Jämförelsen med budgeten visar därför bara en del av stadens klimatpåverkan. För en plan med konsumtionen inräknad: Road2Zero-Plan.</p>' +
      '<h2>Referenser</h2>' +
      '<div class="source"><strong>Forster, P.M. m.fl. (2026)</strong><p>Indicators of Global Climate Change 2025. <i>Earth System Science Data</i>, 18, s. 3889–3933.</p><a href="https://essd.copernicus.org/articles/18/3889/2026/" target="_blank" rel="noopener">essd.copernicus.org/articles/18/3889/2026</a></div>' +
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
      om();
    });
    const c = document.getElementById('r2zr-csv');
    if (c) c.onclick = () => { const b = new Blob([csv(ctx, B)], {type: 'text/csv'}), a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'road2zero_op_resultat_per_ar.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
    rita(ctx, B);
    // Plotly mäter bredden när diagrammet ritas; mät om när sidan har lagt sig (rullningslist, kort i rutnät)
    const omMat = () => document.querySelectorAll('.r2zr-fig.js-plotly-plot').forEach(el => { try { Plotly.Plots.resize(el); } catch (e) { /* diagrammet är borta */ } });
    if (typeof Plotly !== 'undefined') { requestAnimationFrame(omMat); setTimeout(omMat, 250); }
  }

  return {DELPOSTER, KATEGORIER, BUDGETSTART, bana, andelPerPerson, globalGt, perAr, berakna, budgetSnitt, html, bind, csv};
});
