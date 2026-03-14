
#include "minitasks.h"


///////////////////////////////////////////////////////////////////////////////
// TASK FUNCTIONS

void tasks_init(void) {
    for (task_id_t i = 0; i < MAX_TASKS; i++) {
        task_t *task = &TASKS[i];
        task->free = task->mem;
    }
}

uint16_t get_heap_size(task_t *task) {
    if (task->free < task->mem) die("FREE below start of CODE");
    return (task->free - task->mem) - task->code_size;
}

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
    if (task_id >= MAX_TASKS) die("Bad task ID");
    return task_id;
}

void handle_ping(void) {
    char c = uart_get();
    uart_put(c);
}

void handle_get_offsets(void) {
    uart_put_uint16(RAMSTART);

    // NOTE: RAMEND is 2303, which looks to me like the last valid RAM
    // address, whereas in the Python client, I want ram_end - ram_start to
    // be RAM size, thus the "+ 1" here
    uart_put_uint16(RAMEND + 1);

    uart_put_uint16((uint16_t) TASKS);
    uart_put_uint16(MAX_TASKS);
    uart_put_uint16(TASK_SIZE);
    uart_put_uint16(offsetof(task_t, mem));
}

void handle_get_builtin_locations(void) {
    uart_put_uint16((uint16_t) N_BUILTINS);
    for (uint16_t i = 0; i < N_BUILTINS; i++) {
        uart_put_uint16((uint16_t) pgm_read_byte(&BUILTINS[i]));
    }
}

void handle_load_task(void) {
    task_id_t task_id = get_task_id();
    task_t *task = &TASKS[task_id];
    stop_task(task);
    uint16_t code_size = uart_get_uint16();
    uint16_t heap_size = uart_get_uint16();
    uint16_t data_size = code_size + heap_size;
    task->code_size = code_size;
    task->free = task->mem + data_size;
    char *data = (char*) task->mem;
    char *data_end = data + data_size;
    while (data < data_end) *data++ = uart_get();
    data_end += TASK_MEM_SIZE - data_size;
    while (data < data_end) *data++ = '\0';
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
    uart_put_uint16(task->code_size);
    uart_put_uint16(get_heap_size(task));
    char *data = (char*) task;
    char *data_end = data + TASK_SIZE;
    while (data < data_end) uart_put(*data++);
}

void handle_get_memory(void) {
    char *p = (char*)uart_get_uint16();
    char *end = p + uart_get_uint16();
    while (p < end) uart_put(*p++);
}

void handle_set_memory(void) {
    char *p = (char*)uart_get_uint16();
    char *end = p + uart_get_uint16();
    while (p < end) *p++ = uart_get();
}

void handle_message(char msg_type) {
    switch (msg_type) {
        case MESSAGE_PING: handle_ping(); break;
        case MESSAGE_GET_OFFSETS: handle_get_offsets(); break;
        case MESSAGE_GET_BUILTIN_LOCATIONS: handle_get_builtin_locations(); break;
        case MESSAGE_LOAD_TASK: handle_load_task(); break;
        case MESSAGE_START_TASK: handle_start_task(); break;
        case MESSAGE_STOP_TASK: handle_stop_task(); break;
        case MESSAGE_INSPECT_TASK: handle_inspect_task(); break;
        case MESSAGE_GET_MEMORY: handle_get_memory(); break;
        case MESSAGE_SET_MEMORY: handle_set_memory(); break;
        default: die("Bad input message type");
    }
}

void send_ping(char c) {
    uart_put_message(MESSAGE_PING);
    uart_put(c);
    char pong = uart_get();
    if (pong != c) die("Bad pong");
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

const char *death_message = NULL;
void die(const char *msg) {
    cli(); // disable global interrupts, we're dead now
    death_message = msg;
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
    tasks_init();

    // Indicate that we've started, by flashing the LED a few times!
    for (uint8_t i = 8; i--;) {
        led_toggle();
        _delay_ms(50);
    }

    sei(); // enable global interrupts
    while (1) {
        //_delay_ms(1000);
        //led_toggle();
    }

    return 0;
}
