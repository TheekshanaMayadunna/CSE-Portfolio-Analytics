"""
Portfolio Analytics — Full Pipeline
====================================

Runs the four stages in sequence:

  Phase 1 — Download
    • Downloads each ticker (holdings + benchmark) from Yahoo Finance
    • Saves one CSV per asset to data/raw/

  Phase 2 — Validation
    • Checks every CSV for empty files, missing columns,
      negative / zero prices, duplicate dates, etc.
    • Aborts if any file has a hard FAIL (warns on WARNING)

  Phase 3 — Preprocessing
    • Loads raw price files, aligns dates, forward-fills gaps
    • Calculates daily returns, builds portfolio, simulates transactions
    • Saves processed CSVs to data/processed/

  Phase 4 — Metrics
    • Loads processed data and computes return, volatility,
      Sharpe ratio, max drawdown, beta, correlation, contribution
    • Validates results and saves final outputs

Usage
-----
    python main.py

Optional flags
--------------
    python main.py --skip-download   # use existing raw CSVs
    python main.py --overwrite       # re-download even if CSV exists
"""

import argparse
import sys

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ================================================================
# Phase 1 — Download
# ================================================================

def run_download(overwrite: bool = False) -> dict:
    """Download all tickers from Yahoo Finance."""

    logger.info("#" * 60)
    logger.info("# PHASE 1 — DATA DOWNLOAD")
    logger.info("#" * 60)

    from src.data.download_data import YahooDownloader

    downloader = YahooDownloader(overwrite=overwrite)
    summary = downloader.download_all()

    if summary["failed"]:
        logger.warning(
            f"The following tickers FAILED to download: "
            f"{summary['failed']}"
        )

    return summary


# ================================================================
# Phase 2 — Validation
# ================================================================

def run_validation() -> list:
    """Validate every raw CSV and abort on hard failures."""

    logger.info("#" * 60)
    logger.info("# PHASE 2 — DATA VALIDATION")
    logger.info("#" * 60)

    from src.data.validate_data import DataValidator

    validator = DataValidator()
    reports = validator.validate_all()

    hard_fails = [r for r in reports if r["status"] == "FAIL"]
    warnings   = [r for r in reports if r["status"] == "WARNING"]

    if warnings:
        logger.warning(
            f"{len(warnings)} file(s) have warnings — "
            "pipeline will continue but review them."
        )

    if hard_fails:
        logger.error(
            f"{len(hard_fails)} file(s) failed validation:"
        )
        for r in hard_fails:
            logger.error(f"  {r['file']}: {r['issues']}")
        raise RuntimeError(
            "Validation failed — fix the errors above before rerunning."
        )

    logger.info(
        f"Validation passed: {len(reports)} file(s) checked, "
        f"{len(warnings)} warning(s)."
    )

    return reports


# ================================================================
# Phase 3 — Preprocessing
# ================================================================

def run_preprocessing():
    """Load, clean, align, and save processed datasets."""

    logger.info("#" * 60)
    logger.info("# PHASE 3 — PREPROCESSING")
    logger.info("#" * 60)

    from src.data.preprocess import DataPreprocessor

    preprocessor = DataPreprocessor()
    preprocessor.run_pipeline()

    return preprocessor


# ================================================================
# Phase 4 — Metrics
# ================================================================

def run_metrics():
    """Compute and save all portfolio performance metrics."""

    logger.info("#" * 60)
    logger.info("# PHASE 4 — METRIC CALCULATION")
    logger.info("#" * 60)

    from src.analytics.metrics import PortfolioMetrics

    metrics = PortfolioMetrics()
    metrics.run_pipeline()

    return metrics


# ================================================================
# Argument parser
# ================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Portfolio Analytics full pipeline"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip Phase 1 (download) and use existing raw CSVs.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download tickers even if their CSV already exists.",
    )
    return parser.parse_args()


# ================================================================
# Main
# ================================================================

def main():

    args = parse_args()

    logger.info("=" * 60)
    logger.info("PORTFOLIO ANALYTICS PIPELINE — START")
    logger.info("=" * 60)

    # ----------------------------------------------------------
    # Phase 1 — Download
    # ----------------------------------------------------------
    if args.skip_download:
        logger.info("Skipping Phase 1 — using existing raw CSVs.")
    else:
        try:
            run_download(overwrite=args.overwrite)
        except Exception:
            logger.exception(
                "Download failed — stopping pipeline. "
                "Fix the error above before rerunning."
            )
            sys.exit(1)

    # ----------------------------------------------------------
    # Phase 2 — Validation
    # ----------------------------------------------------------
    try:
        run_validation()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
    except Exception:
        logger.exception(
            "Validation raised an unexpected error — stopping pipeline."
        )
        sys.exit(1)

    # ----------------------------------------------------------
    # Phase 3 — Preprocessing
    # ----------------------------------------------------------
    try:
        run_preprocessing()
    except Exception:
        logger.exception(
            "Preprocessing failed — stopping before metrics. "
            "Fix the error above before rerunning."
        )
        sys.exit(1)

    # ----------------------------------------------------------
    # Phase 4 — Metrics
    # ----------------------------------------------------------
    try:
        run_metrics()
    except Exception:
        logger.exception(
            "Metric calculation failed. Check that preprocessing "
            "outputs exist in data/processed/ before rerunning."
        )
        sys.exit(1)

    # ----------------------------------------------------------
    # Done
    # ----------------------------------------------------------
    logger.info("=" * 60)
    logger.info("PORTFOLIO ANALYTICS PIPELINE — COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()