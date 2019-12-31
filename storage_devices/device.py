#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from core.test_run import TestRun
from test_tools import disk_utils
from test_utils.size import Size, Unit


class Device:
    def __init__(self, path):
        self.size = Size(disk_utils.get_size(path.replace('/dev/', '')), Unit.Byte)
        self.system_path = path
        self.filesystem = None
        self.mount_point = None

    def create_filesystem(self, fs_type: disk_utils.Filesystem, force=True, blocksize=None):
        if disk_utils.create_filesystem(self, fs_type, force, blocksize):
            self.filesystem = fs_type

    def is_mounted(self):
        output = TestRun.executor.run(f"findmnt {self.system_path}")
        if output.exit_code != 0:
            return False
        else:
            mount_point_line = output.stdout.split('\n')[1]
            self.mount_point = mount_point_line[0:mount_point_line.find(self.system_path)].strip()
            return True

    def mount(self, mount_point):
        if not self.is_mounted():
            if disk_utils.mount(self, mount_point):
                self.mount_point = mount_point
        else:
            raise Exception(f"Device is already mounted! Actual mount point: {self.mount_point}")

    def unmount(self):
        if not self.is_mounted():
            TestRun.LOGGER.info("Device is not mounted.")
        elif disk_utils.unmount(self):
            self.mount_point = None

    def get_device_link(self, directory: str):
        items = self.get_all_device_links(directory)
        return next(i for i in items if i.full_path.startswith(directory))

    def get_all_device_links(self, directory: str):
        from test_tools import fs_utils
        output = fs_utils.ls(f"$(find -L {directory} -samefile {self.system_path})")
        return fs_utils.parse_ls_output(output, self.system_path)

    @staticmethod
    def get_scsi_devices():
        scsi_devices = TestRun.executor.run("lsscsi | grep Linux").stdout
        return [Device(scsi_device.split()[-1]) for scsi_device in scsi_devices.splitlines()]
