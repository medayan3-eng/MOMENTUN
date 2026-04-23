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
from typing import Optional

import pandas as pd
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
REQUEST_DELAY = 0.35   # seconds between yfinance calls — polite pacing

# ─────────────────────────────────────────────────────────────────────────────
# TICKER UNIVERSE — 196 tickers
# Sources:
#   • Finviz Screener (163): cap:microunder | geo:usa | sh_avgvol:o500 | sh_float:u20
#   • Manual additions (33): gainers/losers $1–$20 spotted on 22/04
# ─────────────────────────────────────────────────────────────────────────────
FINVIZ_UNIVERSE = [
    # ── Original Finviz 163 ──────────────────────────────────────────────
    # 1–20
    "ADTX", "AGAE", "AGH",  "AGIG", "AIB",  "AIFF", "AIM",  "AIMD",
    "AIRS", "ALBT", "AMOD", "ANNA", "ANY",  "APRE", "ARAI", "ARTL",
    "ASBP", "ASTC", "ASTI", "AUID",
    # 21–40
    "AZTR", "BATL", "BCG",  "BENF", "BFRG", "BIAF", "BIRD", "BKKT",
    "BKYI", "BNBX", "BNZI", "BOXL", "BRN",  "BTBD", "BTOC", "BYRN",
    "CALC", "CAPS", "CDIO", "CETX",
    # 41–60
    "CETY", "CLDI", "COCP", "CODX", "CURX", "CYCN", "CYCU", "CYN",
    "DBGI", "DEVS", "DRCT", "DRMA", "EDBL", "EEIQ", "EFOI", "ELAB",
    "EMPD", "ENSC", "ENVB", "EVTV",
    # 61–80
    "EZRA", "FATN", "FCUV", "FEED", "FLYX", "FRGT", "FRMM", "FUSE",
    "GBR",  "GCTK", "GIPR", "GLND", "GNPX", "GWH",  "GXAI", "HCTI",
    "HCWB", "HIND", "HOTH", "IPST",
    # 81–100
    "IPW",  "IVDA", "JACK", "JAGX", "KAPA", "KIDZ", "KITT", "KPRX",
    "KSCP", "LASE", "LGVN", "LIMN", "LNAI", "LOCL", "LRHC", "LTRN",
    "MAMO", "MEHA", "MGRX", "MIGI",
    # 101–120
    "MNTS", "MRAM", "MSS",  "MYSE", "MYXXU","NUWE", "NVVE", "NXL",
    "OBAI", "OGEN", "OLB",  "OLOX", "ONCO", "ONFO", "ONMD", "OSRH",
    "PBM",  "PFSA", "PHGE", "PHIO",
    # 121–140
    "PLYX", "POLA", "PRSO", "QCLS", "QNCX", "QVCGA","RENX", "REVB",
    "RIME", "RMSG", "ROLR", "RVPH", "SBEV", "SEGG", "SER",  "SEV",
    "SILO", "SKYQ", "SLAI", "SNAL",
    # 141–160
    "SNBR", "SNYR", "SOAR", "SOPA", "SOWG", "SQFT", "SST",  "SUNE",
    "SXTP", "TBH",  "TNON", "UGRO", "USBC", "VEAA", "VEEE", "VIVS",
    "VRME", "VTAK", "XHLD", "XPON",
    # 161–163
    "XWEL", "YCBD", "ZSPC",

    # ── Manual additions 22/04 — gainers $1–$20 ─────────────────────────
    "AKAN",   # Akanda           $10.21  +214%
    "AGPU",   # Axe Compute       $8.75   +79%
    "TORO",   # Toro Corp         $6.76   +73%
    "ELPW",   # eLong Power       $2.59   +65%
    "HCAI",   # Huachen AI        $9.74   +43%
    "BEEM",   # Beem Global       $1.97   +30%
    "GNLN",   # Greenline Hold    $5.53   +41%
    "BTM",    # Bitcoin Depot     $7.60   +18%
    "TRUG",   # Trugolf Hold      $2.76   +18%
    "NUCL",   # Eagle Nuclear    $12.46   +18%
    "LWLG",   # Lightwave Logic  $15.16   +17%
    "PLRZ",   # Polyrizon        $14.64   +17%
    "TRT",    # Trio-Tech Intl    $8.26   +17%
    "HELP",   # Cybin             $5.77   +17%
    "NVTS",   # Navitas Semi     $18.47   +20%
    "WSHP",   # WeShop Hold      $12.11   +20%
    "WTI",    # W&T Offshore      $3.90   +20%
    "CGC",    # Canopy Growth     $1.38   +21%
    "ACTU",   # Actuate Therap    $2.78   +23%
    "CVV",    # CVD Equipment     $5.82   +22%
    "REPL",   # Replimune Grp     $2.27   +22%
    "NSRX",   # Nasus Pharma      $3.89   +22%

    # ── Manual additions 22/04 — losers $1–$20 ──────────────────────────
    "STI",    # Solidion Tech     $4.02   -32%
    "FGI",    # FGI Industries    $7.70   -32%
    "SRAD",   # Sportradar Grp   $13.04   -23%
    "VTIX",   # Virtuix Hold      $5.26   -21%
    "NN",     # NextNav Acq      $17.57   -22%
    "AMST",   # Amssite           $1.08   -17%
    "PALI",   # Palisades Bio     $2.34   -16%
    "SMX",    # SMX Security      $3.68   -15%
    "CAST",   # Freecast          $2.35   -14%
    "TMDE",   # TMD Energy        $1.25   -14%
]


