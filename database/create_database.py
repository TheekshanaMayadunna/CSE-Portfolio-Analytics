"""
Create Database
===============
Creates every table in the SQLite portfolio database.

Run this before populate_database.py.

Schema
------
  assets              — one row per ticker; PK = ticker
  daily_prices        — one row per (ticker, date); FK → assets
  transactions        — trade log; PK = transaction_id (auto-increment)
  portfolio_daily_value — one row per date; PK = date
  portfolio_metrics   — key/value store for scalar KPIs; PK = metric

Usage
-----
    python database/create_database.py
"""

import sys
from pathlib import Path

# Allow imports from project root regardless of launch directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.config import DATABASE_PATH
from database.database_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# DDL Statements
# ============================================================

DDL_ASSETS = """
CREATE TABLE IF NOT EXISTS assets (
    ticker        TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    sector        TEXT NOT NULL,
    asset_class   TEXT NOT NULL,
    target_weight REAL NOT NULL
);
"""

DDL_DAILY_PRICES = """
CREATE TABLE IF NOT EXISTS daily_prices (
    ticker         TEXT NOT NULL,
    date           DATE NOT NULL,
    adjusted_close REAL NOT NULL,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
"""

# Index for common time-series queries (all prices for a date range)
IDX_DAILY_PRICES_DATE = """
CREATE INDEX IF NOT EXISTS idx_daily_prices_date
    ON daily_prices(date);
"""

DDL_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date           DATE NOT NULL,
    ticker         TEXT NOT NULL,
    action         TEXT NOT NULL,      -- 'BUY' | 'SELL' | 'REBALANCE'
    quantity       REAL NOT NULL,
    price          REAL NOT NULL,
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);
"""

DDL_PORTFOLIO_DAILY_VALUE = """
CREATE TABLE IF NOT EXISTS portfolio_daily_value (
    date               DATE PRIMARY KEY,
    portfolio_return   REAL NOT NULL,
    cumulative_return  REAL NOT NULL,
    portfolio_value    REAL NOT NULL
);
"""

DDL_PORTFOLIO_METRICS = """
CREATE TABLE IF NOT EXISTS portfolio_metrics (
    metric TEXT PRIMARY KEY,
    value  REAL NOT NULL
);
"""

ALL_DDL = [
    ("assets",               DDL_ASSETS),
    ("daily_prices",         DDL_DAILY_PRICES),
    ("idx_daily_prices_date", IDX_DAILY_PRICES_DATE),
    ("transactions",         DDL_TRANSACTIONS),
    ("portfolio_daily_value", DDL_PORTFOLIO_DAILY_VALUE),
    ("portfolio_metrics",    DDL_PORTFOLIO_METRICS),
]


# ============================================================
# Main
# ============================================================

def create_database(db_path: Path = DATABASE_PATH) -> None:
    """
    Drop & recreate all tables from scratch.

    Safe to re-run: uses IF NOT EXISTS so an existing database
    will not lose data unless you explicitly drop tables first.
    """

    logger.info("=" * 60)
    logger.info("CREATING DATABASE SCHEMA")
    logger.info("=" * 60)
    logger.info(f"Database path: {db_path}")

    with DatabaseManager(db_path) as db:
        for name, ddl in ALL_DDL:
            db.execute(ddl)
            logger.info(f"  ✓  {name}")

        existing_tables = db.tables()
        logger.info(f"Tables in database: {existing_tables}")

    logger.info("Schema creation complete.")


if __name__ == "__main__":
    create_database()
