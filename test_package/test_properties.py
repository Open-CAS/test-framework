#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging


class TestProperties:
    dut = None
    executor = None
    LOGGER = logging.getLogger("Test logger")

    @staticmethod
    def log_command_error(command, output):
        TestProperties.LOGGER.error(
            f"Exception occured while trying to execute '{command}' command.\n"
            f"stdout: {output.stdout}\nstderr: {output.stderr}")

    @staticmethod
    def execute_command_and_check(command):
        output = TestProperties.executor.execute(command)
        if output.exit_code != 0:
            TestProperties.log_command_error(command, output)
            return False, output
        return True, output
