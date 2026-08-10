from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .database import DEFAULT_DB, connect, initialize


REQUIRED_WINDOWS = ("100", "300", "500")
MIN_RANDOM_SEEDS = 1000
MIN_FORWARD_PERIODS = 30


@dataclass(frozen=True)
class Evidence:
    strategy_version: str
    model_version: str
    source_issue: str
    generated_at: str
    status: str
    payload: Mapping[str, Any]
    problems: tuple[str, ...]

    @property
    def bet_eligible(self) -> bool:
        return self.status == "VALID" and not self.problems and bool(self.payload.get("bet_eligible"))

    @property
    def primary_metrics(self) -> Mapping[str, Any]:
        return self.payload.get("walk_forward", {}).get("500", {})

    @property
    def model_stability(self) -> Optional[float]:
        value = self.payload.get("model_stability")
        return float(value) if isinstance(value, (int, float)) else None

    def summary(self) -> dict[str, Any]:
        metrics = self.primary_metrics
        forward = self.payload.get("forward_paper", {})
        holdout = self.payload.get("holdout", {})
        validation = self.payload.get("validation", {})
        return {
            "status": self.status,
            "bet_eligible": self.bet_eligible,
            "source_issue": self.source_issue,
            "generated_at": self.generated_at,
            "walk_forward_roi": metrics.get("roi"),
            "excess_roi_vs_random": metrics.get("excess_roi"),
            "random_percentile": metrics.get("random_percentile"),
            "maximum_drawdown": metrics.get("max_drawdown"),
            "roi_excluding_largest_win": metrics.get("roi_excluding_largest"),
            "validation_status": validation.get("status"),
            "holdout_status": holdout.get("status"),
            "forward_periods": forward.get("settled_periods"),
            "forward_roi": forward.get("roi"),
            "model_stability": self.model_stability,
            "random_seed_count": self.payload.get("random_seed_count"),
            "problems": list(self.problems),
        }


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_evidence_payload(payload: Mapping[str, Any], latest_issue: str) -> tuple[str, tuple[str, ...]]:
    problems: list[str] = []
    if str(payload.get("source_issue", "")) != str(latest_issue):
        problems.append("Evidence已过期：source_issue与最新已验证开奖期不一致")
    if int(payload.get("random_seed_count", 0) or 0) < MIN_RANDOM_SEEDS:
        problems.append(f"Random对照不足{MIN_RANDOM_SEEDS}个seeds")
    windows = payload.get("walk_forward")
    if not isinstance(windows, Mapping):
        problems.append("缺少Walk-forward结果")
        windows = {}
    required_metrics = ("roi", "excess_roi", "random_percentile", "max_drawdown", "roi_excluding_largest")
    for window in REQUIRED_WINDOWS:
        metrics = windows.get(window)
        if not isinstance(metrics, Mapping):
            problems.append(f"缺少最近{window}期Walk-forward结果")
            continue
        for metric in required_metrics:
            if not _number(metrics.get(metric)):
                problems.append(f"最近{window}期缺少真实指标{metric}")
    validation = payload.get("validation")
    if not isinstance(validation, Mapping) or validation.get("status") != "PASS":
        problems.append("数据或回测校验未通过")
    holdout = payload.get("holdout")
    if not isinstance(holdout, Mapping) or holdout.get("status") != "EVALUATED_PASS":
        problems.append("Locked Holdout尚未通过一次性验收")
    forward = payload.get("forward_paper")
    if not isinstance(forward, Mapping):
        problems.append("缺少Forward Paper Test结果")
    else:
        settled = int(forward.get("settled_periods", 0) or 0)
        if settled < MIN_FORWARD_PERIODS:
            problems.append(f"Forward Paper Test仅{settled}期，至少需要{MIN_FORWARD_PERIODS}期")
        if not _number(forward.get("roi")):
            problems.append("Forward Paper Test尚无可计算ROI")
    stability = payload.get("model_stability")
    if not _number(stability):
        problems.append("缺少真实模型稳定度")
    declared = str(payload.get("status", "INVALID"))
    if str(payload.get("source_issue", "")) != str(latest_issue):
        return "STALE", tuple(problems)
    if declared == "INVALID" or any("校验未通过" in item for item in problems):
        return "INVALID", tuple(problems)
    if problems or not bool(payload.get("bet_eligible")):
        return "INSUFFICIENT", tuple(problems)
    return "VALID", ()


def load_evidence(path: Path, latest_issue: str) -> Evidence:
    if not path.exists():
        return Evidence("unknown", "unknown", "", "", "INVALID", {}, ("Evidence文件不存在",))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return Evidence("unknown", "unknown", "", "", "INVALID", {}, (f"Evidence无法读取：{error}",))
    if not isinstance(payload, Mapping):
        return Evidence("unknown", "unknown", "", "", "INVALID", {}, ("Evidence格式无效",))
    status, problems = validate_evidence_payload(payload, latest_issue)
    return Evidence(
        str(payload.get("strategy_version", "unknown")),
        str(payload.get("model_version", "unknown")),
        str(payload.get("source_issue", "")),
        str(payload.get("generated_at", "")),
        status,
        payload,
        problems,
    )


def save_evidence(payload: Mapping[str, Any], path: Path, db_path: Path = DEFAULT_DB) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    immutable_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(path)
    initialize(db_path)
    with connect(db_path) as connection:
        connection.execute(
            """INSERT OR IGNORE INTO strategy_evidence(
            strategy_version,model_version,source_issue,generated_at,status,payload_json,immutable_hash
            ) VALUES(?,?,?,?,?,?,?)""",
            (
                payload["strategy_version"], payload["model_version"], payload["source_issue"],
                payload.get("generated_at", datetime.now(timezone.utc).isoformat()), payload["status"],
                json.dumps(payload, ensure_ascii=False), immutable_hash,
            ),
        )
    return immutable_hash
