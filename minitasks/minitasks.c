
// I'm using an Elegoo Nano V3.0, which is a knockoff of an Arduino Nano.
// I found this F_CPU value by seeing what the Arduino IDE used when compiling
// for the Nano.
#define F_CPU 16000000L

// I'm not yet sure what constitutes a "good" baud value.
// Presumably higher is always better, if you can get away with it, i.e. both
// sides of the communication support it without data corruption?..
#define BAUD 38400

#include <avr/io.h>
#include <util/setbaud.h>
#include <util/delay.h>


// Maximum number of tasks in the system
#define MAX_TASKS 32

// Technically the size of a task's heap *and* stack, which grow towards each
// other: the heap grows upwards, the stack downwards.
// Also, the task's code lives on its heap!..
#define HEAP_SIZE 1024

struct task {
    // TODO...
    char heap[HEAP_SIZE];
};

struct task TASKS[MAX_TASKS] = {0};


void uart_init(void) {
    // Taken from: https://github.com/m3y54m/avr-playground/blob/master/01-serial-port/src/my/serial_port.c

    // These values are defined in setbaud.h, which makes use of BAUD
    // "USART BAUD RATE REGISTER"
    UBRR0H = UBRRH_VALUE;
    UBRR0L = UBRRL_VALUE;

    // "USART CONTROL & STATUS REGISTER"
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
    // "USART DATA REGISTER"
    return UDR0;
}

static void uart_put(char c) {
    // Taken from: https://github.com/m3y54m/avr-playground/blob/master/01-serial-port/src/my/serial_port.c
    loop_until_bit_is_set(UCSR0A, UDRE0);
    // "USART DATA REGISTER"
    UDR0 = c;
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

    // _delay_ms(1000);

    return 0;
}
