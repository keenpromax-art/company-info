"""
Indian Stocks Research — Streamlit App
========================================
An advanced research dashboard for 850+ Indian (NSE-listed) companies,
built on yfinance. Deployable for free on Streamlit Community Cloud.

Run locally:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from difflib import get_close_matches
from datetime import datetime, timedelta

import yfinance as yf
from companies import COMPANIES, TICKER_TO_NAME, company_count

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Indian Stocks Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------

if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None
    st.session_state.selected_name = None


# --------------------------------------------------------------------------
# Data fetching (cached to be gentle on Yahoo Finance & keep app snappy)
# --------------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def get_info(ticker: str):
    t = yf.Ticker(ticker)
    try:
        info = t.info
    except Exception:
        return None
    if not info or len(info) < 3:
        return None
    return info


@st.cache_data(ttl=900, show_spinner=False)
def get_history(ticker: str, period: str = "1y"):
    t = yf.Ticker(ticker)
    try:
        hist = t.history(period=period)
    except Exception:
        return pd.DataFrame()
    return hist


@st.cache_data(ttl=3600, show_spinner=False)
def get_financials(ticker: str):
    t = yf.Ticker(ticker)
    out = {}
    for attr, key in [
        ("financials", "income_annual"),
        ("quarterly_financials", "income_quarterly"),
        ("balance_sheet", "balance_annual"),
        ("quarterly_balance_sheet", "balance_quarterly"),
        ("cashflow", "cashflow_annual"),
        ("quarterly_cashflow", "cashflow_quarterly"),
    ]:
        try:
            out[key] = getattr(t, attr)
        except Exception:
            out[key] = pd.DataFrame()
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def get_holders(ticker: str):
    t = yf.Ticker(ticker)
    out = {}
    try:
        out["major"] = t.major_holders
    except Exception:
        out["major"] = None
    try:
        out["institutional"] = t.institutional_holders
    except Exception:
        out["institutional"] = None
    try:
        out["mutualfund"] = t.mutualfund_holders
    except Exception:
        out["mutualfund"] = None
    return out


@st.cache_data(ttl=900, show_spinner=False)
def get_news(ticker: str):
    t = yf.Ticker(ticker)
    try:
        return t.news or []
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def get_analyst_data(ticker: str):
    """Analyst price targets, recommendations, and revisions."""
    t = yf.Ticker(ticker)
    out = {}
    try:
        out["price_targets"] = t.analyst_price_targets
    except Exception:
        out["price_targets"] = None
    try:
        out["recommendations"] = t.recommendations
    except Exception:
        out["recommendations"] = None
    try:
        out["rec_summary"] = t.recommendations_summary
    except Exception:
        out["rec_summary"] = None
    try:
        out["upgrades_downgrades"] = t.upgrades_downgrades
    except Exception:
        out["upgrades_downgrades"] = None
    try:
        out["growth_estimates"] = t.growth_estimates
    except Exception:
        out["growth_estimates"] = None
    try:
        out["eps_trend"] = t.eps_trend
    except Exception:
        out["eps_trend"] = None
    try:
        out["revenue_estimate"] = t.revenue_estimate
    except Exception:
        out["revenue_estimate"] = None
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def get_earnings_data(ticker: str):
    t = yf.Ticker(ticker)
    out = {}
    try:
        out["earnings_dates"] = t.earnings_dates
    except Exception:
        out["earnings_dates"] = None
    try:
        out["earnings_history"] = t.earnings_history
    except Exception:
        out["earnings_history"] = None
    try:
        out["calendar"] = t.calendar
    except Exception:
        out["calendar"] = None
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def get_corp_actions(ticker: str):
    t = yf.Ticker(ticker)
    out = {}
    try:
        out["dividends"] = t.dividends
    except Exception:
        out["dividends"] = pd.Series(dtype=float)
    try:
        out["splits"] = t.splits
    except Exception:
        out["splits"] = pd.Series(dtype=float)
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def get_insider_data(ticker: str):
    t = yf.Ticker(ticker)
    out = {}
    try:
        out["transactions"] = t.insider_transactions
    except Exception:
        out["transactions"] = None
    try:
        out["purchases"] = t.insider_purchases
    except Exception:
        out["purchases"] = None
    try:
        out["roster"] = t.insider_roster_holders
    except Exception:
        out["roster"] = None
    return out


@st.cache_data(ttl=86400, show_spinner=False)
def get_isin(ticker: str):
    t = yf.Ticker(ticker)
    try:
        return t.isin
    except Exception:
        return None


# --------------------------------------------------------------------------
# Technical indicators (computed locally from price history — no extra API calls)
# --------------------------------------------------------------------------

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add SMA, EMA, RSI, MACD, Bollinger Bands to an OHLCV dataframe."""
    if df.empty or "Close" not in df.columns:
        return df
    out = df.copy()
    close = out["Close"]

    # Moving averages
    out["SMA20"] = close.rolling(20).mean()
    out["SMA50"] = close.rolling(50).mean()
    out["SMA200"] = close.rolling(200).mean()
    out["EMA20"] = close.ewm(span=20, adjust=False).mean()

    # Bollinger Bands (20-period, 2 std dev)
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    out["BB_upper"] = mid + 2 * std
    out["BB_lower"] = mid - 2 * std
    out["BB_mid"] = mid

    # RSI (14-period)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["RSI14"] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    out["MACD"] = ema12 - ema26
    out["MACD_signal"] = out["MACD"].ewm(span=9, adjust=False).mean()
    out["MACD_hist"] = out["MACD"] - out["MACD_signal"]

    return out


