#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2025 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from storage_devices.device import Device
from test_tools.disk_tools import get_partition_path
from test_tools.fs_tools import readlink
from type_def.size import Size


class Partition(Device):
    def __init__(self, parent_dev, type, number, begin: Size, end: Size):
        Device.__init__(self, get_partition_path(parent_dev.path, number))
        self.number = number
        self.parent_device = parent_dev
        self.type = type
        self.begin = begin
        self.end = end
        self.device_id = self.get_device_id()

    def __str__(self):
        return f"\tsystem path: {self.path}, size: {self.size}, type: {self.type}, " \
            f"parent device: {self.parent_device.path}\n"

    def get_device_id(self):
        return readlink(self.path).split('/')[-1]
