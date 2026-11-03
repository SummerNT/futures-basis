#!/usr/bin/env python3
"""Auto-resolve git conflicts in the futures-basis data files.

Why this exists
---------------
`data/history.json` and `data/spot.json` are date-keyed dictionaries. A local
run and a CI run can each append a *different* set of trading days (for
example the local run only fetched the last 3 days while CI had already
committed the previous week). Git inserts both blocks at the same position and
cannot tell which side is right, so the merge stops with conflict markers.

The resolution, however, is never ambiguous:

  * take the union of every date found in any version
  * when the same date exists more than once, keep the remote copy

That is exactly what this script does, then stages the file with `git add`.

Usage
-----
    python scripts/fix-data-conflict.py           # repair and stage
    python scripts/fix-data-conflict.py --check   # report only, exit 1 if dirty

Standard library only, same as the rest of the project.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
REMOTE_REF = "origin/main"

# path -> layout of the JSON document
FLAT = "flat"       # { date: {...} }              e.g. history.json
NESTED = "nested"   # { root: { date: value } }    e.g. spot.json

DATA_FILES: List[Tuple[str, str]] = [
    ("data/history.json", FLAT),
    ("data/spot.json", NESTED),
]

# Root order stays stable so the file does not churn on every merge.
ROOT_ORDER = ["IC", "IM", "IF", "IH"]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True)


def parse(raw: bytes):
    """Decode a JSON document, or return None if it is not valid JSON.

    A conflicted working-tree file contains `<<<<<<<` markers and will simply
    fail to parse -- that is expected and handled.
    """
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def is_conflicted(rel: str) -> bool:
    """True when the index has unmerged stages or the file has markers."""
    r = git("ls-files", "-u", "--", rel)
    if r.returncode == 0 and r.stdout.strip():
        return True
    p = ROOT / rel
    if p.exists() and b"<<<<<<<" in p.read_bytes():
        return True
    return False


def sources(rel: str) -> List[Tuple[str, dict]]:
    """Every readable version of `rel`, ordered lowest to highest priority.

    Priority climbs as we go: working tree < base < theirs < ours < remote.
    The remote copy always wins, which is the documented rule above.
    """
    out: List[Tuple[str, dict]] = []

    p = ROOT / rel
    if p.exists():
        d = parse(p.read_bytes())
        if d is not None:
            out.append(("working tree", d))

    for stage, label in (("1", "base"), ("3", "theirs"), ("2", "ours")):
        r = git("show", f":{stage}:{rel}")
        if r.returncode == 0:
            d = parse(r.stdout)
            if d is not None:
                out.append((f"stage {stage} ({label})", d))

    r = git("show", f"{REMOTE_REF}:{rel}")
    if r.returncode == 0:
        d = parse(r.stdout)
        if d is not None:
            out.append((f"{REMOTE_REF}", d))

    return out


def merge_flat(parts: List[dict]) -> dict:
    """Union of top-level keys; later entries overwrite earlier ones."""
    out: Dict[str, dict] = {}
    for part in parts:
        for k, v in part.items():
            out[k] = v
    return out


def merge_nested(parts: List[dict]) -> dict:
    """Union on both levels; later entries overwrite earlier ones."""
    out: Dict[str, Dict[str, float]] = {}
    for part in parts:
        for root, days in part.items():
            out.setdefault(root, {}).update(days)
    return out


def ordered(doc: dict, layout: str) -> dict:
    """Rebuild the dict in the canonical order used by src/main.py."""
    if layout == FLAT:
        return {k: doc[k] for k in sorted(doc)}
    keys = [r for r in ROOT_ORDER if r in doc] + sorted(r for r in doc if r not in ROOT_ORDER)
    return {r: {d: doc[r][d] for d in sorted(doc[r])} for r in keys}


def date_count(doc: dict, layout: str) -> int:
    if layout == FLAT:
        return len(doc)
    return sum(len(v) for v in doc.values())


def dates_of(doc: dict, layout: str):
    if layout == FLAT:
        return set(doc)
    out = set()
    for days in doc.values():
        out |= set(days)
    return out


def differing_dates(merged: dict, remote: dict, layout: str):
    """Dates present in both `merged` and `remote` but with a different value.

    The merge keeps the remote copy for these, so the caller can warn that a
    local edit (if any) was discarded.
    """
    if layout == FLAT:
        return {k for k in remote if k in merged and merged[k] != remote[k]}
    out = set()
    for root, days in remote.items():
        mine = merged.get(root) or {}
        for d in days:
            if d in mine and mine[d] != days[d]:
                out.add(d)
    return out


def write_json(rel: str, doc: dict) -> None:
    """Match src/main.py exactly: indent=1, UTF-8, LF endings."""
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=1)
    p.write_text(text, encoding="utf-8", newline="\n")


def main(argv: List[str]) -> int:
    check_only = "--check" in argv
    dirty = False

    for rel, layout in DATA_FILES:
        conflicted = is_conflicted(rel)
        if not conflicted:
            print(f"[ok]   {rel}: 无冲突")
            continue

        dirty = True
        print(f"[fix]  {rel}: 检测到冲突")

        parts = sources(rel)
        if not parts:
            print("       !! 没有任何可读取的版本，需要人工处理")
            return 1

        for label, doc in parts:
            print(f"       {label:<18} {date_count(doc, layout):>5} 条")

        docs = [doc for _, doc in parts]
        if layout == FLAT:
            merged = merge_flat(docs)
        else:
            merged = merge_nested(docs)

        # Report which dates only one side had, so the log is auditable.
        union = dates_of(merged, layout)
        remote = next((d for lbl, d in parts if lbl == REMOTE_REF), None)
        if remote is not None:
            newer = union - dates_of(remote, layout)
            if newer:
                print(f"       remote 没有、由本地补上的日期: {sorted(newer)}")
            dropped = dates_of(remote, layout) - union
            if dropped:
                print(f"       !! remote 有但合并结果缺失（异常）: {sorted(dropped)}")
            # Same date, different content: the remote copy silently wins.
            # Compare the two conflicted sides (not the base, whose differences
            # are just normal remote progress) so a discarded local edit to an
            # existing day is visible in the log.
            overwritten = set()
            for label, doc in parts:
                if label == REMOTE_REF or "base" in label:
                    continue
                overwritten |= differing_dates(doc, remote, layout)
            if overwritten:
                head = ", ".join(sorted(overwritten)[:5])
                more = "" if len(overwritten) <= 5 else f" 等 {len(overwritten)} 个"
                print(f"       同日期内容不同、已按 remote 覆盖: {head}{more}")

        merged = ordered(merged, layout)

        if check_only:
            print(f"       合并后会有 {date_count(merged, layout)} 条（未写入）")
            continue

        write_json(rel, merged)
        r = git("add", "--", rel)
        if r.returncode != 0:
            print(f"       !! git add 失败: {r.stderr.decode('utf-8', 'ignore').strip()}")
            return 1
        print(f"       已写入并暂存: {date_count(merged, layout)} 条")

    if check_only:
        return 1 if dirty else 0

    if not dirty:
        print("没有需要处理的数据文件冲突。")
        return 0

    # A rebase left in progress needs one more step to finish applying commits.
    if (ROOT / ".git" / "rebase-merge").exists() or (ROOT / ".git" / "rebase-apply").exists():
        print()
        print("检测到 rebase 进行中，继续 rebase ...")
        env = {**os.environ, "GIT_EDITOR": "true"}
        r = subprocess.run(
            ["git", "rebase", "--continue"],
            cwd=ROOT, capture_output=True, env=env,
        )
        if r.returncode != 0:
            print(f"  rebase --continue 失败:\n{r.stderr.decode('utf-8', 'ignore')}")
            print("  冲突已解决且已暂存，请手动执行 git rebase --continue")
            return 1
        print("  rebase 已完成")

    print()
    print("冲突已解决。现在可以 git push。")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
