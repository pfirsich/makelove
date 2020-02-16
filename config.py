import os
import shutil
import subprocess
import sys
import re

import toml

from buildparams import build_params, all_targets


def load_config_file(path):
    with open(path) as f:
        config_data = toml.load(f)
    validate_config(config_data)
    return config_data


def is_inside_git_repo():
    return (
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"], capture_output=True
        ).returncode
        == 0
    )


def guess_name():
    res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True)
    if res.returncode == 0:
        git_root_path = res.stdout.decode("utf-8").strip()
        return os.path.basename(git_root_path)
    else:
        return os.path.basename(os.getcwd())


def get_default_targets():
    targets = ["win32", "win64"]
    if sys.platform == "linux":
        targets.append("appimage")
    return targets


def guess_love_version():
    with open("conf.lua") as f:
        conf_lua = f.read()

    regex = re.compile(r"(?<!--)\.version\s*=\s*\"(.*)\"")
    matches = regex.findall(conf_lua)
    if len(matches) == 0:
        return None
    elif len(matches) > 1:
        print(
            "Could not determine löve version unambiguously. Candidates: {}".format(
                matches
            )
        )
        return None
    return matches[0]


def expand_wildcard(pattern):
    # Be aware of .gitignore, .hgignore, .ignore and ignore hidden files
    pass


def validate_config(config):
    pass


def get_raw_config(args):
    if args.config != None:
        if not os.path.isfile(args.config):
            sys.exit("Config file '{}' does not exist".format(args.config))
        print("Loading config file '{}'".format(args.config))
        return load_config_file(args.config)
    else:
        default_config_path = "makelove.toml"
        if os.path.isfile(default_config_path):
            print("Loading config from default path '{}'".format(default_config_path))
            return load_config_file(default_config_path)
        else:
            print("No config file found. Using default config.")
            return {}


def get_config(args):
    config = get_raw_config(args)
    if not "name" in config:
        config["name"] = guess_name()
        print("Guessing project name as '{}'".format(config["name"]))
    if not "love_version" in config:
        conf_love_version = guess_love_version()
        if conf_love_version:
            config["love_version"] = conf_love_version
            print("Guessed löve version from conf.lua: {}".format(conf_love_version))
        else:
            config["love_version"] = "11.3"  # update this manually here
            print("Assuming default löve version '{}'".format(config["love_version"]))
    if not "default_targets" in config:
        config["default_targets"] = get_default_targets()
    if not "build_directory" in config:
        config["build_directory"] = "makelove-build"
        print("Using default build directory '{}'".format(config["build_directory"]))
    if not "love_files" in config:
        if is_inside_git_repo():
            config["love_files"] = [
                "::git-ls-tree::",
                "-*/.*",
            ]
        else:
            config["love_files"] = [
                "+*",
                "-*/.*",
                "-./{}/*".format(config["build_directory"]),
            ]
        print("Using default love_files patterns: {}".format(config["love_files"]))
    validate_config(config)
    return config
