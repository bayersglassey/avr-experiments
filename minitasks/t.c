
#include <avr/io.h>

uint16_t flip(uint16_t x) { return ~x; }

uint16_t neg(uint16_t x) { return -x; }

uint16_t add(uint16_t x, uint16_t y) { return x + y; }
uint16_t sub(uint16_t x, uint16_t y) { return x - y; }

int f(int *p) { return *p; }

int set_led(int i) {
    if (i) PORTB |= (1 << PB5);
    else PORTB &= ~(1 << PB5);
    return 3;
}

void main() {}
