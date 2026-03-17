#!/bin/bash
set -euo pipefail

ipython -i -c 'from minitasks import *; c = Client()' "$@"

