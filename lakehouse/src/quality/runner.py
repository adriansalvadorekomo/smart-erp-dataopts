"""DQ runner — collect rule results, log observably, fail fast.

Usage (Databricks task and local runs alike)::

    from lakehouse.src.quality import runner, rules
    results = [
        runner.run_rule("R1 pk-not-null", rules.check_no_null_keys, rows, keys, "orders"),
        ...
    ]
    runner.fail_fast(results)  # raises DataQualityError on any violation

Design: rules stay pure (``rules.py``); this module owns side effects
(logging + the fail-fast exception) so pipelines cannot silently promote
corrupted data to Gold (invariant 9).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

log = logging.getLogger("smart_erp.dq")


class DataQualityError(Exception):
    """Raised when any DQ rule fails — the pipeline must stop before Gold."""


@dataclass
class RuleResult:
    name: str
    violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations


def run_rule(name: str, fn: Callable, *args, **kwargs) -> RuleResult:
    """Execute one rule, log its outcome, return the structured result."""
    violations = list(fn(*args, **kwargs))
    if violations:
        log.error("DQ FAIL %s: %d violation(s); first: %s", name, len(violations), violations[0])
        for v in violations[1:5]:  # cap log noise; full list stays on the result
            log.error("DQ FAIL %s: %s", name, v)
        if len(violations) > 5:
            log.error("DQ FAIL %s: ... and %d more", name, len(violations) - 5)
    else:
        log.info("DQ PASS %s", name)
    return RuleResult(name=name, violations=violations)


def fail_fast(results: list[RuleResult]) -> None:
    """Raise DataQualityError if any rule failed. Call between Silver and Gold."""
    failed = [r for r in results if not r.passed]
    if failed:
        total = sum(len(r.violations) for r in failed)
        names = ", ".join(r.name for r in failed)
        raise DataQualityError(f"{len(failed)} rule(s) failed ({total} violations): {names}")
    log.info("DQ gate: all %d rules passed", len(results))
