"""
app.py — Gap & Go Pre-Market Stock Screener
============================================
Free, read-only Streamlit dashboard for US equity momentum scanning.
Data sources: Yahoo Finance (yfinance + day-gainers page scrape)
Hosting: Streamlit Community Cloud (free tier)
"""

import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from io import StringIO
from typing import Optional

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gap & Go Scanner",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — Dark terminal aesthetic
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

/* ── Root palette ── */
:root {
    --bg-primary:    #090d13;
    --bg-card:       #0d1520;
    --bg-surface:    #111c2b;
    --border-dim:    #1a2d45;
    --border-bright: #1f3a56;
    --accent-green:  #00e5a0;
    --accent-amber:  #ffb800;
    --accent-red:    #ff4560;
    --accent-blue:   #3b9eff;
    --text-primary:  #e8f0fe;
    --text-secondary:#7a9ab8;
    --text-dim:      #3d5a73;
    --mono: 'Space Mono', monospace;
    --sans: 'Syne', sans-serif;
}

/* ── Global overrides ── */
html, body, [class*="css"] {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: var(--sans) !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; max-width: 1400px !important; }

/* ── Masthead ── */
.masthead {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    border-bottom: 1px solid var(--border-bright);
    padding-bottom: 0.75rem;
    margin-bottom: 0.25rem;
}
.masthead-title {
    font-family: var(--sans);
    font-weight: 800;
    font-size: 2rem;
    letter-spacing: -0.04em;
    color: var(--text-primary);
    line-height: 1;
}
.masthead-sub {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--text-secondary);
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
.ticker-badge {
    font-family: var(--mono);
    font-size: 0.65rem;
    padding: 2px 8px;
    border-radius: 2px;
    background: var(--bg-surface);
    border: 1px solid var(--border-bright);
    color: var(--accent-green);
    letter-spacing: 0.1em;
}

/* ── KPI metric cards ── */
.kpi-row { display: flex; gap: 12px; margin: 1rem 0; }
.kpi-card {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border-dim);
    border-top: 2px solid var(--accent-green);
    padding: 14px 18px;
    border-radius: 3px;
}
.kpi-label {
    font-family: var(--mono);
    font-size: 0.6rem;
    color: var(--text-dim);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.kpi-value {
    font-family: var(--mono);
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1;
}
.kpi-value.green { color: var(--accent-green); }
.kpi-value.amber { color: var(--accent-amber); }
.kpi-value.red   { color: var(--accent-red);   }

/* ── Scan button ── */
div.stButton > button {
    background: transparent !important;
    border: 1px solid var(--accent-green) !important;
    color: var(--accent-green) !important;
    font-family: var(--mono) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 10px 28px !important;
    border-radius: 2px !important;
    transition: all 0.15s ease !important;
}
div.stButton > button:hover {
    background: var(--accent-green) !important;
    color: var(--bg-primary) !important;
    box-shadow: 0 0 20px rgba(0,229,160,0.25) !important;
}

/* ── Filter sidebar / expander ── */
.stExpander {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-dim) !important;
    border-radius: 3px !important;
}

/* ── Dataframe / table ── */
.stDataFrame, iframe { background: var(--bg-card) !important; border-radius: 3px !important; }

