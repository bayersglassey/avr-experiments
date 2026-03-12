
// I'm using an Elegoo Nano V3.0, which is a knockoff of an Arduino Nano.
// I found this F_CPU value by seeing what the Arduino IDE used when compiling
// for the Nano.
#define F_CPU 16000000L

// I'm not yet sure what constitutes a "good" baud value.
// Presumably higher is always better, if you can get away with it, i.e. both
// sides of the communication support it without data corruption?..
#define BAUD 38400

#include <stdlib.h>
#include <stddef.h>
#include <avr/io.h>
#include <util/setbaud.h>
#include <util/delay.h>
#include <util/atomic.h> // ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { ... }


// Maximum number of tasks in the system
#define MAX_TASKS 8

#define TASK_SIZE (sizeof(task_t))

// Technically the size of a task's heap *and* stack, which grow towards each
// other: the heap grows upwards, the stack downwards.
// Also, the task's code lives on its heap!..
#define HEAP_SIZE 128

typedef uint8_t task_id_t;

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
    MESSAGE_PING              = 0x00,
    MESSAGE_GET_OFFSETS       = 0x01,
    MESSAGE_LOAD_TASK         = 0x02,
    MESSAGE_START_TASK        = 0x03,
    MESSAGE_STOP_TASK         = 0x04,
    MESSAGE_INSPECT_TASK      = 0x05,
    MESSAGE_KERNEL_LOG        = 0x06,
    MESSAGE_TASK_LOG          = 0x07,
    MESSAGE_TASK_STOPPED      = 0x08,
};

typedef struct task {
    // TODO...
    uint8_t state; // enum task_state
    char heap[HEAP_SIZE];
} task_t;

task_t TASKS[MAX_TASKS] = {0};


void __attribute__((noreturn)) die(void);


///////////////////////////////////////////////////////////////////////////////
// TASK FUNCTIONS

void start_task(task_t *task) {
    task->state = TASK_STATE_STARTED;
    // TODO...
}

void stop_task(task_t *task) {
    task->state = TASK_STATE_STOPPED;
    // TODO...
}


///////////////////////////////////////////////////////////////////////////////
// UART FUNCTIONS

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

uint16_t uart_get_uint16(void) {
    // NOTE: little-endian
    int i = (uint8_t) uart_get();
    i |= ((uint8_t) uart_get()) << 8;
    return i;
}

static void uart_put(char c) {
    loop_until_bit_is_set(UCSR0A, UDRE0);
    // "USART DATA REGISTER"
    UDR0 = c;
}

void uart_put_uint16(uint16_t i) {
    // NOTE: little-endian
    uart_put(i & 0xff);
    uart_put(i >> 8);
}

static char to_hex(uint8_t c) {
    return c < 10? '0' + c: c < 16? 'A' + c - 10: '?';
}

void uart_put_hex(uint8_t c) {
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

static void uart_put_message(char msg_type) {
    uart_put(MESSAGE_ESCAPE);
    uart_put(msg_type);
}


///////////////////////////////////////////////////////////////////////////////
// LED FUNCTIONS

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


///////////////////////////////////////////////////////////////////////////////
// OS/CLIENT MESSAGES

task_id_t get_task_id(void) {
    task_id_t task_id = uart_get();
    if (task_id >= MAX_TASKS) die();
    return task_id;
}

void handle_ping(void) {
    char c = uart_get();
    uart_put(c);
}

void handle_get_offsets(void) {
    uart_put_uint16((uint16_t) TASKS);
    uart_put_uint16(MAX_TASKS);
    uart_put_uint16(TASK_SIZE);
    uart_put_uint16(offsetof(task_t, heap));
}

void handle_load_task(void) {
    task_id_t task_id = get_task_id();
    task_t *task = &TASKS[task_id];
    stop_task(task);
    uint16_t data_size = uart_get_uint16();
    char *task_data = (char*) task->heap;
    char *task_data_end = task_data + data_size;
    while (task_data < task_data_end) *task_data++ = uart_get();
    task_data_end += HEAP_SIZE - data_size;
    while (task_data < task_data_end) *task_data++ = '\0';
}

void handle_start_task(void) {
    task_id_t task_id = get_task_id();
    task_t *task = &TASKS[task_id];
    start_task(task);
}

void handle_stop_task(void) {
    task_id_t task_id = get_task_id();
    task_t *task = &TASKS[task_id];
    stop_task(task);
}

void handle_inspect_task(void) {
    task_id_t task_id = get_task_id();
    task_t *task = &TASKS[task_id];
    char *task_data = (char*) task;
    char *task_data_end = task_data + TASK_SIZE;
    while (task_data < task_data_end) uart_put(*task_data++);
}

void handle_message(char msg_type) {
    switch (msg_type) {
        case MESSAGE_PING: handle_ping(); break;
        case MESSAGE_GET_OFFSETS: handle_get_offsets(); break;
        case MESSAGE_LOAD_TASK: handle_load_task(); break;
        case MESSAGE_START_TASK: handle_start_task(); break;
        case MESSAGE_STOP_TASK: handle_stop_task(); break;
        case MESSAGE_INSPECT_TASK: handle_inspect_task(); break;
        default:
            uart_puts("Can't handle: ");
            uart_put_hex(msg_type);
            uart_put_newline();
            die();
    }
}

void send_ping(char c) {
    uart_put_message(MESSAGE_PING);
    uart_put(c);
    char pong = uart_get();
    if (pong != c) {
        uart_puts("Bad pong: ");
        uart_put_hex(pong);
        uart_put_newline();
        die();
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
// INTERRUPTS

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
// MAIN

void die(void) {
    cli(); // disable global interrupts, we're dead now
    led_off();
    while (1) {
        for (uint8_t i = 6; i--;) {
            led_toggle();
            _delay_ms(100);
        }
        _delay_ms(500);
    }
}

int main(void) {
    led_init();
    uart_init();
    sei(); // enable global interrupts

    // Indicate that we've started, by flashing the LED a few times!
    for (uint8_t i = 3; --i;) {
        led_toggle();
        _delay_ms(100);
    }
    led_off();

    while (1) {
        //_delay_ms(1000);
        //led_toggle();
    }

    return 0;
}
