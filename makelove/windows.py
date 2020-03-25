import copy
import sys
import os
import shutil
from zipfile import ZipFile
from urllib.request import urlopen, urlretrieve, URLError
from io import BytesIO
import subprocess

from PIL import Image, UnidentifiedImageError
import appdirs

from .util import tmpfile, eprint
from .config import should_build_artifact


def common_prefix(l):
    # This is all functional and cool, but entirely unreadable.
    # Just trust that it does what the function name suggests it does.
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
    # This function is intended to handle all the weird special cases and
    # is therefore a allowed to be ugly
    url = "https://github.com/love2d/love/releases/download/{}/".format(version)
    if list(map(int, version.split("."))) <= [0, 8, 0]:
        platform = {"win32": "win-x86", "win64": "win-x64"}[platform]
    if version == "11.0":
        # Why? I don't know.
        filename = "love-11.0.0-{}.zip".format(platform)
    else:
        filename = "love-{}-{}.zip".format(version, platform)
    return url + filename


def download_love(version, platform):
    target_path = get_default_love_binary_dir(version, platform)
    print("Downloading love binaries to: '{}'".format(target_path))

    os.makedirs(target_path, exist_ok=True)
    try:
        download_url = get_download_url(version, platform)
        print("Downloading '{}'..".format(download_url))
        with urlopen(download_url) as response:
            with ZipFile(BytesIO(response.read())) as zipfile:
                zipfile.extractall(target_path)
    except URLError as exc:
        eprint("Could not download löve: {}".format(exc))
        eprint(
            "If there is in fact no download on GitHub for this version, specify 'love_binaries' manually."
        )
        sys.exit(1)

    # There is usually a single directory in the zip files
    # Move the contents up one level, then delete the empty directory
    subdir_path = os.path.join(target_path, os.listdir(target_path)[0])
    for element in os.listdir(subdir_path):
        shutil.move(os.path.join(subdir_path, element), target_path)
    os.rmdir(subdir_path)

    print("Download complete")


def get_rcedit_path():
    return os.path.join(appdirs.user_cache_dir("makelove"), "rcedit-x64.exe")


def prepare_rcedit():
    rcedit_path = get_rcedit_path()
    if not os.path.isfile(rcedit_path):
        try:
            # I don't use the latest release, so I can be sure that the executable behaves as expected
            rcedit_download_url = "https://github.com/electron/rcedit/releases/download/v1.1.1/rcedit-x64.exe"
            os.makedirs(os.path.dirname(rcedit_path), exist_ok=True)
            print("Downloading '{}'..".format(rcedit_download_url))
            urlretrieve(rcedit_download_url, rcedit_path)
        except URLError as exc:
            sys.exit("Could not download rcedit: {}".format(exc))


def can_set_metadata(platform):
    if platform.startswith("win"):
        return True
    elif shutil.which("wine") != None:
        return True
    return False


def get_exe_metadata(config, version):
    # Default values listed here are from löve 11.3 (extra/windows/love.rc)

    metadata = {}
    if "windows" in config and "exe_metadata" in config["windows"]:
        metadata = config["windows"]["exe_metadata"]

    # Default value in löve: "LÖVE <version>"
    if not "FileDescription" in metadata:
        if version != None:
            metadata["FileDescription"] = "{} {}".format(config["name"], version)
        else:
            metadata["FileDescription"] = config["name"]

    # Default value is löve version
    if not "FileVersion" in metadata:
        if version != None:
            metadata["FileVersion"] = version
        else:
            metadata["FileVersion"] = ""

    # Default value is "LÖVE World Domination Inc."
    if not "CompanyName" in metadata:
        metadata["CompanyName"] = ""

    # Default value is "Copyright © 2006-2020 LÖVE Development Team"
    if not "LegalCopyright" in metadata:
        metadata["LegalCopyright"] = ""

    # Default value in löve: "LÖVE"
    if not "ProductName" in metadata:
        metadata["ProductName"] = config["name"]

    # Default value is same as FileVersion's
    if not "ProductVersion" in metadata:
        metadata["ProductVersion"] = metadata["FileVersion"]

    # löve also sets "InternalName" to ""

    return metadata