/* ── Streamlit metrics ── */
[data-testid="metric-container"] {
    background: var(--bg-card);
    border: 1px solid var(--border-dim);
    border-top: 2px solid var(--accent-green);
    padding: 12px 16px;
    border-radius: 3px;
}
[data-testid="metric-container"] label { font-family: var(--mono) !important; font-size: 0.6rem !important; color: var(--text-dim) !important; letter-spacing: 0.15em !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { font-family: var(--mono) !important; font-size: 1.4rem !important; }

/* ── Status badges ── */
.badge-premium {
    display: inline-block;
    font-family: var(--mono);
    font-size: 0.6rem;
    padding: 2px 7px;
    background: rgba(255,184,0,0.12);
    border: 1px solid var(--accent-amber);
    color: var(--accent-amber);
    border-radius: 2px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.badge-standard {
    display: inline-block;
    font-family: var(--mono);
    font-size: 0.6rem;
    padding: 2px 7px;
    background: rgba(0,229,160,0.08);
    border: 1px solid rgba(0,229,160,0.3);
    color: var(--accent-green);
    border-radius: 2px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

/* ── Selectbox / slider ── */
.stSelectbox > div > div, .stSlider { font-family: var(--mono) !important; }
.stProgress > div > div { background-color: var(--accent-green) !important; }

/* ── Info / warning boxes ── */
.stAlert { border-radius: 3px !important; font-family: var(--mono) !important; font-size: 0.75rem !important; }

/* ── Divider ── */
hr { border-color: var(--border-dim) !important; margin: 1.2rem 0 !important; }

/* ── Scanline overlay (subtle) ── */
body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.03) 2px,
        rgba(0,0,0,0.03) 4px
    );
    pointer-events: none;
    z-index: 9999;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC UNIVERSE — NASDAQ Trader FTP (updated daily, ~5,000+ US stocks)
# ─────────────────────────────────────────────────────────────────────────────
# Two official NASDAQ pipe-delimited files list every exchange-listed US stock:
#   nasdaqlisted.txt  — NASDAQ (NMS + Small Cap + Capital Market)
#   otherlisted.txt   — NYSE, AMEX, ARCA, BATS
# Together they cover ~7,000 symbols; after filtering ~4,000 common stocks.
# Cached for 6 hours so the universe refreshes once per trading day.

NASDAQ_FILE_URL = "https://ftp.nasdaqtrader.com/dynamic/SymbolDirectory/nasdaqlisted.txt"
OTHER_FILE_URL  = "https://ftp.nasdaqtrader.com/dynamic/SymbolDirectory/otherlisted.txt"

# Fallback: the 195 manually curated tickers used before, in case both URLs fail
FALLBACK_UNIVERSE = [
    "ADTX","AGAE","AGH","AGIG","AIB","AIFF","AIM","AIMD","AIRS","ALBT",
    "AMOD","ANNA","ANY","APRE","ARAI","ARTL","ASBP","ASTC","ASTI","AUID",
    "AZTR","BATL","BCG","BENF","BFRG","BIAF","BIRD","BKKT","BKYI","BNBX",
    "BNZI","BOXL","BRN","BTBD","BTOC","BYRN","CALC","CAPS","CDIO","CETX",
    "CETY","CLDI","COCP","CODX","CURX","CYCN","CYCU","CYN","DBGI","DEVS",
    "DRCT","DRMA","EDBL","EEIQ","EFOI","ELAB","EMPD","ENSC","ENVB","EVTV",
    "EZRA","FATN","FCUV","FEED","FLYX","FRGT","FRMM","FUSE","GBR","GCTK",
    "GIPR","GLND","GNPX","GWH","GXAI","HCTI","HCWB","HIND","HOTH","IPST",
    "IPW","IVDA","JACK","JAGX","KAPA","KIDZ","KITT","KPRX","KSCP","LASE",
    "LGVN","LIMN","LNAI","LOCL","LRHC","LTRN","MAMO","MEHA","MGRX","MIGI",
    "MNTS","MRAM","MSS","MYSE","NUWE","NVVE","NXL","OBAI","OGEN","OLB",
    "OLOX","ONCO","ONFO","ONMD","OSRH","PBM","PFSA","PHGE","PHIO","PLYX",
    "POLA","PRSO","QCLS","QNCX","RENX","REVB","RIME","RMSG","ROLR","RVPH",
    "SBEV","SEGG","SER","SEV","SILO","SKYQ","SNAL","SNBR","SNYR","SOAR",
    "SOPA","SOWG","SQFT","SST","SUNE","SXTP","TBH","TNON","UGRO","USBC",
    "VEAA","VEEE","VIVS","VRME","VTAK","XHLD","XPON","XWEL","YCBD","ZSPC",
    "AKAN","AGPU","TORO","ELPW","HCAI","BEEM","GNLN","BTM","TRUG","NUCL",
    "LWLG","PLRZ","TRT","HELP","NVTS","WSHP","WTI","CGC","ACTU","CVV",
    "REPL","NSRX","STI","FGI","SRAD","VTIX","NN","AMST","PALI","SMX",
    "CAST","TMDE",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    )
}


