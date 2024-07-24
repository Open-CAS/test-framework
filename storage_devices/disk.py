#
# Copyright(c) 2019-2022 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
#
import json
import re
from datetime import timedelta
from enum import IntEnum

from core.test_run import TestRun
from storage_devices.device import Device
from test_tools import disk_utils, fs_utils, nvme_cli
from test_utils import disk_finder
from test_utils.os_utils import wait
from test_utils.size import Unit
from test_tools.disk_utils import get_pci_address


class DiskType(IntEnum):
    hdd = 0
    hdd4k = 1
    sata = 2
    nand = 3
    optane = 4


class DiskTypeSetBase:
    def resolved(self):
        raise NotImplementedError()

    def types(self):
        raise NotImplementedError()

    def json(self):
        return json.dumps({
            "type": "set",
            "values": [t.name for t in self.types()]
        })

    def __lt__(self, other):
        return min(self.types()) < min(other.types())

    def __le__(self, other):
        return min(self.types()) <= min(other.types())

    def __eq__(self, other):
        return min(self.types()) == min(other.types())

    def __ne__(self, other):
        return min(self.types()) != min(other.types())

    def __gt__(self, other):
        return min(self.types()) > min(other.types())

    def __ge__(self, other):
        return min(self.types()) >= min(other.types())


class DiskTypeSet(DiskTypeSetBase):
    def __init__(self, *args):
        self.__types = set(*args)

    def resolved(self):
        return True

    def types(self):
        return self.__types


class DiskTypeLowerThan(DiskTypeSetBase):
    def __init__(self, disk_name):
        self.__disk_name = disk_name

    def resolved(self):
        return self.__disk_name in TestRun.disks

    def types(self):
        if not self.resolved():
            raise LookupError("Disk type not resolved!")
        disk_type = TestRun.disks[self.__disk_name].disk_type
        return set(filter(lambda d: d < disk_type, [*DiskType]))

    def json(self):
        return json.dumps({
            "type": "operator",
            "name": "lt",
            "args": [self.__disk_name]
        })


class Disk(Device):
    def __init__(
        self,
        path,
        disk_type: DiskType,
        serial_number,
        block_size,
    ):
        Device.__init__(self, path)
        self.serial_number = serial_number
        self.block_size = Unit(block_size)
        self.disk_type = disk_type
        self.partitions = []
        self.pci_address = None

    def create_partitions(
            self,
            sizes: [],
            partition_table_type=disk_utils.PartitionTable.gpt):
        disk_utils.create_partitions(self, sizes, partition_table_type)

    def remove_partition(self, part):
        part_number = int(part.path.split("part")[1])
        disk_utils.remove_parition(self, part_number)
        self.partitions.remove(part)

    def umount_all_partitions(self):
        TestRun.LOGGER.info(
            f"Umounting all partitions from: {self.path}")
        cmd = f'umount -l {fs_utils.readlink(self.path)}*?'
        TestRun.executor.run(cmd)

    def remove_partitions(self):
        for part in self.partitions:
            if part.is_mounted():
                part.unmount()
        if disk_utils.remove_partitions(self):
            self.partitions.clear()

    def is_detected(self):
        if self.serial_number:
            serial_numbers = disk_finder.get_all_serial_numbers()
            return self.serial_number in serial_numbers
        elif self.path:
            output = fs_utils.ls_item(f"{self.path}")
            return fs_utils.parse_ls_output(output)[0] is not None
        raise Exception("Couldn't check if device is detected by the system")

    def wait_for_plug_status(self, should_be_visible):
        if not wait(lambda: should_be_visible == self.is_detected(),
                    timedelta(minutes=1),
                    timedelta(seconds=1)):
            raise Exception(f"Timeout occurred while trying to "
                            f"{'plug' if should_be_visible else 'unplug'} disk.")

    def plug(self):
        if self.is_detected():
            return
        TestRun.executor.run_expect_success(self.plug_command)
        self.wait_for_plug_status(True)

    def unplug(self):
        if not self.is_detected():
            return
        TestRun.executor.run_expect_success(self.unplug_command)
        self.wait_for_plug_status(False)

    @staticmethod
    def plug_all_disks():
        TestRun.executor.run_expect_success(NvmeDisk.plug_all_command)
        TestRun.executor.run_expect_success(SataDisk.plug_all_command)

    def __str__(self):
        disk_str = f'system path: {self.path}, type: {self.disk_type.name}, ' \
            f'serial: {self.serial_number}, size: {self.size}, ' \
            f'block size: {self.block_size}, pci address: {self.pci_address}, partitions:\n'
        for part in self.partitions:
            disk_str += f'\t{part}'
        return disk_str

    @staticmethod
    def create_disk(path,
                    disk_type: DiskType,
                    serial_number,
                    block_size):

        resolved_disk_type = None
        for checked_type in [NvmeDisk, SataDisk, VirtioDisk]:
            try:
                checked_type.get_unplug_path(fs_utils.readlink(path).split('/')[-1])
                resolved_disk_type = checked_type
                break
            except Exception:
                continue

        if resolved_disk_type is None:
            raise Exception(f"Unrecognized device type for {path}")

        return resolved_disk_type(path, disk_type, serial_number, block_size)


