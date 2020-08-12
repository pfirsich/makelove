import io
import os
import plistlib
import struct
import sys
from datetime import datetime
from zipfile import ZipFile
from urllib.request import urlopen, urlretrieve, URLError

from PIL import Image

from .util import eprint, get_default_love_binary_dir, get_download_url


def download_love(version, platform):
    """
    Note, mac builds are stored as zip files because extracting them
    would lose data about symlinks when building on windows
    """
    target_path = get_default_love_binary_dir(version, platform)
    print("Downloading love binaries to: '{}'".format(target_path))

    os.makedirs(target_path, exist_ok=True)
    try:
        download_url = get_download_url(version, platform)
        print("Downloading '{}'..".format(download_url))
        urlretrieve(download_url, os.path.join(target_path, "love.zip"))
    except URLError as exc:
        eprint("Could not download löve: {}".format(exc))
        eprint(
            "If there is in fact no download on GitHub for this version, specify 'love_binaries' manually."
        )
        sys.exit(1)
    print("Download complete")


def write_file(pkg, name, content):
    if isinstance(pkg, str):
        mode = "w" if isinstance(content, str) else "wb"
        with open(name, mode) as f:
            f.write(content)
    elif isinstance(pkg, ZipFile):
        pkg.writestr(name, content)


def make_icns(iconfile, icon_image_file):
    """
    iconfile: an open file to write the ICNS file contents into (mode: wb)
    icon_image: a PIL.Image object of the icon image

    Based on code from learn-python.com:
      https://learning-python.com/cgi/showcode.py?name=pymailgui-products/unzipped/build/build-icons/iconify.py
    """
    icon_image = Image.open(icon_image_file)

    # must all be square (width=height) and of standard pixel sizes
    width, height = icon_image.size  # a 2-tuple
    if width != height:
        eprint("Invalid image size, discarded: %d x %d." % (width, height))
        sys.exit(1)

    sizetotypes = {
        16: [b"icp4"],  # 16x16   std only  (no 8x8@2x)
        32: [b"icp5", b"ic11"],  # 32x32   std -AND- 16x16@2x   high
        64: [b"icp6", b"ic12"],  # 64x64   std -AND- 32x32@2x   high
        128: [b"ic07"],  # 128x128 std only  (no 64x64@2x)
        256: [b"ic08", b"ic13"],  # 256x256 std -AND- 128x128@2x high
        512: [b"ic09", b"ic14"],  # 512x512 std -AND- 256x256@2x high
        1024: [b"ic10"],  # 1024x1024 (10.7) = 512x512@2x high (10.8)
    }

    imagedatas = []
    for size_px, icontypes in sizetotypes.items():
        img = icon_image.resize((size_px, size_px), Image.LANCZOS)
        with io.BytesIO() as img_data_f:
            img.save(img_data_f, "png")
            for icontype in icontypes:
                imagedatas.append([icontype, img_data_f.getvalue()])

    # 1) HEADER: 4-byte "magic" + 4-byte filesize (including header itself)

    filelen = 8 + sum(len(imagedata) + 8 for (_, imagedata) in sorted(imagedatas))
    iconfile.write(b"icns")
    iconfile.write(struct.pack(">I", filelen))

    # 2) IMAGE TYPE+LENGTH+BYTES: packed into rest of icon file sequentially

    for icontype, imagedata in imagedatas:
        # data length includes type and length fields (4+4)
        iconfile.write(icontype)  # 4 byte type
        iconfile.write(struct.pack(">I", 8 + len(imagedata)))  # 4-byte length
        iconfile.write(imagedata)  # and the image


