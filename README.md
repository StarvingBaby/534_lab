# Gold vs. Stocks — The Safe Haven Experiment

A one-page, static financial data experiment comparing monthly SPY and GLD returns with ordinary least squares (OLS). No custom server and no API key.

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
