#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import json
import subprocess
from email.utils import formatdate
import zipfile

from config import get_config
from buildparams import all_targets
from hooks import execute_hook
from filelist import FileList
from jsonfile import JsonFile
from windows import build_windows
from linux import build_linux

all_hooks = ["prebuild", "postgamedir", "postbuild"]

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


def get_build_log_path(build_directory):
    return os.path.join(build_directory, ".makelove-buildlog")


# Why is this so much code?
def prepare_build_directory(args, config):
    assert "build_directory" in config
    build_directory = config["build_directory"]
    if os.path.exists(build_directory):
        if os.path.isfile(get_build_log_path(build_directory)):
            # We are using versioned builds
            if args.version == None and not args.overwrite_build:
                sys.exit(
                    "You have made versioned builds in the past. Please pass a version name or pass --stomp to delete the whole build directory."
                )

    if args.version != None:
        version_directory = os.path.join(build_directory, args.version)
        if os.path.exists(version_directory):
            if os.path.isdir(version_directory):
                if args.overwrite_build:
                    print("Version directory already exists. Deleting..")
                    shutil.rmtree(version_directory)
                else:
                    sys.exit(
                        "Version directory already exists. Remove it manually first or pass --stomp to overwrite it"
                    )
            else:
                sys.exit(
                    "Version directory can not be created, because a non-directory object with the same name already exists"
                )
        # Pretend the build directory is the version directory
        # I think this is somewhat hacky, but also nice at the same time
        build_directory = version_directory
    else:
        if os.path.exists(build_directory):
            if not os.path.isdir(build_directory):
                sys.exit(
                    "Build directory can not be created, because a non-directory object with the same name already exists"
                )
            # If no version is specified, overwrite by default
            print("Clearing build directory")
            shutil.rmtree(build_directory)

    # Make sure we start with a clean build directory
    assert not os.path.exists(build_directory)
    try:
        os.makedirs(build_directory)
    except OSError:
        sys.exit(
            "Could not create build directory. Did you pass a version name that is not a valid file name on your OS?"
        )

    return build_directory


def execute_hooks(args, config, name):
    if (
        "hooks" in config
        and name in config["hooks"]
        and not name in args.disabled_hooks
    ):
        for command in config["hooks"][name]:
            new_config = execute_hook(command, config)
            config.clear()
            config.update(new_config)


def assemble_game_directory(args, config, game_directory):
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
    parser.add_argument("--config")
    parser.add_argument(
        "-d",
        "--disable-hook",
        dest="disabled_hooks",
        action="append",
        choices=all_hooks,
    )
    parser.add_argument("--stomp", dest="overwrite_build", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    # TODO: Restrict version name format somehow? A git refname?
    parser.add_argument("-v", "--version")
    parser.add_argument(
        "targets",
        nargs="*",
        type=_choices(all_targets),
        default=[],
        help="Options: {}".format(", ".join(all_targets)),
    )
    args = parser.parse_args()

    if not os.path.isfile("main.lua"):
        sys.exit(
            "There is no main.lua present in the current directory. Please execute makelove in a love game directory"
        )

    config = get_config(args)

    build_directory = prepare_build_directory(args, config)
    build_log_path = get_build_log_path(config["build_directory"])

    targets = args.targets
    if len(targets) == 0:
        assert "default_targets" in config
        targets = config["default_targets"]

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
    game_directory = os.path.join(love_directory, "game_directory")
    assemble_game_directory(args, config, game_directory)

    assert "name" in config
    love_file_path = os.path.join(love_directory, "{}.love".format(config["name"]))
    create_love_file(game_directory, love_file_path)
    print("Created {}".format(love_file_path))

    for target in targets:
        print("Building target {}".format(target))
        if target == "win32" or target == "win64":
            build_windows(args, config, target, build_directory, love_file_path)
        elif target == "linux" or target == "appimage":
            build_linux(args, config, target, build_directory)

    execute_hooks(args, config, "postbuild")

    if args.version != None:
        with JsonFile(build_log_path, indent=4) as build_log:
            build_log[-1]["completed"] = True


if __name__ == "__main__":
    main()
