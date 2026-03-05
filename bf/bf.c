
#include <inttypes.h>


typedef uint8_t cell_t;


cell_t CELLS[MAX_CELLS] = {0};


void putchar(char c) {
  loop_until_bit_is_set(UCSRA, UDRE);
  UDR = c;
}


void main() {
    cell_t *p = cells;
}
