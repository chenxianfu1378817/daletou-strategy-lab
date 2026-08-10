from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, List, Sequence

from .database import Draw
from .rules import RuleRegistry, validate_numbers


@dataclass(frozen=True)
class ValidationWarning:
    issue: str | None
    code: str
    details: str


def validate_draws(draws: Sequence[Draw], registry: RuleRegistry | None = None) -> List[ValidationWarning]:
    registry = registry or RuleRegistry()
    warnings: List[ValidationWarning] = []
    seen = set()
    previous_issue = None
    previous_date = None
    for draw in sorted(draws, key=lambda value: int(value.issue)):
        if draw.issue in seen:
            warnings.append(ValidationWarning(draw.issue, "DUPLICATE_ISSUE", "期号重复"))
        seen.add(draw.issue)
        try:
            rule = registry.for_issue(draw.issue)
        except LookupError as error:
            warnings.append(ValidationWarning(draw.issue, "UNKNOWN_RULE", str(error)))
            continue
        try:
            validate_numbers(draw.front, draw.back, rule)
        except ValueError as error:
            warnings.append(ValidationWarning(draw.issue, "INVALID_NUMBERS", str(error)))
        if draw.rule_version != rule.rule_version:
            warnings.append(ValidationWarning(draw.issue, "RULE_MISMATCH", f"{draw.rule_version} != {rule.rule_version}"))
        try:
            current_date = date.fromisoformat(draw.draw_date)
        except ValueError:
            warnings.append(ValidationWarning(draw.issue, "INVALID_DATE", draw.draw_date))
            current_date = None
        if previous_issue is not None and int(draw.issue) <= previous_issue:
            warnings.append(ValidationWarning(draw.issue, "ISSUE_ORDER", "期号未严格递增"))
        if previous_date is not None and current_date is not None and current_date < previous_date:
            warnings.append(ValidationWarning(draw.issue, "DATE_ORDER", "开奖日期倒序"))
        if draw.sales_amount is not None and draw.sales_amount < 0:
            warnings.append(ValidationWarning(draw.issue, "INVALID_SALES", "销售额为负"))
        previous_issue = int(draw.issue)
        previous_date = current_date or previous_date
    return warnings

