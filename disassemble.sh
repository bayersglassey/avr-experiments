#!/bin/bash
#
# Based on: https://stackoverflow.com/a/43714073
#
set -euo pipefail

file=$1
func=$2
shift 2

avr-objdump -d "$file" "$@" | sed '/<'"$func"'>:/,/^$/!d'
