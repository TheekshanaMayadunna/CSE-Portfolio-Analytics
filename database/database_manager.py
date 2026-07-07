"""
Database Manager
================
Central API for all SQLite interactions in the portfolio analytics system.

Every other module imports from here instead of writing raw sqlite3 code.

Usage
-----
    # Context manager (recommended)
    with DatabaseManager(DB_PATH) as db:
        df = db.query("SELECT * FROM assets")
        db.execute("INSERT INTO assets VALUES (?,?,?,?,?)", row)

    # Manual lifecycle
    db = DatabaseManager(DB_PATH)
    db.connect()
    ...
    db.close()
"""

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Thin wrapper around sqlite3 that provides four clean primitives:

    connect()     — open the database and configure pragmas
    execute()     — run a single non-SELECT statement
    executemany() — batch insert / update
    query()       — run a SELECT and return a DataFrame
    close()       — shut down cleanly
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> "DatabaseManager":
        """
        Open the SQLite connection.

        Pragmas applied:
          - WAL journal mode  — allows concurrent reads during writes
          - foreign_keys = ON — enforce referential integrity
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        logger.info(f"Connected to database: {self.db_path}")
        return self

    def close(self) -> None:
        """Commit any pending transaction and close the connection."""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed.")

    # ------------------------------------------------------------------
    # Context Manager Support
    # ------------------------------------------------------------------

    def __enter__(self) -> "DatabaseManager":
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            # Roll back on error so the db is not left in a dirty state
            if self.conn:
                self.conn.rollback()
                logger.warning("Transaction rolled back due to exception.")
        self.close()
        return False  # Do not suppress exceptions

    # ------------------------------------------------------------------
    # Core Primitives
    # ------------------------------------------------------------------

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a single non-SELECT SQL statement (INSERT / UPDATE / DELETE / DDL).

        Parameters
        ----------
        sql    : SQL string, with ? placeholders for parameterised queries
        params : tuple of values to bind to the placeholders

        Returns
        -------
        sqlite3.Cursor — useful for `cursor.lastrowid` etc.
        """
        self._require_connection()
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor

    def executemany(self, sql: str, rows: list[tuple]) -> None:
        """
        Execute a parameterised statement once per row in `rows`.

        Wraps the entire batch in one transaction for performance — a
        batch of 25 000 inserts takes ~0.5 s instead of ~25 s.

        Parameters
        ----------
        sql  : SQL string with ? placeholders
        rows : list of tuples, one per row
        """
        self._require_connection()
        self.conn.executemany(sql, rows)
        self.conn.commit()
        logger.debug(f"Batch insert: {len(rows)} rows")

    def query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """
        Execute a SELECT statement and return the result as a DataFrame.

        Parameters
        ----------
        sql    : SELECT statement with optional ? placeholders
        params : tuple of bind values

        Returns
        -------
        pd.DataFrame — empty DataFrame if the query returns no rows
        """
        self._require_connection()
        df = pd.read_sql_query(sql, self.conn, params=params)
        logger.debug(f"Query returned {len(df)} rows")
        return df

    def table_row_count(self, table: str) -> int:
        """Return the number of rows in `table`."""
        self._require_connection()
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table};")  # noqa: S608
        return cursor.fetchone()[0]

    def tables(self) -> list[str]:
        """List all user tables in the database."""
        df = self.query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        return df["name"].tolist()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_connection(self) -> None:
        if self.conn is None:
            raise RuntimeError(
                "DatabaseManager is not connected. "
                "Call connect() or use it as a context manager."
            )
