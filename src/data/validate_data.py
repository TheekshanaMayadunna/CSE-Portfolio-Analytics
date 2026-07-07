"""
Validate downloaded market data.

Checks
------
✓ File exists
✓ Empty files
✓ Missing values
✓ Duplicate dates
✓ Date ordering
✓ Negative prices
✓ Zero prices
"""

from pathlib import Path

import pandas as pd

from config.config import RAW_DATA
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataValidator:

    def __init__(self, data_folder=RAW_DATA):

        self.data_folder = Path(data_folder)

    def validate_file(self, csv_file: Path):

        report = {
            "file": csv_file.name,
            "status": "PASS",
            "issues": [],
        }

        try:

            df = pd.read_csv(csv_file)

            if df.empty:

                report["status"] = "FAIL"
                report["issues"].append("Empty dataframe")

                return report

            if "Date" not in df.columns:

                report["status"] = "FAIL"
                report["issues"].append("Missing Date column")

                return report

            df["Date"] = pd.to_datetime(df["Date"])

            if not df["Date"].is_monotonic_increasing:

                report["issues"].append(
                    "Dates not sorted"
                )

            if df["Date"].duplicated().any():

                report["issues"].append(
                    "Duplicate dates"
                )

            numeric_columns = [
                "Open",
                "High",
                "Low",
                "Close",
                "Adj Close",
            ]

            for col in numeric_columns:

                if col not in df.columns:
                    continue

                df[col] = pd.to_numeric(df[col], errors="coerce")

                if df[col].isna().sum() > 0:
                    report["issues"].append(f"Missing values in {col}")

                if (df[col] <= 0).any():
                    report["issues"].append(f"Invalid values in {col}")

            if len(report["issues"]) > 0:

                report["status"] = "WARNING"

            return report

        except Exception as e:

            report["status"] = "FAIL"
            report["issues"].append(str(e))

            return report

    def validate_all(self):

        reports = []

        logger.info("Validating downloaded files...")

        for csv_file in self.data_folder.glob("*.csv"):

            report = self.validate_file(csv_file)

            reports.append(report)

            logger.info(
                f"{report['file']} -> {report['status']}"
            )

            for issue in report["issues"]:
                logger.warning(issue)

        return reports


if __name__ == "__main__":

    validator = DataValidator()

    results = validator.validate_all()

    print(results)