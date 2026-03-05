exec picocom \
    -c \
    -b 38400 \
    "$@" \
    /dev/ttyUSB0
