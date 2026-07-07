"""
Data preprocessing pipeline.

Pipeline
--------
1. Load CSE stock prices
2. Align dates
3. Handle missing values
4. Calculate daily returns
5. Build portfolio
6. Simulate transaction history
7. Save processed datasets
"""

import pandas as pd

from config.config import (
    RAW_DATA,
    PROCESSED_DATA,
    INITIAL_PORTFOLIO_VALUE,
)

from config.tickers import (
    CSE_TICKERS,
    PORTFOLIO_WEIGHTS,
)

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataPreprocessor:

    def __init__(self):

        self.assets = CSE_TICKERS

        self.prices = None
        self.returns = None
        self.portfolio = None
        self.transactions = None

    # ----------------------------------------------------
    # Load Price Files
    # ----------------------------------------------------

    def load_prices(self):

        logger.info("Loading CSE price files...")

        dfs = []

        for ticker in self.assets:

            file = RAW_DATA / f"{ticker}.csv"

            logger.info(f"Loading {file.name}")

            df = pd.read_csv(file)

            df["Date"] = pd.to_datetime(df["Date"])

            if "Adj Close" in df.columns:
                price_column = "Adj Close"
            else:
                price_column = "Close"

            df = df[["Date", price_column]]

            df.rename(
                columns={
                    price_column: ticker
                },
                inplace=True
            )

            df.set_index(
                "Date",
                inplace=True
            )

            dfs.append(df)

        self.prices = pd.concat(
            dfs,
            axis=1,
            join="outer"
        )

        logger.info(
            f"Loaded {len(self.assets)} assets."
        )

        return self.prices

    # ----------------------------------------------------
    # Align Dates
    # ----------------------------------------------------

    def align_dates(self):

        logger.info("Aligning dates...")

        self.prices.sort_index(inplace=True)

        logger.info(
            f"Rows: {len(self.prices)}"
        )

        return self.prices

    # ----------------------------------------------------
    # Missing Values
    # ----------------------------------------------------

    def handle_missing(self):

        logger.info("Handling missing values...")

        before = self.prices.isna().sum().sum()

        logger.info(
            f"Missing before fill: {before}"
        )

        self.prices.ffill(inplace=True)

        self.prices.dropna(inplace=True)

        after = self.prices.isna().sum().sum()

        logger.info(
            f"Missing after fill: {after}"
        )

        return self.prices

    # ----------------------------------------------------
    # Daily Returns
    # ----------------------------------------------------

    def calculate_returns(self):

        logger.info("Calculating daily returns...")

        self.returns = self.prices.pct_change()

        self.returns.dropna(inplace=True)

        logger.info(
            f"Calculated returns for {len(self.returns.columns)} assets."
        )

        return self.returns

    # ----------------------------------------------------
    # Portfolio
    # ----------------------------------------------------

    def build_portfolio(self):

        logger.info("Building portfolio...")

        weights = pd.Series(PORTFOLIO_WEIGHTS)

        portfolio = self.returns.copy()

        portfolio["Portfolio Return"] = (

            portfolio[weights.index]

            .mul(weights)

            .sum(axis=1)

        )

        portfolio["Portfolio Value"] = (

            (1 + portfolio["Portfolio Return"])

            .cumprod()

            * INITIAL_PORTFOLIO_VALUE

        )

        self.portfolio = portfolio

        logger.info("Portfolio created.")

        return portfolio

    # ----------------------------------------------------
    # Transactions
    # ----------------------------------------------------

    def simulate_transactions(self):

        logger.info(
            "Generating transaction history..."
        )

        rebalance_date = self.portfolio.index[
            len(self.portfolio) // 2
        ]

        self.transactions = pd.DataFrame({

            "Date": [rebalance_date],

            "Transaction Type": [
                "Portfolio Rebalance"
            ],

            "Description": [
                "Portfolio rebalanced to target weights."
            ]

        })

        logger.info(
            "Transaction history created."
        )

        return self.transactions

    # ----------------------------------------------------
    # Save
    # ----------------------------------------------------

    def save_outputs(self):

        logger.info(
            "Saving processed datasets..."
        )

        self.prices.to_csv(
            PROCESSED_DATA /
            "aligned_prices.csv"
        )

        self.returns.to_csv(
            PROCESSED_DATA /
            "daily_returns.csv"
        )

        self.portfolio.to_csv(
            PROCESSED_DATA /
            "portfolio_returns.csv"
        )

        self.transactions.to_csv(
            PROCESSED_DATA /
            "transactions.csv",
            index=False
        )

        logger.info(
            "All processed files saved."
        )

    # ----------------------------------------------------
    # Pipeline
    # ----------------------------------------------------

    def run_pipeline(self):

        logger.info("=" * 60)
        logger.info("STARTING PREPROCESSING")
        logger.info("=" * 60)

        self.load_prices()

        self.align_dates()

        self.handle_missing()

        self.calculate_returns()

        self.build_portfolio()

        self.simulate_transactions()

        self.save_outputs()

        logger.info("=" * 60)
        logger.info("PREPROCESSING COMPLETE")
        logger.info("=" * 60)


if __name__ == "__main__":

    preprocessor = DataPreprocessor()

    preprocessor.run_pipeline()