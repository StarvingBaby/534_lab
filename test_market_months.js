const assert = require('node:assert/strict');
const { completedPrices } = require('./market_months.js');
const rows = [
  {date: '2025-12-31', spy: 100, gld: 100},
  {date: '2026-01-30', spy: 101, gld: 102},
  {date: '2026-02-10', spy: 999, gld: 999}
];
assert.deepEqual(completedPrices(rows, '2026-02-11T02:00:00Z', new Date('2026-02-20T12:00:00Z')), rows.slice(0, 2));
// Opening an old export later must not turn its partial February into a full month.
assert.deepEqual(completedPrices(rows, '2026-02-11T02:00:00Z', new Date('2026-03-20T12:00:00Z')), rows.slice(0, 2));
// A future source timestamp must not allow the visitor's current month either.
assert.deepEqual(completedPrices(rows, '2026-03-11T02:00:00Z', new Date('2026-02-20T12:00:00Z')), rows.slice(0, 2));
assert.deepEqual(completedPrices(rows, '2026-02-28T23:59:59Z', new Date('2026-03-01T00:00:00Z')), rows.slice(0, 2));
assert.deepEqual(completedPrices(rows, '2026-03-01T00:00:00Z', new Date('2026-03-01T00:00:00Z')), rows);
assert.deepEqual(completedPrices([], undefined), []);
console.log('Completed-month filtering passed: current month, cached partial month, year boundary and UTC rollover.');
