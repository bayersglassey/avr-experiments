#!/bin/bash
set -euo pipefail

TTY=`./get_ttyusb.sh`
avrdude -c arduino -p m328p -P "$TTY" -b 57600 -D -U flash:w:minitasks.hex:i