def compute_health_score(info: dict) -> dict:
    """
    A simple, transparent rule-based scoring heuristic (NOT a recommendation).
    Scores 0-100 across four pillars using thresholds commonly cited in
    fundamental analysis. All thresholds are shown to the user for transparency.
    """
    scores = {}
    notes = {}

    # Profitability (out of 25)
    npm = info.get("profitMargins")
    roe = info.get("returnOnEquity")
    prof_score = 0
    if npm is not None:
        prof_score += min(max(npm * 100, 0), 15) / 15 * 12.5
    if roe is not None:
        prof_score += min(max(roe * 100, 0), 25) / 25 * 12.5
    scores["Profitability"] = round(prof_score, 1)
    notes["Profitability"] = f"Net margin {fmt_pct(npm)}, ROE {fmt_pct(roe)}"

    # Balance sheet health (out of 25)
    de = info.get("debtToEquity")
    curr = info.get("currentRatio")
    bs_score = 0
    if de is not None:
        # lower D/E is better; 0 D/E = full marks, 200+ = 0 marks
        bs_score += max(0, (200 - min(de, 200)) / 200) * 12.5
    if curr is not None:
        # current ratio of ~2 considered healthy
        bs_score += min(curr, 2) / 2 * 12.5
    scores["Balance Sheet"] = round(bs_score, 1)
    de_display = f"{de:.1f}" if de is not None else "N/A"
    curr_display = f"{curr:.2f}" if curr is not None else "N/A"
    notes["Balance Sheet"] = f"Debt/Equity {de_display}, Current Ratio {curr_display}"

    # Growth (out of 25)
    rev_g = info.get("revenueGrowth")
    earn_g = info.get("earningsGrowth")
    growth_score = 0
    if rev_g is not None:
        growth_score += min(max(rev_g * 100, -10), 25) / 25 * 12.5 if rev_g > 0 else 0
    if earn_g is not None:
        growth_score += min(max(earn_g * 100, -10), 25) / 25 * 12.5 if earn_g > 0 else 0
    scores["Growth"] = round(growth_score, 1)
    notes["Growth"] = f"Revenue growth {fmt_pct(rev_g)}, Earnings growth {fmt_pct(earn_g)}"

    # Valuation (out of 25) — lower PE/PB relative to typical ranges scores higher
    pe = info.get("trailingPE")
    pb = info.get("priceToBook")
    val_score = 0
    if pe is not None and pe > 0:
        val_score += max(0, (40 - min(pe, 40)) / 40) * 12.5
    if pb is not None and pb > 0:
        val_score += max(0, (10 - min(pb, 10)) / 10) * 12.5
    scores["Valuation"] = round(val_score, 1)
    pe_display = f"{pe:.1f}" if pe is not None else "N/A"
    pb_display = f"{pb:.2f}" if pb is not None else "N/A"
    notes["Valuation"] = f"P/E {pe_display}, P/B {pb_display}"

    total = round(sum(scores.values()), 1)
    return {"total": total, "breakdown": scores, "notes": notes}


def simple_dcf(info: dict, years: int = 5, growth_rate: float = None,
                terminal_growth: float = 0.04, discount_rate: float = 0.11):
    """
    A simplified, transparent Discounted Cash Flow estimate using Free Cash Flow.
    This is a rough educational estimate, NOT a professional valuation —
    real DCF models require far more detail (segment forecasts, WACC
    build-up, working capital changes, etc).
    """
    fcf = info.get("freeCashflow")
    shares = info.get("sharesOutstanding")
    if not fcf or not shares or fcf <= 0:
        return None

    if growth_rate is None:
        # fall back to revenue growth, capped to a sane range
        rg = info.get("revenueGrowth")
        growth_rate = min(max(rg, 0.02), 0.20) if rg else 0.08

    # Guard: Gordon Growth terminal value formula divides by (discount_rate -
    # terminal_growth). If they're equal or inverted, nudge the discount rate
    # up slightly so the model stays mathematically valid instead of crashing.
    if discount_rate <= terminal_growth:
        discount_rate = terminal_growth + 0.01

    projected = []
    cash_flow = fcf
    for year in range(1, years + 1):
        cash_flow = cash_flow * (1 + growth_rate)
        pv = cash_flow / ((1 + discount_rate) ** year)
        projected.append({"year": year, "fcf": cash_flow, "pv": pv})

    terminal_value = (projected[-1]["fcf"] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** years)

    enterprise_value = sum(p["pv"] for p in projected) + pv_terminal
    total_debt = info.get("totalDebt") or 0
    total_cash = info.get("totalCash") or 0
    equity_value = enterprise_value - total_debt + total_cash
    intrinsic_value_per_share = equity_value / shares

    return {
        "projected": projected,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "intrinsic_value_per_share": intrinsic_value_per_share,
        "growth_rate": growth_rate,
        "discount_rate": discount_rate,
        "terminal_growth": terminal_growth,
        "current_price": info.get("currentPrice"),
    }


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------

def fmt_crore(value, currency="₹"):
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    crore = value / 1e7
    if abs(crore) >= 1e5:
        return f"{currency}{crore/1e5:,.2f} Lakh Cr"
    return f"{currency}{crore:,.0f} Cr"


def fmt_pct(value):
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def fmt_num(value):
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if abs(value) >= 1e7:
        return f"{value/1e7:,.2f} Cr"
    if abs(value) >= 1e5:
        return f"{value/1e5:,.2f} Lakh"
    return f"{value:,.2f}"


def safe(d, key, default="N/A"):
    if d is None:
        return default
    v = d.get(key, default)
    return default if v is None else v


# --------------------------------------------------------------------------
# Ticker resolution (name / ticker search)
# --------------------------------------------------------------------------

def resolve_query(query: str):
    """Return list of (display_name, ticker) candidates for a free-text query."""
    q = query.strip()
    if not q:
        return []
    q_upper = q.upper()

    # exact ticker
    for candidate in (q_upper, q_upper + ".NS", q_upper + ".BO"):
        if candidate in TICKER_TO_NAME:
            return [(TICKER_TO_NAME[candidate], candidate)]
    if q_upper.endswith(".NS") or q_upper.endswith(".BO"):
        return [(TICKER_TO_NAME.get(q_upper, q_upper), q_upper)]

    # exact name
    for name, ticker in COMPANIES.items():
        if name.lower() == q.lower():
            return [(name, ticker)]

    # substring
    substr = [(name, t) for name, t in COMPANIES.items() if q.lower() in name.lower()]
    if substr:
        return sorted(substr)[:25]

    # fuzzy
    close = get_close_matches(q, COMPANIES.keys(), n=10, cutoff=0.5)
    return [(name, COMPANIES[name]) for name in close]


# --------------------------------------------------------------------------
# Sidebar — search & navigation
# --------------------------------------------------------------------------

st.sidebar.title("📈 Indian Stocks Research")
st.sidebar.caption(f"{company_count()} companies · powered by yfinance")

search_query = st.sidebar.text_input(
    "Search company or ticker",
    placeholder="e.g. Reliance, TCS.NS, HDFC Bank",
)

candidates = resolve_query(search_query) if search_query else []

