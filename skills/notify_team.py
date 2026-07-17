"""GitAgent skill: notify_team.py
Sends OpenClaw notification for a detected invention.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ergane import notifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Notify team via OpenClaw")
    parser.add_argument("--result", required=True, help="JSON file with result")
    parser.add_argument("--repo", default=".", help="Repo path")
    args = parser.parse_args()

    result = json.loads(Path(args.result).read_text())
    notifier.notify(result, repo_path=args.repo)
    print("Notification sent (if OPENCLAW_WEBHOOK_URL is configured).")


if __name__ == "__main__":
    main()