@st.cache_data(ttl=3600 * 6, show_spinner=False)
def fetch_gainer_tickers() -> list[str]:
    """
    Downloads ALL US-listed common stocks from NASDAQ's official symbol files.
    Returns a deduplicated list of clean 1-5 letter tickers.

    Filters applied at build time:
    • Excludes test issues (Test Issue == 'Y')
    • Excludes ETFs (ETF == 'Y')
    • Excludes warrants, units, rights (symbol ends with W/WS/R/U or contains $)
    • Keeps only symbols matching [A-Z]{1,5}

    Result: ~4,000–5,000 common stocks, cached for 6 hours.
    Falls back to the 195-ticker manual list if both URLs fail.
    """
    import re
    tickers: set[str] = set()

    def clean_sym(s: str) -> Optional[str]:
        if not isinstance(s, str):
            return None
        s = s.strip().upper()
        if not re.fullmatch(r'[A-Z]{1,5}', s):
            return None
        if s.endswith(("W", "WS", "R", "U")) and len(s) > 1:
            return None
        return s

    # ── NASDAQ listed ────────────────────────────────────────────────────
    try:
        resp = requests.get(NASDAQ_FILE_URL, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text), sep='|')
            # Drop the last summary row (starts with "File Creation Time")
            df = df[~df["Symbol"].astype(str).str.startswith("File")]
            # Filter out test issues and ETFs
            if "Test Issue" in df.columns:
                df = df[df["Test Issue"] != "Y"]
            if "ETF" in df.columns:
                df = df[df["ETF"] != "Y"]
            for sym in df["Symbol"]:
                clean = clean_sym(sym)
                if clean:
                    tickers.add(clean)
    except Exception:
        pass

    # ── NYSE / AMEX / ARCA (otherlisted) ────────────────────────────────
    try:
        resp = requests.get(OTHER_FILE_URL, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text), sep='|')
            df = df[~df["ACT Symbol"].astype(str).str.startswith("File")]
            if "Test Issue" in df.columns:
                df = df[df["Test Issue"] != "Y"]
            if "ETF" in df.columns:
                df = df[df["ETF"] != "Y"]
            # "Exchange" column: N=NYSE, A=AMEX, P=ARCA, Z=BATS, V=IEX
            # Exclude non-US exchanges if present
            for sym in df["ACT Symbol"]:
                clean = clean_sym(sym)
                if clean:
                    tickers.add(clean)
    except Exception:
        pass

    if not tickers:
        # Both downloads failed — use hardcoded fallback
        return list(FALLBACK_UNIVERSE)

    result = sorted(tickers)
    return result


def _quick_price(ticker: str) -> Optional[dict]:
    """Phase 1: fast_info only — lightweight, includes pre-market price."""
    try:
        fi    = yf.Ticker(ticker).fast_info
        prev  = _safe_float(fi.previous_close)
        price = _safe_float(fi.last_price)
        vol   = _safe_float(fi.last_volume)
        if prev and price:
            return {"prev_close": prev, "current_price": price, "volume": vol}
        return None
    except Exception:
        return None


