#!/bin/bash
set -euo pipefail

avrdude -c arduino -p m328p -P "${USBTTY:-/dev/ttyUSB0}" -b 57600 -D -U flash:w:minitasks.hex:i
