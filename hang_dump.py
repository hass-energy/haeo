"""Temporary diagnostics: record solves and dump stacks of any test still running after a few seconds."""

import asyncio
import collections
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


class _Sampler(threading.Thread):
    """Record every thread's innermost Python frames every 20 ms while a test runs."""

    def __init__(self) -> None:
        super().__init__(name="hang-dump-sampler", daemon=True)
        self.stop = threading.Event()
        self.samples: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
        self.ticks = 0

    def run(self) -> None:
        own = threading.get_ident()
        while not self.stop.wait(0.02):
            self.ticks += 1
            names = {t.ident: t.name for t in threading.enumerate()}
            for ident, frame in sys._current_frames().items():  # noqa: SLF001
                if ident == own:
                    continue
                inner = traceback.extract_stack(frame)[-4:]
                where = " > ".join(f"{Path(f.filename).name}:{f.lineno} {f.name}" for f in inner)
                self.samples[names.get(ident, str(ident))][where] += 1


def _task_stats() -> dict[str, str]:
    """Return each thread's CPU, page faults and context switches from /proc, where there is one."""
    stats: dict[str, str] = {}
    for task in Path("/proc/self/task").glob("*"):
        try:
            fields = (task / "stat").read_text().rsplit(")", 1)[1].split()
            status = dict(line.split(":\t", 1) for line in (task / "status").read_text().splitlines() if ":\t" in line)
        except OSError:
            continue
        stats[task.name] = (
            f"{status.get('Name', '?').strip()} utime {fields[11]} stime {fields[12]} minflt {fields[7]} "
            f"majflt {fields[9]} voluntary {status.get('voluntary_ctxt_switches', '?').strip()} "
            f"involuntary {status.get('nonvoluntary_ctxt_switches', '?').strip()}"
        )
    return stats


_sampler: _Sampler | None = None
_start_stats: dict[str, str] = {}


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
        out.write("----- sampled frames since the test started, every 20 ms -----\n")
        if _sampler is not None:
            out.write(f"{_sampler.ticks} ticks\n")
            for name, counter in sorted((name, counter.copy()) for name, counter in list(_sampler.samples.items())):
                out.write(f"== {name}\n")
                out.writelines(f"   {count:4d} {where}\n" for where, count in counter.most_common(12))
        out.write("----- per-thread stats at test start, then now -----\n")
        out.writelines(f"start {tid} {line}\n" for tid, line in sorted(_start_stats.items()))
        out.writelines(f"now   {tid} {line}\n" for tid, line in sorted(_task_stats().items()))
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
    global _sampler, _start_stats  # noqa: PLW0603
    _test_start = _clock()
    _start_stats = _task_stats()
    _sampler = _Sampler()
    _sampler.start()
    timer = threading.Timer(DUMP_AFTER_SECONDS, _safe_dump, args=(item.nodeid,))
    timer.daemon = True
    timer.start()
    try:
        return (yield)
    finally:
        timer.cancel()
        _sampler.stop.set()
        _sampler.join()
