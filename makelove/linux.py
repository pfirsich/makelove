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

from .util import fuse_files, tmpfile, parse_love_version, ask_yes_no
from .config import all_love_versions, should_build_artifact


def get_appimagetool_path():
    return os.path.join(appdirs.user_cache_dir("makelove"), "appimagetool")


def download_love_appimage(version):
    parsed_version = parse_love_version(version)

    # If we're building for 11.4 or later, use the official appimages.
    if (parsed_version[0], parsed_version[1]) >= (11, 4):
        return download_official_appimage(version)

    return download_legacy_appimage(version)


def download_official_appimage(version):
    url = f"https://api.github.com/repos/love2d/love/releases/tags/{version}"
    asset_data = get_release_asset_list(url)

    matching_asset = next(
        (a for a in asset_data if a["name"] == f"love-{version}-x86_64.AppImage"), None
    )

    if not matching_asset:
        sys.exit(f"Could not find AppImage to download for {version}!")

    return download_appimage(matching_asset["browser_download_url"])


def download_legacy_appimage(version):
    latest_url = "https://api.github.com/repos/pfirsich/love-appimages/releases/latest"
    asset_data = get_release_asset_list(latest_url)

    Asset = namedtuple("Asset", ["name", "version", "download_url"])
    appimages = []
    for asset in asset_data:
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

    return download_appimage(download_asset.download_url)


def get_release_asset_list(url):
    try:
        with urlopen(url) as req:
            data = json.loads(req.read().decode())
    except Exception as exc:
        sys.exit("Could not retrieve asset list: {}".format(exc))

    return data["assets"]


def download_appimage(url):
    try:
        appimage_path = tmpfile(suffix=".AppImage")
        print("Downloading {}..".format(url))
        urlretrieve(url, appimage_path)
        os.chmod(appimage_path, 0o755)
        return appimage_path
    except Exception as exc:
        sys.exit("Could not download löve appimage from {}: {}".format(url, exc))


def get_appimagetool():
    which_appimagetool = shutil.which("appimagetool")
    if which_appimagetool:
        return which_appimagetool
    else:
        appimagetool_path = os.path.join(
            appdirs.user_cache_dir("makelove"), "appimagetool"
        )
        if os.path.isfile(appimagetool_path):
            return appimagetool_path

        url = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        try:
            os.makedirs(os.path.dirname(appimagetool_path), exist_ok=True)
            print("Downloading '{}'..".format(url))
            urlretrieve(url, appimagetool_path)
            os.chmod(appimagetool_path, 0o755)
            return appimagetool_path
        except URLError as exc:
            sys.exit("Could not download appimagetool from {}: {}".format(url, exc))


def build_linux(config, version, target, target_directory, love_file_path):
    if target in config and "source_appimage" in config[target]:
        source_appimage = config[target]["source_appimage"]
    else:
        assert "love_version" in config
        # Download it every time, in case it's updated (I might make them smaller)
        # TODO: this shouldn't be necessary anymore if we're downloading from the official love repo
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

    game_name = config["name"]
    if " " in game_name:
        # If stripping is ever removed here, it still needs to be done for the AppImage file name, because of the mentioned bug.
        print(
            "Stripping whitespace from game name.\n"
            "Having spaces in the AppImage filename is problematic. This is a known bug in the AppImage runtime: https://github.com/AppImage/AppImageKit/issues/678\n"
            "Also having spaces in the filename of the fused executable inside the AppImage is problematic, because you can't specify it in the Exec field of the .desktop file.\n"
            "Similarly it leads to problems in the Icon field of the .desktop file.\n"
            "This essay shall justify my lazy attempt to address these problems and motivate you to remove spaces from your game name.\n"
            "It's 2022 at the time of writing this and the technology is just not there, I'm truly sorry."
        )
        game_name = game_name.replace(" ", "")

    # Copy .love into AppDir
    if os.path.isfile(appdir("usr/bin/wrapper-love")):
        # pfirsich-style AppImages - > simply copy the love file into the image
        print("Copying {} to {}".format(love_file_path, appdir("usr/bin")))
        shutil.copy2(love_file_path, appdir("usr/bin"))
        desktop_exec = "wrapper-love %F"
    elif os.path.isfile(appdir("bin/love")):
        # Official AppImages (since 11.4) -> fuse the .love file to the love binary
        fused_exe_path = appdir(f"bin/{game_name}")
        print(
            "Fusing {} and {} into {}".format(
                appdir("bin/love"), love_file_path, fused_exe_path
            )
        )
        fuse_files(fused_exe_path, appdir("bin/love"), love_file_path)
        os.chmod(fused_exe_path, 0o755)
        os.remove(appdir("bin/love"))
        desktop_exec = f"{game_name} %f"
    else:
        sys.exit(
            "Could not find love executable in AppDir. The AppImage has an unknown format."
        )

    # Copy icon
    icon_file = config.get("icon_file", None)
    if icon_file:
        os.remove(appdir("love.svg"))
        icon_ext = os.path.splitext(icon_file)[1]
        if icon_ext in [".png", ".svg", ".svgz", ".xpm"]:
            dest_icon_path = appdir(game_name + icon_ext)
            print("Copying {} to {}".format(icon_file, dest_icon_path))
            shutil.copy2(icon_file, dest_icon_path)
        else:
            dest_icon_path = appdir(f"{game_name}.png")
            print("Converting {} to {}".format(icon_file, dest_icon_path))
            try:
                img = Image.open(icon_file)
                img.save(dest_icon_path)
            except FileNotFoundError as exc:
                sys.exit("Could not find icon file: {}".format(exc))
            except UnidentifiedImageError as exc:
                sys.exit("Could not read icon file: {}".format(exc))
            except IOError as exc:
                sys.exit("Could not convert icon to .png: {}".format(exc))
    # appimagetool will create a symlink from the icon to .DirIcon
    os.remove(appdir(".DirIcon"))

    # replace love.desktop with [name].desktop
    # https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html
    os.remove(appdir("love.desktop"))
    desktop_file_fields = {
        "Type": "Application",
        "Name": config["name"],
        "Exec": desktop_exec,
        "Categories": "Game;",
        "Terminal": "false",
        "Icon": "love",
    }
    if icon_file:
        desktop_file_fields["Icon"] = game_name

    if "linux" in config and "desktop_file_metadata" in config["linux"]:
        desktop_file_fields.update(config["linux"]["desktop_file_metadata"])

    with open(appdir(f"{game_name}.desktop"), "w") as f:
        f.write("[Desktop Entry]\n")
        for k, v in desktop_file_fields.items():
            f.write("{}={}\n".format(k, v))

    # Shared libraries
    if target in config and "shared_libraries" in config[target]:
        if os.path.isfile(appdir("usr/lib/liblove.so")):
            # pfirsich-style AppImages
            so_target_dir = appdir("usr/lib")
        elif os.path.isfile(appdir("lib/liblove.so")):
            # Official AppImages (since 11.4)
            so_target_dir = appdir("lib/")
        else:
            sys.exit(
                "Could not find liblove.so in AppDir. The AppImage has an unknown format."
            )

        for f in config[target]["shared_libraries"]:
            shutil.copy(f, so_target_dir)

    # Rebuild AppImage
    if should_build_artifact(config, target, "appimage", True):
        print("Creating new AppImage..")
        appimage_path = os.path.join(target_directory, f"{game_name}.AppImage")
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
