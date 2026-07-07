"""
Download historical market data from Yahoo Finance.

Features
--------
✓ Downloads each ticker separately
✓ Saves one CSV per asset
✓ Skips existing files (optional)
✓ Handles yfinance MultiIndex safely
✓ Logs successes and failures
"""

from pathlib import Path
from typing import Dict

import pandas as pd
import yfinance as yf

from config.config import (
    RAW_DATA,
    START_DATE,
    END_DATE,
    INTERVAL,
    AUTO_ADJUST,
)

from config.tickers import ALL_TICKERS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YahooDownloader:

    def __init__(
        self,
        save_directory: Path = RAW_DATA,
        overwrite: bool = False,
    ):
        self.save_directory = save_directory
        self.overwrite = overwrite

    def download_ticker(self, ticker: str) -> bool:

        file_path = self.save_directory / f"{ticker}.csv"

        if file_path.exists() and not self.overwrite:
            logger.info(f"{ticker} already exists. Skipping.")
            return True

        try:
            logger.info(f"Downloading {ticker}")

            df = yf.download(
                tickers=ticker,
                start=START_DATE,
                end=END_DATE,
                interval=INTERVAL,
                auto_adjust=AUTO_ADJUST,
                progress=False,
                threads=False,
            )

            # ---- SAFETY CHECK ----
            if df is None:
                logger.error(f"{ticker}: returned None")
                return False

            if df.empty:
                logger.warning(f"{ticker}: No data returned")
                return False

            # ---- FIX MULTIINDEX ISSUE ----
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # ---- RESET INDEX ONCE ----
            df = df.reset_index()

            # ---- CLEAN COLUMN NAMES (extra safety) ----
            df.columns = [str(col).strip() for col in df.columns]

            df.to_csv(file_path, index=False)

            logger.info(f"{ticker}: Downloaded {len(df)} rows")

            return True

        except Exception as e:
            logger.error(f"{ticker}: {e}")
            return False

    def download_all(self) -> Dict:

        summary = {"success": [], "failed": []}

        logger.info("=" * 60)
        logger.info("STARTING DOWNLOAD")
        logger.info("=" * 60)

        for ticker in ALL_TICKERS:
            success = self.download_ticker(ticker)

            if success:
                summary["success"].append(ticker)
            else:
                summary["failed"].append(ticker)

        logger.info("=" * 60)
        logger.info("DOWNLOAD COMPLETE")
        logger.info("=" * 60)

        logger.info(f"Successful: {len(summary['success'])}")
        logger.info(f"Failed: {len(summary['failed'])}")

        return summary


if __name__ == "__main__":
    downloader = YahooDownloader()
    print(downloader.download_all())