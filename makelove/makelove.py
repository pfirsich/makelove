#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import json
import subprocess
from email.utils import formatdate
import zipfile
import re

from .config import get_config, all_targets, init_config_assistant
from .hooks import execute_hook
from .filelist import FileList
from .jsonfile import JsonFile
from .windows import build_windows
from .linux import build_linux

all_hooks = ["prebuild", "postbuild"]

# Sadly argparse cannot handle nargs="*" and choices and will error if not at least one argument is provided
def _choices(values):
    def f(s):
        if s not in values:
            raise argparse.ArgumentTypeError(
                "Invalid choice. Options: {}".format(", ".join(values))
            )
        return s

    return f


def files_in_dir(dir_path):
    ret = []
    for root, _dirs, files in os.walk(dir_path):
        for f in files:
            ret.append(os.path.join(root, f))
    return ret


# Obviously this cannot bump everything, just bump the trailing number
def bump_version(version):
    m = re.search(r"\d+$", version)
    if not m:
        sys.exit("Could not bump version '{}'".format(version))
    num = int(m.group(0)) + 1
    return version[: m.start(0)] + str(num)


def get_build_log_path(build_directory):
    return os.path.join(build_directory, ".makelove-buildlog")


# Why is this so much code?
def prepare_build_directory(args, config):
    assert "build_directory" in config
    build_directory = config["build_directory"]
    versioned_build = args.version != None
    made_versioned_builds = os.path.exists(build_directory) and os.path.isfile(
        get_build_log_path(build_directory)
    )

    if made_versioned_builds and not versioned_build:
        if args.overwrite_build:
            shutil.rmtree(build_directory)
        else:
            sys.exit(
                "You have made a versioned build in the past. Please pass a version name or pass --stomp to delete the whole build directory."
            )

    if versioned_build:
        # Pretend the build directory is the version directory
        # I think this is somewhat hacky, but also nice at the same time
        build_directory = os.path.join(build_directory, args.version)

    if os.path.exists(build_directory):
        if not os.path.isdir(build_directory):
            sys.exit(
                "Build directory can not be created, because a non-directory object with the same name already exists"
            )
        # If no version is specified, overwrite by default
        built_targets = os.listdir(build_directory)
        building_target_again = any(target in built_targets for target in args.targets)
        # If the targets being built have not been built before, it should be fine to not do anything
        if building_target_again:
            if versioned_build:
                if args.overwrite_build:
                    print("Version directory already exists. Deleting..")
                    shutil.rmtree(build_directory)
                else:
                    sys.exit(
                        "Version directory/target already exists. Remove it manually first or pass --stomp to overwrite it"
                    )
            else:
                print("Clearing build directory")
                shutil.rmtree(build_directory)
    else:
        os.makedirs(build_directory)
    return build_directory


def execute_hooks(args, config, name):
    if (
        "hooks" in config
        and name in config["hooks"]
        and not name in args.disabled_hooks
    ):
        for command in config["hooks"][name]:
            new_config = execute_hook(command, args, config)
            config.clear()
            config.update(new_config)


def assemble_game_directory(args, config, game_directory):
    if os.path.isdir(game_directory):
        shutil.rmtree(game_directory)
    os.makedirs(game_directory)
    file_list = FileList(".")
    for rule in config["love_files"]:
        if rule == "+::git-ls-tree::" or rule == "::git-ls-tree::":
            ls_tree = (
                subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "HEAD"])
                .decode("utf-8")
                .splitlines()
            )
            for item in ls_tree:
                try:
                    file_list.include_raw(item)
                except FileNotFoundError:
                    sys.exit("Could not find git-tracked file '{}'".format(item))
        elif rule[0] == "-":
            file_list.exclude(rule[1:])
        elif rule[0] == "+":
            file_list.include(rule[1:])
        else:
            file_list.include(rule)

    if args.verbose:
        print(".love files:")

    for fname in file_list:
        if args.verbose:
            print(fname)
        dest_path = os.path.join(game_directory, fname)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copyfile(fname, dest_path)


