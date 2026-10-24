"""Global configuration for the IC roll monitor."""

from __future__ import annotations

# Products we track. multiplier = CNY per index point.
# symbol is the Sina code without the "s_" prefix.
PRODUCTS = {
    "IC": {
        "name_cn": "中证500",
        "multiplier": 200,
        "symbol": "sh000905",
    },
    "IM": {
        "name_cn": "中证1000",
        "multiplier": 200,
        "symbol": "sh000852",
    },
    "IF": {
        "name_cn": "沪深300",
        "multiplier": 300,
        "symbol": "sh000300",
    },
    "IH": {
        "name_cn": "上证50",
        "multiplier": 300,
        "symbol": "sh000016",
    },
}

PRODUCT_ORDER = ["IC", "IM", "IF", "IH"]

# Margin rate used for position sizing math (broker level, exchange is 12%).
DEFAULT_MARGIN_RATE = 0.13

# How many calendar days of history to backfill on first run.
BACKFILL_DAYS = 420

# Rolling window (trading days) for percentile calculations.
PERCENTILE_WINDOW = 244

# Roll signal threshold: near-month minus next-month spread above this
# percentile is treated as a favourable roll window.
ROLL_SIGNAL_PCT = 75.0

DATA_DIR = "data"
HISTORY_FILE = "history.json"
DOCS_DIR = "docs"
