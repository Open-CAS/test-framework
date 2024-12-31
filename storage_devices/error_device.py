#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2023-2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from core.test_run import TestRun
from storage_devices.device import Device
from test_tools.device_mapper import DmTable, DeviceMapper
from test_tools.disk_finder import resolve_to_by_id_link


class ErrorDevice(Device):
    def __init__(self, name: str, base_device: Device, table: DmTable = None):
        self.device = base_device
        self.mapper = DeviceMapper(name)
        self.name = name
        self.table = DmTable.passthrough_table(base_device) if not table else table
        self.active = False
        self.start()
        self.path = resolve_to_by_id_link(self.mapper.get_path().replace('/dev/', ''))

    @property
    def system_path(self):
        if self.active:
            output = TestRun.executor.run_expect_success(f"realpath {self.mapper.get_path()}")

            return output.stdout

        return None

    @property
    def size(self):
        if self.active:
            return self.table.get_size()

        return None

    def start(self):
        self.mapper.create(self.table)
        self.active = True

    def stop(self):
        self.mapper.remove()
        self.active = False

    def change_table(self, table: DmTable, permanent=True):
        if self.active:
            self.mapper.suspend()

        self.mapper.reload(table)

        self.mapper.resume()

        if permanent:
            self.table = table

    def suspend_errors(self):
        empty_table = DmTable.passthrough_table(self.device)
        TestRun.LOGGER.info(f"Suspending issuing errors for error device '{self.name}'")

        self.change_table(empty_table, False)

    def resume_errors(self):
        TestRun.LOGGER.info(f"Resuming issuing errors for error device '{self.name}'")

        self.change_table(self.table, False)

    def suspend(self):
        if not self.active:
            TestRun.LOGGER.warning(
                f"cannot suspend error device '{self.name}'! It's already running"
            )

        self.mapper.suspend()

        self.active = False

    def resume(self):
        if self.active:
            TestRun.LOGGER.warning(
                f"cannot resume error device '{self.name}'! It's already running"
            )

        self.mapper.resume()

        self.active = True
