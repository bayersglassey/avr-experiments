
#include <avr/common.h>
#include <avr/io.h>

#include "avrstuff.h"


.macro builtin name
.global builtin_\name
builtin_\name:
.endm

.macro _BINARYPOP
    ; pop 2 values off the stack, for implementing binary operators.
    ; if stack looks like: x y
    ; ...then this will result in: r25:r24 = x, r23:r22 = y
    pop r23
    pop r22
    pop r25
    pop r24
.endm

.global run_task_immediate
run_task_immediate:
    ; NOTE: intended to be called by C code, with arguments:
    ;  code, free, stack

    movw r28, r24 ; load code pointer into Y
    movw r26, r22 ; load heap pointer into X
                  ;   ...which points to FREE, i.e. just past top of heap

    ; Set the stack pointer.
    ; NOTE: it seems like we must set SPH before SPL; if we set SPL first, it
    ; seems that SPH is always set to 0x08. No idea why. O_o
    out SPH_IO_ADDR, r21  ; set stack pointer
    out SPL_IO_ADDR, r20  ; ...

    ; jump to next instruction, i.e. first instruction in task's CODE
    rjmp _next

_next:
    ; Jump to the next threaded code instruction, and also increment the
    ; threaded code instruction pointer.
    ld r30, Y+   ; load whatever Y is pointing at into Z, and increment Y
    ld r31, Y+   ; ...
    ijmp         ; jump to the code pointed to by Z

loop_forever:
    rjmp loop_forever


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; OPERATORS

BUILTIN add
    ; x y + -> x+y

    ; pop two 16-bit values (x, y) from the stack
    ; x = r25:r24, y = r23:r22
    _BINARYPOP

    ; add the two values together (x += y)
    add r24, r22 ; add the lower bytes
    adc r25, r23 ; add the higher bytes with carry

    ; push the resulting 16-bit value
    push r24
    push r25

    ; jump to the next threaded code instruction
    rjmp _next

BUILTIN sub
    ; x y + -> x-y
    ; see the comments for "add"
    _BINARYPOP
    sub r24, r22 ; x -= y
    sbc r25, r23 ; ...
    push r24
    push r25
    rjmp _next

; TODO...
BUILTIN mul
    rjmp builtin_halt
BUILTIN div
    rjmp builtin_halt
BUILTIN mod
    rjmp builtin_halt
BUILTIN lshift
    rjmp builtin_halt
BUILTIN rshift
    rjmp builtin_halt

_return_true:
    ; return true from an instruction, i.e. push 1 onto stack and jump to
    ; next instruction
    ldi r24, 1
    push r24
    ldi r24, 0
    push r24
    rjmp _next

_return_false:
    ; return false from an instruction, i.e. push 0 onto stack and jump to
    ; next instruction
    ldi r24, 0
    push r24
    push r24
    rjmp _next

; NOTE: the binary logical operator implementations below were tested using
; the Python client as follows:
;
;   code = ' 0xee '.join(f'1 1 {op} 1 2 {op} 2 1 {op}' for op in ('==', '!=', '<', '<=', '>', '>='))
;   c.run_task(0, code)
;   _bytemap = {' ':b'\x00\xee', '0':b'\x00\x00', '1':b'\x00\x01'}
;   expected = b''.join(_bytemap[c] for c in ''.join(reversed('100 011 010 110 001 101')))
;   assert c.inspect_task(0).rest.data[-len(expected):] == expected
;

BUILTIN eq
    ; x y + -> x==y
    _BINARYPOP
    cp r24, r22  ; compare x - y
    cpc r25, r23 ; ...
    breq _return_true
    rjmp _return_false

BUILTIN ne
    ; x y + -> x!=y
    _BINARYPOP
    cp r24, r22  ; compare x - y
    cpc r25, r23 ; ...
    brne _return_true
    rjmp _return_false

