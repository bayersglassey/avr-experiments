#!/bin/bash
#
# Based on: https://wiki.ubuntu.com/Kernel/Debugging/USB
#
set -euo pipefail

sudo modprobe usbmon

sudo cat /sys/kernel/debug/usb/usbmon/3u
