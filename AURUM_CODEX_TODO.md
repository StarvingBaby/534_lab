# Aurum Lab — The Safe Haven Paradox

> **Codex implementation brief / TODO**  
> Project: `534_lab` (existing static GitHub Pages financial analysis site)  
> Goal: satisfy the professor's *Financial Tracking Website* assignment while retaining the existing Gold vs. Stocks identity and adding one engaging, evidence-based bond-market research page.

## 0. Read this first — instructions to Codex

Work **in the existing repository**. Inspect the files and data contracts before coding. **Do not rebuild the project, migrate to a framework, or overwrite existing analyses.** Favor straightforward HTML/CSS/vanilla JavaScript, Python for data preparation, and the existing GitHub Actions/GitHub Pages deployment. Make small, reviewable changes; test before committing. If the project structure differs from the outline below, adapt to what actually exists.

**Non-negotiable:** No made-up prices, term premia, historical dates, market findings, sample metrics presented as real, or invented citations. Historical conclusions must be generated or checked against aligned observations from public data. If a source fails, show an honest last-updated/stale/error state rather than dummy data.

## 1. Background / current state

The FINTECH / ENGRMGMT 534 project began as a standalone HTML financial analysis example. It evolved into **Aurum Lab**, a small public static site themed around gold and investment risk:

- `index.html`: Gold vs. Stocks (SPY versus GLD), scatter plot, OLS best-fit line, slope/intercept/R²/correlation, annualized volatility, Sharpe ratio, drawdown, animated charts, time-range controls.
- `portfolio.html`: adjustable gold/stock weights, historical portfolio comparison, risk-return visualization, and a historical maximum-Sharpe exploration tool.
- `fetch_data.py`: collects SPY / GLD historical adjusted market prices and produces `data.json` (inspect actual schema).
- `.github/workflows/update.yml`: currently fetches data and deploys the static site to GitHub Pages on push, on manual dispatch, and on a weekday schedule. **Preserve the working workflow.**
- `requirements.txt` and `README.md`: already exist.

The visual direction is dark, elegant, modern **gold / champagne / graphite** rather than dense Bloomberg-style dashboard. Existing user interactions and pages should continue working.

## 2. Professor's actual assignment (hard requirements)

Assignment title: **Create a Financial Tracking Website**.

> Build a small **public** page that plots, over history, **a duration measure for a Treasury bond** together with the **10-year term premium**. Use any public data. Once the page is up, identify **a change in the term premium** and relate that change to something observable in **another market**. The relation must rest on **a specific window** and **at least one number the page computes or fetches**.

The duration and term-premium series must be visible over a **multi-year span**. The final written claim should name the other market, the exact window, and the supporting number(s). A URL to the public page is the deliverable.

**Important implication:** SPY vs GLD alone does **not** fulfill the assignment. The new page must prominently chart BOTH Treasury duration and the 10Y term premium; gold is the cross-market comparison, not a substitute for either required bond series.

## 3. Proposed narrative / title

**The Safe Haven Paradox — When Bonds Get Riskier, What Does Gold Do?**

Research question: *When the market's estimated compensation for holding long-term U.S. Treasuries changes, what happens to gold over the same dates?*

The page should help a visitor distinguish:

1. **Duration:** approximate interest-rate sensitivity of a specified Treasury bond or precisely defined Treasury proxy.
2. **10Y term premium:** an **estimated**, model-dependent component of the 10-year Treasury yield; not a directly traded price or a guaranteed premium.
3. **GLD:** publicly traded gold ETF used as the observable **other market**.

Avoid statements such as “term premium causes gold to rise” or “gold always hedges bonds.” Present correlation/OLS as descriptive, not causal.

## 4. Data sources and definitions (verify before implementation)

| Series | Preferred source | Frequency / units | Notes |
|---|---|---|---|
| 10Y term premium (`ACMTP10`) | NY Fed ACM Treasury Term Premia download: https://www.newyorkfed.org/research/data_indicators/term-premia-tabs | Monthly (month-end), % annualized | Use the official **ACM monthly** workbook and confirm its actual current sheet/column names. Published estimates can be revised. |
| Treasury yield for duration | FRED `DGS10`: https://fred.stlouisfed.org/series/DGS10 | Daily, yield in **percent** | Convert to monthly observation using the **last available trading day** of each month; do not forward-fill arbitrary missing periods. May alternatively use an explicitly documented consistent Treasury yield series. |
| Gold comparison | Existing `data.json` GLD adjusted historical price series | Monthly price and return in USD / % | Reuse prior pipeline; calculate same-window GLD price return from aligned month-end endpoints. Label as **GLD ETF**, not spot gold. |

