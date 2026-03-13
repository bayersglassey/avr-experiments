#!/bin/bash
set -euo pipefail

avr-as -mmcu=atmega328p tasklang.S -o tasklang.o

avr-gcc \
    --std=c99 \
    -mmcu=atmega328p \
    -Wall \
    -Wno-unused-function \
    -Os \
    "$@" \
    -o minitasks.elf \
    tasklang.o minitasks.c

avr-objcopy -j .text -j .data -O ihex minitasks.elf minitasks.hex
