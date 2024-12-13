#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from core.test_run import TestRun
from test_tools import fs_tools
from test_tools.fs_tools import check_if_directory_exists, parse_ls_output, ls_item, ls
from test_utils.filesystem.fs_item import FsItem


class Directory(FsItem):
    def __init__(self, full_path):
        FsItem.__init__(self, full_path)

    def ls(self):
        output = ls(self.full_path)
        return parse_ls_output(output, self.full_path)

    @staticmethod
    def create_directory(path: str, parents: bool = False):
        fs_tools.create_directory(path, parents)
        output = ls_item(path)
        return parse_ls_output(output)[0]

    @staticmethod
    def create_temp_directory(parent_dir_path: str = "/tmp"):
        command = f"mktemp --directory --tmpdir={parent_dir_path}"
        output = TestRun.executor.run_expect_success(command)
        if not check_if_directory_exists(output.stdout):
            TestRun.LOGGER.exception("'mktemp' succeeded, but created directory does not exist")
        return Directory(output.stdout)
