# CSE Portfolio Analytics

A sector-diversified portfolio performance and risk analytics project built entirely around **Colombo Stock Exchange (CSE)** listed equities — combining Python, SQL, and Power BI into a single, reproducible end-to-end analytics pipeline.

This project was built as a portfolio piece for a **Data Analytics internship application**. It deliberately demonstrates practical fluency across the full analytics stack an employer is likely to test for — Python for data processing, SQL for structured querying, and Power BI for visualization — rather than building a production trading system.

---

## Project Overview

This project analyzes a hypothetical, sector-diversified portfolio of **12 CSE-listed equities** across multiple sectors. It calculates industry-standard risk and performance metrics — cumulative and annualized return, volatility, Sharpe ratio, maximum drawdown, correlation, and per-asset return contribution — then presents the results through a structured SQLite database, processed datasets, and an interactive Power BI dashboard.


### Note on Data Source

All price data, including CSE-listed tickers, is sourced through `yfinance` using Yahoo Finance's `.CM` suffix convention for Colombo Stock Exchange listings — verified against CSE's own site for data quality before use. No manual data entry was required once this source was confirmed reliable.

---

## Portfolio Composition

| Ticker | Company | Sector | Target Weight |
|---|---|---|---|
| JKH-N0000.CM | John Keells Holdings | Diversified | 15% |
| COMB-N0000.CM | Commercial Bank | Financials | 12% |
| HNB-N0000.CM | Hatton National Bank | Financials | 10% |
| SAMP-N0000.CM | Sampath Bank | Financials | 9% |
| CCS-N0000.CM | Ceylon Cold Stores | Beverages | 8% |
| AAF-N0000.CM | Asian Alliance Finance | Financials | 8% |
| AAIC-N0000.CM | Asian Alliance Insurance | Insurance | 8% |
| AHPL-N0000.CM | Asiri Hospital Holdings | Healthcare | 8% |
| AFSL-N0000.CM | Amana Takaful | Insurance | 7% |
| ALLI-N0000.CM | Alliance Finance | Financials | 7% |
| AEL-N0000.CM | Amana Energy | Energy | 4% |
| CALF-N0000.CM | CAL Futures | Financials | 4% |

> Portfolio weights are defined in `config/tickers.py`. Total portfolio value: **LKR 100,000**.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data acquisition | `yfinance` (Yahoo Finance `.CM`-suffixed tickers) |
| Data processing | Python (`pandas`, `numpy`) |
| Storage | SQLite |
| Visualization | Power BI Desktop |
| Version control | Git |

---

## Methodology

### Risk-Free Rate

Sharpe ratio calculations use the 12-month (364-day) Sri Lankan Treasury Bill rate, sourced from a recent Central Bank of Sri Lanka auction (**approximately 8.4–8.5%** — the pipeline hard-codes `0.0845`). A local risk-free rate was used deliberately, since a USD-denominated rate (e.g., US T-bills) would be conceptually incorrect for an LKR-denominated portfolio.

> **If reproducing later:** confirm the current T-bill yield, as yields move regularly. Update `risk_free_rate` in `src/analytics/metrics.py` accordingly.

### Annualization Convention

**252 trading days per year** — the standard industry convention. Actual CSE trading day counts may differ slightly; this is a stated assumption, not a precise count of Sri Lankan market holidays.

### Benchmark / Beta — Excluded

No benchmark comparison or beta calculation is included in this analysis. The Colombo All-Share Price Index (ASPI, Yahoo ticker `^CSE`) could not be reliably retrieved via `yfinance` at the time of building this project. Rather than substitute an unreliable or manually-sourced series, benchmark comparison was dropped and replaced with an equal-weighted comparison (see below) to still answer *"did the specific weighting scheme add value."*

### Equal-Weighted Comparison (Benchmark Substitute)

In place of a market benchmark, the portfolio's actual (target-weighted) cumulative return is compared against a hypothetical equal-weighted allocation across the same 12 holdings. This isolates the effect of the specific weighting decisions from the effect of simply holding these 12 stocks.

### Rebalancing

A single rebalance event is simulated on **2022-03-14**, restoring each holding to its target allocation. Rebalancing is modeled as a single event, not as a recurring schedule with transaction costs or tax implications.

### Validation

Metrics were spot-checked by manually recalculating one month's cumulative return from raw adjusted close prices and comparing it against the pipeline's output, confirming the calculation logic before relying on it across the full dataset.

---

## Project Structure

