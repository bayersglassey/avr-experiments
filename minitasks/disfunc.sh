#!/bin/bash
#
# Disassemble a single function!
# Based on: https://stackoverflow.com/a/43714073
#
set -euo pipefail

file=minitasks.elf
func=$1
shift 1

avr-objdump -d "$file" "$@" | sed '/<'"$func"'>:/,/^$/!d'
