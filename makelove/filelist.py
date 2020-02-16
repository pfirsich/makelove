import fnmatch
import os
import re


class FileList(object):
    def __init__(self, path):
        self.dir = path
        self.full_list = []
        self.file_list = set()
        for root, _dirs, files in os.walk(self.dir):
            for fname in files:
                self.full_list.append(os.path.join(root, fname))

    def include(self, pattern):
        matches = set(fnmatch.filter(self.full_list, pattern))
        if len(matches) == 0:
            print("Warning: Pattern '{}' does not match any files")
        self.file_list |= matches

    def include_raw(self, item):
        path = os.path.join(".", os.path.normpath(item))
        if os.path.isfile(path):
            self.file_list.add(path)
        else:
            raise FileNotFoundError

    def exclude(self, pattern):
        matches = set(fnmatch.filter(self.file_list, pattern))
        if len(matches) == 0:
            print("Warning: Pattern '{}' does not match any files".format(pattern))
        self.file_list -= matches

    def __iter__(self):
        for path in sorted(self.file_list):
            yield path
