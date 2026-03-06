#!/bin/bash
set -euo pipefail

avr-gcc \
    -mmcu=atmega328p \
    -Wall \
    -Wno-unused-function \
    -Os \
    "$@" \
    -o "$PROJFILE.elf" "$PROJFILE.c"

avr-objcopy -j .text -j .data -O ihex "$PROJFILE.elf" "$PROJFILE.hex"