def run_scan(min_price, max_price, min_gap_pct, min_volume, max_float,
             progress_bar, status_text):
    """
    Two-phase scan for large universes (4,000+ tickers):
    Phase 1: fast_info (8 threads) for ALL tickers → filter by price/gap/vol
    Phase 2: .info for survivors only (~5-20 tickers) → float/SI/country
    """
    def msg(text, color="#00e5a0"):
        status_text.markdown(
            f'<span style="font-family:\'Space Mono\',monospace;'
            f'font-size:0.75rem;color:{color};">{text}</span>',
            unsafe_allow_html=True)

    msg("▶ LOADING UNIVERSE…")
    progress_bar.progress(2)
    tickers = fetch_gainer_tickers()
    total   = len(tickers)
    msg(f"▶ PHASE 1/2 — PRICE SCAN ({total:,} tickers)…")
    progress_bar.progress(5)

    pre_pass: list       = []
    rejected_counts: dict = {}
    done = 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_quick_price, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            done  += 1
            progress_bar.progress(5 + int((done / total) * 70))
            try:
                data = future.result()
            except Exception:
                rejected_counts["Error"] = rejected_counts.get("Error", 0) + 1
                continue
            if not data:
                rejected_counts["No data"] = rejected_counts.get("No data", 0) + 1
                continue
            pv   = data["current_price"]
            prev = data["prev_close"]
            vol  = data.get("volume")
            if not (min_price <= pv <= max_price):
                rejected_counts["Price"] = rejected_counts.get("Price", 0) + 1
                continue
            if ((pv - prev) / prev * 100) < min_gap_pct:
                rejected_counts["Gap"] = rejected_counts.get("Gap", 0) + 1
                continue
            if vol is not None and vol < min_volume:
                rejected_counts["Volume"] = rejected_counts.get("Volume", 0) + 1
                continue
            pre_pass.append((ticker, data))

    n_pre = len(pre_pass)
    msg(f"▶ PHASE 2/2 — DETAIL FETCH ({n_pre} survivors)…")
    progress_bar.progress(78)

    results = []
    for i, (ticker, price_data) in enumerate(pre_pass):
        progress_bar.progress(78 + int((i / max(n_pre, 1)) * 18))
        try:
            info         = yf.Ticker(ticker).info
            float_shares = _safe_float(info.get("floatShares"))
            market_cap   = _safe_float(info.get("marketCap"))
            si_raw       = _safe_float(info.get("shortPercentOfFloat"))
            avg_vol      = _safe_float(info.get("averageVolume10days") or
                                       info.get("averageDailyVolume10Day"))
            country      = info.get("country", "")
            quote_type   = info.get("quoteType", "")
            exchange     = info.get("exchange", "")
        except Exception:
            float_shares = market_cap = si_raw = avg_vol = None
            country = quote_type = exchange = ""

        qt = quote_type.upper()
        if qt and qt not in ("EQUITY", ""):
            rejected_counts["Not equity"] = rejected_counts.get("Not equity", 0) + 1
            continue
        ctry = country.lower()
        if ctry and ctry not in ("united states", "us", "usa", ""):
            rejected_counts["Non-US"] = rejected_counts.get("Non-US", 0) + 1
            continue
        if float_shares is not None and float_shares > max_float:
            rejected_counts["Float"] = rejected_counts.get("Float", 0) + 1
            continue

        pv         = price_data["current_price"]
        prev_close = price_data["prev_close"]
        vol        = price_data.get("volume")
        gap_pct    = (pv - prev_close) / prev_close * 100
        float_tier = ("🔥 PREMIUM" if (float_shares and float_shares < 5_000_000) else
                      "✅ LOW"     if (float_shares and float_shares < 20_000_000) else "N/A")
        rvol   = round(vol / avg_vol, 1) if (vol and avg_vol and avg_vol > 0) else None
        si_pct = None
        if si_raw is not None:
            si_pct = si_raw * 100 if si_raw < 1 else si_raw

        results.append({
            "Ticker":     ticker,
            "Price":      pv,
            "Prev Close": prev_close,
            "Gap %":      round(gap_pct, 2),
            "Volume":     int(vol) if vol else None,
            "RVOL":       rvol,
            "Float":      int(float_shares) if float_shares else None,
            "Float Tier": float_tier,
            "Short %":    round(si_pct, 1) if si_pct else None,
            "Market Cap": market_cap,
            "Exchange":   exchange,
        })

    progress_bar.progress(100)
    msg(f"✓ DONE — {len(results)} candidates from {total:,} tickers scanned")
    st.session_state["last_rejected"]     = rejected_counts
    st.session_state["last_scan_time"]    = datetime.now().strftime("%H:%M:%S")
    st.session_state["last_ticker_count"] = total
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)
    df["_s"] = df["Float Tier"].map({"🔥 PREMIUM": 0, "✅ LOW": 1, "N/A": 2})
    df = df.sort_values(["_s", "Gap %"], ascending=[True, False]).drop("_s", axis=1)
    return df.reset_index(drop=True)


