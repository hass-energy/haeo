#!/bin/sh
# Temporary diagnostics: probe a slow test process. Usage: hang_probe.sh <pid> <py-spy>
pid=$1
spy="sudo -n $2"

echo '----- py-spy record 1s, samples per thread and function -----'
$spy record --nonblocking --threads --idle --duration 1 --rate 200 --format raw --output /tmp/spy.raw --pid "$pid" 2>&1 | tail -1

echo '----- thread state and kernel wait point, 5 samples over 1s -----'
for i in 1 2 3 4 5; do
  echo "sample $i"
  for t in /proc/"$pid"/task/*; do
    echo "  $(basename "$t") $(cut -d' ' -f3 "$t"/stat 2>/dev/null) $(cat "$t"/wchan 2>/dev/null) $(cat "$t"/comm 2>/dev/null)"
  done
  sleep 0.2
done

echo '----- bytes written per process over 1s -----'
io() { for p in /proc/[0-9]*; do b=$(sudo -n awk '/^write_bytes/{print $2}' "$p"/io 2>/dev/null); [ -n "$b" ] && echo "$(basename "$p") $b"; done | sort; }
io >/tmp/io1
sleep 1
io >/tmp/io2
join /tmp/io1 /tmp/io2 | awk '{d=$3-$2; if (d>0) print d, $1}' | sort -rn | head -8 | while read -r bytes p; do
  echo "$bytes bytes  pid $p  $(tr '\0' ' ' </proc/"$p"/cmdline 2>/dev/null | cut -c1-120)"
done

echo '----- system -----'
cat /proc/loadavg
vmstat 1 2
cat /proc/pressure/io /proc/pressure/cpu 2>/dev/null

echo '----- thread names -----'
$spy dump --nonblocking --pid "$pid" 2>&1 | grep '^Thread'

echo '----- profile -----'
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
    for frame, count in inclusive[thread].most_common(20):
        print(f"   incl {count:5d} {frame[:160]}")
EOF
