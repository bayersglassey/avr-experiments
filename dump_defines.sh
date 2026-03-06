avr-gcc -E -dM -include avr/io.h -include avr/iom328p.h "$PROJFILE.c" >defines.txt
