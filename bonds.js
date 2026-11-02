/* Same-origin data only; charts use native SVG, without a CDN dependency. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id), A = window.BondAnalysis;
  let rows = [], visible = [], discovered, charts = [], years = 0;
  const signed = (v, decimals = 2) => `${v > 0 ? '+' : ''}${v.toFixed(decimals)}`;
  const fixed = (v, n = 2) => v.toFixed(n);
  const selected = () => [Number($('start').value), Number($('end').value)];
  const NS = 'http://www.w3.org/2000/svg';
  function element(tag, attrs, text) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function inspect(index) {
    const r = visible[index];
    if (!r) return;
    $('inspect').value = index;
    const base = rows[selected()[0]].gld_adjusted_close_usd;
    $('readout').textContent = `${r.month} | Duration ${fixed(r.modified_duration_years, 3)} years | ACM ${fixed(r.acm_term_premium_pct, 3)}% (${r.acm_date}) | DGS10 ${fixed(r.treasury_10y_yield_pct)}% (${r.treasury_yield_date}) | GLD $${fixed(r.gld_adjusted_close_usd)} · index ${fixed(r.gld_adjusted_close_usd / base * 100)} (${r.gld_price_date})`;
    charts.forEach(({ line, x }) => { line.setAttribute('x1', x(index)); line.setAttribute('x2', x(index)); });
  }
  function draw(container, key, color, startMonth, endMonth, base = 1) {
    const W = 960, H = 190, L = 60, R = 20, T = 12, B = 30;
    const svg = element('svg', { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: 'none', 'aria-hidden': 'true' });
    const values = visible.map(r => r[key] / base);
    const low = Math.min(...values), high = Math.max(...values), pad = (high - low || 1) * .15;
    const min = low - pad, max = high + pad;
    // Calendar spacing retains gaps if a source month is missing.
    const first = A.number(visible[0].month), last = A.number(visible.at(-1).month);
    const x = i => L + (A.number(visible[i].month) - first) / (last - first) * (W - L - R);
    const y = v => T + (max - v) / (max - min) * (H - T - B);
    const si = visible.findIndex(r => r.month === startMonth), ei = visible.findIndex(r => r.month === endMonth);
    if (si >= 0 && ei >= 0) svg.append(element('rect', { x: x(si), y: T, width: x(ei) - x(si), height: H - T - B, fill: '#e2bf7819' }));
    for (let k = 0; k <= 3; k++) {
      const v = min + (max - min) * k / 3;
      svg.append(element('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: '#344039' }));
      svg.append(element('text', { x: L - 9, y: y(v) + 4, fill: '#acb8af', 'text-anchor': 'end', 'font-size': 11 }, fixed(v, 2)));
    }
    let path = '';
    visible.forEach((r, i) => {
      path += `${i === 0 || A.number(r.month) - A.number(visible[i - 1].month) > 1 ? 'M' : 'L'}${x(i)},${y(values[i])} `;
    });
    svg.append(element('path', { d: path, fill: 'none', stroke: color, 'stroke-width': 2.5, 'vector-effect': 'non-scaling-stroke' }));
    [...new Set([0, Math.floor((visible.length - 1) / 3), Math.floor((visible.length - 1) * 2 / 3), visible.length - 1])].forEach(i => {
      svg.append(element('text', { x: x(i), y: H - 5, fill: '#acb8af', 'text-anchor': 'middle', 'font-size': 11 }, visible[i].month));
    });
    [si, ei].filter(i => i >= 0).forEach(i => svg.append(element('circle', { cx: x(i), cy: y(values[i]), r: 4, fill: color })));
    const line = element('line', { x1: L, x2: L, y1: T, y2: H - B, stroke: '#eee8d9', 'stroke-dasharray': '3 4', opacity: .6 });
    svg.append(line);
    const point = event => {
      const rect = svg.getBoundingClientRect();
      const at = first + (((event.clientX - rect.left) / rect.width * W - L) / (W - L - R)) * (last - first);
      let nearest = 0;
      visible.forEach((r, i) => { if (Math.abs(A.number(r.month) - at) < Math.abs(A.number(visible[nearest].month) - at)) nearest = i; });
      inspect(nearest);
    };
    svg.addEventListener('pointermove', point);
    svg.addEventListener('pointerdown', point);
    $(container).replaceChildren(svg);
    charts.push({ line, x });
  }
  function shock() {
    const r = rows[selected()[1]], bps = Number($('shock').value);
    if (!r) return;
    const change = -r.modified_duration_years * bps / 100;
    $('shockLabel').textContent = `${signed(bps, 0)} bps`;
    $('bondValue').textContent = (10000 * (1 + change / 100)).toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
    $('shockResult').textContent = `${signed(change)}% estimated price change · ${fixed(r.modified_duration_years, 3)} years duration · ${r.treasury_yield_date}`;
  }
  function render() {
    const [i, j] = selected();
    if (i >= j) { $('windowError').textContent = 'Select an end month after the start month. The previous valid finding remains below.'; return; }
    $('windowError').textContent = '';
    const a = rows[i], b = rows[j], m = A.metrics(a, b), initial = i === discovered.start && j === discovered.end;
    $('findingLabel').textContent = initial ? 'THE DISCOVERED HISTORICAL WINDOW' : 'YOUR SELECTED HISTORICAL WINDOW';
    $('windowDates').textContent = `ACM ${a.acm_date} → ${b.acm_date} · GLD ${a.gld_price_date} → ${b.gld_price_date}`;
    $('tpChange').textContent = `${signed(m.bps)} bps`;
    $('goldReturn').textContent = `${signed(m.gold)}%`;
    $('durationChange').textContent = `${fixed(a.modified_duration_years)} → ${fixed(b.modified_duration_years)} yr`;
    const verb = n => n > 0 ? 'rose' : n < 0 ? 'fell' : 'was unchanged';
    $('findingTitle').textContent = `Term premium ${verb(m.bps)}; GLD ${verb(m.gold)}.`;
    $('findingText').textContent = `From ${a.acm_date} to ${b.acm_date}, the NY Fed’s 10-year ACM term-premium estimate changed by ${signed(m.bps)} basis points (from ${fixed(a.acm_term_premium_pct, 3)}% to ${fixed(b.acm_term_premium_pct, 3)}%). Over the corresponding month-end GLD pricing dates, ${a.gld_price_date} to ${b.gld_price_date}, the GLD ETF returned ${signed(m.gold)}% using adjusted closes of $${fixed(a.gld_adjusted_close_usd)} and $${fixed(b.gld_adjusted_close_usd)}. The fresh 10-year par-bond duration proxy changed from ${fixed(a.modified_duration_years, 3)} to ${fixed(b.modified_duration_years, 3)} years, using yields observed on ${a.treasury_yield_date} and ${b.treasury_yield_date}. This is an observed association within this window, not evidence of causation or a reliable hedge.`;
    $('selectionNote').textContent = initial ? `Automatically selected: the largest absolute ACM change among ${discovered.count} consecutive six-calendar-month windows in the available aligned history. GLD returns do not influence selection. A retrospective extreme is illustrative and may not represent typical behavior.` : 'User-selected endpoints. Values are recomputed from the same aligned monthly observations; GLD prices and bond observations can have different dates within a month.';
    const endNumber = A.number(rows.at(-1).month), cutoff = years ? endNumber - years * 12 : -Infinity;
    visible = rows.filter(r => A.number(r.month) >= Math.min(cutoff, A.number(a.month)));
    charts = [];
    draw('durationChart', 'modified_duration_years', '#83c8b6', a.month, b.month);
    draw('premiumChart', 'acm_term_premium_pct', '#b9aae5', a.month, b.month);
    draw('goldChart', 'gld_adjusted_close_usd', '#e2bf78', a.month, b.month, a.gld_adjusted_close_usd / 100);
    $('inspect').max = visible.length - 1;
    $('historyRange').textContent = `Chart history: ${visible[0].month} to ${visible.at(-1).month} · ${visible.length} aligned observations${years ? ` · ${years}Y view expands to include the selected window` : ''}. Shading marks the selected window. Gaps indicate unavailable months.`;
    $('start').querySelectorAll('option').forEach(o => o.disabled = Number(o.value) >= j);
    $('end').querySelectorAll('option').forEach(o => o.disabled = Number(o.value) <= i);
    inspect(visible.findIndex(r => r.month === b.month));
    shock();
  }
  async function load() {
    try {
      const response = await fetch('./bond_data.json', { cache: 'no-store' });
      if (!response.ok) throw Error(`Verified bond data unavailable (HTTP ${response.status}). Run the existing GitHub Actions refresh to download official ACM and DGS10 data.`);
      const data = await response.json();
      rows = A.validate(data.observations);
      discovered = A.discover(rows);
      for (const id of ['start', 'end']) rows.forEach((r, i) => {
        const option = document.createElement('option'); option.value = i; option.textContent = `${r.month} · ACM ${r.acm_date.slice(8)}`; $(id).append(option);
      });
      $('start').value = discovered.start; $('end').value = discovered.end;
      document.querySelectorAll('button,select,input').forEach(el => el.disabled = false);
      $('dataStamp').textContent = `Range ${rows[0].month}–${rows.at(-1).month} · Data through: ${rows.at(-1).acm_date} · Retrieved ${(data.generated_at || 'unknown').slice(0, 10)}`;
      $('provenance').textContent = `Bond retrieval: ${data.generated_at || 'unknown'}. GLD retrieval: ${data.sources?.gold?.fetched_at || 'unknown'}. Latest ACM: ${rows.at(-1).acm_date}; DGS10: ${rows.at(-1).treasury_yield_date}; GLD: ${rows.at(-1).gld_price_date}. Ingestion validates workbook sheet and column names before publication.`;
      const age = Date.now() - Date.parse(rows.at(-1).acm_date);
      $('status').textContent = age > 65 * 86400000 ? 'Stale data: latest aligned observation is more than 65 days old. The finding uses the dated historical cache.' : '';
      render();
      try {
        const refresh = await fetch('./bond_refresh_status.json', { cache: 'no-store' });
        if (refresh.ok) {
          const state = await refresh.json();
          if (!state.ok) $('status').textContent = `Latest bond refresh failed (${(state.attempted_at || '').slice(0, 10)}). Showing last verified data through ${rows.at(-1).acm_date}. ${state.error || ''}`;
        }
      } catch (_) { /* The dated artifact remains usable if the optional status request fails. */ }
    } catch (error) {
      $('status').textContent = error.message;
      $('dataStamp').textContent = 'No verified aligned dataset available';
      $('findingTitle').textContent = 'Insufficient aligned observations';
      $('findingText').textContent = 'No historical claim can be computed until the official bond sources and adjusted GLD prices are available. No estimated or synthetic market values are substituted.';
    }
  }
  ['start', 'end'].forEach(id => $(id).addEventListener('change', render));
  $('shock').addEventListener('input', shock);
  $('inspect').addEventListener('input', () => inspect(Number($('inspect').value)));
  $('reset').addEventListener('click', () => { $('start').value = discovered.start; $('end').value = discovered.end; render(); });
  document.querySelectorAll('[data-years]').forEach(button => button.addEventListener('click', () => {
    years = Number(button.dataset.years);
    document.querySelectorAll('[data-years]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    render();
  }));
  $('copy').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('findingText').textContent); $('copy').textContent = 'Copied ✓'; }
    catch (_) { $('copy').textContent = 'Select the finding text to copy'; }
  });
  load();
})();
