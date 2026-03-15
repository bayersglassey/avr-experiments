
#include <avr/io.h>

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

int set_led(int i) {
    if (i) PORTB |= (1 << PB5);
    else PORTB &= ~(1 << PB5);
    return 3;
}

void main() {}