# ─────────────────────────────────────────────────────────────────────────────
# DATA LAYER
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    """Convert any value to float or return None."""
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _fmt_volume(v) -> str:
    if v is None: return "N/A"
    v = int(v)
    if v >= 1_000_000: return f"{v/1_000_000:.2f}M"
    if v >= 1_000:     return f"{v/1_000:.1f}K"
    return str(v)


def _fmt_float_shares(v) -> str:
    if v is None: return "N/A"
    v = int(v)
    if v >= 1_000_000: return f"{v/1_000_000:.2f}M"
    return f"{v:,}"


def _fmt_currency(v) -> str:
    if v is None: return "N/A"
    return f"${float(v):.2f}"


def _fmt_market_cap(v) -> str:
    if v is None: return "N/A"
    v = float(v)
    if v >= 1e9:  return f"${v/1e9:.2f}B"
    if v >= 1e6:  return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"


def fetch_gainer_tickers() -> list[str]:
    """
    Returns the hardcoded Finviz universe of 163 pre-filtered US micro-cap
    tickers (float < 20M, avg vol > 500K, price $1–$15, US only).
    No scraping needed — no rate limits, no failures, instant return.
    """
    return list(FINVIZ_UNIVERSE)


def _scan_single_ticker(ticker: str) -> Optional[dict]:
    """
    Fetches ALL data for one ticker in a single .info call.
    Returns a complete dict or None on failure.
    preMarketPrice is returned when market is in pre-market session.
    """
    try:
        info = yf.Ticker(ticker).info
        pm_price  = _safe_float(info.get("preMarketPrice"))
        reg_price = _safe_float(info.get("regularMarketPrice") or info.get("currentPrice"))
        current_price = (pm_price if pm_price and pm_price > 0 else reg_price)
        prev_close    = _safe_float(info.get("regularMarketPreviousClose") or info.get("previousClose"))
        if not current_price or not prev_close:
            return None
        si_raw = _safe_float(info.get("shortPercentOfFloat"))
        return {
            "ticker":        ticker,
            "current_price": current_price,
            "prev_close":    prev_close,
            "volume":        _safe_float(info.get("regularMarketVolume") or info.get("volume")),
            "float_shares":  _safe_float(info.get("floatShares")),
            "market_cap":    _safe_float(info.get("marketCap")),
            "short_pct":     si_raw,
            "avg_vol_10d":   _safe_float(info.get("averageVolume10days") or info.get("averageDailyVolume10Day")),
            "country":       info.get("country", ""),
            "exchange":      info.get("exchange", ""),
            "quote_type":    info.get("quoteType", ""),
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# FILTER ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def apply_filters(raw, min_price=1.0, max_price=20.0, min_gap_pct=20.0,
                  min_volume=500_000, max_float=20_000_000):
    qt = (raw.get("quote_type") or "").upper()
    if qt and qt not in ("EQUITY", ""):
        return False, "Not equity"
    country = (raw.get("country") or "").lower()
    if country and country not in ("united states", "us", "usa", ""):
        return False, "Non-US"
    price = raw.get("current_price")
    if not price:
        return False, "No price"
    if not (min_price <= price <= max_price):
        return False, "Price"
    prev = raw.get("prev_close")
    if not prev or prev <= 0:
        return False, "No prev close"
    if ((price - prev) / prev * 100) < min_gap_pct:
        return False, "Gap"
    vol = raw.get("volume")
    if vol is not None and vol < min_volume:
        return False, "Volume"
    flt = raw.get("float_shares")
    if flt is not None and flt > max_float:
        return False, "Float"
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCAN — single-phase, 8 threads, no external batch calls
# ─────────────────────────────────────────────────────────────────────────────

