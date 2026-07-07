"""
Portfolio Performance Metrics

Phase 3
-------
1. Load processed datasets
2. Daily / cumulative / annualized return
3. Annualized volatility
4. Sharpe Ratio
5. Maximum Drawdown
6. Correlation Matrix
7. Asset Contribution
8. Validation
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so that `config` and `src` are importable
# regardless of which directory the script is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from config.config import PROCESSED_DATA
from config.tickers import PORTFOLIO_WEIGHTS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioMetrics:

    # --------------------------------------------------
    # Constructor
    # --------------------------------------------------

    def __init__(
        self,
        risk_free_rate: float = 0.0845,
        trading_days: int = 252,
        weights: dict = None,
    ):

        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
        self.weights = weights if weights is not None else PORTFOLIO_WEIGHTS

        self.portfolio = None
        self.asset_returns = None
        self.correlation_matrix = None
        self.asset_contribution = None

        self.metrics = {}

    # --------------------------------------------------
    # Load Data
    # --------------------------------------------------

    def load_data(self):

        logger.info("=" * 60)
        logger.info("Loading processed datasets...")
        logger.info("=" * 60)

        portfolio_file = PROCESSED_DATA / "portfolio_returns.csv"
        returns_file = PROCESSED_DATA / "daily_returns.csv"

        self.portfolio = pd.read_csv(
            portfolio_file,
            parse_dates=["Date"],
        )

        self.asset_returns = pd.read_csv(
            returns_file,
            parse_dates=["Date"],
        )

        logger.info(f"Portfolio rows : {len(self.portfolio)}")
        logger.info(f"Asset return rows : {len(self.asset_returns)}")

        return self.portfolio

    # --------------------------------------------------
    # Return Metrics
    # --------------------------------------------------

    def calculate_return_metrics(self):

        logger.info("Calculating return metrics...")

        initial_value = self.portfolio["Portfolio Value"].iloc[0]
        final_value = self.portfolio["Portfolio Value"].iloc[-1]

        cumulative_return = (final_value / initial_value) - 1

        number_of_days = len(self.portfolio)
        number_of_years = number_of_days / self.trading_days

        annualized_return = (
            (1 + cumulative_return) ** (1 / number_of_years)
        ) - 1

        self.metrics["Initial Value"] = initial_value
        self.metrics["Final Value"] = final_value
        self.metrics["Cumulative Return"] = cumulative_return
        self.metrics["Annualized Return"] = annualized_return

        logger.info(f"Cumulative Return : {cumulative_return:.2%}")
        logger.info(f"Annualized Return : {annualized_return:.2%}")

        return self.metrics

    # --------------------------------------------------
    # Annualized Volatility
    # --------------------------------------------------

    def calculate_volatility(self):

        logger.info("Calculating volatility...")

        daily_std = self.portfolio["Portfolio Return"].std()

        annualized_volatility = daily_std * (self.trading_days ** 0.5)

        self.metrics["Annualized Volatility"] = annualized_volatility

        logger.info(
            f"Annualized Volatility : {annualized_volatility:.2%}"
        )

        return annualized_volatility

    # --------------------------------------------------
    # Sharpe Ratio
    # --------------------------------------------------

    def calculate_sharpe_ratio(self):

        logger.info("Calculating Sharpe Ratio...")

        annual_return = self.metrics["Annualized Return"]
        annual_volatility = self.metrics["Annualized Volatility"]

        if annual_volatility == 0:
            sharpe = 0
        else:
            sharpe = (
                annual_return - self.risk_free_rate
            ) / annual_volatility

        self.metrics["Sharpe Ratio"] = sharpe

        logger.info(f"Sharpe Ratio : {sharpe:.4f}")

        return sharpe

    # --------------------------------------------------
    # Maximum Drawdown
    # --------------------------------------------------

    def calculate_max_drawdown(self):

        logger.info("Calculating Maximum Drawdown...")

        portfolio_value = self.portfolio["Portfolio Value"]

        running_max = portfolio_value.cummax()

        drawdown = (portfolio_value - running_max) / running_max

        self.portfolio["Running Max"] = running_max
        self.portfolio["Drawdown"] = drawdown

        max_drawdown = drawdown.min()
        trough_idx = drawdown.idxmin()
        peak_idx = portfolio_value.loc[:trough_idx].idxmax()

        self.metrics["Maximum Drawdown"] = max_drawdown
        self.metrics["Drawdown Peak Date"] = self.portfolio.loc[
            peak_idx, "Date"
        ]
        self.metrics["Drawdown Trough Date"] = self.portfolio.loc[
            trough_idx, "Date"
        ]

        logger.info(f"Maximum Drawdown : {max_drawdown:.2%}")
        logger.info(f"Peak Date : {self.metrics['Drawdown Peak Date']}")
        logger.info(
            f"Trough Date : {self.metrics['Drawdown Trough Date']}"
        )

        return drawdown

    # --------------------------------------------------
    # Correlation Matrix
    # --------------------------------------------------

    def calculate_correlation_matrix(self):

        logger.info("Calculating Correlation Matrix...")

        # Exclude the Date column — this matrix covers your actual holdings only.
        asset_returns = self.asset_returns.drop(
            columns=["Date"],
            errors="ignore",
        )

        correlation_matrix = asset_returns.corr()

        self.correlation_matrix = correlation_matrix

        logger.info("Correlation matrix created.")
        logger.info("\n%s", correlation_matrix)

        return correlation_matrix

    # --------------------------------------------------
    # Asset Contribution
    # --------------------------------------------------

    def calculate_asset_contribution(self):

        logger.info("Calculating Asset Contribution...")

        asset_returns = self.asset_returns.drop(
            columns=["Date"],
            errors="ignore",
        )

        contributions = {}

        for asset in self.weights:

            if asset not in asset_returns.columns:
                logger.warning(
                    f"'{asset}' in weights but missing from "
                    f"daily_returns.csv — skipped."
                )
                continue

            cumulative_return = (
                1 + asset_returns[asset]
            ).prod() - 1

            contributions[asset] = cumulative_return * self.weights[asset]

        contribution_df = pd.DataFrame(
            {
                "Asset": list(contributions.keys()),
                "Contribution": list(contributions.values()),
            }
        )

        contribution_df.sort_values(
            by="Contribution",
            ascending=False,
            inplace=True,
        )

        self.asset_contribution = contribution_df

        logger.info("Asset contribution calculated.")

        # Sanity check flagged in the guide: contributions should sum
        # close to the portfolio's overall cumulative return.
        total_contribution = contribution_df["Contribution"].sum()
        logger.info(
            f"Sum of contributions : {total_contribution:.2%} "
            f"(compare to Cumulative Return above)"
        )

        return contribution_df

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate_metrics(self):

        logger.info("Validating metrics...")

        total_weight = sum(self.weights.values())

        if abs(total_weight - 1.0) > 0.0001:
            raise ValueError(
                f"Weights sum to {total_weight}, not 1.0"
            )

        if self.metrics["Annualized Volatility"] < 0:
            raise ValueError("Volatility cannot be negative.")

        logger.info("Validation successful.")
        logger.info(
            f"Portfolio Return : {self.metrics['Cumulative Return']:.2%}"
        )
        logger.info(f"Sharpe Ratio : {self.metrics['Sharpe Ratio']:.3f}")

        return True

    # --------------------------------------------------
    # Print Summary
    # --------------------------------------------------

    def print_summary(self):

        logger.info("=" * 60)
        logger.info("METRIC SUMMARY")
        logger.info("=" * 60)

        for key, value in self.metrics.items():

            if isinstance(value, float):
                if "Ratio" in key:
                    logger.info(f"{key:<30} {value:.4f}")
                elif "Value" in key:
                    logger.info(f"{key:<30} {value:,.2f}")
                else:
                    logger.info(f"{key:<30} {value:.2%}")
            else:
                logger.info(f"{key:<30} {value}")

    # --------------------------------------------------
    # Save Results
    # --------------------------------------------------

    def save_results(self):

        logger.info("Saving results...")

        metrics_df = pd.DataFrame(
            {
                "Metric": list(self.metrics.keys()),
                "Value": list(self.metrics.values()),
            }
        )

        metrics_df.to_csv(
            PROCESSED_DATA / "portfolio_metrics.csv",
            index=False,
        )

        self.asset_contribution.to_csv(
            PROCESSED_DATA / "asset_contribution.csv",
            index=False,
        )

        self.correlation_matrix.to_csv(
            PROCESSED_DATA / "correlation_matrix.csv"
        )

        self.portfolio.to_csv(
            PROCESSED_DATA / "portfolio_returns.csv",
            index=False,
        )

        logger.info("Results saved.")

    # --------------------------------------------------
    # Run Pipeline
    # --------------------------------------------------

    def run_pipeline(self):

        logger.info("=" * 60)
        logger.info("STARTING METRIC CALCULATIONS")
        logger.info("=" * 60)

        self.load_data()
        self.calculate_return_metrics()
        self.calculate_volatility()
        self.calculate_sharpe_ratio()
        self.calculate_max_drawdown()
        self.calculate_correlation_matrix()
        self.calculate_asset_contribution()
        self.validate_metrics()
        self.print_summary()
        self.save_results()

        logger.info("=" * 60)
        logger.info("METRIC CALCULATION COMPLETE")
        logger.info("=" * 60)


if __name__ == "__main__":

    metrics = PortfolioMetrics()
    metrics.run_pipeline()