if candidates:
    if len(candidates) == 1:
        name, ticker = candidates[0]
        st.session_state.selected_name = name
        st.session_state.selected_ticker = ticker
    else:
        labels = [f"{n}  ({t})" for n, t in candidates]
        pick = st.sidebar.selectbox("Multiple matches — pick one:", labels)
        idx = labels.index(pick)
        st.session_state.selected_name, st.session_state.selected_ticker = candidates[idx]
elif search_query:
    st.sidebar.warning("No match found. Try a different name or ticker.")

st.sidebar.divider()

# Sector browser as an alternative way to pick a company
with st.sidebar.expander("Browse by name (A–Z)"):
    all_names = sorted(COMPANIES.keys())
    browse_pick = st.selectbox("All companies", ["—"] + all_names, label_visibility="collapsed")
    if browse_pick != "—":
        st.session_state.selected_name = browse_pick
        st.session_state.selected_ticker = COMPANIES[browse_pick]

st.sidebar.divider()

# Watchlist management
st.sidebar.subheader("⭐ Watchlist")
if st.session_state.selected_ticker:
    if st.session_state.selected_ticker not in st.session_state.watchlist:
        if st.sidebar.button(f"➕ Add {st.session_state.selected_ticker} to watchlist"):
            st.session_state.watchlist.append(st.session_state.selected_ticker)
            st.rerun()
    else:
        if st.sidebar.button(f"➖ Remove {st.session_state.selected_ticker} from watchlist"):
            st.session_state.watchlist.remove(st.session_state.selected_ticker)
            st.rerun()

if st.session_state.watchlist:
    for wt in list(st.session_state.watchlist):
        wname = TICKER_TO_NAME.get(wt, wt)
        c1, c2 = st.sidebar.columns([4, 1])
        if c1.button(wname[:22], key=f"wl_{wt}", use_container_width=True):
            st.session_state.selected_ticker = wt
            st.session_state.selected_name = wname
            st.rerun()
        if c2.button("✕", key=f"del_{wt}"):
            st.session_state.watchlist.remove(wt)
            st.rerun()
else:
    st.sidebar.caption("No stocks added yet.")

st.sidebar.divider()
st.sidebar.caption(
    "⚠️ yfinance/Yahoo Finance does not provide structured 'revenue streams' "
    "(segment-wise revenue) or 'market share' data — no free API does. "
    "The Health Score, DCF, and Technicals sections are transparent, "
    "rule-based calculations shown for research/educational purposes — "
    "not recommendations, price targets, or investment advice."
)

# --------------------------------------------------------------------------
# Main area
# --------------------------------------------------------------------------

st.title("Indian Stock Market Research")

tab_research, tab_peers, tab_compare, tab_watchlist, tab_directory = st.tabs(
    ["🔍 Research", "🏭 Sector Peers", "⚖️ Compare", "⭐ Watchlist", "📋 Directory"]
)