class NvmeDisk(Disk):
    plug_all_command = "echo 1 > /sys/bus/pci/rescan"

    def __init__(self, path, disk_type, serial_number, block_size):
        Disk.__init__(self, path, disk_type, serial_number, block_size)
        self.plug_command = NvmeDisk.plug_all_command
        self.unplug_command = f"echo 1 > /sys/block/{self.get_device_id()}/device/remove || " \
                              f"echo 1 > /sys/block/{self.get_device_id()}/device/device/remove"
        self.pci_address = NvmeDisk.get_pci_address(self.get_device_id())

    def format_disk(self, metadata_size=None, block_size=None,
                    force=True, format_params=None, reset=True):
        nvme_cli.format_disk(self, metadata_size, block_size, force, format_params, reset)

    def get_lba_formats(self):
        return nvme_cli.get_lba_formats(self)

    def get_lba_format_in_use(self):
        return nvme_cli.get_lba_format_in_use(self)

    @classmethod
    def get_unplug_path(cls, device_id):
        base = f"/sys/block/{device_id}/device"
        for suffix in ["/remove", "/device/remove"]:
            try:
                output = fs_utils.ls_item(base + suffix)
                fs_utils.parse_ls_output(output)[0]
            except:
                continue

            return base + suffix

        raise Exception(f"Couldn't create unplug path for {device_id}")

    @classmethod
    def get_pci_address(cls, device_id):
        return TestRun.executor.run(f"cat /sys/block/{device_id}/device/address").stdout


class SataDisk(Disk):
    plug_all_command = "for i in $(find -H /sys/devices/ -path '*/scsi_host/*/scan' -type f); " \
                       "do echo '- - -' > $i; done;"

    def __init__(self, path, disk_type, serial_number, block_size):
        Disk.__init__(self, path, disk_type, serial_number, block_size)
        self.plug_command = SataDisk.plug_all_command
        self.unplug_command = \
            f"echo 1 > {self.get_unplug_path(self.get_device_id())}"
        self.pci_address = SataDisk.get_pci_address(self.get_device_id())

    @classmethod
    def get_unplug_path(cls, device_id):
        sysfs_addr = cls.get_sysfs_addr(device_id)
        try:
            cls.get_pci_address(device_id)
        except Exception as e:
            raise Exception(f"Failed to find controller for {device_id}.\n{e}")

        return sysfs_addr + "/device/delete"

    @classmethod
    def get_sysfs_addr(cls, device_id):
        ls_command = f"$(find -H /sys/devices/ -name {device_id} -type d)"
        output = fs_utils.ls_item(f"{ls_command}")
        sysfs_addr = fs_utils.parse_ls_output(output)[0]
        if not sysfs_addr:
            raise Exception(f"Failed to find sysfs address: ls -l {ls_command}")

        return sysfs_addr.full_path

    @classmethod
    def get_pci_address(cls, device_id):
        sysfs_addr = cls.get_sysfs_addr(device_id)
        pci_address = re.findall(r"\d+:\d+:\d+.\d+", sysfs_addr)

        if not pci_address:
            raise Exception(f"Failed to get the pci address of {device_id} device.")

        return pci_address[-1]


class VirtioDisk(Disk):
    plug_all_command = "echo 1 > /sys/bus/pci/rescan"

    def __init__(self, path, disk_type, serial_number, block_size):
        Disk.__init__(self, path, disk_type, serial_number, block_size)
        self.plug_command = VirtioDisk.plug_all_command
        self.unplug_command = \
            f"echo 1 > {self.get_unplug_path(self.get_device_id())}"
        self.pci_address = VirtioDisk.get_pci_address(self.get_device_id())

    @classmethod
    def get_unplug_path(cls, device_id):
        sysfs_path = VirtioDisk.get_sysfs_addr(device_id)
        pci_addr = VirtioDisk.get_pci_address(device_id)

        unplug_path = re.search(f".*{pci_addr}", sysfs_path)
        if not unplug_path:
            raise Exception(f"Failed to find controller for {device_id}")

        return unplug_path.group(0)

    @classmethod
    def get_pci_address(cls, device_id):
        sysfs_addr = VirtioDisk.get_sysfs_addr(device_id)
        pci_address = re.findall(r"\d+:[\da-f]+:[\da-f]+.\d+", sysfs_addr)

        if not pci_address:
            raise Exception(f"Failed to get the pci address of {device_id} device.")

        return pci_address[-1]

    @classmethod
    def get_sysfs_addr(cls, device_id):
        ls_command = f"$(find -H /sys/devices/ -name {device_id} -type d)"
        output = fs_utils.ls_item(f"{ls_command}")
        sysfs_addr = fs_utils.parse_ls_output(output)[0]
        if not sysfs_addr:
            raise Exception(f"Failed to find sysfs address: ls -l {ls_command}")

        return sysfs_addr.full_path


