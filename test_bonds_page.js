/* Exercise the actual page controller with a minimal offline DOM and test-only data. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const A = require('./bond_analysis.js');
class Element {
  constructor() { this.children = []; this.attrs = {}; this.listeners = {}; this.value = '0'; this.textContent = ''; this.disabled = true; }
  setAttribute(k, v) { this.attrs[k] = v; }
  append(child) { this.children.push(child); }
  replaceChildren(...children) { this.children = children; }
  querySelectorAll() { return this.children; }
  addEventListener(k, fn) { this.listeners[k] = fn; }
}
const html = fs.readFileSync('index.html', 'utf8');
const ids = [...html.matchAll(/id="([^"]+)"/g)].map(match => match[1]);
assert.equal(new Set(ids).size, ids.length, 'HTML IDs must be unique');
for (const match of html.matchAll(/(?:src|href)="([^"#]+)"/g)) {
  const asset = match[1].split(/[?#]/)[0];
  if (!asset.startsWith('http') && !asset.endsWith('.json')) assert.ok(fs.existsSync(asset), `Missing local asset: ${asset}`);
}
async function boot(payload, ok = true, refreshOK = true) {
  const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m => [m[1], new Element()]));
  elements.shock.value = '100';
  const presets = [3, 5, 10, 0].map(n => Object.assign(new Element(), {dataset: {years: String(n)}}));
  const document = {
    getElementById: id => elements[id], createElementNS: () => new Element(), createElement: () => new Element(),
    querySelectorAll: query => query === '[data-years]' ? presets : [...Object.values(elements), ...presets]
  };
  const context = {document, window: {BondAnalysis: A}, navigator: {clipboard: {writeText: async () => {}}},
    fetch: async url => url.includes('refresh_status') ? {ok: true, json: async () => ({ok: refreshOK, attempted_at: '2024-01-01', error: 'test failure'})} : {ok, status: 404, json: async () => payload}};
  vm.runInNewContext(fs.readFileSync('bonds.js', 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  return {elements, presets};
}
(async () => {
  const rows = Array.from({length: 61}, (_, i) => {
    const month = `${2020 + Math.floor(i / 12)}-${String(i % 12 + 1).padStart(2, '0')}`;
    return {month, acm_date: `${month}-28`, treasury_yield_date: `${month}-27`, gld_price_date: `${month}-27`,
      acm_term_premium_pct: i * i / 100, treasury_10y_yield_pct: 4, modified_duration_years: 8, gld_adjusted_close_usd: 200 + i};
  });
  const {elements: el, presets} = await boot({observations: rows, generated_at: '2025-02-01', sources: {gold: {fetched_at: '2025-02-01'}}});
  // No click: the initial finding, source dates and charts must already exist.
  assert.equal(el.start.value, 54);
  assert.equal(el.tpChange.textContent, '+684.00 bps');
  assert.equal(el.goldReturn.textContent, '+2.36%');
  assert.match(el.findingText.textContent, /2024-07-28 to 2025-01-28/);
  assert.match(el.findingText.textContent, /2024-07-27 to 2025-01-27/);
  assert.match(el.findingText.textContent, /not evidence of causation/);
  assert.equal(el.durationChart.children.length, 1);
  assert.equal(el.premiumChart.children.length, 1);
  assert.equal(el.goldChart.children.length, 1);
  assert.equal(el.bondValue.textContent, '$9,200');
  el.start.value = '0'; el.end.value = '20'; el.start.listeners.change();
  assert.equal(el.tpChange.textContent, '+400.00 bps');
  assert.equal(el.goldReturn.textContent, '+10.00%');
  assert.match(el.findingLabel.textContent, /YOUR SELECTED/);
  for (const preset of presets) { preset.listeners.click(); assert.ok(el.durationChart.children.length); }
  el.shock.value = '-100'; el.shock.listeners.input();
  assert.equal(el.bondValue.textContent, '$10,800');
  el.reset.listeners.click(); assert.equal(el.start.value, 54);
  const failed = await boot({}, false);
  assert.match(failed.elements.findingTitle.textContent, /Insufficient/);
  assert.match(failed.elements.status.textContent, /unavailable/);
  assert.equal(failed.elements.start.disabled, true);
  const cached = await boot({observations: rows}, true, false);
  assert.match(cached.elements.status.textContent, /Latest bond refresh failed/);
  const fallback = await boot({observations: rows, sources: {yield: {name: 'U.S. Treasury daily 10-year par yield', fallback_reason: 'test timeout'}}});
  assert.match(fallback.elements.readout.textContent, /U.S. Treasury daily 10-year par yield/);
  assert.doesNotMatch(fallback.elements.readout.textContent, /DGS10/);
  assert.match(fallback.elements.provenance.textContent, /official Treasury feed throughout/);
  console.log('Actual page controller passed: automatic finding, exact dates, charts, selectors, history presets, shocks, reset, unavailable and cached-error states.');
})().catch(error => { console.error(error); process.exitCode = 1; });
