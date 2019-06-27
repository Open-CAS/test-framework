#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import test_tools.fio.fio_param
import datetime


class Fio:
    def __init__(self, executor_obj):
        self.fio_version = "fio-3.7"
        self.default_run_time = datetime.timedelta(hours=1)
        self.jobs = []
        self.executor = executor_obj
        self.base_cmd_parameters: test_tools.fio.fio_param.FioParam = None
        self.global_cmd_parameters: test_tools.fio.fio_param.FioParam = None

    def create_command(self):
        self.base_cmd_parameters = test_tools.fio.fio_param.FioParamCmd(self, self.executor)
        self.global_cmd_parameters = test_tools.fio.fio_param.FioParamConfig(self, self.executor)
        self.fio_file = f'fio_run_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%s")}'
        self.base_cmd_parameters\
            .set_param('eta', 'always')\
            .set_param('output-format', 'json')\
            .set_param('output', self.fio_file)
        return self.global_cmd_parameters

    def is_installed(self):
        return self.executor.execute("fio --version").stdout.strip() == self.fio_version

    def calculate_timeout(self):
        if self.global_cmd_parameters.get_parameter_value("time_based") is None:
            return self.default_run_time

        total_time = self.global_cmd_parameters.get_parameter_value("runtime")
        ramp_time = self.global_cmd_parameters.get_parameter_value("ramp_time")
        if ramp_time is not None:
            total_time += ramp_time
        return datetime.timedelta(seconds=total_time)

    def run(self, timeout: datetime.timedelta = None):
        if not self.is_installed():
            raise Exception(
                f"Fio is not installed in correct version. Expected: {self.fio_version}")

        if timeout is None:
            timeout = self.calculate_timeout()

        if len(self.jobs) > 0:
            self.executor.execute(f"{str(self)}-showcmd -")
            print(self.executor.execute(f"cat {self.fio_file}").stdout)
        print(str(self))
        return self.executor.execute(str(self), timeout)

    def execution_cmd_parameters(self):
        if len(self.jobs) > 0:
            separator = "\n\n"
            return f"{str(self.global_cmd_parameters)}\n" \
                f"{separator.join(str(job) for job in self.jobs)}"
        else:
            return str(self.global_cmd_parameters)

    def __str__(self):
        if len(self.jobs) > 0:
            command = f"echo '{self.execution_cmd_parameters()}' |" \
                f" {str(self.base_cmd_parameters)} -"
        else:
            fio_parameters = test_tools.fio.fio_param.FioParamCmd(self, self.executor)
            fio_parameters.command_param_dict.update(self.base_cmd_parameters.command_param_dict)
            fio_parameters.command_param_dict.update(self.global_cmd_parameters.command_param_dict)
            fio_parameters.set_param('name', 'fio')
            command = str(fio_parameters)
        return command
