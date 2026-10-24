"""Run the US130 experiment against two raw SonarQube JSON snapshots."""

import argparse
import json
from pathlib import Path

from core.file_comparison import METRIC, compare_file_complexity
from util.exceptions import InvalidMetricValue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "previous", type=Path, help="Previous complete raw SonarQube tree"
    )
    parser.add_argument(
        "current", type=Path, help="Current complete raw SonarQube tree"
    )
    args = parser.parse_args()
    try:
        previous = json.loads(args.previous.read_text(encoding="utf-8"))
        current = json.loads(args.current.read_text(encoding="utf-8"))
        rows = compare_file_complexity(previous, current)
    except (OSError, ValueError, InvalidMetricValue) as error:
        parser.error(str(error))
    print(
        json.dumps(
            {
                "experimental": True,
                "metric": METRIC,
                "previous_snapshot": str(args.previous),
                "current_snapshot": str(args.current),
                "files": rows,
            },
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
