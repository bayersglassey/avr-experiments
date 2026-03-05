#!/bin/bash
set -euo pipefail

avr-gcc \
    -mmcu=atmega328p \
    -Wall \
    -Wno-unused-function \
    -Os \
    -o blink.elf blink.c

avr-objcopy -j .text -j .data -O ihex blink.elf blink.hex
