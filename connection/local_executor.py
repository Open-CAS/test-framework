#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import subprocess
from datetime import timedelta

from connection.base_executor import BaseExecutor
from core.test_run import TestRun
from test_utils.output import Output


class LocalExecutor(BaseExecutor):
    def _execute(self, command, timeout):
        bash_path = TestRun.config.get("bash_path", "/bin/bash")

        completed_process = subprocess.run(
            command,
            shell=True,
            executable=bash_path,
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
        bash_path = TestRun.config.get("bash_path", "/bin/bash")

        if delete:
            options.append("--delete")
        if symlinks:
            options.append("--links")
        if checksum:
            options.append("--checksum")

        for exclude in exclude_list:
            options.append(f"--exclude {exclude}")

        completed_process = subprocess.run(
            f'rsync -r {src} {dst} {" ".join(options)}',
            shell=True,
            executable=bash_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout.total_seconds(),
        )

        if completed_process.returncode:
            raise Exception(f"rsync failed:\n{completed_process}")
