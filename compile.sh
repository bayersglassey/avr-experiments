#!/bin/bash
set -euo pipefail

avr-gcc \
    --std=c99 \
    -mmcu=atmega328p \
    -Wall \
    -Werror \
    -Wno-unused-function \
    -Os \
    "$@" \
    -o minitasks.elf \
    tasklang.S minitasks.c

avr-objcopy -j .text -j .data -O ihex minitasks.elf minitasks.hex
