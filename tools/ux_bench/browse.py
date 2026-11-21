"""The browse command a benchmark agent uses to see and control the browser.

Usage: ``browse <command> [args...]`` with the session's port in ``UX_BENCH_PORT``.

Commands:
  look                 Show the current page or open dialog.
  click REF            Click an element.
  type REF TEXT        Replace the text in a text box.
  press KEY            Press a key, such as Enter, Escape, ArrowDown or Tab.
  screenshot           Save a screenshot and print its path.
  done SUMMARY         Mark the task complete.
  giveup REASON        Stop without completing the task.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

REQUEST_TIMEOUT_SECONDS = 120


def main() -> int:
    """Send one command to the session and print its reply."""
    command, *args = sys.argv[1:] or ["help"]
    if command in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    port = os.environ["UX_BENCH_PORT"]
    body = json.dumps({"command": command, "args": args}).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/command",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310 (loopback URL built here)
        print(response.read().decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