# ============================== RESEARCH TAB ==============================
with tab_research:
    if not st.session_state.selected_ticker:
        st.info("👈 Search for a company in the sidebar to get started, e.g. **Reliance**, **TCS**, or **HDFC Bank**.")
        st.markdown(f"This app covers **{company_count()} Indian companies** across NSE. Use the sidebar search or the Directory tab to browse.")
    else:
        ticker = st.session_state.selected_ticker
        name = st.session_state.selected_name

        with st.spinner(f"Fetching data for {name}..."):
            info = get_info(ticker)

        if info is None:
            st.error(
                f"Could not fetch data for **{name}** ({ticker}). "
                "The ticker may be invalid, delisted, or Yahoo Finance may be "
                "rate-limiting requests right now. Try again shortly."
            )
        else:
            # ---- Header ----
            col1, col2 = st.columns([3, 1])
            with col1:
                st.header(safe(info, "longName", name))
                st.caption(f"{ticker}  ·  {safe(info, 'sector')}  ·  {safe(info, 'industry')}")
            with col2:
                price = info.get("currentPrice")
                prev = info.get("previousClose")
                if price and prev:
                    delta = price - prev
                    delta_pct = (delta / prev) * 100 if prev else 0
                    st.metric("Price", f"₹{price:,.2f}", f"{delta:+.2f} ({delta_pct:+.2f}%)")
                else:
                    st.metric("Price", "N/A")

            # ---- Top metrics row ----
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Market Cap", fmt_crore(info.get("marketCap")))
            m2.metric("P/E (TTM)", f"{safe(info, 'trailingPE')}")
            m3.metric("P/B", f"{safe(info, 'priceToBook')}")
            m4.metric("Dividend Yield", fmt_pct(info.get("dividendYield")))
            m5.metric("52W Range", f"₹{safe(info,'fiftyTwoWeekLow')} - ₹{safe(info,'fiftyTwoWeekHigh')}")

            st.divider()

            (sub_overview, sub_health, sub_price, sub_technicals, sub_financials, sub_ratios,
             sub_valuation, sub_analyst, sub_earnings, sub_dividends, sub_revenue,
             sub_holders, sub_insider, sub_news) = st.tabs([
                "Overview", "🩺 Health Score", "Price Chart", "📊 Technicals",
                "Financial Statements", "Ratios", "💰 DCF Valuation",
                "🎯 Analyst Views", "📅 Earnings", "💵 Dividends & Splits",
                "Business & Revenue", "Holders", "👤 Insider Activity", "News",
            ])

            # ---- Overview ----
            with sub_overview:
                st.subheader("Business Summary")
                summary = safe(info, "longBusinessSummary", None)
                st.write(summary if summary else "Not available for this ticker.")

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Company Details**")
                    st.write(f"- **Website:** {safe(info, 'website')}")
                    st.write(f"- **Employees:** {fmt_num(info.get('fullTimeEmployees')) if info.get('fullTimeEmployees') else 'N/A'}")
                    st.write(f"- **HQ:** {safe(info,'city')}, {safe(info,'state','')} {safe(info,'country','')}")
                with c2:
                    st.markdown("**Classification**")
                    st.write(f"- **Sector:** {safe(info, 'sector')}")
                    st.write(f"- **Industry:** {safe(info, 'industry')}")
                    st.write(f"- **Exchange:** {safe(info, 'exchange')}")

            # ---- Health Score ----
            with sub_health:
                st.subheader("🩺 Fundamental Health Score")
                st.caption(
                    "A transparent, rule-based heuristic across four pillars — "
                    "**not a recommendation or prediction.** Every threshold used "
                    "is shown below so you can judge the scoring yourself."
                )
                hs = compute_health_score(info)
                total = hs["total"]

                gauge_col, breakdown_col = st.columns([1, 2])
                with gauge_col:
                    gauge_fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=total,
                        title={"text": "Overall Score / 100"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "#2563eb"},
                            "steps": [
                                {"range": [0, 40], "color": "#fee2e2"},
                                {"range": [40, 70], "color": "#fef9c3"},
                                {"range": [70, 100], "color": "#dcfce7"},
                            ],
                        },
                    ))
                    gauge_fig.update_layout(height=280, margin=dict(l=10, r=10, t=50, b=10))
                    st.plotly_chart(gauge_fig, use_container_width=True)

                with breakdown_col:
                    for pillar, score in hs["breakdown"].items():
                        st.write(f"**{pillar}: {score}/25**")
                        st.progress(min(score / 25, 1.0))
                        st.caption(hs["notes"][pillar])

                st.divider()
                with st.expander("How is this score calculated?"):
                    st.markdown("""
- **Profitability (25 pts):** Net profit margin (up to 15%) and Return on Equity (up to 25%), each scaled linearly to half the pillar's points.
- **Balance Sheet (25 pts):** Debt/Equity (0 = best, 200+ = worst) and Current Ratio (2.0 = best), each half the pillar.
- **Growth (25 pts):** YoY revenue growth and earnings growth, each capped at 25% for full marks on its half; negative growth scores zero on that half.
- **Valuation (25 pts):** P/E (lower is "cheaper", scaled against a 40x ceiling) and P/B (scaled against a 10x ceiling), each half the pillar.

This is a simple screening heuristic, not equity research. A low valuation
score can simply mean a stock is expensive for good reasons (high quality,
high growth) — always read the full picture before drawing conclusions.
                    """)

            # ---- Price Chart ----
            with sub_price:
                period_map = {
                    "1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo",
                    "1 Year": "1y", "2 Years": "2y", "5 Years": "5y", "Max": "max",
                }
                period_label = st.select_slider("Period", options=list(period_map.keys()), value="1 Year", key="price_period")
                hist = get_history(ticker, period_map[period_label])

                if hist.empty:
                    st.warning("No price history available.")
                else:
                    hist_ind = add_technical_indicators(hist)
                    show_ma = st.checkbox("Show moving averages (SMA20 / SMA50 / SMA200)", value=True)

                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=hist_ind.index, open=hist_ind["Open"], high=hist_ind["High"],
                        low=hist_ind["Low"], close=hist_ind["Close"], name=ticker,
                    ))
                    if show_ma:
                        for col, color in [("SMA20", "#f59e0b"), ("SMA50", "#3b82f6"), ("SMA200", "#ef4444")]:
                            fig.add_trace(go.Scatter(
                                x=hist_ind.index, y=hist_ind[col], name=col,
                                line=dict(width=1.3, color=color),
                            ))
                    fig.update_layout(
                        height=450, xaxis_rangeslider_visible=False,
                        margin=dict(l=10, r=10, t=30, b=10),
                        yaxis_title="Price (₹)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    vol_fig = px.bar(hist, x=hist.index, y="Volume", height=180)
                    vol_fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Volume")
                    st.plotly_chart(vol_fig, use_container_width=True)

                    # Quick stats for the selected period
                    p_start, p_end = hist["Close"].iloc[0], hist["Close"].iloc[-1]
                    period_return = (p_end - p_start) / p_start * 100
                    s1, s2, s3, s4 = st.columns(4)
                    s1.metric(f"Return ({period_label})", f"{period_return:+.2f}%")
                    s2.metric("Period High", f"₹{hist['High'].max():,.2f}")
                    s3.metric("Period Low", f"₹{hist['Low'].min():,.2f}")
                    s4.metric("Avg Volume", fmt_num(hist["Volume"].mean()))

            # ---- Technicals ----
            with sub_technicals:
                st.caption(
                    "Indicators computed locally from price history (not investment "
                    "advice — technical indicators are lagging and can generate false signals)."
                )
                tech_period = st.select_slider(
                    "Period", options=["3 Months", "6 Months", "1 Year", "2 Years"],
                    value="1 Year", key="tech_period"
                )
                tech_period_map = {"3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y"}
                thist = get_history(ticker, tech_period_map[tech_period])

                if thist.empty or len(thist) < 20:
                    st.warning("Not enough price history to compute indicators.")
                else:
                    tind = add_technical_indicators(thist)

                    # Bollinger Bands chart
                    st.markdown("**Bollinger Bands (20-period, ±2σ)**")
                    bb_fig = go.Figure()
                    bb_fig.add_trace(go.Scatter(x=tind.index, y=tind["BB_upper"], name="Upper Band", line=dict(width=1, color="#94a3b8")))
                    bb_fig.add_trace(go.Scatter(x=tind.index, y=tind["BB_lower"], name="Lower Band", line=dict(width=1, color="#94a3b8"), fill="tonexty", fillcolor="rgba(148,163,184,0.15)"))
                    bb_fig.add_trace(go.Scatter(x=tind.index, y=tind["Close"], name="Close", line=dict(width=1.5, color="#2563eb")))
                    bb_fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Price (₹)")
                    st.plotly_chart(bb_fig, use_container_width=True)

                    rsi_col, macd_col = st.columns(2)
                    with rsi_col:
                        st.markdown("**RSI (14-period)**")
                        latest_rsi = tind["RSI14"].iloc[-1]
                        rsi_status = "Overbought (>70)" if latest_rsi > 70 else ("Oversold (<30)" if latest_rsi < 30 else "Neutral")
                        st.metric("Current RSI", f"{latest_rsi:.1f}", rsi_status)
                        rsi_fig = go.Figure()
                        rsi_fig.add_trace(go.Scatter(x=tind.index, y=tind["RSI14"], line=dict(color="#7c3aed")))
                        rsi_fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5)
                        rsi_fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5)
                        rsi_fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), yaxis_range=[0, 100])
                        st.plotly_chart(rsi_fig, use_container_width=True)

                    with macd_col:
                        st.markdown("**MACD (12, 26, 9)**")
                        latest_macd = tind["MACD"].iloc[-1]
                        latest_signal = tind["MACD_signal"].iloc[-1]
                        macd_status = "Bullish crossover" if latest_macd > latest_signal else "Bearish crossover"
                        st.metric("MACD vs Signal", f"{latest_macd:.2f}", macd_status)
                        macd_fig = go.Figure()
                        macd_fig.add_trace(go.Scatter(x=tind.index, y=tind["MACD"], name="MACD", line=dict(color="#2563eb")))
                        macd_fig.add_trace(go.Scatter(x=tind.index, y=tind["MACD_signal"], name="Signal", line=dict(color="#f59e0b")))
                        macd_fig.add_trace(go.Bar(x=tind.index, y=tind["MACD_hist"], name="Histogram", marker_color="#94a3b8"))
                        macd_fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.15))
                        st.plotly_chart(macd_fig, use_container_width=True)

                    st.divider()
                    ma_col1, ma_col2, ma_col3 = st.columns(3)
                    latest_close = tind["Close"].iloc[-1]
                    for col, label, ma_key in [(ma_col1, "SMA20", "SMA20"), (ma_col2, "SMA50", "SMA50"), (ma_col3, "SMA200", "SMA200")]:
                        ma_val = tind[ma_key].iloc[-1]
                        if pd.notna(ma_val):
                            position = "Above" if latest_close > ma_val else "Below"
                            col.metric(label, f"₹{ma_val:,.2f}", f"Price is {position}")
                        else:
                            col.metric(label, "N/A")

            # ---- Financial Statements ----
            with sub_financials:
                fin = get_financials(ticker)
                stmt_choice = st.radio(
                    "Statement", ["Income Statement", "Balance Sheet", "Cash Flow"],
                    horizontal=True,
                )
                freq_choice = st.radio("Frequency", ["Annual", "Quarterly"], horizontal=True)

                key_map = {
                    ("Income Statement", "Annual"): "income_annual",
                    ("Income Statement", "Quarterly"): "income_quarterly",
                    ("Balance Sheet", "Annual"): "balance_annual",
                    ("Balance Sheet", "Quarterly"): "balance_quarterly",
                    ("Cash Flow", "Annual"): "cashflow_annual",
                    ("Cash Flow", "Quarterly"): "cashflow_quarterly",
                }
                df = fin.get(key_map[(stmt_choice, freq_choice)])

                if df is None or df.empty:
                    st.warning("Not available for this ticker.")
                else:
                    df_display = df.copy()
                    df_display.columns = [c.strftime("%b %Y") if hasattr(c, "strftime") else str(c) for c in df_display.columns]
                    st.dataframe(df_display.style.format(precision=0, na_rep="—"), use_container_width=True, height=450)

                    # Quick trend chart for key line items
                    chartable_rows = [r for r in ["Total Revenue", "Net Income", "Gross Profit", "Operating Income", "EBITDA"] if r in df.index]
                    if chartable_rows:
                        st.markdown("**Trend**")
                        row_pick = st.selectbox("Metric to chart", chartable_rows)
                        row_data = df.loc[row_pick].sort_index()
                        trend_fig = px.bar(
                            x=[c.strftime("%b %Y") if hasattr(c, "strftime") else str(c) for c in row_data.index],
                            y=row_data.values,
                            labels={"x": "Period", "y": row_pick},
                        )
                        trend_fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(trend_fig, use_container_width=True)

                    csv = df_display.to_csv().encode("utf-8")
                    st.download_button("⬇️ Download this statement as CSV", csv, f"{ticker}_{stmt_choice.replace(' ','_')}_{freq_choice}.csv", "text/csv")

            # ---- Ratios ----
            with sub_ratios:
                r1, r2, r3 = st.columns(3)
                with r1:
                    st.markdown("**Profitability**")
                    st.write(f"Gross Margin: {fmt_pct(info.get('grossMargins'))}")
                    st.write(f"Operating Margin: {fmt_pct(info.get('operatingMargins'))}")
                    st.write(f"Net Margin: {fmt_pct(info.get('profitMargins'))}")
                    st.write(f"ROE: {fmt_pct(info.get('returnOnEquity'))}")
                    st.write(f"ROA: {fmt_pct(info.get('returnOnAssets'))}")
                with r2:
                    st.markdown("**Valuation**")
                    st.write(f"P/E (TTM): {safe(info, 'trailingPE')}")
                    st.write(f"Forward P/E: {safe(info, 'forwardPE')}")
                    st.write(f"P/B: {safe(info, 'priceToBook')}")
                    st.write(f"EV/EBITDA: {safe(info, 'enterpriseToEbitda')}")
                    st.write(f"Beta: {safe(info, 'beta')}")
                with r3:
                    st.markdown("**Balance Sheet Health**")
                    st.write(f"Debt/Equity: {safe(info, 'debtToEquity')}")
                    st.write(f"Current Ratio: {safe(info, 'currentRatio')}")
                    st.write(f"Quick Ratio: {safe(info, 'quickRatio')}")
                    st.write(f"Total Debt: {fmt_crore(info.get('totalDebt'))}")
                    st.write(f"Total Cash: {fmt_crore(info.get('totalCash'))}")

                st.divider()
                g1, g2 = st.columns(2)
                g1.metric("Revenue Growth (YoY)", fmt_pct(info.get("revenueGrowth")))
                g2.metric("Earnings Growth (YoY)", fmt_pct(info.get("earningsGrowth")))

            # ---- DCF Valuation ----
            with sub_valuation:
                st.subheader("💰 Simplified Discounted Cash Flow (DCF)")
                st.warning(
                    "**Educational estimate only — not a price target or "
                    "investment advice.** This is a simplified single-stage FCF "
                    "model. Real valuation work needs segment-level forecasts, a "
                    "properly built WACC, working-capital assumptions, and "
                    "scenario analysis. Treat this as a way to see how sensitive "
                    "'fair value' is to the assumptions you feed it — not as an answer."
                )

                fcf = info.get("freeCashflow")
                shares = info.get("sharesOutstanding")

                if not fcf or not shares or fcf <= 0:
                    st.error(
                        "Cannot run a DCF here: this ticker has no positive "
                        "reported Free Cash Flow via yfinance (common for banks/"
                        "financials, which need a different model, or companies "
                        "with negative FCF)."
                    )
                else:
                    dc1, dc2, dc3, dc4 = st.columns(4)
                    default_growth = info.get("revenueGrowth")
                    default_growth = min(max(default_growth, 0.02), 0.20) if default_growth else 0.08

                    growth_input = dc1.slider("FCF growth rate (yrs 1-5)", 0.0, 0.30, float(default_growth), 0.01, key="dcf_growth")
                    discount_input = dc2.slider("Discount rate (WACC proxy)", 0.06, 0.20, 0.11, 0.005, key="dcf_disc")
                    terminal_input = dc3.slider("Terminal growth rate", 0.0, 0.06, 0.04, 0.005, key="dcf_term")
                    years_input = dc4.slider("Projection years", 3, 10, 5, 1, key="dcf_years")

                    if discount_input <= terminal_input:
                        st.caption(
                            f"⚠️ Discount rate must exceed terminal growth rate for the "
                            f"model to be valid — using {terminal_input + 0.01:.1%} as the "
                            f"effective discount rate instead of {discount_input:.1%}."
                        )

                    dcf_result = simple_dcf(
                        info, years=years_input, growth_rate=growth_input,
                        terminal_growth=terminal_input, discount_rate=discount_input,
                    )

                    if dcf_result is None:
                        st.error("Could not compute DCF with current inputs.")
                    else:
                        iv = dcf_result["intrinsic_value_per_share"]
                        cp = dcf_result["current_price"]
                        st.divider()
                        r1, r2, r3 = st.columns(3)
                        r1.metric("Estimated Intrinsic Value / Share", f"₹{iv:,.2f}")
                        r2.metric("Current Market Price", f"₹{cp:,.2f}" if cp else "N/A")
                        if cp:
                            gap_pct = (iv - cp) / cp * 100
                            r3.metric("Implied Gap", f"{gap_pct:+.1f}%", "Model above market" if gap_pct > 0 else "Model below market")

                        proj_df = pd.DataFrame(dcf_result["projected"])
                        proj_df["fcf"] = proj_df["fcf"].apply(lambda x: fmt_crore(x))
                        proj_df["pv"] = proj_df["pv"].apply(lambda x: fmt_crore(x))
                        proj_df.columns = ["Year", "Projected FCF", "Present Value"]
                        st.dataframe(proj_df.set_index("Year"), use_container_width=True)

                        st.write(f"**Terminal Value:** {fmt_crore(dcf_result['terminal_value'])}  ·  "
                                 f"**PV of Terminal Value:** {fmt_crore(dcf_result['pv_terminal'])}")
                        st.write(f"**Enterprise Value:** {fmt_crore(dcf_result['enterprise_value'])}  ·  "
                                 f"**Equity Value:** {fmt_crore(dcf_result['equity_value'])}")

                        st.caption(
                            "Method: projects Free Cash Flow forward at the growth rate, "
                            "discounts each year back to present value at the discount rate, "
                            "adds a Gordon Growth terminal value, subtracts net debt to get "
                            "equity value, then divides by shares outstanding."
                        )

            # ---- Analyst Views ----
            with sub_analyst:
                st.subheader("🎯 Analyst Price Targets & Recommendations")
                adata = get_analyst_data(ticker)

                pt = adata.get("price_targets")
                if pt:
                    pc1, pc2, pc3, pc4 = st.columns(4)
                    pc1.metric("Mean Target", f"₹{pt.get('mean'):,.2f}" if pt.get("mean") else "N/A")
                    pc2.metric("High Target", f"₹{pt.get('high'):,.2f}" if pt.get("high") else "N/A")
                    pc3.metric("Low Target", f"₹{pt.get('low'):,.2f}" if pt.get("low") else "N/A")
                    pc4.metric("Current Price", f"₹{pt.get('current'):,.2f}" if pt.get("current") else "N/A")
                else:
                    st.info("No analyst price target data available for this ticker.")

                rs = adata.get("rec_summary")
                if rs is not None and not (hasattr(rs, "empty") and rs.empty):
                    st.markdown("**Recommendation Summary (Strong Buy → Sell)**")
                    st.dataframe(rs, use_container_width=True)

                recs = adata.get("recommendations")
                if recs is not None and not (hasattr(recs, "empty") and recs.empty):
                    st.markdown("**Recent Recommendation History**")
                    st.dataframe(recs.head(15), use_container_width=True)

                ud = adata.get("upgrades_downgrades")
                if ud is not None and not (hasattr(ud, "empty") and ud.empty):
                    st.markdown("**Recent Upgrades / Downgrades**")
                    st.dataframe(ud.head(15), use_container_width=True)

                ge = adata.get("growth_estimates")
                if ge is not None and not (hasattr(ge, "empty") and ge.empty):
                    st.markdown("**Growth Estimates**")
                    st.dataframe(ge, use_container_width=True)

                if all(
                    (adata.get(k) is None or (hasattr(adata.get(k), "empty") and adata.get(k).empty))
                    for k in ["rec_summary", "recommendations", "upgrades_downgrades", "growth_estimates"]
                ) and not pt:
                    st.info("Analyst coverage data is not available for this ticker via yfinance — common for smaller/mid-cap companies with limited institutional coverage.")

            # ---- Earnings ----
            with sub_earnings:
                st.subheader("📅 Earnings")
                edata = get_earnings_data(ticker)

                edates = edata.get("earnings_dates")
                if edates is not None and not (hasattr(edates, "empty") and edates.empty):
                    st.markdown("**Earnings Dates (past & upcoming)**")
                    st.dataframe(edates, use_container_width=True)
                else:
                    st.info("No earnings date data available for this ticker.")

                ehist = edata.get("earnings_history")
                if ehist is not None and not (hasattr(ehist, "empty") and ehist.empty):
                    st.markdown("**EPS: Estimate vs Actual**")
                    st.dataframe(ehist, use_container_width=True)

                cal = edata.get("calendar")
                if cal:
                    st.markdown("**Next Earnings / Calendar**")
                    if isinstance(cal, dict):
                        cal_df = pd.DataFrame([cal])
                        st.dataframe(cal_df, use_container_width=True)
                    else:
                        st.dataframe(cal, use_container_width=True)

            # ---- Dividends & Splits ----
            with sub_dividends:
                st.subheader("💵 Dividend & Split History")
                corp = get_corp_actions(ticker)
                divs = corp.get("dividends")
                splits = corp.get("splits")

                if divs is not None and not divs.empty:
                    total_1y = divs[divs.index >= (pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=1))].sum()
                    d1, d2 = st.columns(2)
                    d1.metric("Dividend Yield (current)", fmt_pct(info.get("dividendYield")))
                    d2.metric("Dividends Paid (last 12M)", f"₹{total_1y:,.2f}/share")

                    div_fig = px.bar(x=divs.index, y=divs.values, labels={"x": "Date", "y": "Dividend (₹/share)"})
                    div_fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(div_fig, use_container_width=True)

                    with st.expander("Full dividend history"):
                        st.dataframe(divs.sort_index(ascending=False).to_frame("Dividend (₹/share)"), use_container_width=True)
                else:
                    st.info("No dividend history found for this ticker (may be a non-dividend-paying company).")

                if splits is not None and not splits.empty:
                    st.markdown("**Stock Split History**")
                    st.dataframe(splits.sort_index(ascending=False).to_frame("Split Ratio"), use_container_width=True)

            # ---- Business & Revenue (honest section) ----
            with sub_revenue:
                st.subheader("What business is it in?")
                st.write(f"**Sector:** {safe(info, 'sector')}  \n**Industry:** {safe(info, 'industry')}")
                st.write(safe(info, "longBusinessSummary", "No summary available."))

                st.divider()
                st.subheader("Revenue streams & market share")
                st.warning(
                    "**Not available via yfinance or any free API.** Segment-wise "
                    "revenue breakdowns (e.g. '60% from cloud, 40% from consumer "
                    "electronics') and market share figures are disclosed only in "
                    "the company's **Annual Report** (segment reporting note) or "
                    "investor presentations — not in stock market data feeds.\n\n"
                    "**Where to actually find this:**\n"
                    f"- Search: `{name} annual report segment revenue`\n"
                    f"- Investor relations page: {safe(info, 'website')}\n"
                    "- [Screener.in](https://www.screener.in) often has a visual "
                    "business-segment breakdown for Indian listed companies\n"
                    "- Industry reports from CRISIL, IBEF, or CareEdge for market share"
                )

            # ---- Holders ----
            with sub_holders:
                holders = get_holders(ticker)
                if holders["major"] is not None and not holders["major"].empty:
                    st.markdown("**Major Holders**")
                    st.dataframe(holders["major"], use_container_width=True)
                if holders["institutional"] is not None and not holders["institutional"].empty:
                    st.markdown("**Top Institutional Holders**")
                    st.dataframe(holders["institutional"], use_container_width=True)
                if holders["mutualfund"] is not None and not holders["mutualfund"].empty:
                    st.markdown("**Top Mutual Fund Holders**")
                    st.dataframe(holders["mutualfund"], use_container_width=True)
                if all(
                    (holders[k] is None or holders[k].empty) for k in ["major", "institutional", "mutualfund"]
                ):
                    st.info("Holder data not available for this ticker via yfinance.")

            # ---- Insider Activity ----
            with sub_insider:
                st.subheader("👤 Insider Activity")
                st.caption(
                    "Insider trading disclosure data as reported to Yahoo Finance. "
                    "Coverage for Indian (NSE) tickers is often limited or unavailable — "
                    "for authoritative insider/promoter trading data on Indian companies, "
                    "check NSE/BSE corporate announcements or Screener.in's 'shareholding' section."
                )
                idata = get_insider_data(ticker)

                trans = idata.get("transactions")
                if trans is not None and not (hasattr(trans, "empty") and trans.empty):
                    st.markdown("**Recent Insider Transactions**")
                    st.dataframe(trans, use_container_width=True)
                else:
                    st.info("No insider transaction data available for this ticker.")

                purch = idata.get("purchases")
                if purch is not None and not (hasattr(purch, "empty") and purch.empty):
                    st.markdown("**Insider Purchases Summary**")
                    st.dataframe(purch, use_container_width=True)

                roster = idata.get("roster")
                if roster is not None and not (hasattr(roster, "empty") and roster.empty):
                    st.markdown("**Insider Roster (Key Holders)**")
                    st.dataframe(roster, use_container_width=True)

            # ---- News ----
            with sub_news:
                news = get_news(ticker)
                if not news:
                    st.info("No recent news found via yfinance.")
                else:
                    for item in news[:10]:
                        title = item.get("title") or item.get("content", {}).get("title", "Untitled")
                        publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName", "")
                        link = item.get("link") or item.get("content", {}).get("clickThroughUrl", {}).get("url", "")
                        st.markdown(f"**[{title}]({link})**" if link else f"**{title}**")
                        if publisher:
                            st.caption(publisher)
                        st.divider()

