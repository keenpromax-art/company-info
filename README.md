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
- **Search** any company by name or ticker (fuzzy matching included)
- **Overview** — business summary, sector/industry, HQ, employee count
- **Price Chart** — candlestick + volume, selectable period (1mo → max)
- **Financial Statements** — income statement, balance sheet, cash flow
  (annual & quarterly), with trend charts and CSV download
- **Ratios** — profitability, valuation, balance sheet health
- **Compare** — up to 5 companies side by side, with a chart and CSV export
- **Watchlist** — add companies, track live price/change (session-only)
- **Directory** — browse/filter all 850+ companies

### Honest limitation
Like any tool built on free market-data APIs, this app **cannot** show
structured "revenue streams" (segment-wise revenue) or "market share" —
that data isn't published by Yahoo Finance or any free API. The app says
so directly in the Business & Revenue tab and points to the annual report /
Screener.in instead of guessing.

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
- **Private repos:** Streamlit Community Cloud's free tier supports deploying
  from private repos too (once your GitHub account is linked), not just
  public ones — public is just the simplest path for a first deployment.
- This tool is for informational/educational purposes only — not investment
  advice.
