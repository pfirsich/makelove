import subprocess
import tempfile
import copy
import shlex
import sys
import os

import toml

from config import get_config


def execute_hook(command, args, config):
    (fd, tmp_config_path) = tempfile.mkstemp(suffix=".toml")
    os.close(fd)

    with open(tmp_config_path, "w") as f:
        toml.dump(config, f)

    env = {
        "MAKELOVE_TEMP_CONFIG": tmp_config_path,
        "MAKELOVE_VERSION": args.version if args.version != None else "",
    }

    try:
        subprocess.run(command, shell=True, check=True, env=env)
    except Exception as e:
        os.remove(tmp_config_path)
        sys.exit("Hook '{}' failed: {}".format(command, e))

    new_config = get_config(tmp_config_path)
    os.remove(tmp_config_path)
    return new_config
