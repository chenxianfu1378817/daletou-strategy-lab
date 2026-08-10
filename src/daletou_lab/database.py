from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "data" / "daletou.db"


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS draws (
    draw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue TEXT NOT NULL UNIQUE,
    draw_date TEXT NOT NULL,
    front_1 INTEGER NOT NULL,
    front_2 INTEGER NOT NULL,
    front_3 INTEGER NOT NULL,
    front_4 INTEGER NOT NULL,
    front_5 INTEGER NOT NULL,
    back_1 INTEGER NOT NULL,
    back_2 INTEGER NOT NULL,
    sales_amount REAL,
    jackpot_before REAL,
    jackpot_after REAL,
    rule_version TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT
);
CREATE TABLE IF NOT EXISTS prizes (
    issue TEXT NOT NULL,
    prize_level INTEGER NOT NULL,
    prize_name TEXT NOT NULL,
    winning_count INTEGER,
    prize_per_ticket INTEGER,
    additional INTEGER NOT NULL DEFAULT 0,
    rule_version TEXT NOT NULL,
    PRIMARY KEY (issue, prize_name),
    FOREIGN KEY (issue) REFERENCES draws(issue)
);
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue TEXT NOT NULL,
    created_at TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('BET','SKIP')),
    budget_limit INTEGER NOT NULL CHECK(budget_limit BETWEEN 0 AND 100),
    recommended_amount INTEGER NOT NULL CHECK(recommended_amount BETWEEN 0 AND budget_limit),
    bet_type TEXT NOT NULL,
    numbers_json TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    model_version TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    optimizer_version TEXT NOT NULL,
    budget_version TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    code_commit_hash TEXT,
    strategy_version TEXT,
    evidence_status TEXT,
    evidence_json TEXT,
    random_seed INTEGER,
    immutable_hash TEXT NOT NULL UNIQUE
);
CREATE TRIGGER IF NOT EXISTS predictions_no_update
BEFORE UPDATE ON predictions
BEGIN SELECT RAISE(ABORT, 'predictions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS predictions_no_delete
BEFORE DELETE ON predictions
BEGIN SELECT RAISE(ABORT, 'predictions are append-only'); END;
CREATE TABLE IF NOT EXISTS paper_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL,
    strategy_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    settled_at TEXT,
    gross_prize INTEGER,
    net_profit INTEGER,
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
);
CREATE TABLE IF NOT EXISTS real_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue TEXT NOT NULL,
    actual_numbers_json TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    additional_bet INTEGER NOT NULL DEFAULT 0,
    ticket_cost INTEGER NOT NULL CHECK(ticket_cost BETWEEN 0 AND 100),
    purchased_at TEXT NOT NULL,
    settled_at TEXT,
    gross_prize INTEGER,
    applicable_tax INTEGER,
    net_prize INTEGER,
    net_profit INTEGER,
    roi REAL
);
CREATE TABLE IF NOT EXISTS model_versions (
    model_id TEXT NOT NULL,
    version TEXT NOT NULL,
    params_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (model_id, version)
);
CREATE TABLE IF NOT EXISTS strategy_versions (
    strategy_id TEXT NOT NULL,
    version TEXT NOT NULL,
    params_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (strategy_id, version)
);
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    period_label TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS strategy_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_version TEXT NOT NULL,
    model_version TEXT NOT NULL,
    source_issue TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('VALID', 'INSUFFICIENT', 'INVALID', 'STALE')),
    payload_json TEXT NOT NULL,
    immutable_hash TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS holdout_registry (
    holdout_id TEXT PRIMARY KEY,
    start_issue TEXT NOT NULL,
    end_issue TEXT NOT NULL,
    model_version TEXT NOT NULL,
    locked_at TEXT NOT NULL,
    evaluated_at TEXT,
    result_json TEXT,
    CHECK(evaluated_at IS NULL OR result_json IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS strategy_graveyard (
    strategy_id TEXT NOT NULL,
    version TEXT NOT NULL,
    params_json TEXT NOT NULL,
    feature_set TEXT NOT NULL,
    development_period TEXT NOT NULL,
    validation_period TEXT NOT NULL,
    holdout_result TEXT,
    forward_result TEXT,
    roi REAL,
    excess_roi REAL,
    max_drawdown REAL,
    reason_removed TEXT NOT NULL,
    removed_at TEXT NOT NULL,
    PRIMARY KEY(strategy_id, version)
);
CREATE TABLE IF NOT EXISTS data_warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue TEXT,
    warning_code TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
"""


@dataclass(frozen=True)
class Draw:
    issue: str
    draw_date: str
    front: Tuple[int, int, int, int, int]
    back: Tuple[int, int]
    sales_amount: Optional[float] = None
    jackpot_before: Optional[float] = None
    jackpot_after: Optional[float] = None
    rule_version: str = ""
    source: str = ""
    fetched_at: str = ""
    verified: bool = False
    raw_json: str = ""


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(db_path: Path = DEFAULT_DB) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(predictions)")}
        migrations = {
            "strategy_version": "ALTER TABLE predictions ADD COLUMN strategy_version TEXT",
            "evidence_status": "ALTER TABLE predictions ADD COLUMN evidence_status TEXT",
            "evidence_json": "ALTER TABLE predictions ADD COLUMN evidence_json TEXT",
            "random_seed": "ALTER TABLE predictions ADD COLUMN random_seed INTEGER",
        }
        for column, statement in migrations.items():
            if column not in columns:
                connection.execute(statement)
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS predictions_issue_strategy_once "
            "ON predictions(issue, strategy_version) WHERE strategy_version IS NOT NULL"
        )


def upsert_draw(connection: sqlite3.Connection, draw: Draw, prizes: Sequence[Dict[str, object]]) -> None:
    values = (
        draw.issue,
        draw.draw_date,
        *draw.front,
        *draw.back,
        draw.sales_amount,
        draw.jackpot_before,
        draw.jackpot_after,
        draw.rule_version,
        draw.source,
        draw.fetched_at,
        int(draw.verified),
        draw.raw_json,
    )
    connection.execute(
        """
        INSERT INTO draws(issue, draw_date, front_1, front_2, front_3, front_4, front_5,
          back_1, back_2, sales_amount, jackpot_before, jackpot_after, rule_version,
          source, fetched_at, verified, raw_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(issue) DO UPDATE SET
          draw_date=excluded.draw_date, front_1=excluded.front_1, front_2=excluded.front_2,
          front_3=excluded.front_3, front_4=excluded.front_4, front_5=excluded.front_5,
          back_1=excluded.back_1, back_2=excluded.back_2, sales_amount=excluded.sales_amount,
          jackpot_before=excluded.jackpot_before, jackpot_after=excluded.jackpot_after,
          rule_version=excluded.rule_version, source=excluded.source, fetched_at=excluded.fetched_at,
          verified=excluded.verified, raw_json=excluded.raw_json
        """,
        values,
    )
    for prize in prizes:
        connection.execute(
            """
            INSERT INTO prizes(issue, prize_level, prize_name, winning_count, prize_per_ticket, additional, rule_version)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(issue, prize_name) DO UPDATE SET
              winning_count=excluded.winning_count, prize_per_ticket=excluded.prize_per_ticket,
              additional=excluded.additional, rule_version=excluded.rule_version
            """,
            (
                draw.issue,
                prize["prize_level"],
                prize["prize_name"],
                prize.get("winning_count"),
                prize.get("prize_per_ticket"),
                int(bool(prize.get("additional"))),
                draw.rule_version,
            ),
        )


def load_draws(db_path: Path = DEFAULT_DB, limit: Optional[int] = None) -> List[Draw]:
    query = "SELECT * FROM draws WHERE verified=1 ORDER BY CAST(issue AS INTEGER)"
    params: Tuple[object, ...] = ()
    if limit is not None:
        query = "SELECT * FROM (SELECT * FROM draws WHERE verified=1 ORDER BY CAST(issue AS INTEGER) DESC LIMIT ?) ORDER BY CAST(issue AS INTEGER)"
        params = (limit,)
    with connect(db_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [
        Draw(
            issue=row["issue"],
            draw_date=row["draw_date"],
            front=tuple(row[f"front_{i}"] for i in range(1, 6)),
            back=tuple(row[f"back_{i}"] for i in range(1, 3)),
            sales_amount=row["sales_amount"],
            jackpot_before=row["jackpot_before"],
            jackpot_after=row["jackpot_after"],
            rule_version=row["rule_version"],
            source=row["source"],
            fetched_at=row["fetched_at"],
            verified=bool(row["verified"]),
            raw_json=row["raw_json"],
        )
        for row in rows
    ]


def realized_prizes(connection: sqlite3.Connection, issue: str) -> Dict[int, int]:
    rows = connection.execute(
        "SELECT prize_level, prize_per_ticket FROM prizes WHERE issue=? AND additional=0",
        (issue,),
    ).fetchall()
    return {int(row[0]): int(row[1]) for row in rows if row[1] is not None}
