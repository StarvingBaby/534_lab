(function (root) {
  'use strict';
  const number = month => Number(month.slice(0, 4)) * 12 + Number(month.slice(5, 7));
  function metrics(a, b) {
    return { bps: (b.acm_term_premium_pct - a.acm_term_premium_pct) * 100,
      gold: (b.gld_adjusted_close_usd / a.gld_adjusted_close_usd - 1) * 100 };
  }
  function discover(rows) {
    let best = null, count = 0;
    for (let i = 0; i + 6 < rows.length; i++) {
      if (!rows.slice(i, i + 6).every((a, k) => number(rows[i + k + 1].month) - number(a.month) === 1)) continue;
      count++;
      const score = Math.abs(metrics(rows[i], rows[i + 6]).bps);
      if (!best || score > best.score) best = { start: i, end: i + 6, score };
    }
    if (!best) throw Error('Insufficient aligned observations for a six-month finding.');
    return { ...best, count };
  }
  function validate(rows) {
    if (!Array.isArray(rows) || rows.length < 37) throw Error('Insufficient aligned observations: need at least 37 completed months.');
    const dateOK = s => typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s) &&
      Number.isFinite(Date.parse(s)) && new Date(s).toISOString().slice(0, 10) === s;
    rows.forEach((r, i) => {
      if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(r.month) || (i && r.month <= rows[i - 1].month) ||
          !['acm_term_premium_pct', 'treasury_10y_yield_pct', 'modified_duration_years', 'gld_adjusted_close_usd'].every(k => Number.isFinite(r[k])) ||
          r.gld_adjusted_close_usd <= 0 || r.modified_duration_years <= 0 ||
          !['acm_date', 'treasury_yield_date', 'gld_price_date'].every(k => dateOK(r[k]) && r[k].slice(0, 7) === r.month)) {
        throw Error('Invalid, duplicate, or misaligned bond observations.');
      }
    });
    return rows;
  }
  const api = { metrics, discover, validate, number };
  if (typeof module !== 'undefined') module.exports = api;
  else root.BondAnalysis = api;
})(typeof window === 'undefined' ? globalThis : window);
