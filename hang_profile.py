# ruff: noqa: T201
"""Temporary diagnostics: summarize a py-spy raw profile by thread, leaf frame and inclusive frame."""

import collections
from pathlib import Path
import re
import sys

LEAVES = 12
INCLUSIVE = 40


def main(path: str) -> None:
    """Print each thread's sample count, its heaviest leaf frames and its heaviest inclusive frames."""
    leaf: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    inclusive: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for line in Path(path).read_text().splitlines():
        stack, _, count = line.rpartition(" ")
        thread, *frames = stack.split(";")
        # Drop line numbers and addresses so samples of one function add up
        names = [re.sub(r":\d+\)|\s*\(0x[0-9a-f]+\)|^0x[0-9a-f]+ ", ")" if ":" in f else "", f).strip() for f in frames]
        leaf[thread][names[-1] if names else "?"] += int(count)
        for name in set(names):
            inclusive[thread][name] += int(count)
    for thread, counter in sorted(leaf.items(), key=lambda item: -sum(item[1].values())):
        print(f"== {thread}: {sum(counter.values())} samples")
        for name, count in counter.most_common(LEAVES):
            print(f"   leaf {count:5d} {name[:170]}")
        for name, count in inclusive[thread].most_common(INCLUSIVE):
            print(f"   incl {count:5d} {name[:170]}")


if __name__ == "__main__":
    main(sys.argv[1])
