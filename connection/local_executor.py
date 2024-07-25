#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#
import os
import subprocess
from datetime import timedelta

from connection.base_executor import BaseExecutor
from core.test_run import TestRun
from test_tools.fs_utils import copy
from test_utils.output import Output, CmdException


class LocalExecutor(BaseExecutor):
    def __init__(self):
        default_executable_path = "/bin/bash" if os.name == 'posix' else None
        self._executable_path = TestRun.config.get("executable_path", default_executable_path)

    def _execute(self, command, timeout):
        completed_process = subprocess.run(
            command,
            shell=True,
            executable=self._executable_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout.total_seconds(),
        )

        return Output(
            completed_process.stdout, completed_process.stderr, completed_process.returncode
        )

    def _rsync(
        self,
        src,
        dst,
        delete=False,
        symlinks=False,
        checksum=False,
        exclude_list=[],
        timeout: timedelta = timedelta(seconds=90),
        dut_to_controller=False,
    ):
        options = []

        if delete:
            options.append("--delete")
        if symlinks:
            options.append("--links")
        if checksum:
            options.append("--checksum")

        for exclude in exclude_list:
            options.append(f"--exclude {exclude}")

        output = self._execute(f'rsync -r {src} {dst} {" ".join(options)}', timeout)

        if output.exit_code:
            raise CmdException("rsync failed", output)

    def _copy(self, src, dst, dut_to_controller: bool):
        copy(src, dst, recursive=True)
