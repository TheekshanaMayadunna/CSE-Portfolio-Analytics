"""
Populate Database
=================
Loads processed CSV files into the SQLite portfolio database.

Source files (data/processed/)
-------------------------------
  aligned_prices.csv      → daily_prices  (wide → long melt)
  portfolio_returns.csv   → portfolio_daily_value
  portfolio_metrics.csv   → portfolio_metrics  (numeric rows only)

Derived data
------------
  config/tickers.py       → assets  (weights + hardcoded metadata)
  synthetic transactions  → transactions  (initial buys + rebalance)

Run order
---------
    python database/create_database.py   # schema must exist first
    python database/populate_database.py

Usage (standalone)
------------------
    python database/populate_database.py
"""

import sys
from pathlib import Path

# Allow imports from project root regardless of launch directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from config.config import DATABASE_PATH, PROCESSED_DATA
from config.tickers import PORTFOLIO_WEIGHTS
from database.database_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Asset Metadata
# ============================================================

# CSE tickers don't carry sector/name data from Yahoo Finance.
# Hardcoded from public knowledge of the Colombo Stock Exchange.
ASSET_METADATA: dict[str, dict] = {
    "JKH-N0000.CM":   {"name": "John Keells Holdings",      "sector": "Diversified",  "asset_class": "Equity"},
    "COMB-N0000.CM":  {"name": "Commercial Bank",           "sector": "Financials",   "asset_class": "Equity"},
    "HNB-N0000.CM":   {"name": "Hatton National Bank",      "sector": "Financials",   "asset_class": "Equity"},
    "SAMP-N0000.CM":  {"name": "Sampath Bank",              "sector": "Financials",   "asset_class": "Equity"},
    "CCS-N0000.CM":   {"name": "Ceylon Cold Stores",            "sector": "Beverages",       "asset_class": "Equity"},
    "AAF-N0000.CM":   {"name": "Asian Alliance Finance",    "sector": "Financials",   "asset_class": "Equity"},
    "AAIC-N0000.CM":  {"name": "Asian Alliance Insurance",  "sector": "Insurance",    "asset_class": "Equity"},
    "AHPL-N0000.CM":  {"name": "Asiri Hospital Holdings",   "sector": "Healthcare",   "asset_class": "Equity"},
    "AFSL-N0000.CM":  {"name": "Amana Takaful",             "sector": "Insurance",    "asset_class": "Equity"},
    "ALLI-N0000.CM":  {"name": "Alliance Finance",          "sector": "Financials",   "asset_class": "Equity"},
    "AEL-N0000.CM":   {"name": "Amana Energy",              "sector": "Energy",       "asset_class": "Equity"},
    "CALF-N0000.CM":  {"name": "CAL Futures",               "sector": "Financials",   "asset_class": "Equity"},
}


# ============================================================
# Loaders
# ============================================================

def load_assets() -> list[tuple]:
    """
    Build the assets rows from PORTFOLIO_WEIGHTS + ASSET_METADATA.

    Returns
    -------
    list of (ticker, name, sector, asset_class, target_weight)
    """
    rows = []
    for ticker, weight in PORTFOLIO_WEIGHTS.items():
        meta = ASSET_METADATA.get(ticker, {})
        rows.append((
            ticker,
            meta.get("name", ticker),
            meta.get("sector", "Unknown"),
            meta.get("asset_class", "Equity"),
            weight,
        ))
    logger.info(f"Assets prepared: {len(rows)} rows")
    return rows


