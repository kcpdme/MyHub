#!/usr/bin/env bash
set -euo pipefail

echo "=== free -h ==="
free -h

echo
echo "=== top RSS processes ==="
ps -eo pid,ppid,comm,%mem,%cpu,rss,cmd --sort=-rss | head -n 25

echo
echo "=== grouped memory by process name ==="
ps -eo comm,rss --sort=-rss | awk '{sum[$1]+=$2} END {for (k in sum) printf "%s %d\n", k, sum[k]}' | sort -k2 -nr | head -n 20
