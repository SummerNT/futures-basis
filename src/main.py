"""Entry point: refresh data, compute metrics, render output.

Usage:
    python run.py                # incremental refresh + render
    python run.py --days 60      # limit the backfill window
    python run.py --backfill     # ignore local cache and rebuild everything
    python run.py --no-render    # data only, skip HTML generation
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

from . import calc, config, fetch

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / config.DATA_DIR
DOCS = ROOT / config.DOCS_DIR


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def refresh_futures(history: dict, span: int, progress: bool = True) -> int:
    """Fetch any trading day inside the window that is missing locally."""
    today = date.today()
    start = today - timedelta(days=span)
    added = 0
    d = start
    while d <= today:
        if d.weekday() < 5:
            ds = f"{d:%Y-%m-%d}"
            if ds not in history:
                rows = fetch.fetch_cffex_day(d)
                if rows:
                    history[ds] = {"futures": rows}
                    added += 1
                    if progress:
                        print(f"  + {ds}  {len(rows)} contracts")
        d += timedelta(days=1)
    return added


def main(argv: list[str]) -> int:
    span = config.BACKFILL_DAYS
    if "--days" in argv:
        idx = argv.index("--days")
        if idx + 1 < len(argv):
            span = int(argv[idx + 1])
    force = "--backfill" in argv

    DATA.mkdir(parents=True, exist_ok=True)

    print("[1/4] spot index history")
    history = {} if force else load_json(DATA / config.HISTORY_FILE, {})
    spot_map = {} if force else load_json(DATA / "spot.json", {})
    for root, cfg in config.PRODUCTS.items():
        got = fetch.fetch_spot_history(cfg["symbol"], limit=800)
        if got:
            spot_map.setdefault(root, {}).update(got)
        print(f"  {root} {cfg['name_cn']}: {len(spot_map.get(root, {}))} days cached")

    print("[2/4] futures daily quotes")
    added = refresh_futures(history, span)
    print(f"  new trading days: {added}, total cached: {len(history)}")

    save_json(DATA / config.HISTORY_FILE, history)
    save_json(DATA / "spot.json", spot_map)

    print("[3/4] compute metrics")
    payload = calc.build(history, spot_map)
    if not payload:
        print("  no data available, abort")
        return 1
    save_json(DATA / "metrics.json", payload)
    print(f"  as of {payload['as_of']}")

    if "--no-render" not in argv:
        print("[4/5] render html")
        from . import render

        html = render.render(payload)
        DOCS.mkdir(parents=True, exist_ok=True)
        (DOCS / "index.html").write_text(html, encoding="utf-8")
        print(f"  wrote {DOCS / 'index.html'}")

    print("[5/5] push")
    from . import push

    position = load_json(DATA / "position.json", None)
    push.send(payload, position)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
