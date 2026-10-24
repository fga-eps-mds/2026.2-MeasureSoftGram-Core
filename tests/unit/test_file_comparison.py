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


def test_historical_sonar_fixture_is_read_without_losing_empty_files():
    snapshot = json.loads(
        (
            DATA
            / "fga-eps-mds-2021-2-MeasureSoftGram-CLI-04-13-2022-02-13-37-v1.1.1.json"
        ).read_text()
    )
    rows = compare_file_complexity(snapshot, snapshot)
    assert len(rows) == 7
    by_path = {row["path"]: row for row in rows}
    assert by_path["src/cli/create.py"]["previous"] == 37.0
    assert by_path["src/cli/jsonReader.py"]["current"] == 19.0
    assert by_path["src/__init__.py"]["current"] == 0.0
    assert all(row["delta"] == 0 and row["file_status"] == "matched" for row in rows)


def test_path_change_is_removed_plus_added_even_with_same_component_key(snapshots):
    snapshots[1]["components"][0]["path"] = "src/renamed.py"
    rows = {row["path"]: row for row in compare_file_complexity(*snapshots)}
    assert rows["src/changed.py"]["file_status"] == "removed"
    assert rows["src/renamed.py"]["file_status"] == "added"
    assert rows["src/changed.py"]["delta"] is None
    assert rows["src/renamed.py"]["delta"] is None


def test_added_and_removed_files_can_also_have_a_missing_metric(snapshots):
    for snapshot, path in zip(snapshots, ("src/removed.py", "src/added.py")):
        component = next(c for c in snapshot["components"] if c.get("path") == path)
        component.pop("measures")
    rows = {row["path"]: row for row in compare_file_complexity(*snapshots)}
    assert rows["src/added.py"]["missing_metric"] == ["current"]
    assert rows["src/removed.py"]["missing_metric"] == ["previous"]


def test_empty_snapshots_and_absent_paging(snapshots):
    for snapshot in snapshots:
        snapshot.pop("paging")
        snapshot["components"] = []
    assert compare_file_complexity(*snapshots) == []


@pytest.mark.parametrize("components", [None, {}, [None]])
def test_malformed_component_tree_is_rejected(snapshots, components):
    snapshots[0].pop("paging")
    snapshots[0]["components"] = components
    with pytest.raises(ValueError, match="[Cc]omponents"):
        compare_file_complexity(*snapshots)
