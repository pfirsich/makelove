# rcedit builtin hook, check for `which wine` to do it on linux
# rcedit needs ico file, but Pillow can create it
# exiftool to print exe data
import copy
import sys
import os
import shutil
from zipfile import ZipFile
from urllib.request import urlopen
from io import BytesIO

import appdirs


def common_prefix(l):
    # This is all functional and cool, but entirely unreadable.
    # Just trust that it does what the function names suggests it does.
    return max(
        l[0][:i]
        for i in range(len(min(l, key=len)))
        if all(name.startswith(l[0][:i]) for name in l)
    )


def get_default_love_binary_dir(version, platform):
    return os.path.join(
        appdirs.user_cache_dir("makelove"), "love-binaries", version, platform
    )


def get_download_url(version, platform):
    url = "https://bitbucket.org/rude/love/downloads/"
    if list(map(int, version.split("."))) <= [0, 8, 0]:
        platform = {"win32": "win-x86", "win64": "win-x64"}[platform]
    return url + "love-{}-{}.zip".format(version, platform)


def download_love(version, platform):
    target_path = get_default_love_binary_dir(version, platform)
    print("Downloading love binaries to: '{}'".format(target_path))

    os.makedirs(target_path, exist_ok=True)
    with urlopen(get_download_url(version, platform)) as response:
        with ZipFile(BytesIO(response.read())) as zipfile:
            zipfile.extractall(target_path)

    # There is usually a single directory in the zip files
    # Move the contents up one level, then delete the empty directory
    subdir_path = os.path.join(target_path, os.listdir(target_path)[0])
    for element in os.listdir(subdir_path):
        shutil.move(os.path.join(subdir_path, element), target_path)
    os.rmdir(subdir_path)

    print("Download complete")


def build_windows(args, config, target, build_directory, love_file_path):
    if target in config and "love_binaries" in config[target]:
        love_binaries = config[target]["love_binaries"]
    else:
        assert "love_version" in config
        print("No love binaries specified for target {}".format(target))
        love_binaries = get_default_love_binary_dir(config["love_version"], target)
        if os.path.isdir(love_binaries):
            print("Love binaries already present in '{}'".format(love_binaries))
        else:

            download_love(config["love_version"], target)

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

    print("Target {} complete".format(target))
