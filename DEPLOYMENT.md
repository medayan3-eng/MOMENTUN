# Gap & Go Scanner — Deployment Guide
## GitHub → Streamlit Community Cloud (Free Hosting)

---

## What You're Deploying

| File | Purpose |
|---|---|
| `app.py` | The full Streamlit application |
| `requirements.txt` | Python dependencies (auto-installed by Streamlit Cloud) |

No `.env` files, API keys, or secrets are needed — all data is fetched freely via yfinance and Yahoo Finance.

---

## Step 1 — Create a GitHub Repository

1. Go to **https://github.com/new**
2. Set the repository name to something like `gap-go-scanner`
3. Set visibility to **Public** *(required for the free Streamlit tier)*
4. Click **Create repository** — leave it empty for now

---

## Step 2 — Push Your Files to GitHub

### Option A — GitHub Web UI (No terminal needed)

1. In your new repository, click **Add file → Upload files**
2. Drag and drop both `app.py` and `requirements.txt`
3. Scroll down, leave the commit message as-is, and click **Commit changes**

### Option B — Git CLI

```bash
# Clone your new empty repo (replace YOUR_USERNAME)
git clone https://github.com/YOUR_USERNAME/gap-go-scanner.git
cd gap-go-scanner

# Copy app.py and requirements.txt into this folder, then:
git add app.py requirements.txt
git commit -m "Initial commit: Gap & Go Scanner"
git push origin main
```

After this step your repository structure should look like:
```
gap-go-scanner/
├── app.py
└── requirements.txt
```

---

## Step 3 — Deploy on Streamlit Community Cloud

1. Go to **https://share.streamlit.io** and sign in with your GitHub account
2. Click **New app** (top right)
3. Fill in the form:

| Field | Value |
|---|---|
| **Repository** | `YOUR_USERNAME/gap-go-scanner` |
| **Branch** | `main` |
| **Main file path** | `app.py` |
| **App URL** (optional) | `gap-go-scanner` *(or any slug you want)* |

4. Click **Deploy!**

Streamlit Cloud will:
- Clone your repo
- Install all packages from `requirements.txt` (takes ~2 min on first deploy)
- Launch your app at `https://YOUR_USERNAME-gap-go-scanner-app-XXXXX.streamlit.app`

---

## Step 4 — Verify the Deployment

1. Open the app URL in your browser
2. You should see the dark "GAP & GO" masthead
3. Click **SCAN PRE-MARKET** — the scan runs best between **4:00 AM – 9:30 AM ET**
4. Outside those hours, the gap filter will likely return 0 results (since gap-ups are a pre-market phenomenon)

---

## Updating the App Later

Any push to your `main` branch automatically triggers a re-deploy:

```bash
# Edit app.py locally, then:
git add app.py
git commit -m "Update: tweak filter logic"
git push origin main
```

Streamlit Cloud detects the push and re-deploys within ~60 seconds.

---

## Troubleshooting

### App crashes on startup
- Check the **Logs** tab in your Streamlit Cloud dashboard
- Most likely cause: a missing package. Add it to `requirements.txt` and push.

### Scan returns 0 results
- Run during pre-market hours (4:00–9:30 AM ET on US trading days)
- Try loosening filters: lower Gap % to 10%, raise Max Float to 50M
- Yahoo Finance occasionally throttles scraping — wait 60 seconds and retry

### `429 Too Many Requests` errors in logs
- Streamlit Community Cloud shares IP ranges; Yahoo Finance may rate-limit the shared IP
- The `REQUEST_DELAY = 0.35` constant in `app.py` helps — increase it to `0.6` if needed
- The `@st.cache_data(ttl=300)` cache on `fetch_gainer_tickers()` prevents repeated list fetches within 5 minutes

### Pre-market price shows regular market price
- `yfinance` pre-market data requires the market to actually be open for pre-market
- On weekends or after 9:30 AM ET, `preMarketPrice` returns `None` — the app falls back to the regular market price automatically

### Float shows "N/A" for some tickers
- Small/micro-cap stocks sometimes have missing `floatShares` in yfinance
- The app does **not** crash — it shows "N/A" and **does not filter out** the ticker on missing float data (per your spec)
- To hard-filter these out, change `apply_filters()` to return `False` when `flt is None`

---

## Architecture Notes (for your reference)

### Why yfinance + scraping, not a single API?
yfinance does not provide a built-in "top gainers list" — it only lets you look up individual tickers. The app therefore:
1. **Scrapes** Yahoo Finance's day-gainers page to get an initial list of ~50–150 tickers
2. **Fetches full detail** (float, market cap, pre-market price) via `yf.Ticker(ticker).info` for each

### Why `@st.cache_data`?
- The gainers list is cached for 5 minutes (`ttl=300`) — clicking the button twice in quick succession reuses the list instead of re-scraping
- Individual ticker `.info` calls are inherently cached by yfinance's own request cache for the session

### Why the `REQUEST_DELAY`?
- Yahoo Finance's anti-bot systems trigger on rapid-fire requests
- A 350ms delay between calls keeps the total scan time at ~60–90 seconds for 150 tickers while avoiding 429 errors

### Why `_is_valid_us_ticker()` instead of relying on Yahoo's filter?
- Yahoo's gainers list occasionally includes ADRs, ETFs, and leveraged products
- The 1–5 character A-Z regex is the NYSE/NASDAQ ticker convention; dots and numbers denote foreign or special securities
- The `quoteType` and `country` fields in `.info` provide a second layer of verification
