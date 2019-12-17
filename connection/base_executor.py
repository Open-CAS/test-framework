#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import time

from datetime import timedelta

from core.test_run import TestRun
from test_utils.output import CmdException


class BaseExecutor:
    def _execute(self, command, timeout):
        raise NotImplementedError()

    def rsync(self, src, dst, delete, symlinks, exclude_list, timeout):
        raise NotImplementedError()

    def is_remote(self):
        return False

    def is_active(self):
        return True

    def wait_for_connection(self):
        pass

    def run(self, command, timeout: timedelta = timedelta(minutes=30)):
        if TestRun.dut and TestRun.dut.env:
            command = f"{TestRun.dut.env} && {command}"
        command_id = TestRun.LOGGER.get_new_command_id()
        TestRun.LOGGER.write_command_to_command_log(command, command_id)
        output = self._execute(command, timeout)
        TestRun.LOGGER.write_output_to_command_log(output, command_id)
        return output

    def run_in_background(self, command):
        command += "&> /dev/null &echo $!"
        output = self.run(command)

        if output is not None:
            return int(output.stdout)

    def run_as_other_user(self, command, user_name: str, sudo: bool = False):
        prefix = f'sudo -u {user_name}'
        if sudo:
            command = 'sudo ' + command
        command = f'{prefix} {command}'
        output = self.run(command)
        if output.exit_code != 0:
            raise CmdException("Must be run as root.", output)
        return output

    def wait_cmd_finish(self, pid: int, timeout: timedelta = timedelta(minutes=30)):
        self.run(f"tail --pid={pid} -f /dev/null", timeout)

    def kill_process(self, pid: int):
        # TERM signal should be used in preference to the KILL signal, since a
        # process may install a handler for the TERM signal in order to perform
        # clean-up steps before terminating in an orderly fashion.
        self.run(f"kill -s SIGTERM {pid} &> /dev/null")
        time.sleep(3)
        self.run(f"kill -s SIGKILL {pid} &> /dev/null")

    def run_expect_success(self, command):
        output = self.run(command)
        if output.exit_code != 0:
            raise CmdException(f"Exception occurred while trying to execute '{command}' command.",
                               output)
        return output

    def run_expect_fail(self, command):
        output = self.run(command)
        if output.exit_code == 0:
            raise CmdException(f"Command '{command}' executed properly but error was expected.",
                               output)
        return output
