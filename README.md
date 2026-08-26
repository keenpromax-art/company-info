# Indian Stocks Research — Streamlit App

An advanced research dashboard for 850+ NSE-listed Indian companies, built on
`yfinance`. Includes candlestick price charts, financial statement viewer with
trend charts, a multi-company comparison tool, a session watchlist, CSV export,
and a searchable directory.

## What's in this folder
- `app.py` — the Streamlit app
- `companies.py` — database of 850+ Indian companies mapped to NSE tickers
- `requirements.txt` — Python dependencies (needed for deployment)
- `.gitignore`

## Features

**Research tab** (per-company deep dive, 14 sub-sections):
- **Overview** — business summary, sector/industry, HQ, employee count
- **🩺 Health Score** — transparent 0–100 rule-based score across
  Profitability / Balance Sheet / Growth / Valuation, with every threshold
  shown so you can judge the scoring yourself (not a recommendation)
- **Price Chart** — candlestick + volume, selectable period (1mo → max),
  with SMA20/50/200 overlays and period return/high/low/avg-volume stats
- **📊 Technicals** — Bollinger Bands, RSI(14) with overbought/oversold
  read, MACD(12,26,9) with signal crossover read, moving-average position
- **Financial Statements** — income statement, balance sheet, cash flow
  (annual & quarterly), with trend charts and CSV download
- **Ratios** — profitability, valuation, balance sheet health
- **💰 DCF Valuation** — interactive simplified discounted cash flow model;
  adjust growth rate, discount rate, terminal growth, and projection years
  and see the estimated intrinsic value per share update live
- **🎯 Analyst Views** — price targets, recommendation summary, recent
  upgrades/downgrades, growth estimates (where covered by Yahoo Finance)
- **📅 Earnings** — earnings dates (past & upcoming), EPS estimate vs actual
- **💵 Dividends & Splits** — full dividend history with chart, split history
- **Business & Revenue** — honest section on what's/isn't available
  (segment revenue & market share aren't in any free API)
- **Holders** — major, institutional, and mutual fund holders
- **👤 Insider Activity** — insider transactions, purchases, roster
- **News** — recent headlines with links

**Other tabs:**
- **🏭 Sector Peers** — auto-benchmarks the selected company against other
  same-sector companies in the database (market cap, P/E, ROE, margins, growth)
- **⚖️ Compare** — up to 5 companies side by side, with a chart and CSV export
- **⭐ Watchlist** — add companies, track live price/change (session-only)
- **📋 Directory** — browse/filter all 850+ companies

### Honest limitations — please read before relying on this for decisions

**Data that simply isn't available anywhere free:**
Structured "revenue streams" (segment-wise revenue) and "market share" are
not published by Yahoo Finance or any free API. The Business & Revenue tab
says so directly and points to the annual report / Screener.in instead of
guessing.

**Calculated features — these are transparent heuristics, not predictions:**
- **Health Score** is a simple weighted rule (thresholds shown in-app via
  "How is this score calculated?"). A low score can just mean "expensive
  because it's high quality," not "bad company."
- **DCF Valuation** is a single-stage Free Cash Flow model with three
  user-adjustable assumptions (growth, discount rate, terminal growth).
  Move any slider and the "intrinsic value" moves with it — that's the
  point (to show sensitivity), not a hidden precision the model doesn't have.
  Real valuation work needs segment forecasts, a properly derived WACC, and
  scenario ranges. Banks/NBFCs and companies with negative FCF can't be
  DCF'd this way at all — the tab will tell you.
- **Technicals** (RSI/MACD/Bollinger Bands) are standard lagging indicators
  computed from price history. They describe the past, not the future.

None of this is investment advice, a recommendation, or a price target —
treat every number here as a starting point for your own research, not a
conclusion.

---

## Run it locally first (recommended, 2 minutes)

```bash
pip install -r requirements.txt
streamlit run app.py
```

It'll open at `http://localhost:8501`. Confirm it works before deploying.

---

## Deploy for free on Streamlit Community Cloud

Streamlit Community Cloud (share.streamlit.io) hosts public Streamlit apps
for free. You need a **GitHub account** — the app is deployed straight from
a GitHub repo.

### Step 1 — Put the code on GitHub
1. Go to [github.com](https://github.com) and create a new **public** repository
   (e.g. `indian-stocks-research`).
2. Upload these files to the repo root: `app.py`, `companies.py`,
   `requirements.txt` (and `.gitignore` if you like).
   - Easiest way: on the repo page, click **"Add file" → "Upload files"**,
     drag in all files, and commit.
   - Or via git:
     ```bash
     git init
     git add app.py companies.py requirements.txt .gitignore
     git commit -m "Initial commit"
     git branch -M main
     git remote add origin https://github.com/<your-username>/indian-stocks-research.git
     git push -u origin main
     ```

### Step 2 — Deploy on Streamlit Community Cloud
1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in
   with your GitHub account (free — no credit card).
2. Click **"Create app"** → **"Deploy a public app from GitHub"**.
3. Fill in:
   - **Repository:** `<your-username>/indian-stocks-research`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. (Optional) Click **"Advanced settings"** to pin a Python version (3.11
   recommended) if you want reproducible builds.
5. Click **"Deploy"**.

Streamlit Cloud will install everything from `requirements.txt` and launch
the app. First build takes 1–3 minutes. You'll get a public URL like:

```
https://<your-username>-indian-stocks-research-app-xxxxxx.streamlit.app
```

Share that link with anyone — no login required to view it.

### Step 3 — Updating the app later
Any time you push a new commit to the `main` branch on GitHub (e.g. after
adding more companies to `companies.py`), Streamlit Cloud **automatically
redeploys** the app within a minute or two. No manual redeploy step needed.

---

## Adding more companies
Open `companies.py` and add a line to the `COMPANIES` dict:
```python
"Your Company Name": "TICKER.NS",
```
Find the ticker on Yahoo Finance or NSE. Use `.NS` for NSE-listed stocks,
`.BO` for BSE-only listings. Commit and push — the live app updates itself.

## Notes & troubleshooting
- **Free tier limits:** Community Cloud apps sleep after a period of
  inactivity and wake up on the next visit (may take ~30s to "wake"). This
  is normal and expected on the free tier.
- **Rate limiting:** Yahoo Finance can rate-limit heavy traffic. The app
  caches data for 15–60 minutes (`st.cache_data`) to reduce this risk. If
  you see fetch errors, wait a minute and retry.
- **Sector Peers tab is slower on first use:** it fetches data for multiple
  companies to find sector matches (capped at ~120 scanned per session).
  Subsequent visits are fast because results are cached.
- **Private repos:** Streamlit Community Cloud's free tier supports deploying
  from private repos too (once your GitHub account is linked), not just
  public ones — public is just the simplest path for a first deployment.
- This tool is for informational/educational purposes only — not investment
  advice.
