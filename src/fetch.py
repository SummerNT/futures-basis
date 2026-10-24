"""Data fetchers for CFFEX index futures and spot indices.

All network calls use the standard library only, so the project runs on a
bare Python install with no third-party packages.
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from typing import Dict, List, Optional

from . import config

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

CFFEX_URL = "http://www.cffex.com.cn/sj/hqsj/rtj/{ym}/{dd}/{ymd}_1.csv"
SINA_KLINE_URL = (
    "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={lmt}"
)
SINA_URL = "https://hq.sinajs.cn/list={codes}"


def _get(url: str, timeout: int = 20, referer: Optional[str] = None) -> Optional[bytes]:
    """Fetch raw bytes, returning None on any transport failure."""
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def fetch_cffex_day(d: date, timeout: int = 20) -> Optional[List[dict]]:
    """Download one trading day of CFFEX quotes.

    The CSV has one row per contract (futures plus options). We keep only
    the four index futures products and skip option rows such as IC2611-C-6000.
    """
    url = CFFEX_URL.format(ym=f"{d:%Y%m}", dd=f"{d:%d}", ymd=f"{d:%Y%m%d}")
    raw = _get(url, timeout=timeout)
    if not raw or len(raw) < 500:
        return None

    text = raw.decode("gbk", errors="ignore")
    rows = csv.reader(io.StringIO(text))
    out: List[dict] = []
    for row in rows:
        if not row:
            continue
        code = row[0].strip()
        # Futures codes are exactly 6 chars: product root + 4 digit month.
        if len(code) != 6 or code[:2] not in config.PRODUCTS or not code[2:].isdigit():
            continue
        try:
            out.append(
                {
                    "code": code,
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "volume": int(float(row[4] or 0)),
                    "amount": float(row[5] or 0),
                    "oi": int(float(row[6] or 0)),
                    "close": float(row[8]),
                    "settle": float(row[9]),
                    "pre_settle": float(row[10]),
                }
            )
        except (ValueError, IndexError):
            continue
    return out or None


def fetch_spot_history(symbol: str, limit: int = 800, timeout: int = 20) -> Dict[str, float]:
    """Daily close history for one spot index from Sina, keyed by YYYY-MM-DD."""
    url = SINA_KLINE_URL.format(symbol=symbol, lmt=limit)
    raw = _get(url, timeout=timeout, referer="https://finance.sina.com.cn")
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, list):
        return {}
    out: Dict[str, float] = {}
    for item in payload:
        try:
            out[str(item["day"])] = float(item["close"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def fetch_spot_realtime() -> Dict[str, float]:
    """Realtime spot index quotes from Sina, used only as a live fallback."""
    codes = ",".join("s_" + cfg["symbol"] for cfg in config.PRODUCTS.values())
    raw = _get(SINA_URL.format(codes=codes), referer="https://finance.sina.com.cn")
    if not raw:
        return {}
    text = raw.decode("gbk", errors="ignore")
    out: Dict[str, float] = {}
    for line in text.splitlines():
        if "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1].strip()
        body = line.split('"')[1] if '"' in line else ""
        fields = body.split(",")
        if len(fields) < 2:
            continue
        for root, cfg in config.PRODUCTS.items():
            if cfg["symbol"] == key:
                try:
                    out[root] = float(fields[1])
                except ValueError:
                    pass
    return out


def backfill(start: date, end: date, progress: bool = True) -> Dict[str, dict]:
    """Walk calendar days from start to end and collect every available trading day."""
    result: Dict[str, dict] = {}
    total = (end - start).days + 1
    if total <= 0:
        return result
    for i in range(total):
        d = start + timedelta(days=1) * i
        if d.weekday() >= 5:
            continue
        rows = fetch_cffex_day(d)
        if rows:
            result[f"{d:%Y-%m-%d}"] = {"futures": rows}
            if progress:
                print(f"  ok   {d}  {len(rows)} contracts")
        time.sleep(0.12)
    return result
