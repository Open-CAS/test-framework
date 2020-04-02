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

    def _rsync(self, src, dst, delete=False, symlinks=False, checksum=False, exclude_list=[],
               timeout: timedelta = timedelta(seconds=30), dut_to_controller=False):
        options = []

        if delete:
            options.append("--delete")
        if symlinks:
            options.append("--links")
        if checksum:
            options.append("--checksum")

        for exclude in exclude_list:
            options.append(f"--exclude {exclude}")

        src_to_dst = f"{self.user}@{self.ip}:{src} {dst} " if dut_to_controller else\
                     f"{src} {self.user}@{self.ip}:{dst} "

        completed_process = subprocess.run(
            f'sshpass -p "{self.password}" rsync -r -e "ssh -p {self.port} '
            f'-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no" '
            + src_to_dst + f'{" ".join(options)}',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout.total_seconds())

        if completed_process.returncode:
            raise Exception(f"rsync failed:\n{completed_process}")

    def is_remote(self):
        return True

    def reboot(self):
        self.run("reboot")
        self.wait_for_connection_loss()
        self.wait_for_connection()

    def is_active(self):
        try:
            self.ssh.exec_command('', timeout=5)
            return True
        except Exception:
            return False

    def got_compatible_kernels(self):
        count = 0
        try:
            grub_ver = self.run("ls /boot | grep grub").stdout.splitlines()[-1]
            kernel_ver = self.run("uname -r").stdout.split("-")[0]
            kernels = self.run(
                "awk '/menuentry/ && /class/ {count++; print count-1\"#\"$0 }' "
                f"/boot/{grub_ver}/grub.cfg").stdout.splitlines()

            for version in kernels:
                version = version.split('--')[0]
                if ("rescue" or "recovery") in version.lower():
                    continue
                if kernel_ver in version:
                    count += 1

        except Exception:
            pass

        finally:
            return True if count > 1 else False

    def got_incompatible_kernels(self):
        count = 0
        try:
            grub_ver = self.run("ls /boot | grep grub").stdout[-1]
            kernel_ver = self.run("uname -r").stdout.split("-")[0]
            kernels = self.run(
                "awk '/menuentry/ && /class/ {count++; print count-1\"#\"$0 }' "
                f"/boot/{grub_ver}/grub.cfg").stdout.splitlines()

            for version in kernels:
                version = version.split('--')[0]
                if ("rescue" or "recovery") in version.lower():
                    continue
                if kernel_ver not in version:
                    count += 1

        except Exception:
            pass

        finally:
            return True if count > 0 else False

    def wait_for_connection(self, timeout: timedelta = timedelta(minutes=10)):
        start_time = datetime.now()
        with TestRun.group("Waiting for DUT ssh connection"):
            while start_time + timeout > datetime.now():
                try:
                    self.connect(user=self.user, passwd=self.password, port=self.port)
                    return
                except Exception:
                    continue
            raise ConnectionError("Timeout occurred while tying to establish ssh connection")

    def wait_for_connection_loss(self, timeout: timedelta = timedelta(minutes=1)):
        with TestRun.group("Waiting for DUT ssh connection loss"):
            end_time = datetime.now() + timeout
            while end_time > datetime.now():
                try:
                    self.ssh.exec_command(":", timeout=30)
                except (paramiko.SSHException, ConnectionResetError):
                    return
            raise ConnectionError("Timeout occurred before ssh connection loss")
