import html
import json
import os
import sys
import uuid
from pathlib import Path
from zipfile import ZipFile
from urllib.request import urlretrieve, URLError

from .util import eprint, get_default_love_binary_dir, get_download_url


def download_love(version, platform):
    """
    Note, mac builds are stored as zip files because extracting them
    would lose data about symlinks when building on windows
    """
    if version != "11.3":
        eprint("LoveJS builds are only available for Löve 11.3+")
        sys.exit(1)

    target_path = get_default_love_binary_dir(version, platform)
    print("Downloading love binaries to: '{}'".format(target_path))

    os.makedirs(target_path, exist_ok=True)
    try:
        download_url = "https://github.com/Davidobot/love.js/archive/master.zip"
        print("Downloading '{}'..".format(download_url))
        urlretrieve(download_url, os.path.join(target_path, "love.zip"))
    except URLError as exc:
        eprint("Could not download löve: {}".format(exc))
        eprint(
            "If there is in fact no download on GitHub for this version, specify 'love_binaries' manually."
        )
        sys.exit(1)
    print("Download complete")


def render_mustache(tmpl, cx):
    tmpl = tmpl.decode('utf-8')
    for k, v in cx.items():
        tmpl = tmpl.replace("{{{" + k + "}}}", str(v))
        tmpl = tmpl.replace("{{" + k + "}}", html.escape(str(v)))
    return tmpl.encode('utf-8')


def build_lovejs(config, version, target, target_directory, love_file_path):
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
        game_data = love_zip.read()
        fileMetadata = [{
            "filename": "/game.love",
            "crunched": 0,
            "start": 0,
            "end": len(game_data),
            "audio": False,
        }]

        prefix = Path(love_binary_zip.filelist[0].filename)
        app_zip.writestr(f"{config['name']}/index.html", render_mustache(
            love_binary_zip.read(str(prefix / "src" / "compat"/ "index.html")),
            {
                "title": config.get("lovejs", {}).get("title", config["name"]),
                "arguments": json.dumps(['./game.love']),
                "memory": int(config.get('lovejs', {}).get("memory", "20000000")),
            }
        ))
        app_zip.writestr(
            f"{config['name']}/game.js",
            render_mustache(
                love_binary_zip.read(str(prefix / "src" / "game.js")),
                {
                    "create_file_paths": "",
                    "metadata": json.dumps({
                        "package_uuid": uuid.uuid4().hex,
                        "remote_package_size": len(game_data),
                        "files": fileMetadata,
                    }),
                }
            )
        )
        app_zip.writestr(f"{config['name']}/game.data", game_data)
        app_zip.writestr(
            f"{config['name']}/love.js",
            love_binary_zip.read(str(prefix / "src" / "compat" / "love.js"))
        )
        app_zip.writestr(
            f"{config['name']}/love.wasm",
            love_binary_zip.read(str(prefix / "src" / "compat" / "love.wasm"))
        )
        app_zip.writestr(
            f"{config['name']}/theme/love.css",
            love_binary_zip.read(str(prefix / "src" / "compat" / "theme" / "love.css"))
        )
        app_zip.writestr(
            f"{config['name']}/theme/bg.png",
            love_binary_zip.read(str(prefix / "src" / "compat" / "theme" / "bg.png"))
        )
