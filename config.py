import os
import shutil
import subprocess
import sys

import toml

from buildparams import build_params, all_targets


def load_config_file(path):
    with open(path) as f:
        config_data = toml.load(f)
    validate_config(config_data)
    return config_data


def guess_name():
    try:
        git_root_path = (
            subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
            .decode("utf-8")
            .strip()
        )
        return os.path.basename(git_root_path)
    except subprocess.CalledProcessError:
        return os.path.basename(os.getcwd())


def get_default_targets():
    targets = ["love", "win32", "win64"]
    if sys.platform == "linux":
        # TODO: only append if necessary tools are installed
        # Maybe there is some extra config necessary anyways?
        targets.append("appimage")
    return targets


def expand_wildcard(pattern):
    # Be aware of .gitignore, .hgignore, .ignore and ignore hidden files
    pass


def validate_config(config):
    pass


def get_raw_config(args):
    if args.config != None:
        if not os.path.isfile(args.config):
            sys.exit("Config file '{}' does not exist".format(args.config))
        return load_config_file(args.config)
    else:
        default_config_path = "makelove.toml"
        if os.path.isfile(default_config_path):
            return load_config_file(default_config_path)
        else:
            return {}


def get_config(args):
    config = get_raw_config(args)
    if not "name" in config:
        config["name"] = guess_name()
        print("Guessing project name as '{}'".format(config["name"]))
    if not "love_version" in config:
        config["love_version"] = "11.3"  # update this manually here
        print("Assuming default löve version '{}'".format(config["love_version"]))
    if not "default_targets" in config:
        config["default_targets"] = get_default_targets()
        print(
            "Building default targets: {}".format(", ".join(config["default_targets"]))
        )
    if not "build_directory" in config:
        config["build_directory"] = "makelove-build"
        print("Using default build directory '{}'".format(config["build_directory"]))
    if not "love_files" in config:
        config["love_files"] = ["::git-ls-tree::", "-*/.*"]  # exclude hidden files
        print("Using default love_files patterns: {}".format(config["love_files"]))
    validate_config(config)
    return config
