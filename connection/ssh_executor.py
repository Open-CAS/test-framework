#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import paramiko
from utils.output import Output
from connection.base_executor import BaseExecutor
from datetime import timedelta


class SshExecutor(BaseExecutor):
    def __init__(self, ip, username, password, port=22):
        self.ip = ip
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.connect(username, password)

    def connect(self, user, passwd):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.ip, username=user, password=passwd, port=self.port, timeout=30)
        except paramiko.SSHException:
            print("An exception occurred while trying to connect to {}".format(self.ip))

    def execute(self, command, timeout: timedelta = timedelta(hours = 1)):
        stdin, stdout, stderr = self.ssh.exec_command(command=command, timeout=timeout.total_seconds())
        output = Output(stdout.read().decode("utf-8"), stderr.read().decode("utf-8"), stdout.channel.recv_exit_status())
        return output
