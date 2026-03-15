#!/bin/bash
set -euo pipefail

exec avr-objdump -d minitasks.elf
