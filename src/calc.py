"""Compute basis, annualised discount, percentiles and roll signals."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from . import config


def expiry_date(code: str) -> date:
    """Third Friday of the contract month (CFFEX convention, holidays not shifted)."""
    year = 2000 + int(code[2:4])
    month = int(code[4:6])
    first = date(year, month, 1)
    offset = (4 - first.weekday()) % 7  # 4 == Friday
    return first + timedelta(days=offset + 14)


def contract_month_gap(code_a: str, code_b: str) -> int:
    """Number of calendar months between two contract codes."""
    ya, ma = 2000 + int(code_a[2:4]), int(code_a[4:6])
    yb, mb = 2000 + int(code_b[2:4]), int(code_b[4:6])
    return abs((yb * 12 + mb) - (ya * 12 + ma))


def percentile_rank(series: List[float], value: float) -> Optional[float]:
    """Share of observations at or below value, in percent."""
    clean = [x for x in series if x is not None]
    if not clean:
        return None
    hits = sum(1 for x in clean if x <= value)
    return hits / len(clean) * 100.0


def _quantile(series: List[float], q: float) -> Optional[float]:
    clean = sorted(x for x in series if x is not None)
    if not clean:
        return None
    idx = min(len(clean) - 1, max(0, int(round(q * (len(clean) - 1)))))
    return clean[idx]


def contract_metrics(code: str, row: dict, spot: float, as_of: date) -> dict:
    """Basis and annualised discount for a single contract."""
    exp = expiry_date(code)
    days = (exp - as_of).days
    close = row["close"]
    basis_pts = spot - close
    basis_pct = basis_pts / spot if spot else 0.0
    annual = basis_pct * 365.0 / max(days, 1) * 100.0
    mult = config.PRODUCTS[code[:2]]["multiplier"]
    return {
        "code": code,
        "close": round(close, 2),
        "settle": round(row.get("settle", close), 2),
        "oi": row.get("oi", 0),
        "volume": row.get("volume", 0),
        "expiry": f"{exp:%Y-%m-%d}",
        "days": days,
        "basis_pts": round(basis_pts, 2),
        "basis_pct": round(basis_pct * 100, 3),
        "annual_pct": round(annual, 2),
        "notional": round(close * mult, 0),
    }


def daily_product_rows(futures: List[dict], spot: float, as_of: date) -> List[dict]:
    """Metrics for every tradable contract of one product on one day."""
    rows = []
    for row in futures:
        if row["close"] <= 0:
            continue
        metric = contract_metrics(row["code"], row, spot, as_of)
        if metric["days"] < 0:
            continue
        rows.append(metric)
    rows.sort(key=lambda x: x["expiry"])
    return rows


def pick_main(rows: List[dict]) -> Optional[dict]:
    """Main contract = largest open interest, ignoring contracts near expiry."""
    tradable = [r for r in rows if r["oi"] > 0]
    if not tradable:
        return None
    return max(tradable, key=lambda r: r["oi"])


def roll_signal(rows: List[dict]) -> Optional[dict]:
    """Near-month minus next-month spread and its size in months."""
    forward = [r for r in rows if r["days"] > 0 and r["oi"] > 0]
    if len(forward) < 2:
        return None
    near, far = forward[0], forward[1]
    spread = near["close"] - far["close"]
    gaps = contract_month_gap(near["code"], far["code"])
    months = max(gaps, 1)
    return {
        "near": near["code"],
        "far": far["code"],
        "spread": round(spread, 2),
        "months": months,
        "per_month": round(spread / months, 2),
    }


QUARTER_MONTHS = {3, 6, 9, 12}


def quarter_pair(rows: List[dict]):
    """Current-quarter and next-quarter contracts (3/6/9/12 delivery months)."""
    q = [r for r in rows if int(r["code"][4:6]) in QUARTER_MONTHS and r["days"] > 0]
    if len(q) < 2:
        return None, None
    q.sort(key=lambda r: r["expiry"])
    return q[0], q[1]


def slope_series(
    history: Dict[str, dict],
    spot_map: Dict[str, Dict[str, float]],
    root: str,
) -> List[dict]:
    """Annualised term-structure slope between the two nearest quarterly contracts.

    slope = (next quarter - current quarter) / current quarter * 365 / day gap * 100

    Negative means the far contract is cheaper, i.e. rolling further out is
    compensated. The larger the absolute value, the steeper the curve.
    """
    out = []
    for ds in sorted(history.keys()):
        if ds.startswith("__"):
            continue
        spot = spot_map.get(root, {}).get(ds)
        if not spot:
            continue
        fut = [f for f in history[ds].get("futures", []) if f["code"][:2] == root]
        if not fut:
            continue
        as_of = datetime.strptime(ds, "%Y-%m-%d").date()
        rows = daily_product_rows(fut, spot, as_of)
        near, far = quarter_pair(rows)
        if not near or not far:
            continue
        gap = (datetime.strptime(far["expiry"], "%Y-%m-%d") -
               datetime.strptime(near["expiry"], "%Y-%m-%d")).days
        if gap <= 0:
            continue
        slope = (far["close"] - near["close"]) / near["close"] * 365.0 / gap * 100.0
        out.append(
            {
                "date": ds,
                "slope": round(slope, 2),
                "near": near["code"],
                "far": far["code"],
                "gap": gap,
            }
        )
    return out


def contract_snapshots(
    history: Dict[str, dict],
    spot_map: Dict[str, Dict[str, float]],
    root: str,
    target_days: int = 30,
    tolerance: int = 10,
    max_n: int = 16,
) -> List[dict]:
    """One observation per contract, sampled nearest to a fixed days-to-expiry.

    Comparing every delivery month at the same distance from expiry removes the
    term-structure slope, so the series shows how rich or thin the discount was
    for each contract rather than how it varies with maturity.
    """
    obs: Dict[str, List[tuple]] = {}
    for ds, day in history.items():
        as_of = datetime.strptime(ds, "%Y-%m-%d").date()
        spot = spot_map.get(root, {}).get(ds)
        if not spot:
            continue
        for row in day.get("futures", []):
            code = row["code"]
            if code[:2] != root or row["close"] <= 0:
                continue
            m = contract_metrics(code, row, spot, as_of)
            if m["days"] <= 0:
                continue
            obs.setdefault(code, []).append((m["days"], m["annual_pct"], ds))

    out = []
    for code, items in obs.items():
        best = min(items, key=lambda x: abs(x[0] - target_days))
        if abs(best[0] - target_days) > tolerance:
            continue
        out.append(
            {
                "code": code,
                "expiry": f"{expiry_date(code):%Y-%m-%d}",
                "days": best[0],
                "annual": round(best[1], 2),
                "date": best[2],
            }
        )
    out.sort(key=lambda x: x["expiry"])
    return out[-max_n:]


def build(history: Dict[str, dict], spot_map: Dict[str, Dict[str, float]]) -> dict:
    """Turn raw history into the payload consumed by the HTML front end."""
    dates = sorted(history.keys())
    if not dates:
        return {}

    spot_cache = spot_map

    # Per-product daily time series of the main contract.
    series: Dict[str, List[dict]] = {p: [] for p in config.PRODUCTS}
    roll_series: Dict[str, List[dict]] = {p: [] for p in config.PRODUCTS}

    for ds in dates:
        if ds.startswith("__"):
            continue
        day = history[ds]
        as_of = datetime.strptime(ds, "%Y-%m-%d").date()
        for root in config.PRODUCTS:
            spot = spot_cache.get(root, {}).get(ds)
            if not spot:
                continue
            fut = [f for f in day.get("futures", []) if f["code"][:2] == root]
            if not fut:
                continue
            rows = daily_product_rows(fut, spot, as_of)
            main = pick_main(rows)
            if main:
                series[root].append(
                    {
                        "date": ds,
                        "code": main["code"],
                        "annual": main["annual_pct"],
                        "basis_pts": main["basis_pts"],
                        "spot": round(spot, 2),
                    }
                )
            sig = roll_signal(rows)
            if sig:
                sig["date"] = ds
                roll_series[root].append(sig)

    last_date = max(d for d in dates if not d.startswith("__"))
    as_of = datetime.strptime(last_date, "%Y-%m-%d").date()
    day = history[last_date]

    products: Dict[str, dict] = {}
    for root, cfg in config.PRODUCTS.items():
        spot = spot_cache.get(root, {}).get(last_date)
        if not spot:
            continue
        fut = [f for f in day.get("futures", []) if f["code"][:2] == root]
        rows = daily_product_rows(fut, spot, as_of)
        main = pick_main(rows)

        window = series[root][-config.PERCENTILE_WINDOW :]
        annuals = [x["annual"] for x in window]
        roll_window = roll_series[root][-config.PERCENTILE_WINDOW :]
        spreads = [x["spread"] for x in roll_window]

        stats = {}
        if main:
            stats = {
                "current": main["annual_pct"],
                "median": round(_quantile(annuals, 0.5) or 0, 2),
                "p25": round(_quantile(annuals, 0.25) or 0, 2),
                "p75": round(_quantile(annuals, 0.75) or 0, 2),
                "min": round(min(annuals), 2) if annuals else None,
                "max": round(max(annuals), 2) if annuals else None,
                "pct": round(percentile_rank(annuals, main["annual_pct"]) or 0, 1),
                "samples": len(annuals),
            }

        sig = roll_signal(rows)
        if sig:
            sig["pct"] = round(percentile_rank(spreads, sig["spread"]) or 0, 1)
            sig["median"] = round(_quantile(spreads, 0.5) or 0, 2)
            sig["signal"] = "roll" if sig["pct"] >= config.ROLL_SIGNAL_PCT else "hold"
            sig["samples"] = len(spreads)

        products[root] = {
            "name_cn": cfg["name_cn"],
            "multiplier": cfg["multiplier"],
            "spot": round(spot, 2),
            "main": main["code"] if main else None,
            "contracts": rows,
            "stats": stats,
            "roll": sig,
            "contract_snapshots": contract_snapshots(history, spot_map, root),
            "slope_series": slope_series(history, spot_map, root),
            "main_series": {
                "dates": [x["date"] for x in window],
                "annual": [x["annual"] for x in window],
                "spot": [x["spot"] for x in window],
                "codes": [x["code"] for x in window],
            },
            "roll_series": {
                "dates": [x["date"] for x in roll_window],
                "spread": [x["spread"] for x in roll_window],
            },
        }

    return {
        "as_of": last_date,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "margin_rate": config.DEFAULT_MARGIN_RATE,
        "products": products,
    }