Sources should be cited visibly on the new page, with last available observation date, computation/aggregation conventions, and a link to a short Methodology section. Do not require browser CORS access to government APIs: fetch and normalize using Python inside the existing data-refresh workflow, then serve same-origin JSON through GitHub Pages.

**Source verification gate:** before writing the parser, inspect the actual NY Fed workbook and FRED export formats and document the validated URL/column mapping. If an official endpoint changes, fail meaningfully or use a documented publicly accessible backup; do not silently switch series/models.

## 5. Duration methodology — make it academically defensible

There is no direct “duration of the DGS10 yield” series. A 10-year constant-maturity yield is **not** itself a Treasury bond whose duration can be observed. Choose a transparent bond proxy and name it on the chart.

**Recommended MVP:** compute the **modified duration of a hypothetical, newly issued 10-year, semiannual-pay par Treasury bond at each month-end**:

- Face value `F = 100`; maturity `T = 10` years; two coupon payments/year (`m = 2`).
- Monthly observed annual 10Y yield `y` in decimal; assume the bond's annual coupon rate equals the month's yield at par: `c = y`. State this is a **model proxy**, not the observed duration of a particular CUSIP.
- With `N = 20`, cash flow per half-year `C = F*c/2`; add principal `F` at `t = N`. Discount cash flow `CF_t` by `(1+y/2)^t`.
- Bond price `P = sum(CF_t / (1+y/2)^t)`.
- Macaulay duration in **years**: `D_mac = sum((t/2) * PV(CF_t)) / P`.
- Modified duration in **years**: `D_mod = D_mac / (1+y/2)`.
- Rate-shock approximation: `ΔP/P ≈ -D_mod * Δy`, with `Δy` in decimal (so +100 bps = +0.01). This ignores convexity; label it a first-order approximation.

**Caveat to surface prominently:** because the proxy is reset to a fresh 10-year par bond each month, duration changes reflect **yield changes under fixed maturity/model assumptions**, not the aging of a single bond. If a better publicly documented actual Treasury-security duration time series can be sourced and reproduced, that is an optional enhancement; do not block the assignment on it.

Validate with small unit tests: price approximately par, duration positive and below maturity, higher yield tends to reduce duration for this setup, +100 bps gives a negative approximate price impact, and unit conversion (percentage points vs decimal yield) is correct.

## 6. UX / pages and information hierarchy

Keep existing `index.html` and `portfolio.html`. Add `bonds.html`, discoverable from the navigation and with a clear link back. **Make `bonds.html` the obvious assignment entry point** (optionally place a hero CTA on `index.html`: “Explore the Bond–Gold Puzzle”).

New page design: dark graphite canvas, warm gold accents, subtle glow/highlights, tasteful transitions, elegant typography, and generous whitespace. Do not overbuild a heavy dashboard or create 15 statistics cards. Respect `prefers-reduced-motion`; chart interactions should work on mobile and keyboard-accessible inputs.

### Section A — Hero / research question

- Eyebrow: `AURUM LAB / RESEARCH NOTE 03`.
- Heading: **Are safe-haven assets really safe?**
- Subtitle: Treasury duration, 10-year term premium, and gold—one timeline, three views of risk.
- Clearly show range and `Data through: YYYY-MM-DD` as **actual** validated data.
- One clear `Explore the evidence` scroll CTA.

### Section B — Required chart: Treasury duration + 10Y term premium

- **Both series over the same 5–10+ year historical period**, visible without toggling the other off.
- Prefer two aligned stacked line charts sharing a timeline (more honest than one poorly labeled dual-axis chart since units differ: **years** vs **percent**). Distinct series colors and axis labels.
- Hover/tap shared crosshair with precise date, duration (years), term premium (%), and 10Y yield (%).
- Range selector: `3Y / 5Y / 10Y / All` if available, but default to a **multi-year** view.
- A subtle event/window brush or start/end selection mechanism; avoid out-of-range or mismatched dates.

