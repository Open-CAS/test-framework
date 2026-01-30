#
# Copyright(c) 2020-2021 Intel Corporation
# Copyright(c) 2023-2025 Huawei Technologies Co., Ltd.
# Copyright(c) 2026 Unvertical
# SPDX-License-Identifier: BSD-3-Clause
#

import libvirt

from datetime import timedelta

from core.test_run import TestRun


class PowerControlPlugin:
    def __init__(self, params, config):
        print("Power Control LibVirt Plugin initialization")
        try:
            self.url = config["url"]
            self.vm_name = config["vm_name"]
            self.reboot_timeout = config.get("reboot_timeout", 60)

        except AttributeError:
            raise (
                "Missing fields in config! ('url','vm_name' are required fields)"
            )

    def pre_setup(self):
        print("Power Control LibVirt Plugin pre setup")
        self.conn = libvirt.open(self.url)
        self.domain = self.conn.lookupByName(self.vm_name)

    def post_setup(self):
        pass

    def teardown(self):
        pass

    def power_cycle(self, wait_for_connection: bool = False) -> None:
        self.domain.reset()
        TestRun.executor.disconnect()
        if wait_for_connection:
            TestRun.executor.wait_for_connection(timedelta(seconds=self.reboot_timeout))


plugin_class = PowerControlPlugin
