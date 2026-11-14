"""Temporary diagnostics: record solves and dump stacks of any test still running after a few seconds."""

import asyncio
from collections.abc import Generator
import gc
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import traceback

import pytest

DUMP_AFTER_SECONDS = 1.5
DUMP_FILE = Path("hang-dumps.txt")


def _clock() -> float:
    """Return real elapsed seconds; freezegun patches the time module's clocks but not os.times."""
    return os.times().elapsed


_events: list[str] = []
_test_start = 0.0
_loops: list[asyncio.AbstractEventLoop] = []
_installed = False
# Held so a dump still running is never garbage collected, which would warn
_detached: list[subprocess.Popen[bytes]] = []


def _note(text: str) -> None:
    _events.append(f"{_clock() - _test_start:8.4f}s [{threading.current_thread().name}] {text}")


def _install() -> None:
    """Wrap the solve and the loop's executor submission to record when each happens."""
    global _installed  # noqa: PLW0603
    if _installed:
        return
    _installed = True
    # Imported once tests run: importing HAEO when the plugin loads imports the recorder
    # before pytest_homeassistant_custom_component patches it
    from custom_components.haeo.core.model import network, solver  # noqa: PLC0415

    optimize = network.Network.optimize

    def recorded_optimize(self: network.Network) -> float:
        _note("optimize start")
        try:
            return optimize(self)
        finally:
            _note("optimize end")

    network.Network.optimize = recorded_optimize  # type: ignore[method-assign]

    run = solver.Solver.run

    def recorded_run(self: solver.Solver) -> object:
        _, presolve = self.getOptionValue("presolve")
        _, iteration_limit = self.getOptionValue("simplex_iteration_limit")
        _note(
            f"highs run start: {self.getNumCol()} cols, {self.getNumRow()} rows, {self.getNumNz()} nonzeros, "
            f"presolve {presolve}, iteration limit {iteration_limit}"
        )
        try:
            return run(self)
        finally:
            info = self.getInfo()
            _note(
                f"highs run end: {self.modelStatusToString(self.getModelStatus())}, "
                f"{info.simplex_iteration_count} iterations, highs time {self.getRunTime():.3f}s"
            )

    solver.Solver.run = recorded_run  # type: ignore[method-assign]

    run_in_executor = asyncio.BaseEventLoop.run_in_executor

    def recorded_run_in_executor(self: asyncio.BaseEventLoop, executor: object, func: object, *args: object) -> object:
        if self not in _loops:
            _loops.append(self)
        name = getattr(func, "__qualname__", repr(func))
        _note(f"executor job submitted: {name}")
        return run_in_executor(self, executor, func, *args)  # type: ignore[arg-type]

    asyncio.BaseEventLoop.run_in_executor = recorded_run_in_executor  # type: ignore[method-assign]

    gc_started: dict[str, float] = {}

    def record_gc(phase: str, info: dict[str, int]) -> None:
        if phase == "start":
            gc_started["at"] = _clock()
            return
        took = _clock() - gc_started.get("at", _clock())
        if info["generation"] == 2 or took >= 0.05:  # noqa: PLR2004
            _note(f"gc gen {info['generation']} took {took:.3f}s, collected {info['collected']}")

    gc.callbacks.append(record_gc)


def _dump(nodeid: str) -> None:
    py_spy = shutil.which("py-spy") or str(Path(sys.executable).parent / "py-spy")
    pid = str(os.getpid())
    with DUMP_FILE.open("a") as out:
        out.write(f"\n===== {nodeid} still running after {DUMP_AFTER_SECONDS}s =====\n")
        out.write("----- events -----\n" + "\n".join(_events) + "\n")
        out.write("----- python stacks -----\n")
        for ident, frame in sys._current_frames().items():  # noqa: SLF001
            name = next((t.name for t in threading.enumerate() if t.ident == ident), str(ident))
            out.write(f"--- {name}\n{''.join(traceback.format_stack(frame))}")
        out.write("----- loop state -----\n")
        for loop in _loops:
            if loop.is_closed():
                continue
            ready = list(getattr(loop, "_ready", ()))
            scheduled = list(getattr(loop, "_scheduled", ()))
            out.write(f"loop {id(loop)} ready={len(ready)} scheduled={len(scheduled)}\n")
            out.writelines(f"  ready: {handle!r}\n" for handle in ready[:20])
            out.writelines(f"  scheduled: {handle!r}\n" for handle in scheduled[:20])
            try:
                tasks = list(asyncio.all_tasks(loop))
            except RuntimeError as err:
                out.write(f"  tasks unavailable: {err}\n")
                continue
            for task in tasks:
                out.write(f"  task {task.get_name()}: {task.get_coro()!r}\n")
                for frame in task.get_stack(limit=6):
                    out.write(f"      {frame.f_code.co_filename}:{frame.f_lineno} {frame.f_code.co_name}\n")
        out.write(f"----- gc -----\ncounts {gc.get_count()} thresholds {gc.get_threshold()} stats {gc.get_stats()}\n")
        out.write(f"objects tracked {len(gc.get_objects())} allocated blocks {sys.getallocatedblocks()}\n")
        out.flush()
    # Slow tools run detached, so this thread ends before the test's lingering-thread check
    probe = str(Path(__file__).with_name("hang_probe.sh"))
    with DUMP_FILE.open("a") as out:
        _detached.append(
            subprocess.Popen(["sh", probe, pid, py_spy], stdout=out, stderr=subprocess.STDOUT, start_new_session=True)  # noqa: S603, S607
        )


def _safe_dump(nodeid: str) -> None:
    try:
        _dump(nodeid)
    except BaseException:
        with DUMP_FILE.open("a") as out:
            out.write(f"dump failed:\n{traceback.format_exc()}\n")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None]:
    """Record the test's solves, and dump the process if the test outlives DUMP_AFTER_SECONDS."""
    global _test_start  # noqa: PLW0603
    _install()
    _events.clear()
    _test_start = _clock()
    timer = threading.Timer(DUMP_AFTER_SECONDS, _safe_dump, args=(item.nodeid,))
    timer.daemon = True
    timer.start()
    try:
        return (yield)
    finally:
        timer.cancel()
