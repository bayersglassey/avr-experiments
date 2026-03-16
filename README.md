# BAG's experiments with AVR microcontrollers

I bought myself a couple of Adruinos -- errr I mean Elegoos -- which are
little "computer-on-a-chip"s.

They basically consist of an AVR microcontroller plus a USB port and a
bootloader, so you can easily flash code onto them.

See also: https://en.wikipedia.org/wiki/AVR_microcontrollers

This repo contains my initial experiments with these things...


## MINITASKS

This is the main project in here! It's a little multi-tasking OS (written
in C), plus a client (written in Python) for compiling programs written in
a little language (whose runtime is written in assembly) and then sending
them over USB to the OS to be run as concurrent tasks.

That's all in the [minitasks/](minitasks/) subdirectory of this repo... start by looking
at the README!
