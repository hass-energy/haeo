"""Temporary diagnostics: dump native stacks of any test still running after a few seconds."""

from collections.abc import Generator
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading

import pytest

DUMP_AFTER_SECONDS = 3.5
DUMP_FILE = Path("hang-dumps.txt")


def _dump(nodeid: str) -> None:
    py_spy = shutil.which("py-spy") or str(Path(sys.executable).parent / "py-spy")
    with DUMP_FILE.open("a") as out:
        out.write(f"\n===== {nodeid} still running after {DUMP_AFTER_SECONDS}s =====\n")
        out.flush()
        for args in (["--native"], ["--locals"]):
            result = subprocess.run(  # noqa: S603
                ["sudo", "-n", py_spy, "dump", *args, "--pid", str(os.getpid())],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            out.write(f"----- py-spy dump {' '.join(args)} (exit {result.returncode}) -----\n")
            out.write(result.stdout)
            out.write(result.stderr)
        out.write(f"----- threads -----\n{[t.name for t in threading.enumerate()]}\n")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None]:
    """Dump the process if the test outlives DUMP_AFTER_SECONDS."""
    timer = threading.Timer(DUMP_AFTER_SECONDS, _dump, args=(item.nodeid,))
    timer.daemon = True
    timer.start()
    try:
        return (yield)
    finally:
        timer.cancel()
