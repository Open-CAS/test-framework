#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import subprocess
from connection.base_executor import BaseExecutor
from utils.output import Output
from datetime import timedelta


class LocalExecutor(BaseExecutor):
    def execute(self, command, timeout: timedelta = timedelta(hours = 1)):
        completed_process = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout.total_seconds())

        output = Output(
            completed_process.stdout.decode("utf-8"),
            completed_process.stderr.decode("utf-8"),
            completed_process.returncode)
        return output
