#
# Copyright(c) 2019-2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
#

import socket
import subprocess
import paramiko
import os

from datetime import timedelta, datetime
from connection.base_executor import BaseExecutor
from core.test_run import TestRun, Blocked
from test_utils.output import Output


class SshExecutor(BaseExecutor):
    def __init__(self, host, username, port=22):
        self.host = host
        self.user = username
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.ssh_config = None
        self._check_config_for_reboot_timeout()

    def __del__(self):
        self.ssh.close()

    def connect(self, user=None, port=None,
                timeout: timedelta = timedelta(seconds=30)):
        hostname = self.host
        user = user or self.user
        port = port or self.port
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        config, sock, key_filename = None, None, None
        # search for 'host' in SSH config
        try:
            path = os.path.expanduser('~/.ssh/config')
            config = paramiko.SSHConfig.from_path(path)
        except FileNotFoundError:
            pass

        if config is not None:
            target = config.lookup(self.host)
            hostname = target['hostname']
            key_filename = target.get('identityfile', None)
            user = target.get('user', user)
            port = target.get('port', port)
            if target.get('proxyjump', None) is not None:
                proxy = config.lookup(target['proxyjump'])
                jump = paramiko.SSHClient()
                jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    jump.connect(proxy['hostname'], username=proxy['user'],
                                 port=int(proxy.get('port', 22)), key_filename=proxy.get('identityfile', None))
                    transport = jump.get_transport()
                    local_addr = (proxy['hostname'], int(proxy.get('port', 22)))
                    dest_addr = (hostname, port)
                    sock = transport.open_channel("direct-tcpip", dest_addr, local_addr)
                except Exception as e:
                    raise ConnectionError(f"An exception of type '{type(e)}' occurred while trying to "
                                          f"connect to proxy '{proxy['hostname']}'.\n {e}")

        if user is None:
            TestRun.block("There is no user given in config.")

        try:
            self.ssh.connect(hostname, username=user,
                             port=port, timeout=timeout.total_seconds(),
                             banner_timeout=timeout.total_seconds(),
                             sock=sock, key_filename=key_filename)
            self.ssh_config = config
        except paramiko.AuthenticationException as e:
            raise paramiko.AuthenticationException(
                f"Authentication exception occurred while trying to connect to DUT. "
                f"Please check your SSH key-based authentication.\n{e}")
        except (paramiko.SSHException, socket.timeout) as e:
            raise ConnectionError(f"An exception of type '{type(e)}' occurred while trying to "
                                  f"connect to {hostname}.\n {e}")

    def disconnect(self):
        try:
            self.ssh.close()
        except Exception:
            raise Exception(f"An exception occurred while trying to disconnect from {self.host}")

    def _execute(self, command, timeout):
        try:
            (stdin, stdout, stderr) = self.ssh.exec_command(command,
                                                            timeout=timeout.total_seconds())
        except paramiko.SSHException as e:
            raise ConnectionError(f"An exception occurred while executing command '{command}' on"
                                  f" {self.host}\n{e}")

        return Output(stdout.read(), stderr.read(), stdout.channel.recv_exit_status())

    def _rsync(self, src, dst, delete=False, symlinks=False, checksum=False, exclude_list=[],
               timeout: timedelta = timedelta(seconds=90), dut_to_controller=False):
        options = []

        if delete:
            options.append("--delete")
        if symlinks:
            options.append("--links")
        if checksum:
            options.append("--checksum")

        for exclude in exclude_list:
            options.append(f"--exclude {exclude}")

        src_to_dst = f"{self.user}@{self.host}:{src} {dst} " if dut_to_controller else\
                     f"{src} {self.user}@{self.host}:{dst} "

        try:
            completed_process = subprocess.run(
                f'rsync -r -e "ssh -p {self.port} '
                f'-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no" '
                + src_to_dst + f'{" ".join(options)}',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout.total_seconds())
        except Exception as e:
            TestRun.LOGGER.exception(f"Exception occurred during rsync process. "
                                     f"Please check your SSH key-based authentication.\n{e}")

        if completed_process.returncode:
            raise Exception(f"rsync failed:\n{completed_process}")

    def is_remote(self):
        return True

    def _check_config_for_reboot_timeout(self):
        if "reboot_timeout" in TestRun.config.keys():
            self._parse_timeout_to_int()
        else:
            self.reboot_timeout = None

    def _parse_timeout_to_int(self):
        self.reboot_timeout = int(TestRun.config["reboot_timeout"])
        if self.reboot_timeout < 0:
            raise ValueError("Reboot timeout cannot be negative.")

    def reboot(self):
        self.run("reboot")
        self.wait_for_connection_loss()
        self.wait_for_connection(timedelta(seconds=self.reboot_timeout)) \
            if self.reboot_timeout is not None else self.wait_for_connection()

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
                    self.connect()
                    return
                except (paramiko.AuthenticationException, Blocked):
                    raise
                except Exception:
                    continue
            raise ConnectionError("Timeout occurred while trying to establish ssh connection")

    def wait_for_connection_loss(self, timeout: timedelta = timedelta(minutes=1)):
        with TestRun.group("Waiting for DUT ssh connection loss"):
            end_time = datetime.now() + timeout
            while end_time > datetime.now():
                self.disconnect()
                try:
                    self.connect(timeout=timedelta(seconds=5))
                except Exception:
                    return
            raise ConnectionError("Timeout occurred before ssh connection loss")
