#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from core.test_run import TestRun
from test_tools.common.linux_command import LinuxCommand
from type_def.size import Size


class Ddrescue(LinuxCommand):
    def __init__(self):
        LinuxCommand.__init__(self, TestRun.executor, 'ddrescue')
        self.source_path = None
        self.destination_path = None
        self.param_name_prefix = "--"

    def source(self, value):
        self.source_path = value
        return self

    def destination(self, value):
        self.destination_path = value
        return self

    def reverse(self):
        return self.set_flags("reverse")

    def synchronous(self):
        return self.set_flags("synchronous")

    def direct(self):
        return self.set_flags("direct")

    def force(self):
        return self.set_flags("force")

    def block_size(self, value: Size):
        return self.set_param('sector-size', int(value.get_value()))

    def size(self, value: Size):
        return self.set_param('size', int(value.get_value()))

    def __str__(self):
        command = LinuxCommand.__str__(self)
        command += f" {self.source_path} {self.destination_path}"
        return command