# ============================== SECTOR PEERS TAB ==============================
with tab_peers:
    st.subheader("🏭 Sector Peer Benchmarking")
    st.caption(
        "Compares the selected company against other companies in this app's "
        "database that share the same Yahoo Finance sector classification. "
        "This uses sector-level tags, not a formal 'industry/market share' "
        "analysis — see the Business & Revenue tab for that distinction."
    )

    if not st.session_state.selected_ticker:
        st.info("👈 Select a company in the sidebar first, then come back here to see its sector peers.")
    else:
        base_ticker = st.session_state.selected_ticker
        base_name = st.session_state.selected_name
        base_info = get_info(base_ticker)

        if base_info is None:
            st.error("Could not fetch data for the selected company.")
        else:
            base_sector = base_info.get("sector")
            base_industry = base_info.get("industry")
            st.write(f"**{base_name}** is classified under sector **{base_sector or 'N/A'}**, industry **{base_industry or 'N/A'}**.")

            n_peers = st.slider("Number of peers to scan (from database, sorted by market cap)", 5, 40, 15)

            with st.spinner("Scanning database for sector peers... (first run may take a bit)"):
                # Sample from the company database — cap scanning to keep it fast on free tier
                sample_names = list(COMPANIES.keys())
                peer_rows = []
                scanned = 0
                max_scan = 120  # safety cap so this doesn't hammer the API on a huge db
                for pname in sample_names:
                    if scanned >= max_scan:
                        break
                    ptick = COMPANIES[pname]
                    if ptick == base_ticker:
                        continue
                    pinfo = get_info(ptick)
                    scanned += 1
                    if pinfo is None:
                        continue
                    if pinfo.get("sector") == base_sector and base_sector is not None:
                        peer_rows.append({
                            "Company": pname,
                            "Ticker": ptick,
                            "Industry": pinfo.get("industry"),
                            "Market Cap": pinfo.get("marketCap") or 0,
                            "P/E": pinfo.get("trailingPE"),
                            "ROE": pinfo.get("returnOnEquity"),
                            "Net Margin": pinfo.get("profitMargins"),
                            "Revenue Growth": pinfo.get("revenueGrowth"),
                        })
                    if len(peer_rows) >= n_peers:
                        break

            if not peer_rows:
                st.warning(
                    "No sector peers found in the scanned sample. This can happen if "
                    "the sector field is missing, or if peers weren't within the scan "
                    "limit — try increasing 'Number of peers to scan' or browse the "
                    "Directory tab manually for related companies."
                )
            else:
                peer_df = pd.DataFrame(peer_rows).sort_values("Market Cap", ascending=False)
                display_df = peer_df.copy()
                display_df["Market Cap"] = display_df["Market Cap"].apply(fmt_crore)
                display_df["ROE"] = display_df["ROE"].apply(fmt_pct)
                display_df["Net Margin"] = display_df["Net Margin"].apply(fmt_pct)
                display_df["Revenue Growth"] = display_df["Revenue Growth"].apply(fmt_pct)
                st.dataframe(display_df.set_index("Company"), use_container_width=True)

                metric_pick = st.selectbox("Chart peers by", ["Market Cap", "P/E"])
                chart_data = peer_df.copy()
                if metric_pick == "Market Cap":
                    fig = px.bar(chart_data, x="Company", y="Market Cap", color="Company")
                else:
                    fig = px.bar(chart_data.dropna(subset=["P/E"]), x="Company", y="P/E", color="Company")
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)

                csv = peer_df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download peer set as CSV", csv, f"{base_ticker}_peers.csv", "text/csv")

