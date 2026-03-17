
args="-b ${BAUD:-38400}"
if test -z "$NOMAPS"; then args="$args --emap spchex,8bithex --imap spchex,8bithex"; fi
if test -z "$NOECHO"; then args="$args -c"; fi

exec picocom $args "$@" /dev/ttyUSB0
