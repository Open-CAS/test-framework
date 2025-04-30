#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2023-2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import posixpath

from core.test_run import TestRun
from test_tools import disk_tools
from test_tools.disk_tools import get_sysfs_path, validate_dev_path, get_size
from test_tools.fs_tools import (get_device_filesystem_type, Filesystem, wipefs,
                                 readlink, write_file, mkfs, ls, parse_ls_output)
from test_utils.io_stats import IoStats
from type_def.size import Size, Unit


class Device:
    def __init__(self, path):
        try:
            validate_dev_path(path)
            self.path = path
            self.size = Size(get_size(self.get_device_id()), Unit.Byte)
            self.filesystem = get_device_filesystem_type(self.get_device_id())
        except ValueError:
            TestRun.LOGGER.info(f"Device {path} not visible in OS")
            self.path = path
        self.mount_point = None

    def create_filesystem(self, fs_type: Filesystem, force=True, blocksize=None):
        mkfs(self, fs_type, force, blocksize)
        self.filesystem = fs_type

    def wipe_filesystem(self, force=True):
        wipefs(self, force)
        self.filesystem = None

    def is_mounted(self):
        output = TestRun.executor.run(f"findmnt {self.path}")
        if output.exit_code != 0:
            return False
        else:
            mount_point_line = output.stdout.split('\n')[1]
            device_path = readlink(self.path)
            self.mount_point = mount_point_line[0:mount_point_line.find(device_path)].strip()
            return True

    def mount(self, mount_point, options: [str] = None):
        if not self.is_mounted():
            if disk_tools.mount(self, mount_point, options):
                self.mount_point = mount_point
        else:
            raise Exception(f"Device is already mounted! Actual mount point: {self.mount_point}")

    def unmount(self):
        if not self.is_mounted():
            TestRun.LOGGER.info("Device is not mounted.")
        elif disk_tools.unmount(self):
            self.mount_point = None

    def get_device_link(self, directory: str):
        items = self.get_all_device_links(directory)
        return next(i for i in items if i.full_path.startswith(directory))

    def get_device_id(self):
        return readlink(self.path).split('/')[-1]

    def get_all_device_links(self, directory: str):
        output = ls(f"$(find -L {directory} -samefile {self.path})")
        return parse_ls_output(output, self.path)

    def get_io_stats(self):
        return IoStats.get_io_stats(self.get_device_id())

    def get_sysfs_property(self, property_name):
        path = posixpath.join(get_sysfs_path(self.get_device_id()),
                              "queue", property_name)
        return TestRun.executor.run_expect_success(f"cat {path}").stdout

    def set_sysfs_property(self, property_name, value):
        TestRun.LOGGER.info(
            f"Setting {property_name} for device {self.get_device_id()} to {value}.")
        path = posixpath.join(get_sysfs_path(self.get_device_id()), "queue",
                            property_name)
        write_file(path, str(value))

    def set_max_io_size(self, new_max_io_size: Size):
        self.set_sysfs_property("max_sectors_kb",
                                int(new_max_io_size.get_value(Unit.KibiByte)))

    def get_max_io_size(self):
        return Size(int(self.get_sysfs_property("max_sectors_kb")), Unit.KibiByte)

    def get_max_hw_io_size(self):
        return Size(int(self.get_sysfs_property("max_hw_sectors_kb")), Unit.KibiByte)

    def get_discard_granularity(self):
        return self.get_sysfs_property("discard_granularity")

    def get_discard_max_bytes(self):
        return self.get_sysfs_property("discard_max_bytes")

    def get_discard_zeroes_data(self):
        return self.get_sysfs_property("discard_zeroes_data")

    def get_numa_node(self):
        return int(TestRun.executor.run_expect_success(
            f"cat {get_sysfs_path(self.get_device_id())}/device/numa_node").stdout)

    def get_serial(self):
        sysfs_path = get_sysfs_path(self.get_device_id())
        serial_path = posixpath.join(sysfs_path, "device", "serial")
        return TestRun.executor.run_expect_success(f"cat {serial_path}").stdout

    def __str__(self):
        return (
            f'system path: {self.path}, short link: /dev/{self.get_device_id()},'
            f' filesystem: {self.filesystem}, mount point: {self.mount_point}, size: {self.size}'
        )

    def __repr__(self):
        return str(self)

    @staticmethod
    def get_scsi_debug_devices():
        scsi_debug_devices = TestRun.executor.run_expect_success(
            "lsscsi --scsi_id | grep scsi_debug").stdout
        return [Device(f'/dev/disk/by-id/scsi-{device.split()[-1]}')
                for device in scsi_debug_devices.splitlines()]
