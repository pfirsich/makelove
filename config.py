import os
import shutil
import subprocess
import sys
import re

import toml

import validators as val

all_targets = ["win32", "win64", "appimage"]

all_love_versions = [
    "11.3",
    "11.2",
    "11.1",
    "11.0",
    "0.10.2",
    "0.10.1",
    "0.10.0",
    "0.9.2",
    "0.9.1",
    "0.9.0",
    "0.8.0",
    "0.7.2",
    "0.7.1",
    "0.7.0",
    "0.6.2",
    "0.6.1",
    "0.6.0",
    "0.5.0",
    "0.4.0",
    "0.3.2",
    "0.3.1",
    "0.3.0",
    "0.2.1",
    "0.2.0",
    "0.1.1",
]

config_params = {
    "name": val.String(),
    "love_version": val.Choice(*all_love_versions),
    "default_targets": val.List(val.Choice(*all_targets)),
    "build_directory": val.Path(),
    "icon_file": val.Path(),
    "love_files": val.List(val.Path()),
    "archive_files": val.Dict(val.Path(), val.Path()),
    "hooks": val.Section(
        {
            "prebuild": val.List(val.Command()),
            "postbuild": val.List(val.Command()),
            "parameters": val.Dict(val.Any(), val.Any()),
        }
    ),
    "windows": val.Section(
        {
            "exe_metadata": val.Dict(val.String(), val.String()),
            "archive_files": val.Dict(val.Path(), val.Path()),
        }
    ),
    "win32": val.Section(
        {"love_binaries": val.Path(), "shared_libraries": val.List(val.Path())}
    ),
    "win64": val.Section(
        {"love_binaries": val.Path(), "shared_libraries": val.List(val.Path())}
    ),
    "linux": val.Section(
        {"desktop_file_metadata": val.Dict(val.String(), val.String())}
    ),
    "appimage": val.Section(
        {"source_appimage": val.Path(), "shared_libraries": val.List(val.Path()),}
    ),
}


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


def validate_config(config):
    try:
        val.Section(config_params).validate(config)
    except ValueError as exc:
        sys.exit("Could not parse config:\n{}".format(exc))


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