BUILTIN lt
    ; x y + -> x<y
    _BINARYPOP
    cp r24, r22  ; compare x - y
    cpc r25, r23 ; ...
    brcs _return_true ; branch if carry set, i.e. if x < y
    rjmp _return_false

BUILTIN gt
    ; x y + -> x>y
    _BINARYPOP
    cp r22, r24  ; compare y - x
    cpc r23, r25 ; ...
    brcs _return_true ; branch if carry set, i.e. if y < x
    rjmp _return_false

BUILTIN le
    ; x y + -> x<=y
    _BINARYPOP
    cp r22, r24  ; compare y - x
    cpc r23, r25 ; ...
    brcc _return_true ; branch if carry clear (not set), i.e. if not y < x
    rjmp _return_false

BUILTIN ge
    ; x y + -> x>=y
    _BINARYPOP
    cp r24, r22  ; compare x - y
    cpc r25, r23 ; ...
    brcc _return_true ; branch if carry clear (not set), i.e. if not x < y
    rjmp _return_false

BUILTIN not
    pop r25
    pop r24
    or r24, r25 ; we want to know if any of the bits are 1
    breq _return_false ; if it was true, return false
    rjmp _return_true  ; if it was false, return true

BUILTIN bitnot
    pop r25
    pop r24
    com r24
    com r25
    push r24
    push r25
    rjmp _next

BUILTIN bitand
    _BINARYPOP
    and r24, r22
    and r25, r23
    push r24
    push r25
    rjmp _next

BUILTIN bitor
    _BINARYPOP
    or r24, r22
    or r25, r23
    push r24
    push r25
    rjmp _next

BUILTIN bitxor
    _BINARYPOP
    eor r24, r22
    eor r25, r23
    push r24
    push r25
    rjmp _next

BUILTIN getptr
    pop r31    ; pop a pointer from the stack into Z
    pop r30    ; ...
    ld r24, Z+ ; get the 16-bit value pointed at by Z
    ld r25, Z+ ; ...
    push r24   ; push the value onto stack
    push r25   ; ...
    rjmp _next

BUILTIN getptrc
    pop r31    ; pop a pointer from the stack into Z
    pop r30    ; ...
    ld r24, Z+ ; get the 8-bit value pointed at by Z
    push r24   ; push the value onto stack
    ldi r24, 0 ; push 0 for the high byte
    push r24   ; ...
    rjmp _next

BUILTIN setptr
    pop r31    ; pop a pointer from the stack into Z
    pop r30    ; ...
    pop r25    ; pop a 16-bit value from the stack
    pop r24    ; ...
    st Z+, r24 ; store the value at the location pointed at by Z
    st Z+, r25 ; ...
    rjmp _next

BUILTIN setptrc
    pop r31    ; pop a pointer from the stack into Z
    pop r30    ; ...
    pop r25    ; pop a 16-bit value from the stack (but we will "coerce" it
               ; to 8-bit)
    pop r24    ; ...
    st Z+, r24 ; store the lower byte of the value at the location pointed
               ; at by Z
    rjmp _next


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; PRIVATE BUILTINS

BUILTIN literal
    ; load the integer argument from threaded code into a register pair
    ; (and increment Y so instead of pointing at the argument, it now points
    ; at next threaded code instruction)
    ld r24, Y+
    ld r25, Y+

    ; push the integer argument onto the stack
    push r24
    push r25

    ; jump to the next threaded code instruction
    rjmp _next

BUILTIN store
    pop r25
    pop r24
    ld r30, Y+     ; load the argument following this instruction into Z
                   ; (and increment Y to next instruction)
    ld r31, Y+     ; ...
    st Z+, r24     ; store into the memory pointed to by Z
    st Z+, r25     ; ...
    rjmp _next

BUILTIN load
    ld r30, Y+     ; load the argument following this instruction into Z
                   ; (and increment Y to next instruction)
    ld r31, Y+     ; ...
    ld r24, Z+     ; load the word pointed to by Z
    ld r25, Z+     ; ...
    push r24
    push r25
    rjmp _next

