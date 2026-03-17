#!/bin/bash
set -euo pipefail

udevadm info -a -p $(udevadm info -q path -n /dev/ttyUSB0)
