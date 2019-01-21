#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from connection.base_executor import BaseExecutor


class DummyExecutor(BaseExecutor):
    def execute(self, command, timeout=None):
        print(command)
