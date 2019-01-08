#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from collections import defaultdict


class LinuxCommand:
    def __init__(self, command_executor, command_name):
        self.command_executor = command_executor
        self.command_param_dict = defaultdict(list)
        self.command_flags = []
        self.command_name = command_name
        self.param_separator = ' '
        self.param_value_prefix = '='
        self.param_value_list_separator = ','

    def run(self):
        return self.command_executor.execute(self.command())

    def set_flags(self, *flag):
        for f in flag:
            self.command_flags.append(f)
        return self

    def remove_flag(self, flag):
        self.command_flags.remove(flag)
        return self

    def set_param(self, key, *values):
        for val in values:
            self.command_param_dict[key].append(str(val))
        return self

    def remove_param(self, key):
        del self.command_param_dict[key]

    def command(self):
        command = self.command_name
        for key, value in self.command_param_dict.items():
            command += f'{self.param_separator}{key}{self.param_value_prefix}{",".join(value)}'
        for flag in self.command_flags:
            command += f'{self.param_separator}{flag}'
        return command
