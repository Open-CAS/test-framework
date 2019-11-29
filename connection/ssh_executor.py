#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import socket
import subprocess
from datetime import timedelta, datetime

import paramiko

from connection.base_executor import BaseExecutor
from core.test_run import TestRun
from test_utils.output import Output


class SshExecutor(BaseExecutor):
    def __init__(self, ip, username, password, port=22):
        self.ip = ip
        self.user = username
        self.password = password
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.connect(username, password, port)

    def __del__(self):
        self.ssh.close()

    def connect(self, user, passwd, port, timeout: timedelta = timedelta(seconds=30)):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.ip, username=user, password=passwd,
                             port=port, timeout=timeout.total_seconds())
        except (paramiko.SSHException, socket.timeout) as e:
            raise ConnectionError(f"An exception of type '{type(e)}' occurred while trying to "
                                  f"connect to {self.ip}\n{e}")

    def disconnect(self):
        try:
            self.ssh.close()
        except Exception:
            raise Exception(f"An exception occurred while trying to disconnect from {self.ip}")

    def _execute(self, command, timeout):
        try:
            (stdin, stdout, stderr) = self.ssh.exec_command(command,
                                                            timeout=timeout.total_seconds())
        except paramiko.SSHException as e:
            raise ConnectionError(f"An exception occurred while executing command '{command}' on"
                                  f" {self.ip}\n{e}")

        return Output(stdout.read(), stderr.read(), stdout.channel.recv_exit_status())

    def rsync(self, src, dst, delete=False, symlinks=False, exclude_list=[],
              timeout: timedelta = timedelta(seconds=30)):
        options = []

        if delete:
            options.append("--delete")
        if symlinks:
            options.append("--links")

        for exclude in exclude_list:
            options.append(f"--exclude {exclude}")

        subprocess.run(
            f'sshpass -p "{self.password}" '
            f'rsync -r -e "ssh -p {self.port} -o UserKnownHostsFile=/dev/null '
            f'-o StrictHostKeyChecking=no" '
            f'{src} {self.user}@{self.ip}:{dst} {" ".join(options)}',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout.total_seconds())

    def is_remote(self):
        return True

    def is_active(self):
        try:
            self.ssh.exec_command('', timeout=5)
            return True
        except Exception:
            return False

    def wait_for_connection(self, timeout: timedelta = timedelta(minutes=10)):
        start_time = datetime.now()
        with TestRun.group("Waiting for DUT ssh connection"):
            while start_time + timeout > datetime.now():
                try:
                    TestRun.LOGGER.info(f"{(datetime.now() - start_time).total_seconds()}s...")
                    self.connect(user=self.user, passwd=self.password, port=self.port)
                    return
                except Exception:
                    continue
            raise ConnectionError("Timeout occurred while tying to establish ssh connection")
