#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from test_utils.filesystem.fs_item import FsItem
from test_tools import fs_utils
from test_package.test_properties import TestProperties


class File(FsItem):
    def __init__(self, full_path):
        FsItem.__init__(self, full_path)

    def compare(self, other_file, options=None):
        return fs_utils.compare(str(self), str(other_file), options)

    def diff(self, other_file, options=None):
        return fs_utils.diff(str(self), str(other_file), options)

    def md5sum(self, binary=True):
        output = TestProperties.executor.execute(
            f"md5sum {'-b' if binary else ''} {self.full_path}")
        if output.exit_code != 0:
            raise Exception(f"Md5sum command execution failed! {output.stdout}\n{output.stderr}")
        return output.stdout.split()[0]

    def read(self):
        return fs_utils.read_file(str(self))

    def write(self, content, overwrite: bool = True):
        fs_utils.write_file(str(self), content, overwrite)

    @staticmethod
    def create_file(path):
        if fs_utils.create_file(path):
            output = fs_utils.ls(f"{path}")
            return fs_utils.parse_ls_output(output)[0]
        else:
            raise Exception(f"Failed to create file {path}.")

    def copy(self,
             destination,
             force: bool = False,
             recursive: bool = False,
             dereference: bool = False):
        if fs_utils.copy(str(self), destination, force, recursive, dereference):
            if fs_utils.check_if_directory_exists(destination):
                path = f"{destination}{'/' if destination[-1] != '/' else ''}{self.name}"
            else:
                path = destination
            output = fs_utils.ls(f"{path}")
            return fs_utils.parse_ls_output(output)[0]
        return None
