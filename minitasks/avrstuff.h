#ifndef _AVRSTUFF_H_
#define _AVRSTUFF_H_

/*
    The definitions for SPL/SPH (stack pointer) seem to be missing from avr/iom328p.h
    I got their values from page 279 of this doc:
    https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf
*/
#ifndef SPL
#define SPL 0x5d
#endif
#ifndef SPH
#define SPH 0x5e
#endif
#ifndef SPL_IO_ADDR
#define SPL_IO_ADDR  _SFR_IO_ADDR(SPL)
#endif
#ifndef SPH_IO_ADDR
#define SPH_IO_ADDR  _SFR_IO_ADDR(SPH)
#endif

#endif
