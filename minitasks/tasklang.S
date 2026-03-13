
#include <avr/io.h>

.macro builtin name
.global builtin_\name
builtin_\name:
.endm


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; OPERATORS

builtin add
    ; pop a 16-bit value into the register pair r24:r25
    pop r25
    pop r24

    ; pop a 16-bit value into the register pair r22:r23
    pop r23
    pop r22

    ; add the two values together
    add r24, r22 ; add the lower bytes
    adc r25, r23 ; add the higher bytes with carry

    ; push the resulting 16-bit value
    push r24
    push r25

    ; jump to the next threaded code instruction
    adiw r30, 2 ; increment Z by 2 bytes, the width of a pointer
    ijmp ; jump to the routine at which Z is now pointing

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
    adiw r30, 2
    ijmp

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
    adiw r30, 2
    ijmp

builtin bitand
    pop r25
    pop r24
    pop r23
    pop r22
    and r24, r22
    and r25, r23
    push r24
    push r25
    adiw r30, 2
    ijmp

builtin bitor
    pop r25
    pop r24
    pop r23
    pop r22
    or r24, r22
    or r25, r23
    push r24
    push r25
    adiw r30, 2
    ijmp

builtin bitxor
    pop r25
    pop r24
    pop r23
    pop r22
    eor r24, r22
    eor r25, r23
    push r24
    push r25
    adiw r30, 2
    ijmp

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
    adiw r30, 2 ; increment Z by 2

    ; load the integer argument from threaded code into a register pair
    ld r24, Z
    ldd r25, Z+1

    ; push the integer argument onto the stack
    push r24
    push r25

    ; jump to the next threaded code instruction
    adiw r30, 2
    ijmp

builtin store
    pop r25
    pop r24
    adiw r30, 2    ; point Z at current instruction's argument
    ld r26, Z      ; load the argument into X
    ldd r27, Z+1   ; ...
    st X+, r24     ; store into the memory pointed to by X
    st X, r25      ; ...
    adiw r30, 2
    ijmp

builtin load
    adiw r30, 2    ; point Z at current instruction's argument
    ld r26, Z      ; load the argument into X
    ldd r27, Z+1   ; ...
    ld r24, X+     ; load the word pointed to by X
    ld r25, X      ; ...
    push r24
    push r25
    adiw r30, 2
    ijmp

builtin jump
    adiw r30, 2 ; increment Z by 2

    ; load the argument (which is a pointer to another instruction within
    ; the threaded code)
    ld r24, Z
    ldd r25, Z+1

    ; copy the argument from register pair r24:r25 to r30:r31, i.e. Z
    movw r30, r24

    ; jump to the indicated instruction within the threaded code
    ijmp

builtin jumpif
    pop r25
    pop r24
    _jumpif:
    or r24, r25 ; we want to know if any of the bits are 1
    breq 2f
        ; TOS was 1
        adiw r30, 2    ; point Z at current instruction's argument
        ld r24, Z      ; load the argument
        ldd r25, Z+1   ; ...
        movw r30, r24  ; set Z to the argument
        ijmp           ; jump to the argument
    2:
        ; TOS was 0
        adiw r30, 4 ; add 4 bytes: current instruction and its argument
        ijmp

builtin jumpifnot
    pop r25
    pop r24
    com r24 ; bitwise invert the TOS
    com r25 ; ...
    jmp _jumpif

builtin atomic
    rjmp builtin_halt
builtin end_atomic
    rjmp builtin_halt


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; PUBLIC BUILTINS

builtin dup
    ; TODO: see whether this can improved with LDS from stack pointer
    pop r25
    pop r24
    push r24
    push r25
    push r24
    push r25
    adiw r30, 2
    ijmp

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
    adiw r30, 2
    ijmp

builtin drop
    pop r25
    pop r24
    adiw r30, 2
    ijmp

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
    rjmp builtin_halt
builtin error
    rjmp builtin_halt

builtin set_led
    pop r25
    pop r24
    or r24, r25
    breq 2f ; if TOS was zero, turn LED off
        sbi	0x05, 5 ; turn LED on
    1:
        ; jump to next instruction
        adiw r30, 2
        ijmp
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
    rjmp builtin_halt
builtin pause
    rjmp builtin_halt
