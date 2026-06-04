#!/usr/bin/env python3
"""
Hook to run claude update at session start and log the result to custom .jsonl logs.
"""
import json
import sys
import subprocess
from datetime import datetime, timezone
from claude_code_capture_utils import get_log_file_path, add_ab_metadata


def main():
    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "unknown")
        cwd = input_data.get("cwd", "")

        result = subprocess.run(
            ["claude", "update"],
            capture_output=True,
            text=True,
            timeout=30
        )

        log_entry = {
            "type": "claude_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
        log_entry = add_ab_metadata(log_entry, cwd)

        log_file = get_log_file_path(session_id, cwd)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        print(f"[ERROR] claude_update hook: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
