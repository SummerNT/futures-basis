"""Push the daily summary to WeChat via PushPlus (optional, token-gated)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API = "https://www.pushplus.plus/send"
ORDER = ["IC", "IM", "IF", "IH"]


def build_text(payload: dict, position: dict | None = None) -> tuple[str, str]:
    """Return (title, body) for the daily push."""
    as_of = payload.get("as_of", "")
    prods = payload.get("products", {})
    ic = prods.get("IC") or {}
    stats = ic.get("stats") or {}
    roll = ic.get("roll") or {}

    title = f"IC滚贴水 {as_of}"

    def ann(p):
        s = (prods.get(p) or {}).get("stats") or {}
        v = s.get("current")
        return f"{v:.2f}" if isinstance(v, (int, float)) else "--"

    lines = [f"IC 主力 {ic.get('main','--')} 年化贴水 {stats.get('current', 0):.2f}%"]
    lines.append(f"近一年分位 {stats.get('pct', 0):.1f}%（{_verdict(stats.get('pct'))}）")
    lines.append("")
    if roll:
        tag = "已到窗口" if roll.get("signal") == "roll" else "未到窗口"
        lines.append(f"换月：近-次月 {roll.get('spread', 0):.1f} 点，{roll.get('pct', 0):.1f}% 分位，{tag}")
        lines.append("（历史分位 >75% 才建议换月）")
        lines.append("")
    lines.append("四品种年化：" + " | ".join(f"{p} {ann(p)}" for p in ORDER if p in prods))
    lines.append(f"中证500 现货 {ic.get('spot', '--')}")

    if position:
        note = _position_note(prods, position)
        if note:
            lines.append("")
            lines.append(note)

    return title, "\n".join(lines)


def _verdict(pct) -> str:
    if not isinstance(pct, (int, float)):
        return "--"
    if pct >= 70:
        return "丰厚"
    if pct >= 45:
        return "中性偏高"
    if pct >= 25:
        return "中性偏低"
    return "偏薄"


def _position_note(prods: dict, pos: dict) -> str:
    """Safety cushion summary, mirrors the in-page calculator."""
    root = pos.get("product", "IC")
    d = prods.get(root) or {}
    contracts = d.get("contracts") or []
    if not contracts:
        return ""
    cur = None
    for c in contracts:
        if c.get("code") == pos.get("code", d.get("main")):
            cur = c.get("close")
            break
    if cur is None:
        cur = d.get("spot")
    mult = d.get("multiplier", 200)
    capital = float(pos.get("capital", 0))
    lots = int(pos.get("lots", 1))
    open_px = float(pos.get("open_price", cur))
    mr = float(pos.get("margin_rate", 0.13))
    if not capital or not cur:
        return ""

    notional = lots * open_px * mult
    margin = notional * mr
    equity = capital + (cur - open_px) * mult * lots
    buffer_pts = (equity - margin) / (mult * lots)
    buffer_pct = buffer_pts / cur * 100
    return (
        f"持仓：{lots} 手 @ {open_px:.1f}，本金 {capital/1e4:.0f} 万，占用 {margin/capital*100:.0f}%\n"
        f"安全垫：还可跌 {buffer_pct:.1f}%（{buffer_pts:.0f} 点）触及追保"
    )


def send(payload: dict, position: dict | None = None, token: str | None = None) -> bool:
    """POST to PushPlus. Returns True when the service accepted the message."""
    token = token or os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if not token:
        print("  push skipped: PUSHPLUS_TOKEN not set")
        return False

    title, content = build_text(payload, position)
    body = json.dumps(
        {"token": token, "title": title, "content": content, "template": "txt"},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        print(f"  push failed: {exc}")
        return False

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  push unclear: {raw[:120]}")
        return False
    ok = result.get("code") == 200
    print(f"  push {'ok' if ok else 'failed'}: {result.get('msg')}")
    return ok
