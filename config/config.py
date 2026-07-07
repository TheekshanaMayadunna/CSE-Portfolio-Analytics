from pathlib import Path

# ===========================
# PROJECT PATHS
# ===========================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"
EXTERNAL_DATA = PROJECT_ROOT / "data" / "external"

LOG_DIR = PROJECT_ROOT / "logs"

# ===========================
# DOWNLOAD SETTINGS
# ===========================

START_DATE = "2018-01-01"
END_DATE = None  # Today's date

INTERVAL = "1d"

AUTO_ADJUST = False

THREADS = True
INITIAL_PORTFOLIO_VALUE = 100000

DATABASE_DIR = PROJECT_ROOT / "database"

DATABASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_PATH = DATABASE_DIR / "portfolio.db"

# Create folders automatically

for folder in [
    RAW_DATA,
    PROCESSED_DATA,
    EXTERNAL_DATA,
    LOG_DIR
]:
    folder.mkdir(parents=True, exist_ok=True)