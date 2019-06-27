#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from test_tools import disk_utils
from test_package.test_properties import TestProperties
from test_utils.size import Size, Unit


class Device:
    def __init__(self, path):
        self.size = Size(disk_utils.get_size(path.replace('/dev/', '')), Unit.Byte)
        self.system_path = path
        self.filesystem = None
        self.mount_point = None

    def create_filesystem(self, fs_type: disk_utils.Filesystem):
        if disk_utils.create_filesystem(self, fs_type):
            self.filesystem = fs_type

    def is_mounted(self):
        # TODO: Add more specific method to check, whether device is mounted before test
        return self.mount_point is not None

    def mount(self, mount_point):
        if not self.is_mounted():
            if disk_utils.mount(self, mount_point):
                self.mount_point = mount_point
        else:
            TestProperties.LOGGER.error(
                f"Device is already mounted! Actual mount point: {self.mount_point}")

    def unmount(self):
        if not self.is_mounted():
            TestProperties.LOGGER.info("Device is not mounted.")
        elif disk_utils.unmount(self):
            self.mount_point = None