def create_love_file(game_dir, love_file_path):
    love_archive = zipfile.ZipFile(love_file_path, "w")
    for path in files_in_dir(game_dir):
        arcname = os.path.normpath(os.path.relpath(path, game_dir))
        love_archive.write(path, arcname=arcname)
    love_archive.close()


def main():
    parser = argparse.ArgumentParser(prog="makelove")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Start assistant to create a new configuration.",
    )
    parser.add_argument(
        "--config",
        help="Specify config file manually. If not specified 'makelove.toml' in the current working directory is used.",
    )
    parser.add_argument(
        "-d",
        "--disable-hook",
        default=[],
        dest="disabled_hooks",
        action="append",
        choices=all_hooks + ["all"],
    )
    parser.add_argument(
        "--stomp",
        dest="overwrite_build",
        action="store_true",
        help="Specify this option to overwrite a version that was already built.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display more information (files included in love archive)",
    )
    # Restrict version name format somehow? A git refname?
    parser.add_argument("-v", "--version", help="Specify the version to be built.")
    parser.add_argument(
        "-b",
        "--bump-version",
        action="store_true",
        help="Bump the previously built version and use it as --version.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only load config and check some arguments, then exit without doing anything. This is mostly useful development.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        type=_choices(all_targets),
        default=[],
        help="Options: {}".format(", ".join(all_targets)),
    )
    args = parser.parse_args()

    if args.init:
        init_config_assistant()
        sys.exit(0)

    if not os.path.isfile("main.lua"):
        sys.exit(
            "There is no main.lua present in the current directory. Please execute makelove in a love game directory"
        )

    config = get_config(args)

    build_log_path = get_build_log_path(config["build_directory"])

    if args.bump_version:
        if not os.path.isfile(build_log_path):
            sys.exit(
                "Could not find build log. It seems you have not built a versioned build before, so you can't pass --bump-version"
            )
        with open(build_log_path) as f:
            build_log = json.load(f)
            last_built_version = build_log[-1]["version"]
        # Assigning to args.version here is a hack, but I want to get this thing done
        args.version = bump_version(last_built_version)

    if args.version != None:
        print("Building version '{}'".format(args.version))

    if "all" in args.disabled_hooks:
        args.disabled_hooks = all_hooks

    if args.check:
        print("Exiting because --check was passed.")
        sys.exit(0)

    build_directory = prepare_build_directory(args, config)

    targets = args.targets
    if len(targets) == 0:
        assert "default_targets" in config
        targets = config["default_targets"]
    targets = list(set(targets))

    if sys.platform.startswith("win") and "appimage" in targets:
        sys.exit("Currently AppImages can only be built on Linux and WSL2!")

    print("Building targets:", ", ".join(targets))

    if args.version != None:
        with JsonFile(build_log_path, indent=4) as build_log:
            build_log.append(
                {
                    "version": args.version,
                    "build_time": formatdate(localtime=True),
                    "targets": targets,
                    "completed": False,
                }
            )

    execute_hooks(args, config, "prebuild")

    love_directory = os.path.join(build_directory, "love")
    love_file_path = os.path.join(love_directory, "{}.love".format(config["name"]))
    game_directory = os.path.join(love_directory, "game_directory")

    # Check for existence for resumable builds
    if not os.path.isfile(love_file_path):
        print("Assembling game directory..")
        assemble_game_directory(args, config, game_directory)

        create_love_file(game_directory, love_file_path)
        print("Created {}".format(love_file_path))

        if config.get("keep_game_directory", False):
            print("Keeping game directory because 'keep_game_directory' is true")
        else:
            shutil.rmtree(game_directory)

    for target in targets:
        print(">> Building target {}".format(target))
        if target == "win32" or target == "win64":
            build_windows(args, config, target, build_directory, love_file_path)
        elif target == "appimage":
            build_linux(args, config, target, build_directory, love_file_path)
        print("Target {} complete".format(target))

    execute_hooks(args, config, "postbuild")

    if args.version != None:
        with JsonFile(build_log_path, indent=4) as build_log:
            build_log[-1]["completed"] = True


if __name__ == "__main__":
    main()
