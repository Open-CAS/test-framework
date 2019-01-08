#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import utils.linux_command as linux_comm
import utils.size as size
import connection.base_executor as executor
from multimethod import multimethod


class Dd(linux_comm.LinuxCommand):
    def __init__(self, command_executor: executor.BaseExecutor):
        linux_comm.LinuxCommand.__init__(self, command_executor, 'dd')

    @multimethod
    def block_size(self, value: int):
        return self.set_param('bs', value)

    @multimethod
    def block_size(self, value: size.Size):
        return self.block_size(int(value.get_value(size.Unit.Byte)))

    def count(self, value):
        return self.set_param('count', value)

    def input(self, value):
        return self.set_param('if', value)

    def iflag(self, *values):
        return self.set_param('iflag', *values)

    def oflag(self, *values):
        return self.set_param('oflag', *values)

    def output(self, value):
        return self.set_param('of', value)
