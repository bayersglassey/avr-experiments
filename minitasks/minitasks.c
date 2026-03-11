
// I'm using an Elegoo Nano V3.0, which is a knockoff of an Arduino Nano.
// I found this F_CPU value by seeing what the Arduino IDE used when compiling
// for the Nano.
#define F_CPU 16000000L

// I'm not yet sure what constitutes a "good" baud value.
// Presumably higher is always better, if you can get away with it, i.e. both
// sides of the communication support it without data corruption?..
#define BAUD 38400

#include <stdlib.h>
#include <avr/io.h>
#include <util/setbaud.h>
#include <util/delay.h>
#include <util/atomic.h> // ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { ... }


// Maximum number of tasks in the system
#define MAX_TASKS 8

// Technically the size of a task's heap *and* stack, which grow towards each
// other: the heap grows upwards, the stack downwards.
// Also, the task's code lives on its heap!..
#define HEAP_SIZE 128

typedef uint8_t task_id_t;
#define BAD_TASK_ID ((task_id_t) -1)

// The "escape character" over USART communications, indicating the start
// of a message
#define MESSAGE_ESCAPE ((char) 0xFF)

enum task_state {
    TASK_STATE_STOPPED   = 0,
    TASK_STATE_STARTED   = 1,
    TASK_STATE_SLEEPING  = 2,
    TASK_STATE_QUEUED    = 3,
};

enum message_type {
    MESSAGE_PING          = 0,
    MESSAGE_LOAD_TASK     = 1,
    MESSAGE_START_TASK    = 2,
    MESSAGE_STOP_TASK     = 3,
    MESSAGE_INSPECT_TASK  = 4,
    MESSAGE_KERNEL_LOG    = 5,
    MESSAGE_TASK_LOG      = 6,
    MESSAGE_TASK_STOPPED   = 7,
};

struct task {
    // TODO...
    uint8_t state; // enum task_state
    char heap[HEAP_SIZE];
};

struct task TASKS[MAX_TASKS] = {0};


void uart_init(void) {
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
    // Enable UART0 transmit, receive, and receive interrupt
    UCSR0B = (1 << TXEN0) | (1 << RXEN0) | (1 << RXCIE0);
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00); // 8 data bits, no parity, 1 stop bit
}

static char uart_get(void) {
    loop_until_bit_is_set(UCSR0A, RXC0);
    // "USART DATA REGISTER"
    return UDR0;
}

static void uart_put(char c) {
    loop_until_bit_is_set(UCSR0A, UDRE0);
    // "USART DATA REGISTER"
    UDR0 = c;
}

static char to_hex(uint8_t c) {
    return c < 10? '0' + c: c < 16? 'A' + c - 10: '?';
}

static void uart_put_hex(uint8_t c) {
    uart_put('0');
    uart_put('x');
    char a = to_hex(c >> 4);
    char b = to_hex(c & 0x0f);
    uart_put(a);
    uart_put(b);
}

static void uart_put_newline(void) {
    uart_put('\r');
    uart_put('\n');
}

void uart_puts(const char *msg) {
    char c;
    while ((c = *msg++)) uart_put(c);
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

static void led_toggle(void) {
    PORTB ^= (1 << PB5);
}


void handle_ping(void) {
    char c = uart_get();
    uart_put(c);
}

task_id_t uart_get_task_id(void) {
    task_id_t task_id = uart_get();
    if (task_id >= MAX_TASKS) {
        uart_put(1); // error status
        return BAD_TASK_ID;
    }
    return task_id;
}

void handle_load_task(void) {
    task_id_t task_id = uart_get_task_id();
    if (task_id == BAD_TASK_ID) return;
    // TODO...
}

void handle_start_task(void) {
    task_id_t task_id = uart_get_task_id();
    if (task_id == BAD_TASK_ID) return;
    // TODO...
}

void handle_stop_task(void) {
    task_id_t task_id = uart_get_task_id();
    if (task_id == BAD_TASK_ID) return;
    // TODO...
}

void handle_inspect_task(void) {
    task_id_t task_id = uart_get_task_id();
    if (task_id == BAD_TASK_ID) return;
    // TODO...
}

void handle_message(char msg_type) {
    switch (msg_type) {
        case MESSAGE_PING: handle_ping(); break;
        case MESSAGE_LOAD_TASK: handle_load_task(); break;
        case MESSAGE_START_TASK: handle_start_task(); break;
        case MESSAGE_STOP_TASK: handle_stop_task(); break;
        case MESSAGE_INSPECT_TASK: handle_inspect_task(); break;
        default:
            uart_puts("Can't handle: ");
            uart_put_hex(msg_type);
            uart_put_newline();
            abort();
    }
}

static void uart_put_message(char msg_type) {
    uart_put(MESSAGE_ESCAPE);
    uart_put(msg_type);
}

void send_ping(char c) {
    uart_put_message(MESSAGE_PING);
    uart_put(c);
    char c2 = uart_get();
    if (c2 != c) {
        uart_puts("Bad pong: ");
        uart_put_hex(c2);
        uart_put_newline();
        abort();
    }
}

void send_kernel_log(void) {
    uart_put_message(MESSAGE_KERNEL_LOG);
    // Caller should now use e.g. uart_put_string to send the log message
}

void send_task_log(task_id_t task_id) {
    uart_put_message(MESSAGE_TASK_LOG);
    uart_put(task_id);
    // Caller should now use e.g. uart_put_string to send the log message
}

void send_task_stopped(task_id_t task_id, char reason) {
    uart_put_message(MESSAGE_TASK_STOPPED);
    uart_put(task_id);
    uart_put(reason);
}


///////////////////////////////////////////////////////////////////////////////
// Interrupts

ISR (USART_RX_vect) {
    // USART received data
    led_toggle();
    char c0 = UDR0;
    if (c0 == MESSAGE_ESCAPE) {
        char c1 = uart_get();
        if (c1 != MESSAGE_ESCAPE) {
            handle_message(c1);
            return;
        }
    }

    // TODO: implement stdin queue
    uart_puts("Got: ");
    uart_put_hex(c0);
    uart_put_newline();
}

/*
ISR (USART0_UDRE_vect) {
    // USART is ready for more input

    // TODO: implement stdout queue
    UDR0 = ...;
}
*/


///////////////////////////////////////////////////////////////////////////////
// Main

int main(void) {
    led_init();
    uart_init();
    sei(); // enable global interrupts

    while (1) {
        //_delay_ms(1000);
        //led_toggle();
    }

    return 0;
}
