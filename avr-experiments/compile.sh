#!/bin/bash
set -euo pipefail

avr-gcc \
    --std=c99 \
    -mmcu=atmega328p \
    -Wall \
    -Wno-unused-function \
    -Os \
    "$@" \
    -o "$PROJFILE.elf" "$PROJFILE.c"

avr-objcopy -j .text -j .data -O ihex "$PROJFILE.elf" "$PROJFILE.hex"
