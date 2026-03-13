#ifndef _MINITASKS_H_
#define _MINITASKS_H_

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

// A "builtin" is an assembly routine implementing a tasklang instruction
typedef void builtin_t(void);

void __attribute__((noreturn)) die(void);

// A listing of all tasklang "builtins".
// NOTE: this list of builtins must be in the same order as that of BUILTINS
// in tasklang.py!.. the names don't need to match up exactly, but the order
// must be the same.
#define _BUILTINS \
    BUILTIN(builtin_add) \
    BUILTIN(builtin_sub) \
    BUILTIN(builtin_mul) \
    BUILTIN(builtin_div) \
    BUILTIN(builtin_mod) \
    BUILTIN(builtin_lshift) \
    BUILTIN(builtin_rshift) \
    BUILTIN(builtin_eq) \
    BUILTIN(builtin_ne) \
    BUILTIN(builtin_lt) \
    BUILTIN(builtin_gt) \
    BUILTIN(builtin_le) \
    BUILTIN(builtin_ge) \
    BUILTIN(builtin_not) \
    BUILTIN(builtin_bitnot) \
    BUILTIN(builtin_bitand) \
    BUILTIN(builtin_bitor) \
    BUILTIN(builtin_bitxor) \
    BUILTIN(builtin_getptr) \
    BUILTIN(builtin_getptrc) \
    BUILTIN(builtin_setptr) \
    BUILTIN(builtin_setptrc) \
    BUILTIN(builtin_literal) \
    BUILTIN(builtin_store) \
    BUILTIN(builtin_load) \
    BUILTIN(builtin_jump) \
    BUILTIN(builtin_jumpif) \
    BUILTIN(builtin_jumpifnot) \
    BUILTIN(builtin_atomic) \
    BUILTIN(builtin_end_atomic) \
    BUILTIN(builtin_dup) \
    BUILTIN(builtin_swap) \
    BUILTIN(builtin_drop) \
    BUILTIN(builtin_heap) \
    BUILTIN(builtin_hpush) \
    BUILTIN(builtin_hpop) \
    BUILTIN(builtin_hdrop) \
    BUILTIN(builtin_hpushc) \
    BUILTIN(builtin_hpopc) \
    BUILTIN(builtin_hdropc) \
    BUILTIN(builtin_assert) \
    BUILTIN(builtin_error) \
    BUILTIN(builtin_set_led) \
    BUILTIN(builtin_sleep) \
    BUILTIN(builtin_getc) \
    BUILTIN(builtin_putc) \
    BUILTIN(builtin_logs) \
    BUILTIN(builtin_logc) \
    BUILTIN(builtin_logi) \
    BUILTIN(builtin_halt) \
    BUILTIN(builtin_pause)

// Function prototypes for assembly routines defined in tasklang.S
#define BUILTIN(name) extern __attribute__((noreturn)) builtin_t name;
_BUILTINS
#undef BUILTIN

// Table of assembly routines
#define BUILTIN(name) &name,
builtin_t *BUILTINS[] = { _BUILTINS };
#undef BUILTIN

#endif
