"""Run one benchmark task: Home Assistant, a browser, and the server behind ``browse``.

The session seeds the hub, opens HAEO's integration page, and answers browse
commands over HTTP on a loopback port until the orchestrator posts ``/finish``.
It then scores the hub's subentries against the task (see ``scoring``) and
writes ``result.json`` to the run directory.

Run directory files:

- ``session.json``: the port, written once the page is ready.
- ``actions.jsonl``: one line per browse command.
- ``subentries.json``: the hub's subentries before and after, for rescoring.
- ``result.json``: the outcome and the action counts.
- ``agent/``: screenshots the agent asked for.
"""

from __future__ import annotations

import argparse
from contextlib import suppress
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
from pathlib import Path
import sys
from typing import override

from homeassistant.util.json import JsonValueType
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, ViewportSize, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tools.live_hass import LiveHomeAssistant, live_home_assistant
from tools.sim_hass import setup_haeo_entry
from tools.ux_bench.scoring import Subentries, evaluate, plain
from tools.ux_bench.tasks import HUB_TITLE, hub_config, load_task, world_environment, world_states

START_PATH = "/config/integrations/integration/haeo"
# Playwright enforces these timeouts in its driver, on a real clock. Timeouts that
# Python enforces (such as wait_for_event) never fire while freezegun holds the clock.
ACTION_TIMEOUT_MS = 3000
SETTLE_TIMEOUT_MS = 2000
SETTLE_PAUSE_MS = 300
READY_TIMEOUT_MS = 15000
# Startup takes seconds; these keep a stuck start well inside run.READY_SECONDS
START_TIMEOUT_SECONDS = 20
SEED_TIMEOUT_SECONDS = 20
VIEWPORT: ViewportSize = {"width": 1280, "height": 900}

_LOGGER = logging.getLogger(__name__)


def elapsed() -> float:
    """Return real elapsed seconds; freezegun patches the time module but not os.times."""
    return os.times().elapsed


# Counts error alerts the user can see, inside shadow roots as well
_VISIBLE_ERRORS_JS = """() => {
  let count = 0;
  const walk = (root) => {
    for (const el of root.querySelectorAll('*')) {
      const isError = el.tagName === 'HA-ALERT' && el.getAttribute('alert-type') === 'error';
      if (isError && el.getClientRects().length > 0) count++;
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(document);
  return count;
}"""


@dataclass
class SessionState:
    """What the agent has done so far."""

    page: Page
    agent_dir: Path
    log_path: Path
    started: float = field(default_factory=elapsed)
    status: str = "unfinished"
    message: str = ""
    actions: int = 0
    looks: int = 0
    screenshots: int = 0
    failed_commands: int = 0
    errors_shown: int = 0
    visible_errors: int = 0
    finished: float | None = None
    finish_requested: bool = False

    def counts(self) -> dict[str, JsonValueType]:
        """Return the counters for ``result.json``."""
        return {
            "status": self.status,
            "message": self.message,
            "actions": self.actions,
            "looks": self.looks,
            "screenshots": self.screenshots,
            "failed_commands": self.failed_commands,
            "errors_shown": self.errors_shown,
            "seconds": round((self.finished or elapsed()) - self.started, 1),
        }


def settle(page: Page) -> None:
    """Give the page a moment to finish loading and redraw after an action.

    Home Assistant keeps some requests open, so a page that never goes idle is
    taken as settled once the timeout passes.
    """
    with suppress(PlaywrightTimeoutError):
        page.wait_for_load_state("networkidle", timeout=SETTLE_TIMEOUT_MS)
    page.wait_for_timeout(SETTLE_PAUSE_MS)


def observe(page: Page) -> str:
    """Describe what the user sees: the open dialog if there is one, else the page."""
    dialogs = page.get_by_role("alertdialog").or_(page.get_by_role("dialog"))
    target: Page | Locator = dialogs.last if dialogs.count() else page
    path = page.url.split("://", 1)[-1].split("/", 1)[-1]
    return f"Page: /{path}\n{target.aria_snapshot(mode='ai')}"


def run_command(state: SessionState, command: str, args: list[str]) -> str:
    """Run one browse command and return what the agent should see next."""
    if state.status != "unfinished":
        return f"The task is already marked {state.status}."
    page = state.page
    error: str | None = None
    result = ""
    try:
        result = _dispatch(state, command, args)
    except (PlaywrightError, ValueError) as err:
        error = str(err).splitlines()[0]
        state.failed_commands += 1
    if command in {"click", "type", "press"}:
        settle(page)
    visible = _visible_errors(page)
    if visible > state.visible_errors:
        state.errors_shown += visible - state.visible_errors
    state.visible_errors = visible
    entry = {
        "t": round(elapsed() - state.started, 1),
        "command": command,
        "args": args,
        "error": error,
        "visible_errors": visible,
    }
    with state.log_path.open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry) + "\n")
    if error is not None:
        return f"Error: {error}\n\n{_observe_after_change(page)}"
    if command in {"done", "giveup", "screenshot"}:
        return result
    return f"{result}\n\n{_observe_after_change(page)}".lstrip()


def _visible_errors(page: Page) -> int:
    """Count visible error alerts, or zero while the page is mid-navigation."""
    try:
        return int(page.evaluate(_VISIBLE_ERRORS_JS))
    except PlaywrightError:
        return 0


