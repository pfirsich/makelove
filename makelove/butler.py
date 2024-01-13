#! /usr/bin/env python

import os
import subprocess
import sys

def publish(itchapp, config, version, targets, build_directory):
    if config.get("publish_love", False):
        targets = targets.copy()
        targets += ['love']
    for platform_target in targets:
        target_root = os.path.join(build_directory, platform_target)
        for file in os.listdir(target_root):
            fpath = os.path.join(target_root, file)
            if not os.path.isfile(fpath):
                continue
            
            cmd = "butler push {fpath} {itchapp}:{platform_target} --userversion {version}".format(
                fpath = fpath,
                version = version,
                itchapp = itchapp,
                platform_target = platform_target
            )
            subprocess.check_call(cmd.split(' '))