BUILTIN jump
    ; load the argument (which is a pointer to another instruction within
    ; the threaded code)
    ld r24, Y+
    ld r25, Y+

    ; copy the argument from register pair r25:r24 to r29:r28, i.e. Y
    movw r28, r24

    ; jump to the indicated instruction within the threaded code
    ijmp

BUILTIN jumpif
    pop r25
    pop r24
    _jumpif:
    or r24, r25 ; we want to know if any of the bits are 1
    breq 2f
        ; TOS was 1
        ld r24, Y+     ; load the argument
        ld r25, Y+     ; ...
        movw r28, r24  ; set Y to the argument
        rjmp _next      ; jump to the argument
    2:
        ; TOS was 0
        adiw r28, 2 ; add 2 bytes, so we point at next instruction instead
                    ; of our argument
        rjmp _next   ; jump to next instruction

BUILTIN jumpifnot
    pop r25
    pop r24
    com r24 ; bitwise invert the TOS
    com r25 ; ...
    rjmp _jumpif

BUILTIN atomic
    ; start an atomic "block" by disabling interrupts
    ; NOTE: THIS INSTRUCTION IS SUPER HACKY!..
    cli
    rjmp _next

BUILTIN end_atomic
    ; end an atomic "block" by enabling interrupts
    ; NOTE: THIS INSTRUCTION IS SUPER HACKY!..
    sei
    rjmp _next


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; PUBLIC BUILTINS

BUILTIN neg
    pop r25
    pop r24
    ; TODO: understand the following!.. I got it from avr-gcc generated asm
    neg	r25 ; two's compliment
    neg	r24 ; ...
    ldi r23, 0
    sbc	r25, r23
    rjmp _next

BUILTIN dup
    ; TODO: see whether this can improved with LDS from stack pointer
    pop r25
    pop r24
    push r24
    push r25
    push r24
    push r25
    rjmp _next

BUILTIN swap
    ; TODO: see whether this can improved with LDS from stack pointer
    _BINARYPOP ; if stack look like: x y ...then x=r25:r24, y=r23:r22
    push r22 ; push y
    push r23 ; ...
    push r24 ; push x
    push r25 ; ...
    rjmp _next

BUILTIN drop
    pop r25
    pop r24
    rjmp _next

BUILTIN heap
    ; push X (address of top of heap) onto stack
    push r26
    push r27
    rjmp _next

BUILTIN hpush
    ; pop a value from stack, push it onto the heap
    pop r25
    pop r24
    st X+, r24
    st X+, r25
    rjmp _next

BUILTIN hpushc
    ; pop a value from stack, push its lower byte onto the heap
    pop r25
    pop r24
    st X+, r24
    rjmp _next

BUILTIN assert
    pop r25
    pop r24
    or r24, r25 ; we want to know if any of the bits are 1
    breq 1f
        ; TOS was 1: assertion passed!
        rjmp _next
    1:
        ; TOS was 0: assertion failed!
        ; TODO: send a TASK_STOPPED message
        rjmp loop_forever

BUILTIN error
    ; TODO: send a TASK_STOPPED message
    rjmp loop_forever

BUILTIN set_led
    pop r25
    pop r24
    or r24, r25
    breq 2f ; if TOS was zero, turn LED off
        sbi	0x05, 5 ; turn LED on
    1:
        ; jump to next instruction
        rjmp _next
    2:
        cbi	0x05, 5 ; turn LED off
        rjmp 1b

BUILTIN sleep
    rjmp builtin_halt
BUILTIN getc
    rjmp builtin_halt
BUILTIN putc
    rjmp builtin_halt
BUILTIN logs
    rjmp builtin_halt
BUILTIN logc
    rjmp builtin_halt
BUILTIN logi
    rjmp builtin_halt

BUILTIN halt
    ; TODO: send a TASK_STOPPED message
    rjmp loop_forever

BUILTIN pause
    ; TODO: send a TASK_STOPPED message
    rjmp loop_forever