def _observe_after_change(page: Page) -> str:
    """Observe the page, waiting once more if a navigation replaced it mid-read."""
    try:
        return observe(page)
    except PlaywrightError:
        settle(page)
    try:
        return observe(page)
    except PlaywrightError as err:
        return f"The page is still changing ({str(err).splitlines()[0]}). Run ./browse look."


def _dispatch(state: SessionState, command: str, args: list[str]) -> str:
    page = state.page
    match command, args:
        case "look", []:
            state.looks += 1
            return ""
        case "click", [ref]:
            state.actions += 1
            page.locator(f"aria-ref={ref}").click(timeout=ACTION_TIMEOUT_MS)
            return f"Clicked {ref}."
        case "type", [ref, *words] if words:
            state.actions += 1
            page.locator(f"aria-ref={ref}").fill(" ".join(words), timeout=ACTION_TIMEOUT_MS)
            return f"Typed into {ref}."
        case "press", [key]:
            state.actions += 1
            page.keyboard.press(key)  # applies at once, so it takes no timeout
            return f"Pressed {key}."
        case "screenshot", []:
            state.screenshots += 1
            path = state.agent_dir / f"screenshot-{state.screenshots}.png"
            page.screenshot(path=str(path))
            return f"Saved {path}"
        case ("done" | "giveup") as status, [*words] if words:
            state.status = status
            state.finished = elapsed()
            state.message = " ".join(words)
            return "Recorded. You can stop now."
        case _:
            msg = f"Unknown command or wrong arguments: {command} {' '.join(args)}"
            raise ValueError(msg)


def serve(state: SessionState, run_dir: Path) -> None:
    """Answer browse commands until the orchestrator asks the session to finish."""

    class Handler(BaseHTTPRequestHandler):
        @override
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body: object = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/finish":
                state.finish_requested = True
                reply = "ok"
            elif isinstance(body, dict) and isinstance(args := body.get("args", []), list):
                reply = run_command(state, str(body.get("command")), [str(arg) for arg in args])
            else:
                reply = "Error: the request must be a JSON object with a command and a list of args"
            data = reply.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    # Written whole and renamed into place, so a reader never sees it half written
    pending = run_dir / "session.json.tmp"
    pending.write_text(json.dumps({"port": server.server_address[1]}), encoding="utf-8")
    pending.replace(run_dir / "session.json")
    while not state.finish_requested:
        server.handle_request()
    server.server_close()


def snapshot_subentries(hass: LiveHomeAssistant, entry_id: str) -> Subentries:
    """Return each subentry of the hub as type, title, and plain data."""
    entry = hass.hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        msg = "The hub config entry is gone"
        raise RuntimeError(msg)
    return {
        subentry_id: {"type": subentry.subentry_type, "title": subentry.title, "data": plain_data(subentry.data)}
        for subentry_id, subentry in entry.subentries.items()
    }


def plain_data(data: object) -> dict[str, JsonValueType]:
    """Return subentry data as a plain JSON object."""
    value = plain(data)
    if not isinstance(value, dict):
        msg = "Subentry data is not a mapping"
        raise TypeError(msg)
    return value


def main() -> None:
    """Run one task's session."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="Task id")
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s %(name)s %(message)s")
    _LOGGER.setLevel(logging.INFO)
    run_dir = Path(args.run_dir)
    task = load_task(str(args.task))
    agent_dir = run_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    states_file = run_dir / "states.json"
    states_file.write_text(json.dumps(world_states(task)), encoding="utf-8")

    with live_home_assistant(
        timeout=START_TIMEOUT_SECONDS, environment=world_environment(task), states=states_file
    ) as hass:
        _LOGGER.info("Home Assistant started, seeding the hub")
        entry = hass.run_coro(setup_haeo_entry(hass.hass, hub_config(task)), timeout=SEED_TIMEOUT_SECONDS)

        async def retitle() -> None:
            hass.hass.config_entries.async_update_entry(entry, title=HUB_TITLE)

        hass.run_coro(retitle())
        before = snapshot_subentries(hass, entry.entry_id)

        _LOGGER.info("Hub seeded, opening the browser")
        with sync_playwright() as playwright:
            executable = os.environ.get("UX_BENCH_CHROMIUM")
            browser = (
                playwright.chromium.launch(executable_path=executable) if executable else playwright.chromium.launch()
            )
            context = browser.new_context(viewport=VIEWPORT)
            hass.configure_context(context)
            page = context.new_page()
            page.goto(f"{hass.url}{START_PATH}")
            settle(page)
            page.get_by_role("heading", name="HAEO").first.wait_for(timeout=READY_TIMEOUT_MS)
            _LOGGER.info("Page ready, serving browse commands")
            state = SessionState(page=page, agent_dir=agent_dir, log_path=run_dir / "actions.jsonl")
            serve(state, run_dir)
            browser.close()

        hass.run_coro(hass.hass.async_block_till_done(wait_background_tasks=True))
        after = snapshot_subentries(hass, entry.entry_id)

    (run_dir / "subentries.json").write_text(json.dumps({"before": before, "after": after}, indent=2), encoding="utf-8")
    result = {"task": task["id"], **evaluate(task, before, after), **state.counts()}
    (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