### Section C — The experiment: duration risk

- Interactive slider for rate shock, e.g. `-200 to +200 bps`, default `+100 bps`.
- Current proxy modified duration at selected date; output approximate percentage price change and resulting value of hypothetical `$10,000` bond.
- Explain `ΔP/P ≈ −D_mod × Δy`; **this is a sensitivity estimate**, not actual realized bond return.
- Optional animation of the bond-value display; no misleading real-time claim.

### Section D — Gold as the “other market”

- Plot **GLD** adjusted price index (or $10,000 growth) over the **same time window**; optionally a gold-coloured performance line.
- Show exactly computed `Δ term premium` in **basis points**, `GLD holding-period return` in **%**, and optionally `Δ duration` in years.
- If including correlation, use aligned monthly `Δ term premium` (in bps) and **monthly GLD returns**; identify sample count; correlation does not demonstrate causality. Keep this secondary to the required concrete historical observation.
- Clicking or brushing a window updates all supporting values and the written takeaway.

### Section E — The finding (professor-critical)

A prominent evidence-backed research note that fills in **actual** values from the same selected observation window:

> From **[start month/year]** to **[end month/year]**, the NY Fed's 10-year ACM term-premium estimate **[rose/fell] [N] basis points** (from **[A]%** to **[B]%**). Over the same dates, **GLD [rose/fell] [R]%** using adjusted month-end prices. Our 10-year par-bond duration proxy changed from **[D0] to [D1] years**. This is an observed association in this window, **not evidence of causation**.

- Use robust exact date matching; show actual GLD pricing dates if different from ACM month-end dates.
- If insufficient overlap or too few points, show `Insufficient aligned observations` instead of a narrative.
- The window should be **found by inspecting real data** (possibly compare a few candidate periods), not chosen because it will support a predetermined conclusion.
- Include a **Copy finding** button, if quick to implement.

### Section F — Sources / methodology / limitations

Short, expandable explanation of **ACM estimate vs observed yield**, hypothetical duration assumptions, frequency alignment, GLD adjusted prices (corporate-action treatment), correlation limitations, and dates/source URLs. Include source access/retrieval date if available.

## 7. Implementation plan / TODO checklist

### Phase 0 — Inspect and protect the current project

- [ ] Read `index.html`, `portfolio.html`, `fetch_data.py`, `data.json`, `.github/workflows/update.yml`, `requirements.txt`, `README.md`.
- [ ] Determine the actual existing JSON schema, dependency versions, navigation conventions, and chart libraries.
- [ ] Keep the existing working SPY/GLD display and current GitHub Pages workflow behavior intact.
- [ ] Decide whether to store new bond data in **`bond_data.json`** (preferred separation) or a backward-compatible extension to `data.json`; document schema.

### Phase 1 — Build reproducible public-data ingestion

- [ ] Obtain official NY Fed ACM **monthly** 10Y term-premium values and record verified workbook/column names.
- [ ] Obtain historical 10Y Treasury yields via FRED and aggregate to monthly last-available observations.
- [ ] Read existing GLD adjusted-price history; extend its history if needed for the chosen range.
- [ ] Normalize dates/month keys; sort, deduplicate, reject invalid rows, and align on **common available months**.
- [ ] Calculate hypothetical par Treasury `modified_duration_years` for each monthly yield.
- [ ] Save generated `bond_data.json` containing observations plus metadata: `generated_at`, `sources`, `definitions`, `frequency`, `last_observation_date`, `assumptions`.
- [ ] Ensure data fetching occurs in Python/GitHub Actions, **not from the browser using cross-origin endpoints**.
- [ ] On fetch failure, do not commit corrupt or empty JSON; fail clearly, and retain previous published data.

Suggested normalized observation (schema is illustrative, not actual values):

```json
{
  "month": "YYYY-MM",
  "acm_term_premium_pct": null,
  "treasury_10y_yield_pct": null,
  "modified_duration_years": null,
  "gld_adjusted_close_usd": null,
  "gld_price_date": "YYYY-MM-DD"
}
```

Replace `null` only with **verified computed or fetched numeric data**. Distinguish missing data from zero. Consider keeping raw source-specific datasets as well as aligned observations for traceability.

