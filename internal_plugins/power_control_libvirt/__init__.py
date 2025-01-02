#
# Copyright(c) 2020-2021 Intel Corporation
# Copyright(c) 2023-2025 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from datetime import timedelta

from connection.local_executor import LocalExecutor
from connection.ssh_executor import SshExecutor
from core.test_run import TestRun

DEFAULT_REBOOT_TIMEOUT = 60


class PowerControlPlugin:
    def __init__(self, params, config):
        print("Power Control LibVirt Plugin initialization")
        try:
            self.host = config["host"]
            self.user = config["user"]
            self.connection_type = config["connection_type"]
            self.port = config.get("port", 22)

        except AttributeError:
            raise (
                "Missing fields in config! ('host','user','connection_type','vm_name' "
                "are required fields)"
            )

    def pre_setup(self):
        print("Power Control LibVirt Plugin pre setup")
        if self.connection_type == "ssh":
            self.executor = SshExecutor(
                self.host,
                self.user,
                self.port,
            )
            self.executor.connect()
        else:
            self.executor = LocalExecutor()

    def post_setup(self):
        pass

    def teardown(self):
        pass

    def power_cycle(self, wait_for_connection: bool = False, delay_until_reboot: int = 0) -> None:
        self.executor.run_expect_success(f"sudo virsh destroy {TestRun.dut.virsh['vm_name']}")
        TestRun.executor.disconnect()
        self.executor.run_expect_success(
            f"(sleep {delay_until_reboot} && sudo virsh start {TestRun.dut.virsh['vm_name']}) &"
        )
        if wait_for_connection:
            TestRun.executor.wait_for_connection(
                timedelta(seconds=TestRun.dut.virsh["reboot_timeout"])
            )

    def check_if_vm_exists(self, vm_name) -> bool:
        return self.executor.run(f"sudo virsh list|grep -w {vm_name}").exit_code == 0

    def parse_virsh_config(self, vm_name, reboot_timeout=DEFAULT_REBOOT_TIMEOUT) -> dict | None:
        if not self.check_if_vm_exists(vm_name=vm_name):
            raise ValueError(
                f"Virsh power plugin error: couldn't find VM {vm_name} on host {self.host}"
            )
        return {
            "vm_name": vm_name,
            "reboot_timeout": reboot_timeout,
        }


plugin_class = PowerControlPlugin