def get_game_icon_content(config):
    # Mac icons are not supposed to take up the full image area and generally
    # have shadows, etc - allow users to provide a different design but fall
    # back on the generic icon_file setting
    icon_file = config.get("macos", {}).get("icon_file")
    if icon_file is None:
        icon_file = config.get("icon_file", None)
    elif not os.path.isfile(icon_file):
        sys.exit(f"Couldn't find macOS icon_file at {icon_file}")

    if icon_file is None:
        icon_file = config.get("icon_file", None)
    elif not os.path.isfile(icon_file):
        sys.exit(f"Couldn't find icon_file at {icon_file}")

    if not icon_file:
        return False

    with io.BytesIO() as icns_f, open(icon_file, "rb") as icon_img_f:
        icon_key = f"{config['name']}.app/Contents/Resources/icon-{config['name']}.icns"
        if icon_file.lower().endswith(".png"):
            make_icns(icns_f, icon_img_f)
            return icns_f.getvalue()
        else:
            return icon_img_f.read()


def get_info_plist_content(config, version):
    plist = {
        "BuildMachineOSBuild": "19B88",
        "CFBundleDevelopmentRegion": "English",
        "CFBundleExecutable": "love",
        "CFBundleIconFile": "icon.icns",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundlePackageType": "APPL",
        "CFBundleSignature": "LoVe",
        "CFBundleSupportedPlatforms": ["MacOSX"],
        "DTCompiler": "com.apple.compilers.llvm.clang.1_0",
        "DTPlatformBuild": "11C504",
        "DTPlatformVersion": "GM",
        "DTSDKBuild": "19B90",
        "DTSDKName": "macosx10.15",
        "DTXcode": "1130",
        "DTXcodeBuild": "11C504",
        "LSApplicationCategoryType": "public.app-category.games",
        "LSMinimumSystemVersion": "10.7",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "NSSupportsAutomaticGraphicsSwitching": False,
        # dynamic defaults
        "CFBundleShortVersionString": version or config["love_version"],
        "CFBundleName": config["name"],
        "NSHumanReadableCopyright": "© 2006-2020 LÖVE Development Team",
        "CFBundleIdentifier": f"tld.yourgamename",
    }

    if "macos" in config and "app_metadata" in config["macos"]:
        metadata = config["macos"]["app_metadata"]
        plist.update(metadata)

    return plistlib.dumps(plist)


def build_macos(config, version, target, target_directory, love_file_path):
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

    src = os.path.join(love_binaries, "love.zip")
    dst = os.path.join(target_directory, f"{config['name']}-{target}.zip")
    with open(src, "rb") as lovef, ZipFile(lovef) as love_binary_zip, open(
        dst, "wb+"
    ) as outf, ZipFile(outf, mode="w") as app_zip, open(
        love_file_path, "rb"
    ) as love_zip:

        for zipinfo in love_binary_zip.infolist():
            if not zipinfo.filename.startswith("love.app/"):
                eprint("Got bad or unxpexpectedly formatted love zip file")
                sys.exit(1)

            # for getting files out of the original love archive
            orig_filename = zipinfo.filename

            # rename app from "love.app" to "cool game.app"
            zipinfo.filename = config["name"] + zipinfo.filename[len("love") :]

            # makes the modification time on the app correct
            zipinfo.date_time = tuple(datetime.now().timetuple()[:6])

            if orig_filename == "love.app/Contents/Resources/GameIcon.icns":
                continue  # not needed for game distributions
            elif orig_filename == "love.app/Contents/Resources/Assets.car":
                continue  # not needed for game distributions
            elif orig_filename == "love.app/Contents/Resources/OS X AppIcon.icns":
                # hack: change name to make macos pick up the icon
                zipinfo = f"{config['name']}.app/Contents/Resources/icon.icns"

                content = get_game_icon_content(config)
                if not content:
                    content = love_binary_zip.read(orig_filename)
            elif orig_filename == "love.app/Contents/Info.plist":
                app_zip.writestr(
                    zipinfo.filename, get_info_plist_content(config, version)
                )
                continue
            else:
                content = love_binary_zip.read(orig_filename)

            app_zip.writestr(zipinfo, content)

        loveZipKey = f"{config['name']}.app/Contents/Resources/{config['name']}.love"
        app_zip.writestr(loveZipKey, love_zip.read())
