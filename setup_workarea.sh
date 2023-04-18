#!/bin/bash

# Expecting the first parameter to be the path of installer
# 
#
INSTALLER_HOME=${BASH_ARGV[0]}

echo INSTALLER_HOME set to $INSTALLER_HOME
if [[ $INSTALLER_HOME == "" ]];
then
    echo Using standard installation path
    KBOT_HOME=$HOME/dev/installer/kbot
else
    echo Using custom installation path
    KBOT_HOME=$INSTALLER_HOME/kbot
fi

echo Using KBOT_HOME as: $KBOT_HOME

# Note that we send all parameters excepter for the installer path which is not required.
PARAMS_TO_KEEP=$(($#-1))
INSTALLER_PARAMS=${@: 1:$PARAMS_TO_KEEP}

source $KBOT_HOME/bin/env.sh

# prevent the running script from git directory
if [ -f $KBOT_HOME/Definitions.make ]
then
  echo "Error: $KBOT_HOME is not a Kbot installation directory."
  exit 1
fi

# If no readline6 installed then use binaries from readline7
manage_os

export PYTHON_MAJOR_VERSION
export PYTHON_DIR
export PG_VERSION
export PG_DIR

export PYTHONPATH=$PYTHONPATH:$KBOT_HOME/rest

$KBOT_HOME/bin/python.sh $( dirname "${BASH_SOURCE[0]}" )/install.py $INSTALLER_PARAMS |& tee /tmp/install.log ; test ${PIPESTATUS[0]} -eq 0
