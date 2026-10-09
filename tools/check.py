#!/usr/bin/env python3
"""Run HAEO's CI gates.

This module is the single definition of what a gate is and how it runs.
`.github/workflows/ci.yml` invokes `uv run check <gate>` rather than repeating
the commands, so a gate cannot pass locally and fail in CI because the two
drifted apart. `tests/test_check_gates.py` enforces that correspondence.

    uv run check                 # every gate that runs locally
    uv run check --fast          # ruff, pyright and unit tests
    uv run check --fix           # apply formatter autofixes, then check
    uv run check pyright test    # only the named gates
    uv run check --list          # gate names, for CI and for scripting

Extra arguments after `--` are appended to a single gate's command, which is how
CI adds its coverage flags:

    uv run check test -- --cov=custom_components/haeo --cov-report=xml
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parent.parent

GREEN: Final = "\033[32m"
RED: Final = "\033[31m"
DIM: Final = "\033[2m"
RESET: Final = "\033[0m"


@dataclass(frozen=True)
class GateResult:
    """Outcome of running one gate."""

    ok: bool
    output: str


type GateFn = Callable[[Sequence[str]], GateResult]
type SetupFn = Callable[[], None]


def execute(argv: Sequence[str]) -> GateResult:
    """Run a command in the repository root, capturing combined output."""
    completed = subprocess.run(  # noqa: S603 (argv is built from this module's own gate definitions, never user input)
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return GateResult(ok=completed.returncode == 0, output=completed.stdout + completed.stderr)


def command(*argv: str) -> GateFn:
    """Build a gate that runs a fixed command, plus any pass-through arguments."""

    def run(extra: Sequence[str]) -> GateResult:
        return execute([*argv, *extra])

    return run


def markdown_files() -> list[str]:
    """Return tracked markdown files that still exist.

    A clean CI checkout has every tracked file present, so this matches the
    behavior of piping `git ls-files` straight in. Locally it tolerates a
    deletion that has not been staged yet.
    """
    listed = execute(["git", "ls-files", "*.md", "*.mdx"])
    return [name for name in listed.output.splitlines() if (REPO_ROOT / name).exists()]


def mdformat(*flags: str) -> GateFn:
    """Build a gate that runs mdformat over the tracked markdown files."""

    def run(extra: Sequence[str]) -> GateResult:
        return execute(["uv", "run", "mdformat", *flags, *markdown_files(), *extra])

    return run


def check_versions(_extra: Sequence[str]) -> GateResult:
    """Verify the version numbers that must agree across project metadata."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    manifest = json.loads((REPO_ROOT / "custom_components" / "haeo" / "manifest.json").read_text())
    hacs = json.loads((REPO_ROOT / "hacs.json").read_text())

    problems: list[str] = []

    project_version = pyproject["project"]["version"]
    if project_version != manifest["version"]:
        problems.append(f"pyproject.toml version ({project_version}) != manifest.json version ({manifest['version']})")

    dependencies = str(pyproject["project"]["dependencies"])
    required = re.search(r"homeassistant>=(\d+\.\d+\.\d+)", dependencies)
    if required is None:
        problems.append("pyproject.toml has no pinned homeassistant version")
    elif required.group(1) != hacs["homeassistant"]:
        problems.append(
            f"pyproject.toml homeassistant>={required.group(1)} != hacs.json homeassistant {hacs['homeassistant']}"
        )

    detail = "\n".join(problems) if problems else "versions agree"
    return GateResult(ok=not problems, output=detail)


def npm_root() -> None:
    """Install the root node modules prettier needs for its sort-json plugin."""
    if not (REPO_ROOT / "node_modules").is_dir():
        execute(["npm", "ci", "--silent"])


def card_dependencies() -> None:
    """Install the frontend card's node modules."""
    if not (REPO_ROOT / "frontend" / "haeo-forecast-card" / "node_modules").is_dir():
        execute(["npm", "--prefix", "frontend/haeo-forecast-card", "ci", "--silent"])


def card_build() -> None:
    """Build the card bundle that scenario tests render topology SVGs through."""
    card_dependencies()
    if not (REPO_ROOT / "frontend" / "haeo-forecast-card" / "dist" / "render-topology-svg.mjs").exists():
        execute(["npm", "--prefix", "frontend/haeo-forecast-card", "run", "build", "--silent"])


@dataclass(frozen=True)
class Gate:
    """One CI gate, defined once and run by both CI and developers."""

    name: str
    summary: str
    check: GateFn | None = None
    fix: GateFn | None = None
    setup: tuple[SetupFn, ...] = field(default=())
    fast: bool = False
    default: bool = True
    reason: str = ""

    @property
    def runs_locally(self) -> bool:
        """Whether this gate has a command that can run outside GitHub Actions."""
        return self.check is not None


