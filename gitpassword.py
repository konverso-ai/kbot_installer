#!/usr/bin/python3
import sys
from sys import argv
from os import environ


if 'username' in argv[1].lower():
    print(environ['GIT_USERNAME'])
    sys.exit(0)

if 'password' in argv[1].lower():
    print(environ['GIT_PASSWORD'])
    sys.exit(0)

sys.exit(1)

