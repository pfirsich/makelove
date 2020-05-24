import io
import os
import shutil
import struct
import sys
from datetime import datetime
from zipfile import ZipFile
from urllib.request import urlopen, urlretrieve, URLError

from PIL import Image

from .util import eprint, tmpfile
from .windows import get_default_love_binary_dir, get_download_url


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
        with urlopen(download_url) as response:
            with open(os.path.join(target_path, "love.zip"), 'wb') as target_f:
                target_f.write(response.read())
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
        raise ValueError('Invalid image size, discarded: %d x %d.' % (width, height))

    sizetotypes = {
        16: [b'icp4'],  # 16x16   std only  (no 8x8@2x)
        32: [b'icp5', b'ic11'],  # 32x32   std -AND- 16x16@2x   high
        64: [b'icp6', b'ic12'],  # 64x64   std -AND- 32x32@2x   high
        128: [b'ic07'],  # 128x128 std only  (no 64x64@2x)
        256: [b'ic08', b'ic13'],  # 256x256 std -AND- 128x128@2x high
        512: [b'ic09', b'ic14'],  # 512x512 std -AND- 256x256@2x high
        1024: [b'ic10']  # 1024x1024 (10.7) = 512x512@2x high (10.8)
    }

    imagedatas = []
    for size_px, icontypes in sizetotypes.items():
        img = icon_image.resize((size_px, size_px), Image.LANCZOS)
        with io.BytesIO() as img_data_f:
            img.save(img_data_f, 'png')
            for icontype in icontypes:
                imagedatas.append([icontype, img_data_f.getvalue()])

    # 1) HEADER: 4-byte "magic" + 4-byte filesize (including header itself)

    filelen = 8 + sum(
        len(imagedata) + 8
        for (_, imagedata) in sorted(imagedatas)
    )
    iconfile.write(b'icns')
    iconfile.write(struct.pack('>I', filelen))

    # 2) IMAGE TYPE+LENGTH+BYTES: packed into rest of icon file sequentially

    for icontype, imagedata in imagedatas:
        # data length includes type and length fields (4+4)
        iconfile.write(icontype)  # 4 byte type
        iconfile.write(struct.pack('>I', 8 + len(imagedata)))  # 4-byte length
        iconfile.write(imagedata)  # and the image


def get_game_icon_content(config):
    # Mac icons are not supposed to take up the full image area and generally
    # have shadows, etc - allow users to provide a different design but fall
    # back on the generic icon_file setting
    icon_file = config.get("macos", {}).get('icon_file')
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

    with io.BytesIO() as icns_f, open(icon_file, 'rb') as icon_img_f:
        icon_key = f"{config['name']}.app/Contents/Resources/icon-{config['name']}.icns"
        if icon_file.lower().endswith('.png'):
            make_icns(icns_f, icon_img_f)
            return icns_f.getvalue()
        else:
            return icon_img_f.read()


def get_info_plist_content(config, version):
    metadata = {}
    if "macos" in config and "app_metadata" in config["macos"]:
        metadata = config["macos"]["app_metadata"]

    metadata.setdefault('FileVersion', version or config['love_version'])
    metadata.setdefault('ProductName', config['name'])
    metadata.setdefault('LegalCopyright', "© 2006-2020 LÖVE Development Team")
    metadata.setdefault('BundleIdentifier', f"tld.{config['name']}")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>BuildMachineOSBuild</key>
            <string>19B88</string>
            <key>CFBundleDevelopmentRegion</key>
            <string>English</string>
            <key>CFBundleExecutable</key>
            <string>love</string>
            <key>CFBundleIconFile</key>
            <string>icon.icns</string>
            <key>CFBundleIdentifier</key>
            <string>{metadata['BundleIdentifier']}</string>
            <key>CFBundleInfoDictionaryVersion</key>
            <string>6.0</string>
            <key>CFBundleName</key>
            <string>{metadata['ProductName']}</string>
            <key>CFBundlePackageType</key>
            <string>APPL</string>
            <key>CFBundleShortVersionString</key>
            <string>{metadata['FileVersion']}</string>
            <key>CFBundleSignature</key>
            <string>LoVe</string>
            <key>CFBundleSupportedPlatforms</key>
            <array>
                <string>MacOSX</string>
            </array>
            <key>DTCompiler</key>
            <string>com.apple.compilers.llvm.clang.1_0</string>
            <key>DTPlatformBuild</key>
            <string>11C504</string>
            <key>DTPlatformVersion</key>
            <string>GM</string>
            <key>DTSDKBuild</key>
            <string>19B90</string>
            <key>DTSDKName</key>
            <string>macosx10.15</string>
            <key>DTXcode</key>
            <string>1130</string>
            <key>DTXcodeBuild</key>
            <string>11C504</string>
            <key>LSApplicationCategoryType</key>
            <string>public.app-category.games</string>
            <key>LSMinimumSystemVersion</key>
            <string>10.7</string>
            <key>NSHighResolutionCapable</key>
            <true/>
            <key>NSHumanReadableCopyright</key>
            <string>{metadata['LegalCopyright']}</string>
            <key>NSPrincipalClass</key>
            <string>NSApplication</string>
            <key>NSSupportsAutomaticGraphicsSwitching</key>
            <false/>
        </dict>
        </plist>
    """


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

    src = os.path.join(love_binaries, 'love.zip')
    dst = os.path.join(target_directory, f"{config['name']}-{target}.zip")
    with open(src, 'rb') as lovef, ZipFile(lovef) as loveBinaryZip, \
            open(dst, 'wb+') as outf, ZipFile(outf, mode='w') as appZip, \
            open(love_file_path, 'rb') as loveZip:

        for zipinfo in loveBinaryZip.infolist():
            if not zipinfo.filename.startswith("love.app/"):
                raise RuntimeError("Got bad or unxpexpectedly formatted love zip file")

            # for getting files out of the original love archive
            orig_filename = zipinfo.filename

            # rename app from "love.app" to "cool game.app"
            zipinfo.filename = config['name'] + zipinfo.filename[len("love"):]

            # makes the modification time on the app correct
            zipinfo.date_time = tuple(datetime.now().timetuple()[:6])

            if orig_filename == "love.app/Contents/Resources/GameIcon.icns":
                continue  # not needed for game distributions
            elif orig_filename == "love.app/Contents/Resources/Assets.car":
                continue  # not needed for game distributions
            elif orig_filename == "love.app/Contents/Resources/OS X AppIcon.icns":
                zipinfo = f"{config['name']}.app/Contents/Resources/icon.icns"  # hack: change name to make macos pick up the icon
                content = get_game_icon_content(config)
                if not content:
                    content = loveBinaryZip.read(orig_filename)
            elif orig_filename == 'love.app/Contents/Info.plist':
                appZip.writestr(zipinfo.filename, get_info_plist_content(config, version))
                continue
            else:
                content = loveBinaryZip.read(orig_filename)

            appZip.writestr(zipinfo, content)

        loveZipKey = f"{config['name']}.app/Contents/Resources/{config['name']}.love"
        appZip.writestr(loveZipKey, loveZip.read())
