"""Run the config flow usability benchmark and summarize the results.

Each run starts a session (Home Assistant plus a browser), then a sandboxed
``claude -p`` that plays the user. The agent can only run ``./browse`` and read
the screenshots it saves. Results go to ``--out``:

- ``<task>/run<N>/``: the session log, actions, screenshots, the agent's reply, and ``result.json``.
- ``summary.json`` and ``summary.md``: success rate and effort per task.
- ``report.md``: every run's problems and the agent's own account of where it struggled.

Usage::

    uv run python -m tools.ux_bench.run --repeats 3 --parallel 8
    uv run python -m tools.ux_bench.run --task add_battery --repeats 1
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shlex
import statistics
import subprocess
import sys
import time
from typing import NotRequired, Required, TypedDict
import urllib.error
import urllib.request

from homeassistant.util.json import JsonValueType

from tools.ux_bench.scoring import Subentries, evaluate
from tools.ux_bench.tasks import HUB_TITLE, PROJECT_ROOT, Task, load_task, load_tasks

READY_SECONDS = 60
FINISH_SECONDS = 60
DEFAULT_MODEL = "sonnet"
# Variables that tie a Claude process to the session that started it. The agent
# gets none of them, so it runs as a standalone session.
SESSION_VARIABLE_PREFIXES = ("CLAUDE", "AI_AGENT")
SESSION_VARIABLES_KEPT = frozenset({"CLAUDE_CONFIG_DIR"})


class RunResult(TypedDict, total=False):
    """One run's outcome, effort, and the agent's own account."""

    task: Required[str]
    repeat: Required[int]
    success: Required[bool]
    problems: list[str]
    result_data: dict[str, JsonValueType] | None
    status: str
    message: str
    actions: int
    looks: int
    screenshots: int
    failed_commands: int
    errors_shown: int
    seconds: float
    cost_usd: float | None
    turns: int | None
    report: str
    driver_error: str | None


class TaskSummary(TypedDict):
    """Pass count and median effort for one task."""

    runs: int
    passed: int
    actions: float | None
    actions_when_passed: float | None
    errors_shown: float | None
    seconds: float | None
    cost_usd: float


class Summary(TypedDict):
    """Pass rate and effort over every run."""

    runs: int
    passed: int
    success_rate: float | None
    actions: float | None
    cost_usd: float
    tasks: dict[str, TaskSummary]
    model: NotRequired[str]


DRIVER_PROMPT = """\
You are a homeowner setting up HAEO (Home Assistant Energy Optimizer) in the Home Assistant web interface.
You know your own home and energy equipment, but you have never used HAEO before.
You have no documentation, and you cannot read HAEO's code.

You see and control the browser only through the ./browse command, run with the Bash tool:

  ./browse look              Show the current page or open dialog as an accessibility tree.
                             Elements have refs like [ref=f2e15].
  ./browse click REF         Click an element.
  ./browse type REF TEXT     Replace the text in a text box. Also use it to search in pickers.
  ./browse press KEY         Press a key, such as Enter, Escape, ArrowDown or Tab.
  ./browse screenshot        Save a screenshot and print its path. Read the file to see the page.
  ./browse done SUMMARY      Finish once the task is complete.
  ./browse giveup REASON     Stop if you cannot complete the task.

Each action prints the page as it is afterwards. Refs change, so use refs from the latest output.

Work the way a careful user would. Read labels and help text, make the choices you believe are right,
and check that the result took effect before you finish. Pick entities from what the interface offers.

When you have finished, end your reply with a short list of every point where you hesitated,
were unsure, or made a mistake, and say why.
"""


def task_prompt(task: Task) -> str:
    """Return the goal as the user is told it."""
    parts = ", ".join(task["participants"])
    return (
        f"{task['goal']}\n\n"
        f"HAEO is already set up for your home, called {HUB_TITLE!r}, with these parts: {parts}. "
        "You are logged in to Home Assistant and looking at the HAEO integration page."
    )


def driver_command(task: Task, agent_dir: Path, model: str, budget: float) -> list[str]:
    """Return the sandboxed ``claude`` command for one run."""
    return [
        "claude",
        "-p",
        task_prompt(task),
        "--model",
        model,
        "--system-prompt",
        DRIVER_PROMPT,
        "--tools",
        "Bash,Read",
        "--allowedTools",
        "Bash(./browse *)",
        f"Read(/{agent_dir}/**)",
        "--permission-mode",
        "dontAsk",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--output-format",
        "json",
        "--max-budget-usd",
        str(budget),
    ]


def driver_environment() -> dict[str, str]:
    """Return this process's environment without the variables of its Claude session."""
    return {
        name: value
        for name, value in os.environ.items()
        if name in SESSION_VARIABLES_KEPT or not name.startswith(SESSION_VARIABLE_PREFIXES)
    }


