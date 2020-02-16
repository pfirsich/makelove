import os
import sys
from urllib.request import urlretrieve, URLError
import shutil
import subprocess
import re

from PIL import Image, UnidentifiedImageError
import appdirs

appimage_urls = {
    "11.3": "https://bitbucket.org/rude/love/downloads/love-11.3-x86_64.AppImage",
    "11.2": "https://bitbucket.org/rude/love/downloads/love-11.2-x86_64.AppImage",
    "11.1": "https://bitbucket.org/rude/love/downloads/love-11.1-linux-x86_64.AppImage",
    "11.0": "https://bitbucket.org/rude/love/downloads/love-11.0-linux-x86_64.AppImage",
}


def get_default_source_appimage_path(version):
    return os.path.join(
        appdirs.user_cache_dir("makelove"), "love-appimages", version, "love.AppImage"
    )


def get_appimagetool_path():
    return os.path.join(appdirs.user_cache_dir("makelove"), "appimagetool")


def download_love_appimage(version):
    appimage_path = get_default_source_appimage_path(version)
    url = appimage_urls[version]
    try:
        os.makedirs(os.path.dirname(appimage_path), exist_ok=True)
        urlretrieve(appimage_urls[version], appimage_path)
        os.chmod(appimage_path, 0o755)
    except URLError as exc:
        sys.exit("Could not download löve appimage from {}: {}".format(url, exc))


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


def build_linux(args, config, target, build_directory, love_file_path):
    if target in config and "source_appimage" in config[target]:
        source_appimage = config[target]["source_appimage"]
    else:
        assert "love_version" in config
        love_version = config["love_version"]
        if not love_version in appimage_urls.keys():
            sys.exit(
                "Currently there are no downloadable AppImages for löve {}".format(
                    love_version
                )
            )
        source_appimage = get_default_source_appimage_path(love_version)
        if not os.path.isfile(source_appimage):
            print("Downloading löve AppImage for version {}..".format(love_version))
            download_love_appimage(love_version)

    target_directory = os.path.join(build_directory, target)
    os.makedirs(target_directory)

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
    shutil.copy2(love_file_path, appdir_path)

    # Modify entry script 'love' (and save under new name)
    with open(appdir("love")) as f:
        entry_script = f.read()
    appimage_love_path = "${LOVE_LAUNCHER_LOCATION}/" + os.path.basename(love_file_path)
    entry_script = replace_single(entry_script, "$@", appimage_love_path)
    os.remove(appdir("love"))
    with open(appdir(config["name"]), "w") as f:
        f.write(entry_script)
    os.chmod(appdir(config["name"]), 0o755)

    # Patch wrapper-love
    wrapper_path = appdir("usr/bin/wrapper-love")
    with open(wrapper_path) as f:
        wrapper_script = f.read()
    wrapper_script = replace_single(
        wrapper_script, "${APPIMAGE_DIR}/love", "${APPIMAGE_DIR}/" + config["name"]
    )
    with open(wrapper_path, "w") as f:
        f.write(wrapper_script)
    os.chmod(wrapper_path, 0o755)

    # replace love.desktop with [name].desktop
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

    os.remove(appdir("love.desktop"))
    desktop_file_fields = {
        "Type": "Application",
        "Name": config["name"],
        "Exec": "wrapper-love %f",
        "Categories": "Game;",
        "Terminal": "false",
        "Icon": "love",
    }
    if icon_file:
        desktop_file_fields["Icon"] = config["name"]

    with open(appdir("{}.desktop".format(config["name"])), "w") as f:
        f.write("[Desktop Entry]\n")
        for k, v in desktop_file_fields.items():
            f.write("{}={}\n".format(k, v))

    if "appimage" in config and config["appimage"].get("keep_appdir", False):
        print("Done. ('keep_appdir' is true)")
        return

    print("Creating new AppImage..")
    appimage_path = os.path.join(target_directory, "{}.AppImage".format(config["name"]))
    ret = subprocess.run(
        [get_appimagetool(), appdir_path, appimage_path], capture_output=True
    )
    if ret.returncode != 0:
        sys.exit("Could not create appimage: {}".format(ret.stderr.decode("utf-8")))
    print("Created {}".format(appimage_path))
