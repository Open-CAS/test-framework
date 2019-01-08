#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from base_executor import BaseExecutor


class DummyExecutor(BaseExecutor):
    def execute(self, command):
        print(command)
