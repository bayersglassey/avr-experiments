//
// This file is for testing out little C snippets and seeing what
// avr-gcc assembles them to.
// See also: t.sh
//

#include <avr/io.h>
#include <util/delay.h>

#define F_CPU 16000000L

uint16_t flip(uint16_t x) { return ~x; }

uint16_t neg(uint16_t x) { return -x; }

uint16_t add(uint16_t x, uint16_t y) { return x + y; }
uint16_t sub(uint16_t x, uint16_t y) { return x - y; }

int f(int *p) { return *p; }

uint16_t eq(uint16_t x, uint16_t y) { return x == y? x: y; }
uint16_t ne(uint16_t x, uint16_t y) { return x != y? x: y; }
uint16_t lt(uint16_t x, uint16_t y) { return x < y? x: y; }
uint16_t le(uint16_t x, uint16_t y) { return x < y? x: y; }
uint16_t gt(uint16_t x, uint16_t y) { return x < y? x: y; }
uint16_t ge(uint16_t x, uint16_t y) { return x < y? x: y; }
uint16_t not(uint16_t x) { return !x; }

void sleep(void) {
    _delay_ms(1000);
}

int set_led(int i) {
    if (i) PORTB |= (1 << PB5);
    else PORTB &= ~(1 << PB5);
    return 3;
}

void toggle_led(void) {
    PORTB ^= (1 << PB5);
}

void main() {}
