#!/bin/bash
#
# Compile & disassemble t.c, so we can see what kind of assembly
# avr-gcc generates for small C snippets.
#
set -euo pipefail

avr-gcc -mmcu=atmega328p t.c -Os
avr-objdump -d a.out
