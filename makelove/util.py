import sys
import tempfile
import atexit
import os
import re
from distutils.util import strtobool

import appdirs


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


def get_default_love_binary_dir(version, platform):
    return os.path.join(
        appdirs.user_cache_dir("makelove"), "love-binaries", version, platform
    )


def get_download_url(version, platform):
    # This function is intended to handle all the weird special cases and
    # is therefore a allowed to be ugly
    url = "https://github.com/love2d/love/releases/download/{}/".format(version)
    if list(map(int, version.split("."))) <= [0, 8, 0]:
        platform = {"win32": "win-x86", "win64": "win-x64", "macos": "macosx-ub"}[
            platform
        ]
    elif version == "0.9.0" and platform == "macos":
        platform = "macosx-x64"

    if version == "11.0":
        # Why? I don't know.
        filename = "love-11.0.0-{}.zip".format(platform)
    else:
        filename = "love-{}-{}.zip".format(version, platform)
    return url + filename
