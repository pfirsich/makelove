import fnmatch
import os
import re
import sys


class FileList(object):
    def __init__(self, path):
        self.dir = path
        self.full_list = []
        self.file_list = set()
        dirs_seen = set()
        for root, dirs, files in os.walk(self.dir, followlinks=True):
            for d in dirs:
                realpath = os.path.realpath(os.path.join(root, d))
                if realpath in dirs_seen:
                    sys.exit("Detected infinite recursion while walking directory")
                dirs_seen.add(realpath)

            for fname in files:
                path = os.path.join(root, fname)
                self.full_list.append(path)

    def include(self, pattern):
        matches = set(fnmatch.filter(self.full_list, pattern))
        if len(matches) == 0:
            print("Warning: Pattern '{}' does not match any files".format(pattern))
        self.file_list |= matches

    def include_raw(self, item):
        path = os.path.join(".", os.path.normpath(item))
        if os.path.isfile(path):
            self.file_list.add(path)
        # we ignore directories (which git doesn't track) and symlinks (which git does track!)
        elif not os.path.exists(path):
            raise FileNotFoundError
        else:
            print("'{}' is not a file!".format(path))

    def exclude(self, pattern):
        matches = set(fnmatch.filter(self.file_list, pattern))
        if len(matches) == 0:
            print("Warning: Pattern '{}' does not match any files".format(pattern))
        self.file_list -= matches

    def __iter__(self):
        for path in sorted(self.file_list):
            yield path