# ============================== COMPARE TAB ==============================
with tab_compare:
    st.subheader("Compare up to 5 companies side by side")
    default_sel = [st.session_state.selected_name] if st.session_state.selected_name else []
    compare_names = st.multiselect(
        "Select companies to compare",
        options=sorted(COMPANIES.keys()),
        default=default_sel,
        max_selections=5,
    )

    if compare_names:
        rows = []
        with st.spinner("Fetching comparison data..."):
            for cname in compare_names:
                ctick = COMPANIES[cname]
                cinfo = get_info(ctick)
                if cinfo is None:
                    continue
                rows.append({
                    "Company": cname,
                    "Ticker": ctick,
                    "Price (₹)": cinfo.get("currentPrice"),
                    "Market Cap": fmt_crore(cinfo.get("marketCap")),
                    "P/E": cinfo.get("trailingPE"),
                    "P/B": cinfo.get("priceToBook"),
                    "ROE": fmt_pct(cinfo.get("returnOnEquity")),
                    "Net Margin": fmt_pct(cinfo.get("profitMargins")),
                    "Debt/Equity": cinfo.get("debtToEquity"),
                    "Div Yield": fmt_pct(cinfo.get("dividendYield")),
                    "Revenue Growth": fmt_pct(cinfo.get("revenueGrowth")),
                })
        if rows:
            comp_df = pd.DataFrame(rows).set_index("Company")
            st.dataframe(comp_df, use_container_width=True)

            # Bar chart comparison for a chosen numeric metric
            numeric_metric = st.selectbox(
                "Chart a metric", ["Price (₹)", "P/E", "P/B", "Debt/Equity"]
            )
            chart_df = pd.DataFrame(rows)
            chart_df[numeric_metric] = pd.to_numeric(chart_df[numeric_metric], errors="coerce")
            fig = px.bar(chart_df, x="Company", y=numeric_metric, color="Company")
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)

            csv = comp_df.to_csv().encode("utf-8")
            st.download_button("⬇️ Download comparison as CSV", csv, "comparison.csv", "text/csv")
        else:
            st.warning("Could not fetch data for the selected companies.")
    else:
        st.info("Pick 2–5 companies above to compare valuation & fundamentals side by side.")

