#!/bin/bash
#
# Looks up a C macro/definition.
# Assumes you've run ./dump_defines.sh.
#
set -euo pipefail

name="$1"
shift

ack "$@" "#define $name" defines.txt
