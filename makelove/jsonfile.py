import json
import os


class JsonFile(object):
    def __init__(self, path, indent=None):
        self.path = path
        self.indent = indent

    def __enter__(self):
        if os.path.isfile(self.path):
            with open(self.path) as f:
                self.build_log = json.load(f)
        else:
            self.build_log = []
        return self.build_log

    def __exit__(self, type, value, traceback):
        with open(self.path, "w") as f:
            json.dump(self.build_log, f, indent=self.indent)
