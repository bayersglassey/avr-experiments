#!/bin/bash
set -euo pipefail

for i in `seq 0 4`; do
    filename="/dev/ttyUSB$i"
    if test -c "$filename"; then
        printf %s "$filename"
        exit 0
    fi
done

echo "=== Can't find a ttyUSB" >&2
exit 1
