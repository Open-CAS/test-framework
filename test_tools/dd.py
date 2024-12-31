#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import type_def.size as size
from core.test_run import TestRun
from test_tools.common.linux_command import LinuxCommand


class Dd(LinuxCommand):
    def __init__(self):
        LinuxCommand.__init__(self, TestRun.executor, 'dd')

    def block_size(self, value: size.Size):
        return self.set_param('bs', int(value.get_value()))

    def count(self, value):
        return self.set_param('count', value)

    def input(self, value):
        return self.set_param('if', value)

    def iflag(self, *values):
        return self.set_param('iflag', *values)

    def oflag(self, *values):
        return self.set_param('oflag', *values)

    def conv(self, *values):
        return self.set_param('conv', *values)

    def output(self, value):
        return self.set_param('of', value)

    def seek(self, value):
        return self.set_param('seek', value)

    def skip(self, value):
        return self.set_param('skip', value)
