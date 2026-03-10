////////////////////////////////////////////////////////////////////////////////////////////////////////
// BASED ON: https://dev.to/heymrdj/digging-deeper-led-blink-from-arduino-c-and-avr-assembly-3a92
////////////////////////////////////////////////////////////////////////////////////////////////////////

#include <stdbool.h>

// Default clock source is internal 8MHz RC oscillator
// Taken from: https://github.com/m3y54m/start-avr
//#define F_CPU 8000000UL

// From: /usr/lib/avr/include/util/setbaud.h
//#define F_CPU 11059200
#define BAUD 38400

// From running an Arduino IDE compilation & looking at what it used
#define F_CPU 16000000L

// From: https://github.com/m3y54m/avr-playground/blob/master/01-serial-port/src/my/project_config.h
//#define F_CPU 16000000UL
//#define BAUD 115200UL

#include <avr/io.h> //Lets me use names like DDRB, PORTB, instead of memory addresses
#include <util/setbaud.h>
#include <util/delay.h> // Used for _delay_ms


void uart_init(void) {
    // Taken from: https://github.com/m3y54m/avr-playground/blob/master/01-serial-port/src/my/serial_port.c

    // requires BAUD
    UBRR0H = UBRRH_VALUE; // defined in setbaud.h
    UBRR0L = UBRRL_VALUE;
    #if USE_2X
    UCSR0A |= (1 << U2X0);
    #else
    UCSR0A &= ~(1 << U2X0);
    #endif
    UCSR0B = (1 << TXEN0) | (1 << RXEN0);   // Enable UART0 both transmitter and receiver
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00); // 8 data bits, no parity, 1 stop bit
}

static char uart_get(void) {
    // Taken from: https://github.com/m3y54m/avr-playground/blob/master/01-serial-port/src/my/serial_port.c
    loop_until_bit_is_set(UCSR0A, RXC0);
    return UDR0;
}

static void uart_put(char c) {
    // Taken from: https://github.com/m3y54m/avr-playground/blob/master/01-serial-port/src/my/serial_port.c
    loop_until_bit_is_set(UCSR0A, UDRE0);
    UDR0 = c;
}

static char uart_get_noblock(void) {
    if (bit_is_set(UCSR0A, RXC0)) return UDR0;
    else return '\0';
}

static bool uart_put_noblock(char c) {
    if (bit_is_set(UCSR0A, UDRE0)) {
        UDR0 = c;
        return true;
    } else return false;
}


void led_init(void) {
    DDRB |= (1 << PB5);
}

static void led_on(void) {
    PORTB |= (1 << PB5);
}

static void led_off(void) {
    PORTB &= ~(1 << PB5);
}


int main(void) {
    led_init();
    uart_init();
    uint8_t i = 0;
    while (1) {
        uart_put('H');
        uart_put('e');
        uart_put('l');
        uart_put('l');
        uart_put('o');
        uart_put('!');
        uart_put('\n');

        led_on();
        _delay_ms(1000);

        for (uint8_t j = 0; j < i; j++) uart_put('A');
        uart_put('H');
        uart_put('!');
        uart_put('\n');

        led_off();
        _delay_ms(1000);

        i++;
    }
    return 0;
}