def load_daily_prices() -> list[tuple]:
    """
    Melt aligned_prices.csv (wide) into long format for daily_prices table.

    Returns
    -------
    list of (ticker, date, adjusted_close)
    """
    path = PROCESSED_DATA / "aligned_prices.csv"
    df = pd.read_csv(path, parse_dates=["Date"])

    # Wide → long: each ticker column becomes its own rows
    long_df = df.melt(
        id_vars=["Date"],
        var_name="ticker",
        value_name="adjusted_close",
    )

    # Drop any NaN prices (some tickers had gaps early in the series)
    long_df.dropna(subset=["adjusted_close"], inplace=True)

    rows = [
        (row["ticker"], row["Date"].strftime("%Y-%m-%d"), row["adjusted_close"])
        for _, row in long_df.iterrows()
    ]
    logger.info(f"Daily prices prepared: {len(rows):,} rows")
    return rows


def load_transactions(prices_df: pd.DataFrame) -> list[tuple]:
    """
    Synthesise a meaningful transactions table.

    For each ticker:
      - BUY on the first date in the price series (initial portfolio construction)
      - REBALANCE on 2022-03-14 (the recorded rebalance event from transactions.csv)

    The initial buy quantity is calculated as:
        (INITIAL_PORTFOLIO_VALUE × target_weight) / first_price

    Returns
    -------
    list of (date, ticker, action, quantity, price)
    """
    from config.config import INITIAL_PORTFOLIO_VALUE

    rows = []

    for ticker, weight in PORTFOLIO_WEIGHTS.items():
        ticker_prices = prices_df[prices_df["ticker"] == ticker].sort_values("date")
        if ticker_prices.empty:
            logger.warning(f"No prices found for {ticker}, skipping transactions.")
            continue

        # --- Initial BUY ---
        first_row = ticker_prices.iloc[0]
        first_price = first_row["adjusted_close"]
        first_date = first_row["date"]
        capital_allocated = INITIAL_PORTFOLIO_VALUE * weight
        quantity = round(capital_allocated / first_price, 4) if first_price > 0 else 0
        rows.append((first_date, ticker, "BUY", quantity, first_price))

        # --- REBALANCE event (2022-03-14) ---
        rebalance_date = "2022-03-14"
        rebal_price_row = ticker_prices[ticker_prices["date"] == rebalance_date]
        if not rebal_price_row.empty:
            rebal_price = rebal_price_row.iloc[0]["adjusted_close"]
            # Represent the rebalance as restoring target allocation at that price
            portfolio_value_est = INITIAL_PORTFOLIO_VALUE  # simplified estimate
            rebal_quantity = round(
                (portfolio_value_est * weight) / rebal_price, 4
            ) if rebal_price > 0 else 0
            rows.append((rebalance_date, ticker, "REBALANCE", rebal_quantity, rebal_price))

    logger.info(f"Transactions prepared: {len(rows)} rows")
    return rows


def load_portfolio_daily_value() -> list[tuple]:
    """
    Load portfolio_returns.csv → portfolio_daily_value table.

    Computes cumulative_return from Portfolio Value column.

    Returns
    -------
    list of (date, portfolio_return, cumulative_return, portfolio_value)
    """
    path = PROCESSED_DATA / "portfolio_returns.csv"
    df = pd.read_csv(path, parse_dates=["Date"])

    initial_value = df["Portfolio Value"].iloc[0]
    df["cumulative_return"] = (df["Portfolio Value"] / initial_value) - 1

    rows = [
        (
            row["Date"].strftime("%Y-%m-%d"),
            row["Portfolio Return"],
            row["cumulative_return"],
            row["Portfolio Value"],
        )
        for _, row in df.iterrows()
    ]
    logger.info(f"Portfolio daily value prepared: {len(rows):,} rows")
    return rows


def load_portfolio_metrics() -> list[tuple]:
    """
    Load portfolio_metrics.csv — numeric rows only.

    Rows like 'Drawdown Peak Date' and 'Drawdown Trough Date' contain
    timestamps, not floats, so they are skipped here (they live in the
    portfolio_daily_value table instead).

    Returns
    -------
    list of (metric, value)
    """
    path = PROCESSED_DATA / "portfolio_metrics.csv"
    df = pd.read_csv(path)

    rows = []
    for _, row in df.iterrows():
        try:
            value = float(row["Value"])
            rows.append((row["Metric"], value))
        except (ValueError, TypeError):
            logger.debug(f"Skipping non-numeric metric: {row['Metric']} = {row['Value']}")

    logger.info(f"Portfolio metrics prepared: {len(rows)} rows")
    return rows


