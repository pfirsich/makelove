import subprocess
import tempfile
import copy
import shlex
import sys
import os

import toml

from config import get_config


def execute_hook(command, config):
    tmp_config = tempfile.NamedTemporaryFile(mode="w+", suffix=".toml.tmp")
    toml.dump(config, tmp_config)
    filename = tmp_config.name
    tmp_config.close()

    try:
        subprocess.run(
            shlex.split(command), check=True, env={"MAKELOVE_TEMP_CONFIG": filename}
        )
    except Exception as e:
        sys.exit("Hook '{}' failed: {}".format(command, e))

    new_config = get_config(filename)
    os.remove(filename)
    return new_config
