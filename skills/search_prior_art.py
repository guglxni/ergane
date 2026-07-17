"""GitAgent skill: search_prior_art.py
Generates Coral SQL and executes prior art search.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ergane import prior_art


def main() -> None:
    parser = argparse.ArgumentParser(description="Search prior art")
    parser.add_argument("--problem", required=True, help="Technical problem description")
    parser.add_argument("--solution", required=True, help="Technical solution description")
    parser.add_argument("--elements", nargs="+", default=[], help="Key claim elements")
    args = parser.parse_args()

    results = prior_art.search_prior_art(
        technical_problem=args.problem,
        technical_solution=args.solution,
        key_claim_elements=args.elements,
    )
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
