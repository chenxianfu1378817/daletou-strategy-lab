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
from io import BytesIO
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence, Tuple
from zoneinfo import ZoneInfo

from pypdf import PdfReader

from .database import DEFAULT_DB, Draw, connect, initialize, upsert_draw
from .rules import RuleRegistry


OFFICIAL_API = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
OFFICIAL_SOURCE = "China Sports Lottery official gateway"
OFFICIAL_PDF_SOURCE = "China Sports Lottery official draw announcement PDF"
OFFICIAL_PDF_TEMPLATE = "https://pdf.sporttery.cn/33800/{issue}/{issue}.pdf"
SHANGHAI_SOURCE = "Shanghai Sports Lottery official draw data"
SHANGHAI_DRAW_TEMPLATE = "https://www.shsportslottery.com/cpsj/dlt/kj_{issue}.json"


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
        source=str(item.get("_source") or OFFICIAL_SOURCE),
        fetched_at=fetched_at,
        verified=True,
        raw_json=json.dumps(
            {key: value for key, value in item.items() if not key.startswith("_")},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
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


def _parse_official_pdf(issue: str, content: bytes) -> Dict[str, object]:
    reader = PdfReader(BytesIO(content), strict=False)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    issue_match = re.search(r"第\s*(\d{5})\s*期开奖公告", text)
    if not issue_match or issue_match.group(1) != issue:
        raise ValueError(f"Official draw PDF does not match expected issue {issue}")

    date_match = re.search(r"开奖日期：\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    sales_match = re.search(r"本期全国销售金额：\s*([\d,]+)元", text)
    jackpot_match = re.search(r"([\d,.]+)元奖金滚入下期奖池", text)
    numbers_match = re.search(r"本期开奖号码：([\s\S]*?)本期中奖情况", text)
    if not all((date_match, sales_match, jackpot_match, numbers_match)):
        raise ValueError(f"Official draw PDF for issue {issue} is missing required fields")

    numbers = [int(value) for value in re.findall(r"\b\d{1,2}\b", numbers_match.group(1))]
    if len(numbers) != 7:
        raise ValueError(f"Official draw PDF for issue {issue} has {len(numbers)} winning numbers")

    prize_rows: List[Dict[str, str]] = []
    current_level = ""
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        level_match = re.match(r"^([一二三四五六七八九]等奖)\s*(.*)$", line)
        if level_match:
            current_level = level_match.group(1)
            remainder = level_match.group(2)
        elif line.startswith("追加") and current_level in {"一等奖", "二等奖"}:
            remainder = line
        else:
            continue

        count_match = re.search(r"([\d,]+)\s*注", remainder)
        if not count_match:
            continue
        count = int(count_match.group(1).replace(",", ""))
        amount_match = re.search(r"([\d,]+)\s*元", remainder[count_match.end() :])
        if not amount_match and count != 0:
            continue
        additional = "追加" in remainder
        prize_rows.append(
            {
                "prizeLevel": f"{current_level}{'(追加)' if additional else ''}",
                "stakeCount": str(count),
                "stakeAmountFormat": (
                    amount_match.group(1).replace(",", "") if amount_match else "0"
                ),
            }
        )

    return {
        "lotteryDrawNum": issue,
        "lotteryDrawResult": " ".join(f"{value:02d}" for value in numbers),
        "lotteryDrawTime": (
            f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
        ),
        "totalSaleAmount": sales_match.group(1).replace(",", ""),
        "poolBalanceAfterdraw": jackpot_match.group(1).replace(",", ""),
        "prizeLevelList": prize_rows,
        "_source": OFFICIAL_PDF_SOURCE,
        "_sourceUrl": OFFICIAL_PDF_TEMPLATE.format(issue=issue),
    }


def _fetch_official_pdf(issue: str, timeout: int = 30) -> Dict[str, object] | None:
    request = urllib.request.Request(
        OFFICIAL_PDF_TEMPLATE.format(issue=issue),
        headers={"User-Agent": "daletou-strategy-lab/1.0 (+public research; no gambling claims)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read(2_000_001)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    if len(content) > 2_000_000 or not content.startswith(b"%PDF-"):
        raise ValueError(f"Official draw PDF for issue {issue} is not a valid PDF")
    return _parse_official_pdf(issue, content)


def _parse_shanghai_draw(issue: str, payload: Dict[str, object]) -> Dict[str, object]:
    if payload.get("ret") is not True or not isinstance(payload.get("data"), dict):
        raise ValueError(f"Shanghai Sports Lottery returned an invalid draw for issue {issue}")
    data = payload["data"]
    if data.get("lotId") != "dlt" or str(data.get("issueNo")) != issue:
        raise ValueError(f"Shanghai Sports Lottery draw does not match issue {issue}")

    code = str(data.get("bonusCode", ""))
    match = re.fullmatch(r"(\d{2},){4}\d{2}#\d{2},\d{2}", code)
    if not match:
        raise ValueError(f"Shanghai Sports Lottery issue {issue} has invalid winning numbers")
    front_text, back_text = code.split("#")
    front = [int(value) for value in front_text.split(",")]
    back = [int(value) for value in back_text.split(",")]
    if (front != sorted(set(front)) or back != sorted(set(back))
            or any(value < 1 or value > 35 for value in front)
            or any(value < 1 or value > 12 for value in back)):
        raise ValueError(f"Shanghai Sports Lottery issue {issue} has invalid winning numbers")

    date = str(data.get("bonusDate", ""))
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError(f"Shanghai Sports Lottery issue {issue} has invalid draw date") from error

    prize_rows = []
    for row in data.get("bonusList", []):
        if not isinstance(row, dict):
            raise ValueError(f"Shanghai Sports Lottery issue {issue} has invalid prize rows")
        name = str(row.get("name", ""))
        level, additional = _parse_prize_level(name)
        count = _integer(row.get("amount"))
        prize = _integer(row.get("money"))
        if count is None or count < 0 or prize is None and count != 0:
            raise ValueError(f"Shanghai Sports Lottery issue {issue} has invalid prize amounts")
        prize_rows.append({
            "prizeLevel": f"{name}",
            "stakeCount": str(count),
            "stakeAmountFormat": str(prize or 0),
        })

    return {
        "lotteryDrawNum": issue,
        "lotteryDrawResult": " ".join(f"{value:02d}" for value in front + back),
        "lotteryDrawTime": date,
        "prizeLevelList": prize_rows,
        "sourceUrl": SHANGHAI_DRAW_TEMPLATE.format(issue=issue),
        "_source": SHANGHAI_SOURCE,
    }


def _fetch_shanghai_draw(issue: str, timeout: int = 30) -> Dict[str, object] | None:
    request = urllib.request.Request(
        SHANGHAI_DRAW_TEMPLATE.format(issue=issue),
        headers={"User-Agent": "daletou-strategy-lab/1.0 (+public research; no gambling claims)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    return _parse_shanghai_draw(issue, payload)


def _update_from_issue_files(
    connection,
    existing: set[str],
    registry: RuleRegistry,
    fetched_at: str,
    raw_dir: Path,
    fetch_issue: Callable[[str], Dict[str, object] | None],
    source: str,
    cache_prefix: str,
    max_issues: int = 30,
) -> Dict[str, object]:
    if not existing:
        raise RuntimeError("Cannot use the issue-file fallback without an existing issue number")

    latest_issue = max(existing, key=int)
    year = int(latest_issue[:2])
    sequence = int(latest_issue[2:])
    current_year = datetime.now(ZoneInfo("Asia/Shanghai")).year % 100
    inserted = 0
    checked = 0

    while checked < max_issues:
        candidate = f"{year:02d}{sequence + 1:03d}"
        item = fetch_issue(candidate)
        if item is None and year < current_year:
            year += 1
            sequence = 0
            candidate = f"{year:02d}{sequence + 1:03d}"
            item = fetch_issue(candidate)
        if item is None:
            break

        if "_sourceUrl" in item:
            item["sourceUrl"] = item.pop("_sourceUrl")
        draw, prizes = parse_item(item, registry, fetched_at)
        if draw.issue in existing:
            break
        rule = registry.for_issue(draw.issue)
        expected_prizes = {(level.level, False) for level in rule.prize_levels}
        expected_prizes.update((level, True) for level in rule.additional_levels)
        actual_prizes = {(row["prize_level"], row["additional"]) for row in prizes}
        if actual_prizes != expected_prizes:
            raise ValueError(
                f"{source} for issue {candidate} has an incomplete prize table"
            )
        if (
            datetime.fromisoformat(draw.draw_date).date()
            > datetime.now(ZoneInfo("Asia/Shanghai")).date()
        ):
            raise ValueError(f"{source} for issue {candidate} is dated in the future")

        upsert_draw(connection, draw, prizes)
        write_raw_cache(item, raw_dir / f"{cache_prefix}-{candidate}.json")
        connection.commit()
        existing.add(candidate)
        inserted += 1
        checked += 1
        year = int(candidate[:2])
        sequence = int(candidate[2:])

    return {
        "inserted": inserted,
        "source": source,
        "fetched_at": fetched_at,
        "fallback_checked": checked,
    }


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
            try:
                payload = fetch_page(page_no)
            except RuntimeError as error:
                if (
                    not isinstance(error.__cause__, urllib.error.HTTPError)
                    or error.__cause__.code != 567
                ):
                    raise
                try:
                    return _update_from_issue_files(
                        connection, existing, registry, fetched_at, db_path.parent / "raw",
                        _fetch_shanghai_draw, SHANGHAI_SOURCE, "shanghai-official",
                    )
                except (urllib.error.URLError, RuntimeError):
                    return _update_from_issue_files(
                        connection, existing, registry, fetched_at, db_path.parent / "raw",
                        _fetch_official_pdf, OFFICIAL_PDF_SOURCE, "official-pdf",
                    )
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
