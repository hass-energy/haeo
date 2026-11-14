#!/bin/sh
# Temporary diagnostics: probe a slow test process. Usage: hang_probe.sh <pid> <py-spy>
pid=$1
spy="sudo -n $2"

echo '----- system -----'
cat /proc/loadavg
vmstat 1 3
top -b -n 1 -o %CPU | head -15

echo '----- per-thread CPU over 1s (clock ticks) -----'
snap() { for t in /proc/"$pid"/task/*; do echo "$(basename "$t") $(cut -d' ' -f14,15 "$t"/stat)"; done; }
snap >/tmp/cpu1
sleep 1
snap >/tmp/cpu2
join /tmp/cpu1 /tmp/cpu2 | awk '{d=($4+$5)-($2+$3); if (d>0) print "tid", $1, "ticks", d}' | sort -k4 -rn

echo '----- thread names -----'
$spy dump --nonblocking --pid "$pid" 2>&1 | grep '^Thread'

echo '----- py-spy record 2s, samples per thread and function -----'
$spy record --nonblocking --threads --duration 2 --rate 200 --format raw --output /tmp/spy.raw --pid "$pid" 2>&1 | tail -1
python3 - /tmp/spy.raw <<'EOF'
import collections, re, sys

leaf = collections.defaultdict(collections.Counter)
inclusive = collections.defaultdict(collections.Counter)
for line in open(sys.argv[1]):
    stack, _, count = line.rstrip("\n").rpartition(" ")
    frames = stack.split(";")
    thread, frames = frames[0], [re.sub(r":\d+\)", ")", f) for f in frames[1:]]
    leaf[thread][frames[-1] if frames else "?"] += int(count)
    for frame in set(frames):
        inclusive[thread][frame] += int(count)
for thread, counter in sorted(leaf.items(), key=lambda item: -sum(item[1].values())):
    print(f"== {thread}: {sum(counter.values())} samples")
    for frame, count in counter.most_common(8):
        print(f"   leaf {count:5d} {frame[:160]}")
    for frame, count in inclusive[thread].most_common(25):
        print(f"   incl {count:5d} {frame[:160]}")
EOF