# ============================================================
# Populate
# ============================================================

def populate_database(db_path: Path = DATABASE_PATH) -> None:
    """
    Clear existing rows and reload all tables from processed CSVs.

    Tables are populated in FK-safe order:
        assets → daily_prices → transactions → portfolio_daily_value → portfolio_metrics
    """
    logger.info("=" * 60)
    logger.info("POPULATING DATABASE")
    logger.info("=" * 60)

    # --- Prepare data before opening the connection ---
    assets_rows        = load_assets()
    prices_rows        = load_daily_prices()

    # Build a DataFrame for transaction price lookups
    prices_df = pd.DataFrame(prices_rows, columns=["ticker", "date", "adjusted_close"])
    transactions_rows  = load_transactions(prices_df)
    portfolio_rows     = load_portfolio_daily_value()
    metrics_rows       = load_portfolio_metrics()

    with DatabaseManager(db_path) as db:

        # --- Clear tables in reverse FK order ---
        logger.info("Clearing existing data...")
        for table in [
            "portfolio_metrics",
            "portfolio_daily_value",
            "transactions",
            "daily_prices",
            "assets",
        ]:
            db.execute(f"DELETE FROM {table};")  # noqa: S608

        # ----------------------------------------------------------------
        # assets
        # ----------------------------------------------------------------
        logger.info("Inserting assets...")
        db.executemany(
            """
            INSERT INTO assets (ticker, name, sector, asset_class, target_weight)
            VALUES (?, ?, ?, ?, ?);
            """,
            assets_rows,
        )
        count = db.table_row_count("assets")
        logger.info(f"  ✓  assets: {count} rows")

        # ----------------------------------------------------------------
        # daily_prices
        # ----------------------------------------------------------------
        logger.info("Inserting daily prices (this may take a moment)...")
        db.executemany(
            """
            INSERT OR IGNORE INTO daily_prices (ticker, date, adjusted_close)
            VALUES (?, ?, ?);
            """,
            prices_rows,
        )
        count = db.table_row_count("daily_prices")
        logger.info(f"  ✓  daily_prices: {count:,} rows")

        # ----------------------------------------------------------------
        # transactions
        # ----------------------------------------------------------------
        logger.info("Inserting transactions...")
        db.executemany(
            """
            INSERT INTO transactions (date, ticker, action, quantity, price)
            VALUES (?, ?, ?, ?, ?);
            """,
            transactions_rows,
        )
        count = db.table_row_count("transactions")
        logger.info(f"  ✓  transactions: {count} rows")

        # ----------------------------------------------------------------
        # portfolio_daily_value
        # ----------------------------------------------------------------
        logger.info("Inserting portfolio daily value...")
        db.executemany(
            """
            INSERT OR IGNORE INTO portfolio_daily_value
                (date, portfolio_return, cumulative_return, portfolio_value)
            VALUES (?, ?, ?, ?);
            """,
            portfolio_rows,
        )
        count = db.table_row_count("portfolio_daily_value")
        logger.info(f"  ✓  portfolio_daily_value: {count:,} rows")

        # ----------------------------------------------------------------
        # portfolio_metrics
        # ----------------------------------------------------------------
        logger.info("Inserting portfolio metrics...")
        db.executemany(
            """
            INSERT OR REPLACE INTO portfolio_metrics (metric, value)
            VALUES (?, ?);
            """,
            metrics_rows,
        )
        count = db.table_row_count("portfolio_metrics")
        logger.info(f"  ✓  portfolio_metrics: {count} rows")

    logger.info("=" * 60)
    logger.info("DATABASE POPULATION COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    populate_database()
