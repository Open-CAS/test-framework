#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import datetime
import uuid

from packaging.version import Version

from core.test_run import TestRun
from connection.utils.output import CmdException
from test_tools import wget
from test_tools.fio.fio_param import FioParam, FioParamCmd, FioOutput, FioParamConfig
from test_tools.fs_tools import uncompress_archive


class Fio:
    def __init__(self, executor_obj=None):
        self.min_fio_version = Version(TestRun.config.get("fio_version", "3.30"))
        self.default_run_time = datetime.timedelta(hours=1)
        self.jobs = []
        self.executor = executor_obj if executor_obj is not None else TestRun.executor
        self.base_cmd_parameters: FioParam = None
        self.global_cmd_parameters: FioParam = None

    def create_command(self, output_type=FioOutput.json):
        self.base_cmd_parameters = FioParamCmd(self, self.executor)
        self.global_cmd_parameters = FioParamConfig(self, self.executor)

        self.fio_file = \
            f'fio_run_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_{uuid.uuid4().hex}'
        self.base_cmd_parameters\
            .set_param('eta', 'always')\
            .set_param('output-format', output_type.value)\
            .set_param('output', self.fio_file)

        self.global_cmd_parameters.set_flags('group_reporting')

        return self.global_cmd_parameters

    def is_installed(self):
        try:
            output = self.executor.run_expect_success("fio --version").stdout
        except CmdException:
            return False
        current_version = Version(output.strip().removeprefix("fio-"))
        return current_version >= self.min_fio_version

    def install(self):
        fio_url = f"http://brick.kernel.dk/snaps/fio-{self.min_fio_version}.tar.bz2"
        fio_package = wget.download_file(fio_url)
        uncompress_archive(fio_package)
        TestRun.executor.run_expect_success(
            f"cd {fio_package.parent_dir}/fio-{self.min_fio_version}"
            f" && ./configure && make -j && make install"
        )

    def calculate_timeout(self):
        if "time_based" not in self.global_cmd_parameters.command_flags:
            return self.default_run_time

        total_time = self.global_cmd_parameters.get_parameter_value("runtime")
        if len(total_time) != 1:
            raise ValueError("Wrong fio 'runtime' parameter configuration")
        total_time = int(total_time[0])
        ramp_time = self.global_cmd_parameters.get_parameter_value("ramp_time")
        if ramp_time is not None:
            if len(ramp_time) != 1:
                raise ValueError("Wrong fio 'ramp_time' parameter configuration")
            ramp_time = int(ramp_time[0])
            total_time += ramp_time
        return datetime.timedelta(seconds=total_time)

    def run(self, timeout: datetime.timedelta = None):
        if timeout is None:
            timeout = self.calculate_timeout()

        self.prepare_run()
        return self.executor.run(str(self), timeout)

    def run_in_background(self):
        self.prepare_run()
        return self.executor.run_in_background(str(self))

    def prepare_run(self):
        if not self.is_installed():
            self.install()

        if len(self.jobs) > 0:
            self.executor.run(f"{str(self)}-showcmd -")
            TestRun.LOGGER.info(self.executor.run(f"cat {self.fio_file}").stdout)
        TestRun.LOGGER.info(str(self))

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
            fio_parameters = FioParamCmd(self, self.executor)
            fio_parameters.command_env_var.update(self.base_cmd_parameters.command_env_var)
            fio_parameters.command_param.update(self.base_cmd_parameters.command_param)
            fio_parameters.command_param.update(self.global_cmd_parameters.command_param)
            fio_parameters.command_flags.extend(self.global_cmd_parameters.command_flags)
            fio_parameters.set_param('name', 'fio')
            command = str(fio_parameters)
        return command
