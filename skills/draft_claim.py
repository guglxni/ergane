"""GitAgent skill: draft_claim.py
Drafts preliminary patent claims from detection result.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ergane import detector, prior_art, synthesizer


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft claims from diff")
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
    if detection.get("skip"):
        print(json.dumps({"skipped": True, "reason": detection}, indent=2, default=str))
        return

    prior = prior_art.search_prior_art(
        technical_problem=detection["technical_problem"],
        technical_solution=detection["technical_solution"],
        key_claim_elements=detection["key_claim_elements"],
    )
    synthesis = synthesizer.synthesize(detection=detection, prior_art_results=prior)
    print(json.dumps(synthesis, indent=2, default=str))


if __name__ == "__main__":
    main()
