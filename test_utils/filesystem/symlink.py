#
# Copyright(c) 2019-2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
import os

from core.test_run import TestRun
from test_tools.fs_utils import (
    readlink, create_directory, check_if_file_exists,
    check_if_symlink_exists, check_if_directory_exists
)
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
    def get_symlink(link_path, target, **params):
        if check_if_directory_exists(link_path):
            link_path = os.path.join(link_path, Symlink.get_name(target))
        else:
            parent_dir = Symlink.get_parent_dir(link_path)
            if not check_if_directory_exists(parent_dir):
                create_directory(parent_dir, True)

        file_exists = check_if_file_exists(link_path)
        is_symlink = check_if_symlink_exists(link_path)
        if file_exists and not is_symlink:
            raise FileExistsError(
                "Overwriting item that is not symbolic link could cause problems "
                "and will not be executed."
            )
        elif file_exists and is_symlink and not bool(params.get('force')):
            if readlink(link_path) == readlink(target):
                return Symlink(link_path)
            else:
                raise FileExistsError("Symbolic link already exists and leads to the other target.")
        else:
            cmd = f"ln -s {target} {link_path}"
            for param, value in params.items():
                cmd += f' --{str(param)} {str(value)}'
            TestRun.executor.run_expect_success(cmd)
            return Symlink(link_path)
