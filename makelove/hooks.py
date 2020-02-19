import subprocess
import tempfile
import copy
import shlex
import sys
import os

import toml

from .config import get_config
from .util import tmpfile


def execute_hook(command, config, version, targets, build_directory):
    tmp_config_path = tmpfile(suffix=".toml")

    with open(tmp_config_path, "w") as f:
        toml.dump(config, f)

    env = {
        "MAKELOVE_TEMP_CONFIG": tmp_config_path,
        "MAKELOVE_VERSION": version or "",
        "MAKELOVE_TARGETS": ",".join(targets),
        "MAKELOVE_BUILD_DIRECTORY": build_directory,
    }

    command_replaced = command.format(
        version=version or "", build_directory=build_directory
    )

    try:
        subprocess.run(command_replaced, shell=True, check=True, env=env)
    except Exception as e:
        sys.exit("Hook '{}' failed: {}".format(command, e))

    new_config = get_config(tmp_config_path)
    os.remove(tmp_config_path)
    return new_config