# ============================== WATCHLIST TAB ==============================
with tab_watchlist:
    st.subheader("⭐ Your Watchlist")
    if not st.session_state.watchlist:
        st.info("Your watchlist is empty. Search for a company and click 'Add to watchlist' in the sidebar.")
    else:
        rows = []
        with st.spinner("Refreshing watchlist prices..."):
            for wt in st.session_state.watchlist:
                winfo = get_info(wt)
                if winfo is None:
                    continue
                price = winfo.get("currentPrice")
                prev = winfo.get("previousClose")
                change_pct = ((price - prev) / prev * 100) if price and prev else None
                rows.append({
                    "Company": TICKER_TO_NAME.get(wt, wt),
                    "Ticker": wt,
                    "Price (₹)": price,
                    "Change %": round(change_pct, 2) if change_pct is not None else None,
                    "Market Cap": fmt_crore(winfo.get("marketCap")),
                    "P/E": winfo.get("trailingPE"),
                })
        if rows:
            wl_df = pd.DataFrame(rows).set_index("Company")
            st.dataframe(
                wl_df.style.applymap(
                    lambda v: "color: green" if isinstance(v, (int, float)) and v > 0 else (
                        "color: red" if isinstance(v, (int, float)) and v < 0 else ""
                    ),
                    subset=["Change %"],
                ),
                use_container_width=True,
            )
        note = st.caption("Note: watchlist is stored only for this browser session and resets when the app restarts.")

# ============================== DIRECTORY TAB ==============================
with tab_directory:
    st.subheader(f"📋 Full Company Directory ({company_count()} entries)")
    dir_search = st.text_input("Filter directory", placeholder="Type to filter by name or ticker...")
    dir_df = pd.DataFrame(
        [{"Company": n, "Ticker": t} for n, t in sorted(COMPANIES.items())]
    )
    if dir_search:
        mask = (
            dir_df["Company"].str.contains(dir_search, case=False)
            | dir_df["Ticker"].str.contains(dir_search, case=False)
        )
        dir_df = dir_df[mask]
    st.dataframe(dir_df, use_container_width=True, height=500)
    st.caption("To research a company, search for it in the sidebar or copy its ticker there.")

st.divider()
st.caption(
    "Data via [yfinance](https://pypi.org/project/yfinance/) / Yahoo Finance. "
    "Prices may be delayed. This tool is for informational/educational purposes "
    "only and is not investment advice."
)