def _wait_for_file(path: Path, process: subprocess.Popen[bytes], seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            return True
        if process.poll() is not None:
            return False
        time.sleep(0.5)
    return False


def _finish_session(port: int) -> None:
    request = urllib.request.Request(f"http://127.0.0.1:{port}/finish", data=b"{}", method="POST")
    with urllib.request.urlopen(request, timeout=FINISH_SECONDS):  # noqa: S310 (loopback URL built here)
        pass


def browse_script(port: int) -> str:
    """Return the ``browse`` wrapper the agent runs, bound to its session's port."""
    browse = PROJECT_ROOT / "tools" / "ux_bench" / "browse.py"
    return f'#!/bin/sh\nUX_BENCH_PORT={port} exec {shlex.quote(sys.executable)} {shlex.quote(str(browse))} "$@"\n'


def run_one(task: Task, repeat: int, out: Path, *, model: str, budget: float, timeout: float) -> RunResult:
    """Run one task once and return its result."""
    run_dir = out / task["id"] / f"run{repeat}"
    agent_dir = run_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    result: RunResult = {"task": task["id"], "repeat": repeat, "success": False}

    with (run_dir / "session.log").open("wb") as session_log:
        session = subprocess.Popen(  # noqa: S603 (fixed command; the task id names a file in tasks/)
            [sys.executable, "-m", "tools.ux_bench.session", "--task", task["id"], "--run-dir", str(run_dir)],
            cwd=PROJECT_ROOT,
            stdout=session_log,
            stderr=subprocess.STDOUT,
        )
        try:
            if not _wait_for_file(run_dir / "session.json", session, READY_SECONDS):
                result["problems"] = ["The session did not start; see session.log"]
                return result
            port = int(json.loads((run_dir / "session.json").read_text(encoding="utf-8"))["port"])
            browse = agent_dir / "browse"
            browse.write_text(browse_script(port), encoding="utf-8")
            browse.chmod(0o755)

            try:
                driver = subprocess.run(  # noqa: S603 (fixed command, task text passed as an argument)
                    driver_command(task, agent_dir, model, budget),
                    cwd=agent_dir,
                    env=driver_environment(),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                (run_dir / "driver.json").write_text(driver.stdout, encoding="utf-8")
                (run_dir / "driver.stderr").write_text(driver.stderr, encoding="utf-8")
                _add_driver_summary(result, driver.stdout)
            except subprocess.TimeoutExpired:
                result["driver_error"] = f"The agent did not finish within {timeout:.0f} s"

            try:
                _finish_session(port)
                session.wait(timeout=FINISH_SECONDS)
            except (urllib.error.URLError, subprocess.TimeoutExpired) as err:
                result["problems"] = [f"The session did not finish cleanly ({err}); see session.log"]
        finally:
            if session.poll() is None:
                session.kill()

    result_file = run_dir / "result.json"
    if result_file.exists():
        result.update(json.loads(result_file.read_text(encoding="utf-8")))
    else:
        result["problems"] = ["The session wrote no result; see session.log"]
    (run_dir / "run.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _add_driver_summary(result: RunResult, stdout: str) -> None:
    try:
        reply: object = json.loads(stdout)
    except json.JSONDecodeError:
        reply = None
    if not isinstance(reply, dict):
        result["driver_error"] = "The agent's output was not a JSON object; see driver.json"
        return
    cost, turns, report = reply.get("total_cost_usd"), reply.get("num_turns"), reply.get("result")
    result["cost_usd"] = float(cost) if isinstance(cost, int | float) else None
    result["turns"] = turns if isinstance(turns, int) else None
    result["report"] = report if isinstance(report, str) else ""
    result["driver_error"] = str(reply.get("subtype")) if reply.get("is_error") else None


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def summarize(results: list[RunResult]) -> Summary:
    """Aggregate run results per task and overall."""
    by_task: dict[str, list[RunResult]] = {}
    for result in results:
        by_task.setdefault(result["task"], []).append(result)

    tasks: dict[str, TaskSummary] = {}
    for task_id, runs in sorted(by_task.items()):
        passed = [run for run in runs if run["success"]]
        tasks[task_id] = {
            "runs": len(runs),
            "passed": len(passed),
            "actions": _median([run["actions"] for run in runs if "actions" in run]),
            "actions_when_passed": _median([run["actions"] for run in passed if "actions" in run]),
            "errors_shown": _median([run["errors_shown"] for run in runs if "errors_shown" in run]),
            "seconds": _median([run["seconds"] for run in runs if "seconds" in run]),
            "cost_usd": round(sum(run.get("cost_usd") or 0 for run in runs), 2),
        }
    total = len(results)
    passed_total = sum(1 for result in results if result["success"])
    return {
        "runs": total,
        "passed": passed_total,
        "success_rate": round(passed_total / total, 3) if total else None,
        "actions": _median([result["actions"] for result in results if "actions" in result]),
        "cost_usd": round(sum(result.get("cost_usd") or 0 for result in results), 2),
        "tasks": tasks,
    }


def summary_markdown(summary: Summary, model: str) -> str:
    """Render the summary as a Markdown table."""
    rate = summary["success_rate"] or 0
    lines = [
        f"Model: {model}. Passed {summary['passed']}/{summary['runs']} runs ({rate:.0%}), "
        f"median {summary['actions']} actions, ${summary['cost_usd']:.2f}.",
        "",
        "| Task | Passed | Actions | Actions when passed | Errors shown | Seconds | Cost |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {task_id} | {row['passed']}/{row['runs']} | {row['actions']} | {row['actions_when_passed']} | "
        f"{row['errors_shown']} | {row['seconds']} | ${row['cost_usd']:.2f} |"
        for task_id, row in summary["tasks"].items()
    )
    return "\n".join(lines) + "\n"


def report_markdown(results: list[RunResult]) -> str:
    """Collect every run's problems and the agent's account of where it struggled."""
    lines: list[str] = []
    for result in sorted(results, key=lambda run: (run["task"], run["repeat"])):
        verdict = "passed" if result["success"] else "failed"
        lines.extend(["", f"## {result['task']} run {result['repeat']}: {verdict}", ""])
        lines.extend(f"- {problem}" for problem in result.get("problems", []))
        if result.get("driver_error"):
            lines.append(f"- Agent error: {result.get('driver_error')}")
        if report := result.get("report"):
            lines.extend(["", report.strip()])
    return "# Benchmark runs\n" + "\n".join(lines) + "\n"


def rescore(out: Path) -> list[RunResult]:
    """Score every run in ``out`` again from its saved subentries."""
    results: list[RunResult] = []
    for run_file in sorted(out.glob("*/run*/run.json")):
        result: RunResult = json.loads(run_file.read_text(encoding="utf-8"))
        snapshot_file = run_file.parent / "subentries.json"
        if snapshot_file.exists():
            snapshots: dict[str, Subentries] = json.loads(snapshot_file.read_text(encoding="utf-8"))
            outcome = evaluate(load_task(result["task"]), snapshots["before"], snapshots["after"])
            result["success"] = outcome["success"]
            result["problems"] = outcome["problems"]
            result["result_data"] = outcome["result_data"]
            run_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        results.append(result)
    return results


def write_summaries(out: Path, results: list[RunResult], model: str) -> None:
    """Write the summary and report files and print the summary."""
    summary = summarize(results)
    (out / "summary.json").write_text(json.dumps({**summary, "model": model}, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(summary_markdown(summary, model), encoding="utf-8")
    (out / "report.md").write_text(report_markdown(results), encoding="utf-8")
    print(summary_markdown(summary, model))
    print(f"Results in {out}")


def main() -> None:
    """Run the benchmark."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", action="append", help="Task id to run; repeat for several (default: all)")
    parser.add_argument("--holdout", action="store_true", help="Include the holdout tasks")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--parallel", type=int, default=8)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--budget", type=float, default=3.0, help="Spend limit per run in USD")
    parser.add_argument("--timeout", type=float, default=900, help="Time limit per run in seconds")
    parser.add_argument("--out", type=Path, help="Output directory (default: .ux-bench/<timestamp>)")
    parser.add_argument("--rescore", action="store_true", help="Score the runs already in --out again")
    args = parser.parse_args()
    model = str(args.model)

    if args.rescore:
        if args.out is None:
            parser.error("--rescore needs --out")
        out = Path(args.out)
        summary: Summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        write_summaries(out, rescore(out), summary.get("model", model))
        return

    selected: set[str] = set(args.task or [])
    tasks = [
        task
        for task in load_tasks(include_holdout=bool(args.holdout or selected))
        if not selected or task["id"] in selected
    ]
    unknown = selected - {task["id"] for task in load_tasks(include_holdout=True)}
    if unknown:
        parser.error(f"Unknown task ids: {', '.join(sorted(unknown))}")
    out = (
        Path(args.out).resolve()
        if args.out
        else PROJECT_ROOT / ".ux-bench" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(task, repeat) for task in tasks for repeat in range(1, int(args.repeats) + 1)]

    with ThreadPoolExecutor(max_workers=int(args.parallel)) as pool:
        futures = [
            pool.submit(run_one, task, repeat, out, model=model, budget=float(args.budget), timeout=float(args.timeout))
            for task, repeat in jobs
        ]
        results: list[RunResult] = []
        for future in futures:
            result = future.result()
            results.append(result)
            print(f"{result['task']} run {result['repeat']}: {'passed' if result['success'] else 'failed'}", flush=True)

    write_summaries(out, results, model)


if __name__ == "__main__":
    main()
