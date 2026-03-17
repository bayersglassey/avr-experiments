#!/bin/bash
#
# Dumps all C macros/definitions; they can then be searched with find_define.sh.
# Basically a poor man's "ctags".
#
avr-gcc -E -dM -include avr/io.h -include avr/iom328p.h "$PROJFILE.c" >defines.txt
