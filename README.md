# Gold vs. Stocks — The Safe Haven Experiment

## Bond–Gold Puzzle / assignment entry point

Open [`bonds.html`](bonds.html) for **The Safe Haven Paradox**. It charts both the
modified-duration proxy and official 10-year ACM term premium across the available
multi-year history, alongside a GLD adjusted-price index. On initial load it
automatically selects the **largest absolute six-calendar-month ACM change** among
consecutive aligned observations (earliest tie). GLD returns do not influence that
selection. Exact source endpoint dates, the premium change in bps, GLD return in
percent, and a descriptive conclusion appear without interaction. Start/end
selectors let visitors recompute the finding; the shaded window and all three
charts follow that selection. Chart-history presets retain the selected window.

The existing GitHub Pages workflow is retained. Its only additions are the bond
refresh command and inclusion of the two bond JSON artifacts in the data commit;
push/manual/weekday triggers and deployment steps are unchanged. No second hosting
service or deployment workflow is needed.

```bash
pip install -r requirements.txt
python fetch_data.py
python fetch_bond_data.py
python -m unittest -v test_bonds
node test_bond_analysis.js
node test_bonds_page.js
python -m http.server 8000
```

Visit `http://localhost:8000/bonds.html`. For Actions, run the existing **Refresh
market data & deploy** workflow; it refreshes market prices before bond alignment.

### Bond data contract and source validation

`bond_data.json` is generated, never populated with example market values. It has
`schema_version`, `generated_at` (UTC), `last_observation_date`, `frequency`,
`sources`, `definitions`, `assumptions`, `selection_rule`, `default_window`, and
`observations`. Each observation contains `month`, `acm_date`,
`acm_term_premium_pct`, `treasury_yield_date`, `treasury_10y_yield_pct`,
`modified_duration_years`, `gld_price_date`, and `gld_adjusted_close_usd`.

