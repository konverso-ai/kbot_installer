#!/bin/bash

# Wrapper around the `kbot-installer` CLI.
#
# All arguments are forwarded as-is to `kbot-installer`. The installer path is
# read from the `-i` / `--installer` option (when present) and used to locate
# the kbot installation whose `bin/env.sh` must be sourced before running.

set -euo pipefail

# Extract the installer path from the -i / --installer option without
# consuming the arguments (they are all forwarded to kbot-installer).
INSTALLER_HOME=""
prev=""
for arg in "$@"; do
    case "$prev" in
        -i|--installer)
            INSTALLER_HOME="$arg"
            break
            ;;
    esac
    case "$arg" in
        -i=*|--installer=*)
            INSTALLER_HOME="${arg#*=}"
            break
            ;;
    esac
    prev="$arg"
done

export KBOT_INSTALLER="$INSTALLER_HOME"

if [[ -z "$INSTALLER_HOME" ]]; then
    echo "Using standard installation path"
    KBOT_HOME="$HOME/dev/installer/kbot"
else
    echo "Using custom installation path"
    KBOT_HOME="$INSTALLER_HOME/kbot"
fi

echo "$KBOT_HOME/bin/env.sh"
set +u
source "$KBOT_HOME/bin/env.sh"
set -u

# prevent the running script from git directory
if [ -f "$KBOT_HOME/Definitions.make" ]; then
    echo "Error: $KBOT_HOME is not a Kbot installation directory."
    exit 1
fi

# If no readline6 installed then use binaries from readline7
manage_os

export PYTHON_MAJOR_VERSION
export PYTHON_DIR
export PG_VERSION
export PG_DIR

export PYTHONPATH="${PYTHONPATH:-}:$KBOT_HOME/rest"

kbot-installer "$@" 2>&1 | tee /tmp/install.log
exit "${PIPESTATUS[0]}"