def get_rcedit_command():
    rcedit_path = get_rcedit_path()
    if sys.platform.startswith("win32"):
        return [rcedit_path]
    elif sys.platform.startswith("linux"):
        return ["wine", rcedit_path]
    else:
        sys.exit("Can not execute rcedit on ths platform ({})".format(sys.platform))


def set_exe_metadata(exe_path, metadata, icon_file):
    args = get_rcedit_command()[:]
    args.append(exe_path)
    for k, v in metadata.items():
        args.extend(["--set-version-string", k, v])

    temp_ico_path = None
    if icon_file != None:
        if not os.path.isfile(icon_file):
            sys.exit("Icon file does not exist '{}'".format(icon_file))
        if icon_file.lower().endswith(".ico"):
            args.extend(["--set-icon", icon_file])
        else:
            try:
                img = Image.open(icon_file)
                temp_ico_path = tmpfile(".ico")
                img.save(temp_ico_path)
                args.extend(["--set-icon", temp_ico_path])
            except FileNotFoundError as exc:
                sys.exit("Could not find icon file: {}".format(exc))
            except UnidentifiedImageError as exc:
                sys.exit("Could not read icon file: {}".format(exc))
            except IOError as exc:
                sys.exit("Could not convert icon to .ico: {}".format(exc))

    res = subprocess.run(args)
    if temp_ico_path:
        os.remove(temp_ico_path)
    if res.returncode != 0:
        sys.exit("Could not set exe metadata:\n" + res.stderr.decode("utf-8"))


def build_windows(config, version, target, target_directory, love_file_path):
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

    temp_archive_dir = os.path.join(target_directory, "archive_temp")
    os.makedirs(temp_archive_dir)

    src = lambda x: os.path.join(love_binaries, x)
    dest = lambda x: os.path.join(temp_archive_dir, x)
    copy = lambda x: shutil.copyfile(src(x), dest(x))

    if not os.path.isfile(src("love_orig.exe")):
        # Copy metadata too, because we are making a backup
        shutil.copy2(src("love.exe"), src("love_orig.exe"))

    target_exe_path = dest("{}.exe".format(config["name"]))

    if can_set_metadata(sys.platform):
        prepare_rcedit()

        metadata = get_exe_metadata(config, version)

        # Default value is "löve.exe" of course.
        # This value is used to determine if an executable has been renamed
        if not "OriginalFilename" in metadata:
            metadata["OriginalFilename"] = os.path.basename(target_exe_path)

        set_exe_metadata(
            src("love.exe"), metadata, config.get("icon_file", None),
        )
    else:
        print(
            "Cannot set exe metadata on this platform ({})".format(sys.platform),
            file=sys.stderr,
        )
        print("If you are using a POSIX-compliant system, try installing WINE.")

    with open(target_exe_path, "wb") as fused:
        with open(src("love.exe"), "rb") as loveExe:
            with open(love_file_path, "rb") as loveZip:
                fused.write(loveExe.read())
                fused.write(loveZip.read())

    copy("license.txt")
    for f in os.listdir(love_binaries):
        if f.endswith(".dll"):
            copy(f)

    archive_files = {}
    if "archive_files" in config:
        archive_files.update(config["archive_files"])
    if "windows" in config and "archive_files" in config["windows"]:
        archive_files.update(config["windows"]["archive_files"])

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

    if should_build_artifact(config, target, "archive", True):
        archive_path = os.path.join(
            target_directory, "{}-{}".format(config["name"], target)
        )
        shutil.make_archive(archive_path, "zip", temp_archive_dir)

    if should_build_artifact(config, target, "directory", False):
        os.rename(temp_archive_dir, os.path.join(target_directory, config["name"]))
    else:
        shutil.rmtree(temp_archive_dir)
