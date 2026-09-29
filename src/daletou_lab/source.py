from __future__ import annotations

import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .database import DEFAULT_DB, Draw, connect, initialize, upsert_draw
from .rules import RuleRegistry


OFFICIAL_API = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
OFFICIAL_SOURCE = "China Sports Lottery official gateway"


def _number(value: object) -> float | None:
    if value in (None, ""):
        return None
    cleaned = re.sub(r"[^0-9.-]", "", str(value))
    return float(cleaned) if cleaned else None


def _integer(value: object) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def fetch_page(page_no: int, page_size: int = 100, timeout: int = 30) -> Dict[str, object]:
    query = urllib.parse.urlencode(
        {"gameNo": "85", "provinceId": "0", "pageSize": page_size, "isVerify": "1", "pageNo": page_no}
    )
    request = urllib.request.Request(
        f"{OFFICIAL_API}?{query}",
        headers={"User-Agent": "daletou-strategy-lab/1.0 (+public research; no gambling claims)"},
    )
    retryable_statuses = {408, 429, 500, 502, 503, 504}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            break
        except urllib.error.HTTPError as error:
            if error.code == 567:
                raise RuntimeError(
                    "Official lottery API rejected this request with HTTP 567; "
                    "the upstream gateway/security policy must allow this client. "
                    "The request was not retried."
                ) from error
            if error.code not in retryable_statuses or attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except urllib.error.URLError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    if not payload.get("success"):
        raise RuntimeError(f"Official API error: {payload.get('errorMessage')}")
    return payload


def _parse_prize_level(name: str) -> Tuple[int, bool]:
    chinese = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    match = re.search(r"([一二三四五六七八九])等奖", name)
    if not match:
        raise ValueError(f"Unknown prize name: {name}")
    return chinese[match.group(1)], "追加" in name


def parse_item(item: Dict[str, object], registry: RuleRegistry, fetched_at: str) -> Tuple[Draw, List[Dict[str, object]]]:
    issue = str(item["lotteryDrawNum"])
    numbers = tuple(int(value) for value in str(item["lotteryDrawResult"]).split())
    if len(numbers) != 7:
        raise ValueError(f"Issue {issue}: expected 7 numbers, got {len(numbers)}")
    rule = registry.for_issue(issue)
    draw = Draw(
        issue=issue,
        draw_date=str(item["lotteryDrawTime"]),
        front=tuple(numbers[:5]),
        back=tuple(numbers[5:]),
        sales_amount=_number(item.get("totalSaleAmount")),
        jackpot_before=_number(item.get("poolBalance")),
        jackpot_after=_number(item.get("poolBalanceAfterdraw")),
        rule_version=rule.rule_version,
        source=OFFICIAL_SOURCE,
        fetched_at=fetched_at,
        verified=True,
        raw_json=json.dumps(item, ensure_ascii=False, separators=(",", ":")),
    )
    prizes = []
    for row in item.get("prizeLevelList", []):
        level, additional = _parse_prize_level(str(row["prizeLevel"]))
        prizes.append(
            {
                "prize_level": level,
                "prize_name": row["prizeLevel"],
                "winning_count": _integer(row.get("stakeCount")),
                "prize_per_ticket": _integer(row.get("stakeAmountFormat") or row.get("stakeAmount")),
                "additional": additional,
            }
        )
    return draw, prizes


def write_raw_cache(payload: Dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def update_official(db_path: Path = DEFAULT_DB, full: bool = False, max_pages: int = 100) -> Dict[str, object]:
    initialize(db_path)
    registry = RuleRegistry()
    fetched_at = datetime.now(timezone.utc).isoformat()
    inserted = 0
    page_no = 1
    seen_issues = set()
    with connect(db_path) as connection:
        existing = {row[0] for row in connection.execute("SELECT issue FROM draws").fetchall()}
        while page_no <= max_pages:
            payload = fetch_page(page_no)
            items = payload.get("value", {}).get("list", [])
            if not items:
                break
            write_raw_cache(payload, db_path.parent / "raw" / f"official-page-{page_no:03d}.json")
            reached_existing = False
            for item in items:
                issue = str(item["lotteryDrawNum"])
                if issue in seen_issues:
                    continue
                seen_issues.add(issue)
                if issue in existing and not full:
                    reached_existing = True
                    continue
                try:
                    draw, prizes = parse_item(item, registry, fetched_at)
                except LookupError:
                    continue
                upsert_draw(connection, draw, prizes)
                inserted += 1
            connection.commit()
            if reached_existing and not full:
                break
            page_no += 1
    return {"inserted": inserted, "pages": page_no, "fetched_at": fetched_at, "source": OFFICIAL_SOURCE}