def run_scan(min_price, max_price, min_gap_pct, min_volume, max_float,
             progress_bar, status_text):
    def msg(text, color="#00e5a0"):
        status_text.markdown(
            f'<span style="font-family:\'Space Mono\',monospace;font-size:0.75rem;color:{color};">{text}</span>',
            unsafe_allow_html=True)

    tickers = fetch_gainer_tickers()
    total   = len(tickers)
    msg(f"▶ SCANNING {total} TICKERS — 8 threads…")
    progress_bar.progress(5)

    results = []
    rejected_counts: dict[str, int] = {}
    done = 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_scan_single_ticker, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            done  += 1
            progress_bar.progress(5 + int((done / total) * 88))
            try:
                raw = future.result()
            except Exception:
                rejected_counts["Error"] = rejected_counts.get("Error", 0) + 1
                continue
            if raw is None:
                rejected_counts["No data"] = rejected_counts.get("No data", 0) + 1
                continue
            passes, reason = apply_filters(raw, min_price, max_price,
                                            min_gap_pct, min_volume, max_float)
            if not passes:
                rejected_counts[reason] = rejected_counts.get(reason, 0) + 1
                continue

            price_val    = raw["current_price"]
            prev_close   = raw["prev_close"]
            gap_pct      = (price_val - prev_close) / prev_close * 100
            float_shares = raw.get("float_shares")
            vol          = raw.get("volume")
            avg_vol      = raw.get("avg_vol_10d")
            si_raw       = raw.get("short_pct")
            float_tier   = ("🔥 PREMIUM" if (float_shares and float_shares < 5_000_000) else
                            "✅ LOW"     if (float_shares and float_shares < 20_000_000) else "N/A")
            rvol   = round(vol / avg_vol, 1) if (vol and avg_vol and avg_vol > 0) else None
            si_pct = None
            if si_raw is not None:
                si_pct = si_raw * 100 if si_raw < 1 else si_raw
            results.append({
                "Ticker":     ticker,
                "Price":      price_val,
                "Prev Close": prev_close,
                "Gap %":      round(gap_pct, 2),
                "Volume":     int(vol) if vol else None,
                "RVOL":       rvol,
                "Float":      int(float_shares) if float_shares else None,
                "Float Tier": float_tier,
                "Short %":    round(si_pct, 1) if si_pct else None,
                "Market Cap": raw.get("market_cap"),
                "Exchange":   raw.get("exchange", ""),
            })

    progress_bar.progress(100)
    msg(f"✓ DONE — {len(results)} candidates from {total} tickers")
    st.session_state["last_rejected"]     = rejected_counts
    st.session_state["last_scan_time"]    = datetime.now().strftime("%H:%M:%S")
    st.session_state["last_ticker_count"] = total
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)
    df["_s"] = df["Float Tier"].map({"🔥 PREMIUM": 0, "✅ LOW": 1, "N/A": 2})
    df = df.sort_values(["_s", "Gap %"], ascending=[True, False]).drop("_s", axis=1)
    return df.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
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
