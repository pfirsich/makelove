import os
import sys
from urllib.request import urlretrieve, urlopen, URLError
import shutil
import subprocess
import re
import json
from collections import namedtuple

from PIL import Image, UnidentifiedImageError
import appdirs

from .util import tmpfile, parse_love_version, ask_yes_no
from .config import all_love_versions, should_build_artifact


def get_appimagetool_path():
    return os.path.join(appdirs.user_cache_dir("makelove"), "appimagetool")


def download_love_appimage(version):
    latest_url = "https://api.github.com/repos/pfirsich/love-appimages/releases/latest"
    try:
        with urlopen(latest_url) as req:
            data = json.loads(req.read().decode())
    except Exception as exc:
        sys.exit("Could not retrieve asset list: {}".format(exc))

    Asset = namedtuple("Asset", ["name", "version", "download_url"])
    appimages = []
    for asset in data["assets"]:
        m = re.match(r"love[-_]((?:\d+[_.])+\d+)[-_.].*", asset["name"])
        if m:
            appimage_version = parse_love_version(m.group(1))
            appimages.append(
                Asset(asset["name"], appimage_version, asset["browser_download_url"])
            )

    parsed_version = parse_love_version(version)
    same_major = [
        appimg for appimg in appimages if appimg.version[0] == parsed_version[0]
    ]
    if len(same_major) == 0:
        sys.exit("Did not find an available AppImage with matching major version")
    same_major.sort(key=lambda x: x.version, reverse=True)
    download_asset = same_major[0]
    if download_asset.version != parsed_version:
        print("Could not find AppImage with matching version.")
        print(
            "The most current AppImage with the same major version is for version {}".format(
                ".".join(map(str, download_asset.version))
            )
        )
        if not ask_yes_no("Use {} instead?".format(download_asset.name), default=True):
            sys.exit("Aborting.")

    try:
        appimage_path = tmpfile(suffix=".AppImage")
        print("Downloading {}..".format(download_asset.download_url))
        urlretrieve(download_asset.download_url, appimage_path)
        os.chmod(appimage_path, 0o755)
        return appimage_path
    except Exception as exc:
        sys.exit(
            "Could not download löve appimage from {}: {}".format(
                download_asset.download_url, exc
            )
        )


def get_appimagetool():
    which_appimagetool = shutil.which("appimagetool")
    if which_appimagetool:
        return which_appimagetool
    else:
        appimage_path = os.path.join(appdirs.user_cache_dir("makelove"), "appimagetool")
        if os.path.isfile(appimage_path):
            return appimage_path

        url = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        try:
            os.makedirs(os.path.dirname(appimage_path), exist_ok=True)
            print("Downloading '{}'..".format(url))
            urlretrieve(url, appimage_path)
            os.chmod(appimage_path, 0o755)
            return appimage_path
        except URLError as exc:
            sys.exit("Could not download löve appimage from {}: {}".format(url, exc))


def replace_single(string, pat, subst):
    matches = [m for m in re.finditer(re.escape(pat), string)]
    if len(matches) == 0:
        sys.exit("Could not find pattern '{}'".format(pat))
    elif len(matches) > 1:
        sys.exit("Multiple matches for pattern '{}'".format(pat))
    else:
        return string.replace(pat, subst)


def build_linux(config, version, target, target_directory, love_file_path):
    if target in config and "source_appimage" in config[target]:
        source_appimage = config[target]["source_appimage"]
    else:
        assert "love_version" in config
        # Download it every time, in case it's updated (I might make them smaller)
        source_appimage = download_love_appimage(config["love_version"])

    print("Extracting source AppImage '{}'..".format(source_appimage))
    ret = subprocess.run(
        [source_appimage, "--appimage-extract"],
        cwd=target_directory,
        capture_output=True,
    )
    if ret.returncode != 0:
        sys.exit("Could not extract AppImage: {}".format(ret.stderr.decode("utf-8")))

    appdir_path = os.path.join(target_directory, "squashfs-root")
    appdir = lambda x: os.path.join(appdir_path, x)

    # Modify AppDir
    shutil.copy2(love_file_path, appdir("usr/bin"))

    # Copy icon
    icon_file = config.get("icon_file", None)
    appdir_icon_path = appdir("{}.png".format(config["name"]))
    if icon_file:
        os.remove(appdir("love.svg"))
        if icon_file.lower().endswith(".png"):
            shutil.copy2(icon_file, appdir_icon_path)
        else:
            try:
                img = Image.open(icon_file)
                img.save(appdir_icon_path)
            except FileNotFoundError as exc:
                sys.exit("Could not find icon file: {}".format(exc))
            except UnidentifiedImageError as exc:
                sys.exit("Could not read icon file: {}".format(exc))
            except IOError as exc:
                sys.exit("Could not convert icon to .png: {}".format(exc))
    os.remove(appdir(".DirIcon"))

    # replace love.desktop with [name].desktop
    os.remove(appdir("love.desktop"))
    desktop_file_fields = {
        "Type": "Application",
        "Name": config["name"],
        "Exec": "wrapper-love %F",
        "Categories": "Game;",
        "Terminal": "false",
        "Icon": "love",
    }
    if icon_file:
        desktop_file_fields["Icon"] = config["name"]

    if "linux" in config and "desktop_file_metadata" in config["linux"]:
        desktop_file_fields.update(config["linux"]["desktop_file_metadata"])

    with open(appdir("{}.desktop".format(config["name"])), "w") as f:
        f.write("[Desktop Entry]\n")
        for k, v in desktop_file_fields.items():
            f.write("{}={}\n".format(k, v))

    # shared libraries
    if target in config and "shared_libraries" in config[target]:
        for f in config[target]["shared_libraries"]:
            shutil.copy(f, appdir("usr/lib"))

    if should_build_artifact(config, target, "appimage", True):
        print("Creating new AppImage..")
        appimage_filename = "{}.AppImage".format(config["name"])
        if " " in appimage_filename:
            print(
                "Stripping whitespace in AppImage filename.\nThis is a known bug in the AppImage runtime: https://github.com/AppImage/AppImageKit/issues/678"
            )
            appimage_filename = appimage_filename.replace(" ", "")
        appimage_path = os.path.join(target_directory, appimage_filename)
        ret = subprocess.run(
            [get_appimagetool(), appdir_path, appimage_path], capture_output=True
        )
        if ret.returncode != 0:
            sys.exit("Could not create appimage: {}".format(ret.stderr.decode("utf-8")))
        print("Created {}".format(appimage_path))

    if should_build_artifact(config, target, "appdir", False):
        os.rename(appdir_path, os.path.join(target_directory, "AppDir"))
    else:
        print("Removing AppDir..")
        shutil.rmtree(appdir_path)
