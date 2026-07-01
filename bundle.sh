#!/bin/bash

KBOT_INSTALLER_FOLDER=`pwd`/$( dirname "${BASH_SOURCE[0]}" )
export PYTHONPATH=${KBOT_INSTALLER_FOLDER}/core/python:${PYTHONPATH}

echo PYTHONPATH: $PYTHONPATH

python3 $( dirname "${BASH_SOURCE[0]}" )/bundle.py $*
