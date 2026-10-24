"""Experimental US130 comparison of raw SonarQube file complexity snapshots."""

import math

from util.check import Checker
from util.exceptions import InvalidMetricValue

METRIC = "complexity"


def _complexity_value(component: dict) -> float | None:
    measures = component.get("measures", [])
    if not isinstance(measures, list) or any(
        not isinstance(measure, dict) for measure in measures
    ):
        raise ValueError("Component measures must be a list of objects")
    matches = [measure for measure in measures if measure.get("metric") == METRIC]
    if len(matches) > 1:
        raise ValueError(f"Duplicate {METRIC} for {component['path']}")
    value = matches[0].get("value") if matches else None
    if value is None:
        return None
    Checker.check_metric_value(value, METRIC)
    value_float = float(value)
    if isinstance(value, bool) or not math.isfinite(value_float) or value_float < 0:
        raise InvalidMetricValue(f'"{METRIC}" must be a finite non-negative number')
    return value_float


def _file_values(snapshot: dict) -> dict[str, float | None]:
    components = snapshot.get("components")
    if not isinstance(components, list):
        raise ValueError("Expected a raw SonarQube tree with a components list")
    files = {}
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("Components must be objects")
        if component.get("qualifier") != "FIL":
            continue
        path = component.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Every FIL component must have a non-empty path")
        if path in files:
            raise ValueError(f"Duplicate file path: {path}")
        files[path] = _complexity_value(component)
    return files


def compare_file_complexity(previous: dict, current: dict) -> list[dict]:
    """Join FIL paths exactly; return raw values and current minus previous.

    Missing values stay None. File status describes snapshot membership only,
    not verified Git additions/removals or rename detection. Inputs are not mutated.
    This experiment does not calculate measure scores or infer quality changes.
    """
    before = _file_values(previous)
    after = _file_values(current)
    rows = []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        missing = [
            side
            for side, files in (("previous", before), ("current", after))
            if path in files and files[path] is None
        ]
        rows.append(
            {
                "path": path,
                "previous": old,
                "current": new,
                "delta": new - old if old is not None and new is not None else None,
                "file_status": (
                    "added"
                    if path not in before
                    else "removed" if path not in after else "matched"
                ),
                "missing_metric": missing,
            }
        )
    return rows