- NY Fed: [ACM source page](https://www.newyorkfed.org/research/data_indicators/term-premia-tabs),
  [official XLS workbook](https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls).
  Parser requires sheet **ACM Monthly**, columns **DATE** and **ACMTP10**, and rejects
  duplicate months. ACM is an estimated, revisable annualized percentage series.
- FRED: [DGS10 definition](https://fred.stlouisfed.org/series/DGS10),
  [CSV export](https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2004-01-01).
  Parser requires **DGS10** and **observation_date** (or legacy **DATE**); blank/dot
  observations are omitted. DGS10 is a daily observed yield in percent, not duration.
- GLD: existing `data.json` adjusted prices from Yahoo Finance/yfinance; no changes
  to the SPY/GLD analysis or return calculations.

**Verification status:** local access to the official downloads was denied during
implementation. The workbook mapping and live CSV format have therefore **not yet
been verified against a downloaded source in this checkout**. The refresh validates
these contracts at runtime and fails explicitly if either source differs. Until a
real refresh succeeds, no `bond_data.json` or historical claim is supplied. The first
successful Actions refresh and public-page review remain required for acceptance.

Only completed calendar months common to all three sources are retained. Last
available observations are used without filling missing months; actual source
dates remain visible because they can differ within a month. The existing roughly
six-year GLD history bounds the shared history. Current partial months are excluded.

Duration models a fresh 10-year par Treasury each month: face 100, 20 semiannual
cash flows, annual coupon equal to DGS10 / 100. Discount at `1 + y/2`, compute
time-weighted present values in years, then divide Macaulay duration by `1 + y/2`.
The maturity resets each month; this does not track an aging CUSIP. A shock uses
`ΔP/P ≈ -modified_duration × shock_bps / 10000`, excluding convexity.
The GLD holding-period return is `(end/start - 1) * 100`; the premium change in bps
is `(end_pct - start_pct) * 100`. These retrospective observations imply neither
causality nor reliable hedging; choosing an extreme window is disclosed explicitly.

On refresh failure, the previous verified JSON remains untouched and
`bond_refresh_status.json` records the failed attempt. With no valid cache the
refresh exits unsuccessfully. The page reports missing/invalid data, failed
refreshes, or observations over 65 days old; it never supplies synthetic values.
Offline test fixtures are restricted to test files.

A gold-themed, animated, one-page financial experiment comparing SPY and GLD through OLS, investment growth, volatility, Sharpe ratio, maximum drawdown, and diversification. No custom server and no API key.

## Publishing to GitHub Pages

1. Put **all** files from this folder in the root of a **public** GitHub repository (including the hidden `.github/workflows/update.yml` directory). Use the `main` branch.
2. In **Settings → Pages → Build and deployment**, select **GitHub Actions**.
3. In **Actions**, run **Refresh market data & deploy** using **Run workflow** (or push to `main`). The workflow fetches adjusted market data, commits `data.json`, and deploys the site.
4. Open the URL shown on **Settings → Pages** or in the successful deployment job.

If the first Yahoo Finance fetch fails, rerun the workflow later. If a previous `data.json` exists, the update job will keep it on transient failures. The page never substitutes made-up market values.

## Local testing

```bash
pip install -r requirements.txt
python fetch_data.py
python -m http.server 8000
```

Visit `http://localhost:8000`. Opening the HTML file with `file://` does not reliably permit `fetch('./data.json')`; use the tiny local test server or GitHub Pages.

## Methodology

- SPY and GLD are **ETF proxies**, not the S&P 500 index or the gold spot price.
- Historical **adjusted closes**, downloaded using `auto_adjust=True`, are aligned on the **last common trading date** of each calendar month.
- Simple monthly return: `P_t/P_(t-1) - 1`, expressed as percentage points.
- OLS: `GLD monthly return (%) = intercept + slope × SPY monthly return (%)`.
- R² and Pearson correlation are calculated on the same observations.
- 'Down months' highlights months where SPY monthly return was negative. **The regression remains based on all selected months**, unless the UI explicitly says otherwise.
- Historical data is descriptive; correlation does not establish causality, future hedging, or investment merit.
- Prices may be delayed; exact source update time is shown on the page.

## Data and hosting notes

Yahoo Finance is not an official guaranteed API; usage and availability can change. GitHub Actions performs network access on the server-side *build/refresh step*, not in the static browser page. For personal/classroom demonstration. Chart.js is loaded from a public CDN; for complete offline independence, vendor its JS file.

## Additional finance indicators (v2)

- **Cumulative return:** `last_adjusted_price / first_adjusted_price - 1` over the selected horizon.
- **Volatility:** sample standard deviation of monthly simple returns, multiplied by `sqrt(12)` (annualized). Assumes zero serial correlation for annualization.
- **Sharpe ratio:** `(12 × arithmetic mean monthly return − assumed annual risk-free rate) / annualized volatility`. The user-selected risk-free value defaults to **3% for illustration**, not a live Treasury observation.
- **Maximum drawdown:** worst peak-to-trough decline of hypothetical monthly-end wealth; intramonth drawdowns can be larger.
- **Diversification label:** qualitative description of absolute historical Pearson correlation (less than 0.3 low; less than 0.7 moderate; otherwise high).

All calculations are backward-looking. Returns use adjusted prices, so hypothetical growth approximates reinvestment of distributions and is not a tax/fee-inclusive result.


## Allocation Lab (new subpage)

Open `portfolio.html` through the navigation link on the homepage. It uses the **same** `data.json` (no additional API credentials or workflow changes), with interactive SPY/GLD weights, historical monthly-rebalanced growth, annualized return/volatility, a risk–return plot, max drawdown and Sharpe ratio. The "best Sharpe" weight is backward-looking and calculated on a 1% grid; it is not a forecast. Risk-free rate is an editable assumption, not a live Treasury quote. Requires 61+ verified aligned monthly prices; first GitHub Actions refresh must succeed.