# DISPLAY HELPERS
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def style_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """
    Apply color-coding:
    • Rows where Float < 5M → amber highlight (premium setup)
    • Gap % column → green gradient
    • RVOL column → green gradient
    """

    def highlight_row(row):
        flt = row.get("Float")
        base = "background-color: #0d1520; color: #e8f0fe;"
        if flt is not None and flt < 5_000_000:
            return [
                "background-color: #1a1500; border-left: 3px solid #ffb800; color: #ffe082;"
            ] * len(row)
        return [base] * len(row)

    def color_gap(val):
        if val is None or not isinstance(val, (int, float)): return ""
        if val >= 100: return "color: #ff4560; font-weight: 700;"
        if val >= 50:  return "color: #ffb800; font-weight: 700;"
        if val >= 20:  return "color: #00e5a0; font-weight: 600;"
        return "color: #7a9ab8;"

    def color_rvol(val):
        if val is None or not isinstance(val, (int, float)): return ""
        if val >= 10:  return "color: #ff4560; font-weight: 700;"
        if val >= 5:   return "color: #ffb800; font-weight: 600;"
        return "color: #7a9ab8;"

    # Build display copy with formatted strings
    disp = df.copy()
    disp["Price"]      = disp["Price"].apply(_fmt_currency)
    disp["Prev Close"] = disp["Prev Close"].apply(_fmt_currency)
    disp["Gap %"]      = disp["Gap %"].apply(lambda x: f"+{x:.1f}%" if x else "N/A")
    disp["Volume"]     = disp["Volume"].apply(_fmt_volume)
    disp["RVOL"]       = disp["RVOL"].apply(lambda x: f"{x:.1f}x" if x else "N/A")
    disp["Float"]      = disp["Float"].apply(_fmt_float_shares)
    disp["Short %"]    = disp["Short %"].apply(lambda x: f"{x:.1f}%" if x else "N/A")
    disp["Market Cap"] = disp["Market Cap"].apply(_fmt_market_cap)

    styler = (
        disp.style
        .apply(highlight_row, axis=1)
        .applymap(color_gap,  subset=["Gap %"])
        .applymap(color_rvol, subset=["RVOL"])
        .set_properties(**{
            "font-family":  "'Space Mono', monospace",
            "font-size":    "0.75rem",
            "border":       "1px solid #1a2d45",
            "padding":      "6px 12px",
        })
        .set_table_styles([
            {
                "selector": "th",
                "props": [
                    ("background-color", "#0d1520"),
                    ("color", "#7a9ab8"),
                    ("font-family", "'Space Mono', monospace"),
                    ("font-size", "0.65rem"),
                    ("letter-spacing", "0.12em"),
                    ("text-transform", "uppercase"),
                    ("border-bottom", "2px solid #1f3a56"),
                    ("padding", "8px 12px"),
                ]
            },
            {
                "selector": "td",
                "props": [("border-color", "#1a2d45")]
            },
        ])
    )
    return styler


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — SCAN PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<p style="font-family:\'Space Mono\',monospace;font-size:0.6rem;'
        'color:#3d5a73;letter-spacing:0.18em;text-transform:uppercase;'
        'margin-bottom:0.5rem;">SCAN PARAMETERS</p>',
        unsafe_allow_html=True,
    )

    min_price = st.slider("Min Price ($)", 0.5, 5.0, 1.0, 0.5)
    max_price = st.slider("Max Price ($)", 5.0, 30.0, 15.0, 1.0)
    min_gap   = st.slider("Min Gap Up (%)", 10, 100, 20, 5)
    min_vol   = st.select_slider(
        "Min Volume",
        options=[100_000, 250_000, 500_000, 750_000, 1_000_000, 2_000_000],
        value=500_000,
        format_func=_fmt_volume,
    )
    max_float = st.select_slider(
        "Max Float (shares)",
        options=[1_000_000, 2_000_000, 5_000_000, 10_000_000, 20_000_000, 50_000_000],
        value=20_000_000,
        format_func=_fmt_float_shares,
    )

    st.divider()
    st.markdown(
        '<p style="font-family:\'Space Mono\',monospace;font-size:0.6rem;'
        'color:#3d5a73;letter-spacing:0.15em;">DATA SOURCE</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Space Mono\',monospace;font-size:0.65rem;'
        'color:#7a9ab8;">Yahoo Finance (yfinance)<br/>No API key required</p>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        '<p style="font-family:\'Space Mono\',monospace;font-size:0.55rem;'
        'color:#3d5a73;line-height:1.6;">⚠ For educational use only.<br/>'
        'Not financial advice. Data may<br/>be delayed 15–20 min.</p>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MASTHEAD
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="masthead">
  <span class="masthead-title">GAP & GO</span>
  <span class="masthead-sub">Pre-Market Scanner</span>
  <span style="flex:1;"></span>
  <span class="ticker-badge">US EQUITIES ONLY</span>
  <span class="ticker-badge">READ-ONLY</span>
</div>
""", unsafe_allow_html=True)

now_et = datetime.now()  # Server time (cloud is UTC; note this)
col_date, col_time, col_spacer = st.columns([2, 2, 6])
col_date.markdown(
    f'<span style="font-family:\'Space Mono\',monospace;font-size:0.65rem;'
    f'color:#3d5a73;">{now_et.strftime("%A, %B %d %Y")}</span>',
    unsafe_allow_html=True,
)
col_time.markdown(
    f'<span style="font-family:\'Space Mono\',monospace;font-size:0.65rem;'
    f'color:#3d5a73;">{now_et.strftime("%H:%M:%S")} UTC</span>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SCAN TRIGGER
# ─────────────────────────────────────────────────────────────────────────────

col_btn, col_status = st.columns([2, 8])
with col_btn:
    scan_clicked = st.button("⬡  SCAN PRE-MARKET", use_container_width=True)

status_placeholder = col_status.empty()
progress_placeholder = st.empty()

if scan_clicked:
    progress_bar = progress_placeholder.progress(0)
    df_results = run_scan(
        min_price   = min_price,
        max_price   = max_price,
        min_gap_pct = min_gap,
        min_volume  = min_vol,
        max_float   = max_float,
        progress_bar = progress_bar,
        status_text  = status_placeholder,
    )
    st.session_state["scan_results"] = df_results


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

if "scan_results" in st.session_state and st.session_state["scan_results"] is not None:
    df = st.session_state["scan_results"]

    # ── KPI row ────────────────────────────────────────────────────────
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)

    last_time  = st.session_state.get("last_scan_time", "—")
    total_seen = st.session_state.get("last_ticker_count", 0)
    n_results  = len(df)
    n_premium  = len(df[df["Float Tier"] == "🔥 PREMIUM"]) if not df.empty else 0
    top_gap    = df["Gap %"].max() if not df.empty and "Gap %" in df.columns else None

    with k1:
        st.metric("SCAN TIME (UTC)", last_time)
    with k2:
        st.metric("TICKERS SCANNED", f"{total_seen:,}")
    with k3:
        st.metric("CANDIDATES", n_results)
    with k4:
        st.metric("PREMIUM SETUPS", n_premium, help="Float < 5M shares")
    with k5:
        st.metric("TOP GAP", f"+{top_gap:.1f}%" if top_gap else "—")

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if df.empty:
        st.markdown(
            '<div style="background:#0d1520;border:1px solid #1a2d45;border-left:3px solid #ff4560;'
            'padding:16px 20px;border-radius:3px;font-family:\'Space Mono\',monospace;font-size:0.75rem;'
            'color:#7a9ab8;">NO CANDIDATES FOUND matching current filter criteria.<br/>'
            'Consider loosening the Gap % or Volume thresholds, or wait until pre-market activity increases.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        # ── Legend ────────────────────────────────────────────────────
        st.markdown(
            '<div style="display:flex;gap:12px;margin-bottom:8px;align-items:center;">'
            '<span style="font-family:\'Space Mono\',monospace;font-size:0.6rem;color:#3d5a73;'
            'letter-spacing:0.12em;text-transform:uppercase;">FLOAT TIER:</span>'
            '<span style="font-size:0.7rem;background:rgba(255,184,0,0.12);border:1px solid #ffb800;'
            'color:#ffb800;padding:2px 8px;border-radius:2px;font-family:\'Space Mono\',monospace;">'
            '🔥 PREMIUM — &lt;5M shares</span>'
            '<span style="font-size:0.7rem;background:rgba(0,229,160,0.08);border:1px solid rgba(0,229,160,0.3);'
            'color:#00e5a0;padding:2px 8px;border-radius:2px;font-family:\'Space Mono\',monospace;">'
            '✅ LOW — 5M–20M shares</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Styled table ──────────────────────────────────────────────
        styled = style_dataframe(df)
        st.dataframe(
            styled,
            use_container_width = True,
            hide_index          = True,
            height              = min(600, 55 + len(df) * 38),
        )

        # ── Download ──────────────────────────────────────────────────
        csv = df.to_csv(index=False)
        dl_col, _ = st.columns([2, 8])
        dl_col.download_button(
            label    = "⬇  EXPORT CSV",
            data     = csv,
            file_name = f"gap_go_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime     = "text/csv",
        )

        # ── Rejection breakdown ───────────────────────────────────────
        rejected = st.session_state.get("last_rejected", {})
        if rejected:
            with st.expander("📊  Filter rejection breakdown"):
                rdf = pd.DataFrame(
                    {"Reason": list(rejected.keys()), "Count": list(rejected.values())}
                ).sort_values("Count", ascending=False)
                st.dataframe(rdf, use_container_width=True, hide_index=True, height=200)

else:
    # ── Welcome state ───────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-top:2rem;background:#0d1520;border:1px solid #1a2d45;
    border-left:3px solid #00e5a0;padding:24px 28px;border-radius:3px;
    max-width:680px;">
      <p style="font-family:'Space Mono',monospace;font-size:0.65rem;
      color:#3d5a73;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:12px;">
      HOW TO USE</p>
      <p style="font-family:'Space Mono',monospace;font-size:0.75rem;color:#7a9ab8;
      line-height:1.8;margin:0;">
      1. Adjust scan parameters in the sidebar (or use defaults).<br/>
      2. Press <span style="color:#00e5a0;font-weight:700;">SCAN PRE-MARKET</span>
         during the 4:00–9:30 AM ET pre-market window.<br/>
      3. Review candidates sorted by Float Tier → Gap %.<br/>
      4. 🔥 <span style="color:#ffb800;font-weight:700;">PREMIUM</span> rows =
         float &lt; 5M shares (highest momentum potential).<br/>
      5. Export results to CSV for further analysis.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1rem;background:#0d1520;border:1px solid #1a2d45;
    border-top:2px solid #1f3a56;padding:20px 28px;border-radius:3px;max-width:680px;">
      <p style="font-family:'Space Mono',monospace;font-size:0.65rem;
      color:#3d5a73;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px;">
      SCAN CRITERIA ACTIVE</p>
      <p style="font-family:'Space Mono',monospace;font-size:0.72rem;color:#7a9ab8;
      line-height:2.0;margin:0;">
      ▸ US Equities Only (NYSE / NASDAQ / AMEX)<br/>
      ▸ Price: $1.00 – $15.00<br/>
      ▸ Pre-Market Gap Up: ≥ +20%<br/>
      ▸ Volume: &gt; 500,000 shares<br/>
      ▸ Float: &lt; 20,000,000 shares
      </p>
    </div>
    """, unsafe_allow_html=True)