### Phase 2 — Implement the new `bonds.html`

- [ ] Build hero and site navigation consistent with Aurum Lab.
- [ ] Draw aligned multi-year duration and term-premium time series, with correctly labeled units.
- [ ] Add shared hover, window selection, and responsive layout.
- [ ] Implement rate-shock slider and duration-based hypothetical bond-value estimate.
- [ ] Add GLD cross-market comparison over selected exact window.
- [ ] Dynamically compute term-premium bps change, same-window GLD return, and duration change.
- [ ] Display evidence-based finding with precise dates; never hardcode a claimed historical relationship.
- [ ] Add sources, assumptions, data-as-of timestamp, and understandable failure/empty states.
- [ ] Add keyboard focus states, accessible labels, and reduced-motion handling.

### Phase 3 — Integrate automation and navigation

- [ ] Update `fetch_data.py` or add `fetch_bond_data.py` and call it from **the existing** `.github/workflows/update.yml`.
- [ ] Add new data dependencies to `requirements.txt` only if needed.
- [ ] Ensure the deploy artifact includes `bonds.html` and `bond_data.json`.
- [ ] Keep **a single active deployment workflow**. Do not reintroduce obsolete `update-market-data.yml` / `update_data.py` logic from the old Treasury/WTI demo.
- [ ] Add prominent `Bond–Gold Puzzle` link to home/nav; link all pages consistently.
- [ ] Keep push, manual and current weekday scheduled triggers **unless explicitly requested to change them**.
- [ ] Document how to execute data refresh locally and through Actions in `README.md`.

### Phase 4 — Verify the economics, frontend, and deploy

- [ ] Unit tests: coupon/price/duration math, bps conversions, rate-shock sign, GLD holding-period return, date alignment, window endpoints.
- [ ] Test missing trading days, month boundaries, zero or missing observations, empty overlap, API failure, and stale data.
- [ ] Verify all calculated output values against a small independent Python/pandas or spreadsheet sample.
- [ ] Test 3Y/5Y/10Y selectors; slider; chart tooltips; responsive mobile/desktop; links; keyboard usage.
- [ ] Confirm existing `index.html` and `portfolio.html` still work and show unchanged calculations.
- [ ] Deploy via GitHub Actions; verify public `/bonds.html` URL and data freshness on actual GitHub Pages.
- [ ] Record a **real** 2–4 sentence observation for one meaningful historical window, with exact numbers and supporting data/source URLs.

## 8. Suggested acceptance criteria (definition of done)

1. Public GitHub Pages URL loads without server-side infrastructure or a user-supplied API key.
2. `bonds.html` visibly plots **both** a multi-year monthly modified-duration **proxy** and official ACM **10-year term premium**.
3. Every metric/chart has correct units and clear source/assumption labels.
4. An explicit historical **start/end window** is shown, alongside a computed term-premium change in **bps** and same-window **GLD return** in **%**.
5. A readable, evidence-based sentence states which market, which window, and which computed/fetched numbers support the observation; does **not** infer causality.
6. Users can interactively explore the window and duration shock, with reliable handling of missing data.
7. Existing home and portfolio analyses still work; deployment remains automatic via the current GitHub Actions setup.
8. README provides deploy/run instructions and sources; no synthetic figures are presented as historical facts.

## 9. Scope control / stretch goals

**Must do:** accurate data ingestion, duration methodology, multi-year bond charts, one real GLD cross-market window with numbers, public URL.

**Nice to have:** smooth scroll animations, annotated financial events, one-click finding copy, GLD monthly return vs term-premium-change scatter/OLS, optional alternate market selector (QQQ or mortgage rates).

**Do not do yet:** rewrite as React/Vite, add a backend, invent a generic AI chatbot, introduce lots of new APIs, replace the existing gold visuals, or present a duration-shock simulation as realized investment performance.

## 10. Immediate instruction to Codex

**Start with Phase 0 and Phase 1.** Inspect the repository and fetch/validate the **actual** NY Fed and Treasury yield source formats. Implement the normalized dataset and duration calculation, with tests, **before** building the new page. Then proceed through Phase 2–4. If a data endpoint is blocked, report the verified blocker and implement a documented, non-fabricated fallback—never substitute toy data into production charts.
