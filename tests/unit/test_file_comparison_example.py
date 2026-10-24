"""Check the documented command, including readable failures at the boundary."""

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "examples" / "compare_file_complexity.py"
DATA = ROOT / "tests" / "unit" / "data" / "us130"


def run_example(previous, current):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(previous), str(current)],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
    )


def test_documented_example_outputs_json():
    result = run_example(DATA / "before.json", DATA / "after.json")
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["experimental"] is True
    assert output["metric"] == "complexity"
    rows = {row["path"]: row for row in output["files"]}
    assert rows["src/changed.py"]["delta"] == -2
    assert rows["src/added.py"]["previous"] is None
    assert rows["src/missing_after.py"]["missing_metric"] == ["current"]


def test_example_reports_file_error_without_traceback(tmp_path):
    result = run_example(tmp_path / "missing.json", DATA / "after.json")
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def test_example_reports_invalid_json_without_traceback(tmp_path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not JSON")
    result = run_example(invalid, DATA / "after.json")
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout
