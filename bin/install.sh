#!/bin/bash

# Thin wrapper around the `kbot-installer` CLI.
#
# All arguments are forwarded as-is to `kbot-installer`. Unlike the previous
# version, this wrapper does NOT source any kbot script (`kbot/bin/env.sh`):
# `kbot-installer` is installed in its own isolated interpreter (via
# `uv tool install`) with its own dependencies, and everything it needs from
# the 3rdparty tree (PG_DIR, LD_LIBRARY_PATH) is resolved in Python *after*
# the product has been downloaded. Sourcing `env.sh` here used to run before
# kbot was even downloaded and leaked kbot's PYTHONPATH into this interpreter,
# causing package collisions (e.g. `utils` -> `ModuleNotFoundError: magic`).
#
# Advanced override: exporting `PG_DIR` before calling this script still takes
# precedence over the automatic resolution from `3rdparty/versions.env`.

set -euo pipefail

kbot-installer "$@" 2>&1 | tee /tmp/install.log
exit "${PIPESTATUS[0]}"
