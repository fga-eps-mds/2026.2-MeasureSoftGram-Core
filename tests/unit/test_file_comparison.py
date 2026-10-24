"""US130: raw per-file comparison, independent of the quality formulas."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from core.file_comparison import compare_file_complexity
from util.exceptions import InvalidMetricValue

DATA = Path(__file__).parent / "data"


@pytest.fixture
def snapshots():
    return tuple(
        json.loads((DATA / "us130" / f"{name}.json").read_text())
        for name in ("before", "after")
    )


def test_comparison_preserves_values_membership_and_missing_metrics(snapshots):
    previous, current = snapshots
    original = deepcopy(snapshots)
    rows = compare_file_complexity(previous, current)
    assert snapshots == original
    assert [row["path"] for row in rows] == sorted(row["path"] for row in rows)
    assert len(rows) == 8  # FIL only, including paths with missing metrics
    by_path = {row["path"]: row for row in rows}
    expected = {
        "added": (None, 0.0, None, "added", []),
        "removed": (3.0, None, None, "removed", []),
        "changed": (6.0, 4.0, -2.0, "matched", []),
        "unchanged": (2.0, 2.0, 0.0, "matched", []),
        "zero": (0.0, 1.0, 1.0, "matched", []),
        "missing_before": (None, 7.0, None, "matched", ["previous"]),
        "missing_after": (5.0, None, None, "matched", ["current"]),
        "missing_both": (None, None, None, "matched", ["previous", "current"]),
    }
    for name, values in expected.items():
        path = f"src/{name}.py"
        assert by_path[path] == dict(
            zip(
                (
                    "path",
                    "previous",
                    "current",
                    "delta",
                    "file_status",
                    "missing_metric",
                ),
                (path, *values),
            )
        )


@pytest.mark.parametrize("value", ["bad", "", "NaN", "inf", -1, True, [], {}])
def test_invalid_metric_is_rejected_instead_of_becoming_zero(snapshots, value):
    previous, current = snapshots
    current["components"][0]["measures"][0]["value"] = value
    with pytest.raises(InvalidMetricValue):
        compare_file_complexity(previous, current)


@pytest.mark.parametrize("side", [0, 1])
def test_duplicate_paths_are_rejected(snapshots, side):
    snapshots[side].pop("paging")
    snapshots[side]["components"].append(snapshots[side]["components"][0])
    with pytest.raises(ValueError, match="Duplicate file path"):
        compare_file_complexity(*snapshots)


def test_duplicate_metric_is_rejected(snapshots):
    measures = snapshots[0]["components"][0]["measures"]
    measures.append(deepcopy(measures[0]))
    with pytest.raises(ValueError, match="Duplicate complexity"):
        compare_file_complexity(*snapshots)


@pytest.mark.parametrize(
    "field,value", [("key", "another-project"), ("branch", "other")]
)
def test_project_or_branch_mismatch_is_rejected(snapshots, field, value):
    snapshots[1]["baseComponent"][field] = value
    with pytest.raises(ValueError, match="same SonarQube project key and branch"):
        compare_file_complexity(*snapshots)


@pytest.mark.parametrize(
    "paging",
    [
        None,
        {},
        {"pageIndex": 2, "pageSize": 500, "total": 9},
        {"pageIndex": 1, "pageSize": 500, "total": 501},
        {"pageIndex": 1, "pageSize": 1, "total": 9},
        {"pageIndex": True, "pageSize": 500, "total": 9},
    ],
)
def test_incomplete_or_invalid_paging_is_rejected(snapshots, paging):
    snapshots[1]["paging"] = paging
    with pytest.raises(ValueError, match="[Pp]aging"):
        compare_file_complexity(*snapshots)


@pytest.mark.parametrize("snapshot", [None, [], {}, {"baseComponent": {"key": " "}}])
def test_unidentified_snapshot_is_rejected(snapshots, snapshot):
    with pytest.raises(ValueError):
        compare_file_complexity(snapshot, snapshots[1])


@pytest.mark.parametrize("path", [None, "", "   ", 42])
def test_file_requires_a_path(snapshots, path):
    snapshots[0]["components"][0]["path"] = path
    with pytest.raises(ValueError, match="non-empty path"):
        compare_file_complexity(*snapshots)


@pytest.mark.parametrize("measures", [None, {}, [None]])
def test_malformed_measures_are_rejected(snapshots, measures):
    snapshots[0]["components"][0]["measures"] = measures
    with pytest.raises(ValueError, match="measures must be a list"):
        compare_file_complexity(*snapshots)
