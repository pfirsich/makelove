import sys
import tempfile
import atexit
import os
import re
from distutils.util import strtobool


def eprint(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def _tempfile_deleter(path):
    if os.path.isfile(path):
        os.remove(path)


def tmpfile(*args, **kwargs):
    (fd, path) = tempfile.mkstemp(*args, **kwargs)
    os.close(fd)
    atexit.register(_tempfile_deleter, path)
    return path


def parse_love_version(version_str):
    parts = list(map(int, re.split(r"_|\.", version_str)))
    if len(parts) == 3 and parts[0] == 0:
        parts = parts[1:]
    if len(parts) != 2:
        sys.exit("Could not parse version '{}'".format(".".join(parts)))
    return parts


def ask_yes_no(question, default=None):
    if default == None:
        option_str = "[y/n]: "
    else:
        option_str = " [{}/{}]: ".format(
            "Y" if default else "y", "N" if not default else "n"
        )

    while True:
        sys.stdout.write(question + option_str)
        choice = input().lower()
        if choice == "" and default != None:
            return default
        else:
            try:
                return bool(strtobool(choice))
            except ValueError:
                sys.stdout.write("Invalid answer.\n")


def prompt(prompt_str, default=None):
    default_str = ""
    if default != None:
        default_str = " [{}]".format(default)
    while True:
        sys.stdout.write(prompt_str + default_str + ": ")
        s = input()
        if s:
            return s
        else:
            if default != None:
                return default
