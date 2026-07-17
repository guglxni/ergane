"""GitAgent skill: detect_invention.py
Detects inventions in a single diff.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ergane import detector


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect invention in a diff")
    parser.add_argument("--diff", required=True, help="Diff text or file path")
    parser.add_argument("--message", default="", help="Commit message")
    args = parser.parse_args()

    diff_text = args.diff
    if Path(diff_text).exists():
        diff_text = Path(diff_text).read_text()

    detection = detector.detect_invention(
        diff=diff_text,
        commit_message=args.message,
        subgraph={"nodes": [], "edges": []},
        files_changed=[],
    )
    print(json.dumps(detection, indent=2, default=str))


if __name__ == "__main__":
    main()
