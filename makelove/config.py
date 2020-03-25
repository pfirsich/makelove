import os
import shutil
import subprocess
import sys
import re

import toml

from . import validators as val
from .util import prompt

default_config_name = "makelove.toml"

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
    "keep_game_directory": val.Bool(),
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
        {
            "love_binaries": val.Path(),
            "shared_libraries": val.List(val.Path()),
            "artifacts": val.ValueOrList(val.Choice("directory", "archive")),
        }
    ),
    "win64": val.Section(
        {
            "love_binaries": val.Path(),
            "shared_libraries": val.List(val.Path()),
            "artifacts": val.ValueOrList(val.Choice("directory", "archive")),
        }
    ),
    "linux": val.Section(
        {"desktop_file_metadata": val.Dict(val.String(), val.String())}
    ),
    "appimage": val.Section(
        {
            "source_appimage": val.Path(),
            "shared_libraries": val.List(val.Path()),
            "artifacts": val.ValueOrList(val.Choice("appdir", "appimage")),
        }
    ),
}


def should_build_artifact(config, target, artifact, default):
    if not target in config or not "artifacts" in config[target]:
        return default
    if artifact in config[target]["artifacts"]:
        return True


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


def get_conf_filename():
    candidates = ["conf.lua", "conf.moon", "conf.ts"]
    for name in candidates:
        if os.path.isfile(name):
            print("Found {}".format(name))
            return name
    print("Could not find löve config file")
    return None


def guess_love_version():
    filename = get_conf_filename()
    if filename == None:
        return None

    with open(filename) as f:
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


def get_default_love_files(build_directory):
    if is_inside_git_repo():
        return [
            "::git-ls-tree::",
            "-*/.*",
        ]
    else:
        return [
            "+*",
            "-*/.*",
            "-./{}/*".format(build_directory),
        ]


def validate_config(config):
    try:
        val.Section(config_params).validate(config)
    except ValueError as exc:
        sys.exit("Could not parse config:\n{}".format(exc))


def get_raw_config(config_path):
    if config_path != None:
        if not os.path.isfile(config_path):
            sys.exit("Config file '{}' does not exist".format(config_path))
        print("Loading config file '{}'".format(config_path))
        return load_config_file(config_path)
    else:
        if os.path.isfile(default_config_name):
            print("Loading config from default path '{}'".format(default_config_name))
            return load_config_file(default_config_name)
        else:
            print("No config file found. Using default config.")
            return {}


def get_config(config_path):
    config = get_raw_config(config_path)
    if not "name" in config:
        config["name"] = guess_name()
        print("Guessing project name as '{}'".format(config["name"]))
    if not "love_version" in config:
        conf_love_version = guess_love_version()
        if conf_love_version:
            config["love_version"] = conf_love_version
            print(
                "Guessed löve version from löve config file: {}".format(
                    conf_love_version
                )
            )
        else:
            config["love_version"] = "11.3"  # update this manually here
            print("Assuming default löve version '{}'".format(config["love_version"]))
    if not "default_targets" in config:
        config["default_targets"] = get_default_targets()
    if not "build_directory" in config:
        config["build_directory"] = "makelove-build"
        print("Using default build directory '{}'".format(config["build_directory"]))
    if not "love_files" in config:
        config["love_files"] = get_default_love_files(config["build_directory"])
        print("Using default love_files patterns: {}".format(config["love_files"]))
    validate_config(config)
    return config


init_config_template = """name = {name}
default_targets = [{default_targets}]
build_directory = {build_directory}

love_files = [
{love_files}
]
"""


def init_config_assistant():
    if os.path.isfile(default_config_name):
        sys.exit("{} already exists in this directory".format(default_config_name))

    if not is_inside_git_repo():
        print("If you plan on using git, please initialize the repository first!")

    name = prompt("Project name")
    default_targets = get_default_targets()
    build_directory = prompt("Build directory", "makelove-build")
    love_files = get_default_love_files(build_directory)

    quote = lambda x: '"' + x.replace('"', '\\"') + '"'
    config = init_config_template.format(
        name=quote(name),
        default_targets=", ".join(map(quote, default_targets)),
        build_directory=quote(build_directory),
        love_files="\n".join("    " + quote(pat) + "," for pat in love_files),
    )

    with open(default_config_name, "w") as f:
        f.write(config)
    print("Configuration written to {}".format(default_config_name))
    print("You should probably adjust love_files before you build.")
