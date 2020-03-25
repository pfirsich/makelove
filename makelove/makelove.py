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
import pkg_resources

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


def prepare_build_directory(args, config, version):
    assert "build_directory" in config
    build_directory = config["build_directory"]
    versioned_build = version != None

    if versioned_build:
        # Pretend the build directory is the version directory
        # I think this is somewhat hacky, but also nice at the same time
        build_directory = os.path.join(build_directory, version)

    if os.path.isdir(build_directory):
        # If no version is specified, overwrite by default
        built_targets = os.listdir(build_directory)
        building_target_again = any(target in built_targets for target in args.targets)
        # If the targets being built have not been built before, it should be fine to not do anything
        # The deletion/creation of the target directories is handled in main() (they are just deleted if they exist).
        if versioned_build and building_target_again and not args.force:
            sys.exit(
                "Cannot rebuild an already built version + target combination. Remove it manually first or pass --force to overwrite it"
            )
    elif os.path.exists(build_directory):
        sys.exit("Build directory exists and is not a directory")
    else:
        os.makedirs(build_directory)
    return build_directory


def execute_hooks(hook, config, version, targets, build_directory):
    if "hooks" in config and hook in config["hooks"]:
        for command in config["hooks"][hook]:
            new_config = execute_hook(
                command, config, version, targets, build_directory
            )
            config.clear()
            config.update(new_config)


def git_ls_tree(path=".", visited=None):
    p = os.path

    if visited == None:
        visited = set()
    rpath = p.realpath(path)
    if rpath in visited:
        sys.exit("Symlink loop detected!")
    else:
        visited.add(rpath)

    ls_tree = (
        subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=path
        )
        .decode("utf-8")
        .splitlines()
    )
    out = []
    for item in ls_tree:
        item_path = p.join(path, item)
        if p.islink(item_path) and p.isdir(item_path):
            out.extend(git_ls_tree(item_path, visited))
        else:
            out.append(item_path)
    return out


def assemble_game_directory(args, config, game_directory):
    if os.path.isdir(game_directory):
        shutil.rmtree(game_directory)
    os.makedirs(game_directory)
    file_list = FileList(".")
    for rule in config["love_files"]:
        if rule == "+::git-ls-tree::" or rule == "::git-ls-tree::":
            ls_tree = git_ls_tree(".")
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


def get_build_version(args, config):
    build_log_path = get_build_log_path(config["build_directory"])

    # Bump version if we are doing a versioned build and no version is specified
    were_versioned_builds_made = os.path.isfile(build_log_path)
    if were_versioned_builds_made and args.version == None:
        print(
            "Versioned builds were made in the past, but no version was specified for this build. Bumping last built version."
        )
        with open(build_log_path) as f:
            build_log = json.load(f)
            last_built_version = build_log[-1]["version"]

        return bump_version(last_built_version)

    return args.version


def get_targets(args, config):
    targets = args.targets
    if len(targets) == 0:
        assert "default_targets" in config
        targets = config["default_targets"]

    # use this lame loop to make unique but keep target order
    unique_targets = []
    for target in targets:
        if target not in unique_targets:
            unique_targets.append(target)
    targets = unique_targets

    return targets


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
        "--force",
        dest="force",
        action="store_true",
        help="If doing a versioned build, specify this to overwrite a target that was already built.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="If doing an unversioned build, specify this to not rebuild targets that were already built.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display more information (files included in love archive)",
    )
    # Restrict version name format somehow? A git refname?
    parser.add_argument(
        "-n",
        "--version-name",
        dest="version",
        help="Specify the name of the version to be built.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only load config and check some arguments, then exit without doing anything. This is mostly useful development.",
    )
    parser.add_argument(
        "--version",
        dest="display_version",
        action="store_true",
        help="Output the makelove version and exit.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        type=_choices(all_targets),
        default=[],
        help="Options: {}".format(", ".join(all_targets)),
    )
    args = parser.parse_args()

    if args.display_version:
        print("makelove {}".format(pkg_resources.get_distribution("makelove").version))
        sys.exit(0)

    if not os.path.isfile("main.lua"):
        print(
            "There is no main.lua present in the current directory! Unless you use MoonScript, this might be a mistake."
        )

    if args.init:
        init_config_assistant()
        sys.exit(0)

    config = get_config(args.config)

    version = get_build_version(args, config)

    if version != None:
        print("Building version '{}'".format(version))

    if "all" in args.disabled_hooks:
        args.disabled_hooks = all_hooks

    if args.check:
        print("Exiting because --check was passed.")
        sys.exit(0)

    build_directory = prepare_build_directory(args, config, version)

    targets = get_targets(args, config)

    if sys.platform.startswith("win") and "appimage" in targets:
        sys.exit("Currently AppImages can only be built on Linux and WSL2!")

    build_log_path = get_build_log_path(config["build_directory"])
    print("Building targets:", ", ".join(targets))

    if version != None:
        with JsonFile(build_log_path, indent=4) as build_log:
            build_log.append(
                {
                    "version": version,
                    "build_time": formatdate(localtime=True),
                    "targets": targets,
                    "completed": False,
                }
            )

    if not "prebuild" in args.disabled_hooks:
        execute_hooks("prebuild", config, version, targets, build_directory)

    love_directory = os.path.join(build_directory, "love")
    love_file_path = os.path.join(love_directory, "{}.love".format(config["name"]))
    game_directory = os.path.join(love_directory, "game_directory")

    # This hold for both the löve file and the targets below:
    # If we do a versioned build and reached this place, force/--force
    # was passed, so we can just delete stuff.

    rebuild_love = version != None or not args.resume
    if not os.path.isfile(love_file_path) or rebuild_love:
        print("Assembling game directory..")
        assemble_game_directory(args, config, game_directory)

        if not os.path.isfile(os.path.join(game_directory, "main.lua")):
            sys.exit(
                "Your game directory does not contain a main.lua. This will result in a game that can not be run."
            )

        create_love_file(game_directory, love_file_path)
        print("Created {}".format(love_file_path))

        if config.get("keep_game_directory", False):
            print("Keeping game directory because 'keep_game_directory' is true")
        else:
            shutil.rmtree(game_directory)
    else:
        print(".love file already exists. Not rebuilding.")

    for target in targets:
        print(">> Building target {}".format(target))

        target_directory = os.path.join(build_directory, target)
        # If target_directory is not a directory, let it throw an exception
        # We can overwrite here
        if os.path.exists(target_directory):
            shutil.rmtree(target_directory)
        os.makedirs(target_directory)

        if target == "win32" or target == "win64":
            build_windows(config, version, target, target_directory, love_file_path)
        elif target == "appimage":
            build_linux(config, version, target, target_directory, love_file_path)

        print("Target {} complete".format(target))

    if not "postbuild" in args.disabled_hooks:
        execute_hooks("postbuild", config, version, targets, build_directory)

    if version != None:
        with JsonFile(build_log_path, indent=4) as build_log:
            build_log[-1]["completed"] = True


if __name__ == "__main__":
    main()
