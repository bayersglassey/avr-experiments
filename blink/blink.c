////////////////////////////////////////////////////////////////////////////////////////////////////////
// TAKEN FROM: https://dev.to/heymrdj/digging-deeper-led-blink-from-arduino-c-and-avr-assembly-3a92
////////////////////////////////////////////////////////////////////////////////////////////////////////

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

int add(int x, int y) { return x + y; }
uint8_t add8(uint8_t x, uint8_t y) { return x + y; }
int add3(int x, int y, int z) { return x + y + z; }
uint8_t add38(uint8_t x, uint8_t y, uint8_t z) { return x + y + z; }
int incp(int *x) { return *x + 1; }
void incpp(int *x) { *x += 1; }
int addp(int *x, int *y) { return *x + *y; }
void addpp(int *x, int *y, int *result) { *result = *x + *y; }
int f(int *x, int *y, void fp(int *, int *)) { fp(x, y); return *x + *y; }
int g(void fp(int *, int *)) { int x = 2, y = 3; fp(&x, &y); return x + y; }
int h(void fp(int *, int *)) { static int x = 2, y = 3; fp(&x, &y); return x + y; }


int main(void) {
    led_init();
    uart_init();

    (void)add(2, 3);
    (void)add8(2, 3);
    (void)add3(2, 3, 4);
    (void)add38(2, 3, 4);
    int x = 3, y = 4, z;
    (void)addp(&x, &y);
    (void)addpp(&x, &y, &z);

    while (1) {
        led_on();
        _delay_ms(1000);
        led_off();
        _delay_ms(1000);
        uart_put('A');
    }
    return 0;
}
