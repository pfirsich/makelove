from collections import namedtuple

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
LoveVersion = val.Choice(*all_love_versions)

BuildParam = namedtuple("BuildParam", ["name", "validator", "help"])

build_params = [
    BuildParam("name", str, "The project's name"),
    BuildParam("love_version", val.LoveVersion(), "The löve version of the project"),
    BuildParam(
        "default_targets",
        val.List(val.Choice(*all_targets)),
        "The targets to build by default",
    ),
    BuildParam("build_directory", val.Path(), "The target directory for builds"),
    BuildParam(
        "love_files", val.List(val.Path()), "The files to include in the .love file",
    ),
    BuildParam(
        "archive_files",
        val.Dict(val.Path(), val.Path()),
        "The files to include in the final archive that contains the binary",
    ),
    BuildParam(
        "hooks.prebuild",
        val.List(str),
        "The hooks to execute before the build is started",
    ),
    BuildParam(
        "hooks.postbuild",
        val.List(str),
        "The hook to execute after the prebuild target is built",
    ),
    BuildParam("win32.love_binaries", val.Path(), ""),
    BuildParam(
        "windows.archive_files",
        val.Dict(val.Path(), val.Path()),
        "Overwrite archive-files for the windows targets win32 and win64",
    ),
]
