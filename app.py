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
    "This app shows what's genuinely available: profile, financials, ratios, "
    "and price data, and points you elsewhere for the rest."
)

# --------------------------------------------------------------------------
# Main area
# --------------------------------------------------------------------------

st.title("Indian Stock Market Research")

tab_research, tab_compare, tab_watchlist, tab_directory = st.tabs(
    ["🔍 Research", "⚖️ Compare", "⭐ Watchlist", "📋 Directory"]
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

            sub_overview, sub_price, sub_financials, sub_ratios, sub_revenue, sub_holders, sub_news = st.tabs(
                ["Overview", "Price Chart", "Financial Statements", "Ratios", "Business & Revenue", "Holders", "News"]
            )

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

            # ---- Price Chart ----
            with sub_price:
                period_map = {
                    "1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo",
                    "1 Year": "1y", "2 Years": "2y", "5 Years": "5y", "Max": "max",
                }
                period_label = st.select_slider("Period", options=list(period_map.keys()), value="1 Year")
                hist = get_history(ticker, period_map[period_label])

                if hist.empty:
                    st.warning("No price history available.")
                else:
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=hist.index, open=hist["Open"], high=hist["High"],
                        low=hist["Low"], close=hist["Close"], name=ticker,
                    ))
                    fig.update_layout(
                        height=450, xaxis_rangeslider_visible=False,
                        margin=dict(l=10, r=10, t=30, b=10),
                        yaxis_title="Price (₹)",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    vol_fig = px.bar(hist, x=hist.index, y="Volume", height=180)
                    vol_fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Volume")
                    st.plotly_chart(vol_fig, use_container_width=True)

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
