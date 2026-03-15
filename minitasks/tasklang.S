
#include <avr/common.h>
#include <avr/io.h>

#include "avrstuff.h"


.macro builtin name
.global builtin_\name
builtin_\name:
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
    rjmp next


next:
    ; Jump to the next threaded code instruction, and also increment the
    ; threaded code instruction pointer.
    ld r30, Y+   ; load whatever Y is pointing at into Z, and increment Y
    ld r31, Y+   ; ...
    ijmp         ; jump to the code pointed to by Z


loop_forever:
    rjmp loop_forever


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; OPERATORS

builtin add
    ; pop a 16-bit value into the register pair r25:r24
    pop r25
    pop r24

    ; pop a 16-bit value into the register pair r23:r22
    pop r23
    pop r22

    ; add the two values together
    add r24, r22 ; add the lower bytes
    adc r25, r23 ; add the higher bytes with carry

    ; push the resulting 16-bit value
    push r24
    push r25

    ; jump to the next threaded code instruction
    rjmp next

builtin sub
    ; see the comments for "add"
    pop r25
    pop r24
    pop r23
    pop r22
    sub r24, r22
    sbc r25, r23
    push r24
    push r25
    rjmp next

builtin mul
    rjmp builtin_halt
builtin div
    rjmp builtin_halt
builtin mod
    rjmp builtin_halt
builtin lshift
    rjmp builtin_halt
builtin rshift
    rjmp builtin_halt
builtin eq
    rjmp builtin_halt
builtin ne
    rjmp builtin_halt
builtin lt
    rjmp builtin_halt
builtin gt
    rjmp builtin_halt
builtin le
    rjmp builtin_halt
builtin ge
    rjmp builtin_halt
builtin not
    rjmp builtin_halt

builtin bitnot
    pop r25
    pop r24
    com r24
    com r25
    push r24
    push r25
    rjmp next

builtin bitand
    pop r25
    pop r24
    pop r23
    pop r22
    and r24, r22
    and r25, r23
    push r24
    push r25
    rjmp next

builtin bitor
    pop r25
    pop r24
    pop r23
    pop r22
    or r24, r22
    or r25, r23
    push r24
    push r25
    rjmp next

builtin bitxor
    pop r25
    pop r24
    pop r23
    pop r22
    eor r24, r22
    eor r25, r23
    push r24
    push r25
    rjmp next

builtin getptr
    rjmp builtin_halt
builtin getptrc
    rjmp builtin_halt
builtin setptr
    rjmp builtin_halt
builtin setptrc
    rjmp builtin_halt


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; PRIVATE BUILTINS

builtin literal
    ; load the integer argument from threaded code into a register pair
    ; (and increment Y so instead of pointing at the argument, it now points
    ; at next threaded code instruction)
    ld r24, Y+
    ld r25, Y+

    ; push the integer argument onto the stack
    push r24
    push r25

    ; jump to the next threaded code instruction
    rjmp next

builtin store
    pop r25
    pop r24
    ld r30, Y+     ; load the argument following this instruction into Z
                   ; (and increment Y to next instruction)
    ld r31, Y+     ; ...
    st Z+, r24     ; store into the memory pointed to by Z
    st Z+, r25     ; ...
    rjmp next

builtin load
    ld r30, Y+     ; load the argument following this instruction into Z
                   ; (and increment Y to next instruction)
    ld r31, Y+     ; ...
    ld r24, Z+     ; load the word pointed to by Z
    ld r25, Z+     ; ...
    push r24
    push r25
    rjmp next

builtin jump
    ; load the argument (which is a pointer to another instruction within
    ; the threaded code)
    ld r24, Y+
    ld r25, Y+

    ; copy the argument from register pair r25:r24 to r29:r28, i.e. Y
    movw r28, r24

    ; jump to the indicated instruction within the threaded code
    ijmp

builtin jumpif
    pop r25
    pop r24
    _jumpif:
    or r24, r25 ; we want to know if any of the bits are 1
    breq 2f
        ; TOS was 1
        ld r24, Y+     ; load the argument
        ld r25, Y+     ; ...
        movw r28, r24  ; set Y to the argument
        rjmp next      ; jump to the argument
    2:
        ; TOS was 0
        adiw r28, 2 ; add 2 bytes, so we point at next instruction instead
                    ; of our argument
        rjmp next   ; jump to next instruction

builtin jumpifnot
    pop r25
    pop r24
    com r24 ; bitwise invert the TOS
    com r25 ; ...
    rjmp _jumpif

builtin atomic
    rjmp builtin_halt
builtin end_atomic
    rjmp builtin_halt


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; PUBLIC BUILTINS

builtin neg
    pop r25
    pop r24
    ; TODO: understand the following!.. I got it from avr-gcc generated asm
    neg	r25 ; two's compliment
    neg	r24 ; ...
    ldi r23, 0
    sbc	r25, r23
    rjmp next

builtin dup
    ; TODO: see whether this can improved with LDS from stack pointer
    pop r25
    pop r24
    push r24
    push r25
    push r24
    push r25
    rjmp next

builtin swap
    ; TODO: see whether this can improved with LDS from stack pointer
    pop r25
    pop r24
    pop r23
    pop r22
    push r24
    push r25
    push r22
    push r23
    rjmp next

builtin drop
    pop r25
    pop r24
    rjmp next

builtin heap
    rjmp builtin_halt
builtin hpush
    rjmp builtin_halt
builtin hpop
    rjmp builtin_halt
builtin hdrop
    rjmp builtin_halt
builtin hpushc
    rjmp builtin_halt
builtin hpopc
    rjmp builtin_halt
builtin hdropc
    rjmp builtin_halt

builtin assert
    pop r25
    pop r24
    or r24, r25 ; we want to know if any of the bits are 1
    breq 1f
        ; TOS was 1: assertion passed!
        rjmp next
    1:
        ; TOS was 0: assertion failed!
        ; TODO: send a TASK_STOPPED message
        rjmp loop_forever

builtin error
    ; TODO: send a TASK_STOPPED message
    rjmp loop_forever

builtin set_led
    pop r25
    pop r24
    or r24, r25
    breq 2f ; if TOS was zero, turn LED off
        sbi	0x05, 5 ; turn LED on
    1:
        ; jump to next instruction
        rjmp next
    2:
        cbi	0x05, 5 ; turn LED off
        rjmp 1b

builtin sleep
    rjmp builtin_halt
builtin getc
    rjmp builtin_halt
builtin putc
    rjmp builtin_halt
builtin logs
    rjmp builtin_halt
builtin logc
    rjmp builtin_halt
builtin logi
    rjmp builtin_halt

builtin halt
    ; TODO: send a TASK_STOPPED message
    rjmp loop_forever

builtin pause
    ; TODO: send a TASK_STOPPED message
    rjmp loop_forever
