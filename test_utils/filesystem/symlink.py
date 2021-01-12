#
# Copyright(c) 2019-2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
import os

from core.test_run import TestRun
from test_tools.fs_utils import readlink, check_if_directory_exists, create_directory
from test_utils.filesystem.file import File


class Symlink(File):
    def __init__(self, full_path):
        File.__init__(self, full_path)

    def md5sum(self, binary=True):
        output = TestRun.executor.run(
            f"md5sum {'-b' if binary else ''} {self.get_target()}")
        if output.exit_code != 0:
            raise Exception(
                f"Md5sum command execution failed! {output.stdout}\n{output.stderr}")
        return output.stdout.split()[0]

    def get_target(self):
        return readlink(self.full_path)

    @staticmethod
    def new_symlink(link_name, path, target, force: bool = False):
        if not check_if_directory_exists(path):
            create_directory(path, True)
        full_path = os.path.join(path, link_name)
        TestRun.executor.run(f"ln -s {target} {full_path} {'-f' if force else ''}")
        return Symlink(full_path)
