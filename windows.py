# rcedit builtin hook, check for `which wine` to do it on linux
# rcedit needs ico file, but Pillow can create it
# exiftool to print exe data
import copy
import sys
import os
import shutil


def build_windows(args, config, target, build_directory, love_file_path):
    if target in config and "love_binaries" in config[target]:
        love_binaries = config[target]["love_binaries"]
    else:
        print("No love binaries specified for target {}".format(target))
        sys.exit("IMPL")

    target_directory = os.path.join(build_directory, target)
    os.makedirs(target_directory)

    temp_archive_dir = os.path.join(target_directory, "archive_temp")
    os.makedirs(temp_archive_dir)

    src = lambda x: os.path.join(love_binaries, x)
    dest = lambda x: os.path.join(temp_archive_dir, x)
    copy = lambda x: shutil.copyfile(src(x), dest(x))
    copy("license.txt")
    for f in os.listdir(love_binaries):
        if f.endswith(".dll"):
            copy(f)

    target_exe_path = dest("{}.exe".format(config["name"]))
    with open(target_exe_path, "wb") as fused:
        with open(src("love.exe"), "rb") as loveExe:
            with open(love_file_path, "rb") as loveZip:
                fused.write(loveExe.read())
                fused.write(loveZip.read())

    archive_files = {}
    if "archive_files" in config:
        archive_files = config["archive_files"]
    if "windows" in config and "archive_files" in config["windows"]:
        archive_files.update(config["windows"]["archive_files"])
    if target in config and "archive_files" in config[target]:
        archive_files.update(config[target]["archive_files"])

    for k, v in archive_files.items():
        path = dest(v)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.isfile(k):
            shutil.copyfile(k, path)
        elif os.path.isdir(k):
            shutil.copytree(k, path)
        else:
            sys.exit("Cannot copy archive file '{}'".format(k))

    if target in config and "shared_libraries" in config[target]:
        for f in config[target]["shared_libraries"]:
            shutil.copyfile(f, dest(os.path.basename(f)))
