"""GitAgent skill: scan_repo.py
Scans a repository for potential patentable inventions across recent commits.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ergane import analyzer, detector


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan repo for inventions")
    parser.add_argument("--repo", default=".", help="Repo path")
    parser.add_argument("--since", default="HEAD~5", help="Commit range start")
    parser.add_argument("--to", default="HEAD", help="Commit range end")
    args = parser.parse_args()

    diffs = analyzer.get_commit_diffs(args.repo, args.since, args.to)
    results = []
    for d in diffs:
        detection = detector.detect_invention(
            diff=d["diff_text"],
            commit_message=d["commit_message"],
            subgraph={"nodes": [], "edges": []},
            files_changed=d["files_changed"],
        )
        if not detection.get("skip"):
            results.append({"commit": d["commit_hash"], "detection": detection})

    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