```
portfolio-analytics/
├── config/
│   ├── config.py           # paths, constants (start date, initial portfolio value, etc.)
│   └── tickers.py          # ticker list and target weights — edit here to change holdings
├── data/
│   ├── external/           # any external data sources
│   ├── raw/                # untouched downloaded price data
│   └── processed/          # cleaned, calculated datasets
├── database/
│   ├── create_database.py  # SQLite schema definition
│   ├── populate_database.py# loads processed CSVs into the database
│   ├── database_manager.py # connection / execution helper
│   └── portfolio.db        # SQLite database
├── logs/
│   └── portfolio.log       # pipeline execution logs
├── notebooks/
│   └── metrix_1.ipynb      # exploratory analysis and validation
├── powerBi/
│   └── newport.pbix        # interactive Power BI dashboard
├── src/
│   ├── data/               # data acquisition and preprocessing
│   │   ├── download_data.py
│   │   ├── preprocess.py
│   │   └── validate_data.py
│   ├── analytics/          # metric calculations
│   │   └── metrics.py
│   └── utils/              # shared logger, helpers
│       └── logger.py
├── main.py                 # runs the full Python pipeline end-to-end
├── requirements.txt
└── README.md
```

---

## How to Run

### 1. Environment setup

```bash
python -m venv venv
source venv/bin/activate     # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configure your portfolio (optional)

Edit `config/tickers.py` to change tickers or weights. No other file needs to change — the pipeline reads from this config throughout.

### 3. Run the full pipeline

```bash
python main.py
```

This executes four phases in sequence:

1. **Download** — fetches each ticker from Yahoo Finance → `data/raw/`
2. **Validation** — checks for empty files, missing columns, bad prices, duplicates
3. **Preprocessing** — aligns dates, fills gaps, computes daily returns, builds the portfolio
4. **Metrics** — computes return, volatility, Sharpe, max drawdown, correlation, contribution

All processed outputs are written to `data/processed/`.

> Optional flags: `python main.py --skip-download` (reuse existing raw CSVs) · `python main.py --overwrite` (re-download).

### 4. Build the database

```bash
python database/create_database.py
python database/populate_database.py
```

### 5. Open the Power BI dashboard

1. Open `powerBi/newport.pbix` in Power BI Desktop.
2. The dashboard connects to `database/portfolio.db` via **ODBC** (SQLite ODBC driver required).

   ![Uploading image.png…]()


---

## Key Findings

> Results below are produced by the pipeline against the current dataset (period **2018-01-02 → 2026-07-03**, 2,189 trading days).

**Overall performance:** The target-weighted portfolio grew from LKR 100,854 to **LKR 485,935**, a **cumulative return of +381.8%** over the period. Annualized return is **+19.8%**, with an annualized volatility of **19.4%** and a **Sharpe ratio of 0.59** (using an 8.45% local risk-free rate).

**Risk:** Maximum drawdown was **−42.5%**. (Exact peak/trough dates are stored in the `portfolio_daily_value` table and surfaced in the dashboard.)

**Diversification:** Correlation among holdings is generally moderate, but **COMB and HNB show an elevated correlation of 0.60** — the two largest bank positions provide limited mutual diversification benefit despite being separate companies. This is the clearest concentration risk in the portfolio and is worth flagging to any reviewer.

**Attribution:** The single largest return contributor was **ALLI (Alliance Finance)** at **+60.7%** of portfolio contribution, followed by **AAIC (Asian Alliance Insurance)** at **+45.9%**. Notably, the highest-weight holding, **JKH (John Keells Holdings, 15%)**, was the *only negative contributor* at **−12.6%** — a strong illustration of the weighting-vs-return dynamic: a high weight does not guarantee high contribution, and a moderate-weight outperformer can dominate.

**Weighting vs. equal-weight:** The actual target-weighted portfolio (**+381.8%** cumulative) *underperformed* a hypothetical equal-weighted allocation of the same 12 stocks (**+586.4%** cumulative) over the full period. In other words, the chosen (concentration-heavy) weights detracted from return relative to simply holding equal amounts of each name — largely because the high JKH weight dragged while smaller financial/insurance positions outperformed.

---

## Limitations & Next Steps

Stated directly, as a deliberate part of this project's documentation rather than an afterthought:

- **No benchmark/beta**, due to unreliable free access to CSE All-Share Index historical data via `yfinance` at the time of building this project. An equal-weighted comparison was used as a partial substitute.
- **Annualization uses a fixed 252-day convention**, not an exact count of CSE trading days, which may differ slightly from global markets.
- **Rebalancing is simulated as a single event**, not modeled with transaction costs or tax implications, which would matter in a real-world implementation.
- **Data availability:** The project covers 2018-01-01 to present. Limited historical depth and any early-series gaps for certain tickers may affect metrics like maximum drawdown.

**With more time, this project could be extended with:**
- A proper rebalancing cost/frequency comparison (quarterly vs. never).
- A manually-sourced ASPI benchmark series to restore beta calculation.
- Additional CSE sector exposure (e.g., telecom, manufacturing) to further strengthen the diversification analysis.

---

