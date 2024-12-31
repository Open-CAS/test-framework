#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2023-2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from datetime import timedelta

from test_tools import fs_tools
from test_tools.dd import Dd
from test_tools.fs_tools import read_file, write_file, ls_item, parse_ls_output, remove, \
    check_if_directory_exists
from test_utils.filesystem.fs_item import FsItem
from type_def.size import Size


class File(FsItem):
    def __init__(self, full_path):
        FsItem.__init__(self, full_path)

    def compare(self, other_file, timeout: timedelta = timedelta(minutes=30)):
        return fs_tools.compare(str(self), str(other_file), timeout)

    def diff(self, other_file, timeout: timedelta = timedelta(minutes=30)):
        return fs_tools.diff(str(self), str(other_file), timeout)

    def md5sum(self, binary=True, timeout: timedelta = timedelta(minutes=30)):
        return fs_tools.md5sum(str(self), binary, timeout)

    def crc32sum(self, timeout: timedelta = timedelta(minutes=30)):
        return fs_tools.crc32sum(str(self), timeout)

    def read(self):
        return read_file(str(self))

    def write(self, content, overwrite: bool = True):
        write_file(str(self), content, overwrite)
        self.refresh_item()

    def get_properties(self):
        return FileProperties(self)

    @staticmethod
    def create_file(path: str):
        fs_tools.create_file(path)
        output = ls_item(path)
        return parse_ls_output(output)[0]

    def padding(self, size: Size):
        dd = Dd().input("/dev/zero").output(self).count(1).block_size(size)
        dd.run()
        self.refresh_item()

    def remove(self, force: bool = False, ignore_errors: bool = False):
        remove(str(self), force=force, ignore_errors=ignore_errors)

    def copy(self,
             destination,
             force: bool = False,
             recursive: bool = False,
             dereference: bool = False,
             timeout: timedelta = timedelta(minutes=30)):
        fs_tools.copy(str(self), destination, force, recursive, dereference, timeout)
        if check_if_directory_exists(destination):
            path = f"{destination}{'/' if destination[-1] != '/' else ''}{self.name}"
        else:
            path = destination
        output = ls_item(path)
        return parse_ls_output(output)[0]


class FileProperties:
    def __init__(self, file):
        file = parse_ls_output(ls_item(file.full_path))[0]
        self.full_path = file.full_path
        self.parent_dir = FsItem.get_parent_dir(self.full_path)
        self.name = FsItem.get_name(self.full_path)
        self.modification_time = file.modification_time
        self.owner = file.owner
        self.group = file.group
        self.permissions = file.permissions
        self.size = file.size

    def __eq__(self, other):
        return (self.permissions == other.permissions and self.size == other.size
                and self.owner == other.owner and self.group == other.group
                and self.name == other.name)
