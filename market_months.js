/* Completed-month guard for both market pages, including older cached exports. */
(function (root) {
  'use strict';
  function completedPrices(prices, fetchedAt, now = new Date()) {
    const currentMonth = now.toISOString().slice(0, 7);
    const fetched = new Date(fetchedAt);
    // A partial month in an older cache must not become a full month just
    // because the visitor opens that cache after the calendar rolls over.
    const sourceMonth = Number.isFinite(fetched.getTime()) ? fetched.toISOString().slice(0, 7) : currentMonth;
    const cutoff = sourceMonth < currentMonth ? sourceMonth : currentMonth;
    return prices.filter(p => typeof p.date === 'string' && p.date.slice(0, 7) < cutoff);
  }
  const api = { completedPrices };
  if (typeof module !== 'undefined') module.exports = api;
  else root.MarketMonths = api;
})(typeof window === 'undefined' ? globalThis : window);
