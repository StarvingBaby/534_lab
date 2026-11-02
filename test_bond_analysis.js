// Synthetic offline test inputs; never shipped as historical data.
const assert = require('node:assert/strict');
const A = require('./bond_analysis.js');
const rows = Array.from({length: 61}, (_, i) => {
  const month = `${2020 + Math.floor(i / 12)}-${String(i % 12 + 1).padStart(2, '0')}`;
  return {month, acm_date: `${month}-28`, treasury_yield_date: `${month}-27`, gld_price_date: `${month}-27`,
    acm_term_premium_pct: i * i / 100, treasury_10y_yield_pct: 4,
    modified_duration_years: 8, gld_adjusted_close_usd: 200 + i};
});
assert.equal(A.validate(rows), rows);
assert.deepEqual(A.discover(rows), {start: 54, end: 60, score: 684, count: 55});
assert.ok(Math.abs(A.metrics(rows[0], rows[20]).gold - 10) < 1e-10);
assert.equal(A.metrics(rows[0], rows[20]).bps, 400);
assert.throws(() => A.validate([]), /Insufficient/);
for (const bad of [null, NaN, '4']) {
  assert.throws(() => A.validate(rows.map((r, i) => i ? r : {...r, acm_term_premium_pct: bad})), /Invalid/);
}
assert.throws(() => A.validate(rows.map((r, i) => i === 5 ? {...r, gld_price_date: '2020-02-31'} : r)), /Invalid/);
assert.throws(() => A.validate(rows.map((r, i) => i === 5 ? {...r, month: rows[4].month} : r)), /Invalid/);
assert.throws(() => A.discover(rows.filter((_, i) => i % 5 !== 0)), /Insufficient/);
console.log('Frontend data validation, discovery, dates, gaps, bps and GLD returns passed.');
