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
        self.file_list |= set(fnmatch.filter(self.full_list, pattern))

    def include_raw(self, item):
        path = os.path.join(".", os.path.normpath(item))
        if os.path.isfile(path):
            self.file_list.add(path)
        else:
            raise FileNotFoundError

    def exclude(self, pattern):
        self.file_list -= set(fnmatch.filter(self.file_list, pattern))

    def __iter__(self):
        for path in sorted(self.file_list):
            yield path