GATES: Final[tuple[Gate, ...]] = (
    Gate(
        name="ruff-lint",
        summary="Ruff lint",
        check=command("uv", "run", "ruff", "check"),
        fix=command("uv", "run", "ruff", "check", "--fix-only", "--quiet"),
        fast=True,
    ),
    Gate(
        name="ruff-format",
        summary="Ruff format",
        check=command("uv", "run", "ruff", "format", "--check"),
        fix=command("uv", "run", "ruff", "format", "--quiet"),
        fast=True,
    ),
    Gate(
        name="imports",
        summary="Import boundaries",
        check=command("uv", "run", "lint-imports"),
    ),
    Gate(
        name="mdformat",
        summary="Markdown format",
        check=mdformat("--check"),
        fix=mdformat(),
    ),
    Gate(
        name="prettier",
        summary="Prettier",
        check=command("npx", "prettier@3", "--check", "."),
        fix=command("npx", "prettier@3", "--write", "--log-level", "warn", "."),
        setup=(npm_root,),
    ),
    Gate(
        name="version",
        summary="Version consistency",
        check=check_versions,
    ),
    Gate(
        name="pyright",
        summary="Pyright",
        check=command("uv", "run", "pyright"),
        fast=True,
    ),
    Gate(
        name="test",
        summary="Tests",
        check=command("uv", "run", "pytest", "-m", "not guide and not scenario and not benchmark", "-q", "--no-header"),
        fast=True,
    ),
    Gate(
        name="scenario",
        summary="Scenario tests",
        check=command("uv", "run", "pytest", "-m", "scenario", "-q", "--no-header"),
        setup=(card_build,),
    ),
    Gate(
        name="frontend",
        summary="Frontend card checks",
        check=command("npm", "--prefix", "frontend/haeo-forecast-card", "run", "check"),
        setup=(card_dependencies,),
    ),
    Gate(
        name="docs",
        summary="Documentation build",
        check=command("uv", "run", "zensical", "build"),
    ),
    Gate(
        name="guide",
        summary="Guide screenshot tests",
        check=command("uv", "run", "pytest", "-m", "guide", "-q", "--no-header", "--timeout=300"),
        setup=(card_build,),
        default=False,
        reason="slow and needs Playwright Firefox; runs in guides.yml, not the CI passed check",
    ),
    Gate(
        name="hassfest",
        summary="Hassfest",
        reason="only available as a GitHub Action",
    ),
    Gate(
        name="hacs",
        summary="HACS validation",
        reason="only available as a GitHub Action",
    ),
)

GATES_BY_NAME: Final[dict[str, Gate]] = {gate.name: gate for gate in GATES}


def selected_gates(names: Sequence[str], *, fast: bool) -> list[Gate]:
    """Resolve the gates to run from the command line selection."""
    if names:
        chosen: list[Gate] = []
        for name in names:
            matches = [gate for gate in GATES if name in gate.name]
            if not matches:
                known = ", ".join(gate.name for gate in GATES)
                msg = f"unknown gate {name!r}; available: {known}"
                raise SystemExit(msg)
            chosen += [gate for gate in matches if gate not in chosen]
        return chosen

    pool = [gate for gate in GATES if gate.default and gate.runs_locally]
    return [gate for gate in pool if gate.fast] if fast else pool


def run_gate(gate: Gate, extra: Sequence[str]) -> tuple[bool, str, int]:
    """Run one gate, returning whether it passed, its output, and its duration."""
    if gate.check is None:
        return True, "", 0
    for step in gate.setup:
        step()
    started = time.monotonic()
    result = gate.check(extra)
    return result.ok, result.output, round(time.monotonic() - started)


def main() -> None:
    """Run the CI gates."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("gates", nargs="*", help="Gate names to run; omit for all local gates")
    parser.add_argument("--fast", action="store_true", help="Run only ruff, pyright and unit tests")
    parser.add_argument("--fix", action="store_true", help="Apply formatter autofixes before checking")
    parser.add_argument("--list", action="store_true", help="List gate names and exit")

    # Split on `--` before parsing: a greedy positional would otherwise swallow
    # the pass-through arguments instead of leaving them for the gate command.
    argv = sys.argv[1:]
    extra: list[str] = []
    if "--" in argv:
        separator = argv.index("--")
        argv, extra = argv[:separator], argv[separator + 1 :]
    args = parser.parse_args(argv)

    if args.list:
        width = max(len(gate.name) for gate in GATES)
        for gate in GATES:
            note = "" if gate.runs_locally and gate.default else f"  {DIM}({gate.reason}){RESET}"
            print(f"{gate.name:<{width}}  {gate.summary}{note}")
        return

    if extra and len(args.gates) != 1:
        parser.error("pass-through arguments require exactly one gate")

    gates = selected_gates(args.gates, fast=args.fast)

    if args.fix:
        print("── applying autofixes ──")
        for gate in gates:
            if gate.fix is None:
                continue
            for step in gate.setup:
                step()
            gate.fix([])
            print(f"  {gate.name}")
        print()

    print("── gates ──")
    failed: list[str] = []
    passed = 0
    for gate in gates:
        if not gate.runs_locally:
            print(f"{DIM}-{RESET} {gate.name:<14} {DIM}{gate.reason}{RESET}")
            continue
        ok, output, elapsed = run_gate(gate, extra)
        if ok:
            passed += 1
            print(f"{GREEN}✓{RESET} {gate.name:<14} {elapsed}s")
        else:
            failed.append(gate.name)
            print(f"{RED}✗{RESET} {gate.name:<14} {elapsed}s")
            print("\n".join(f"    {line}" for line in output.splitlines()))
            print()

    print()
    skipped = [gate.name for gate in GATES if gate not in gates]
    if failed:
        print(f"{RED}FAILED:{RESET} {' '.join(failed)}")
        sys.exit(1)
    print(f"{GREEN}All {passed} gates passed.{RESET}")
    if skipped:
        print(f"{DIM}not run: {' '.join(skipped)}{RESET}")


if __name__ == "__main__":
    main()
