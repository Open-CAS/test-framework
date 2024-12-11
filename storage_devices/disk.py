#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import json
import re

from datetime import timedelta
from enum import IntEnum

from core.test_run import TestRun
from storage_devices.device import Device
from test_tools import disk_utils, fs_utils, nvme_cli
from test_tools.common.wait import wait
from connection.utils.output import Output
from test_tools.disk_finder import get_block_devices_list, resolve_to_by_id_link
from type_def.size import Unit


class DiskType(IntEnum):
    hdd = 0
    hdd4k = 1
    sata = 2
    nand = 3
    optane = 4


def static_init(cls):
    if getattr(cls, "static_init", None):
        cls.static_init()
    return cls


class DiskTypeSetBase:
    def resolved(self):
        raise NotImplementedError()

    def types(self):
        raise NotImplementedError()

    def json(self):
        return json.dumps(
            {
                "type": "set",
                "values": [t.name for t in self.types()],
            }
        )

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
        return json.dumps(
            {
                "type": "operator",
                "name": "lt",
                "args": [self.__disk_name],
            }
        )


class Disk(Device):
    types_registry = []

    def __init__(
        self,
        path,
        disk_type: DiskType,
        serial_number,
        block_size,
    ):
        Device.__init__(self, path)
        self.disk_type = disk_type
        self.serial_number = serial_number
        self.block_size = Unit(block_size)
        self.device_id = self.get_device_id()
        self.partitions = []
        self.pci_address = None

    @classmethod
    def register_type(cls, new_type):
        cls.types_registry.append(new_type)

    @classmethod
    def resolve_type(cls, disk_path):
        recognized_types = [
            disk_type for disk_type in cls.types_registry if disk_type.identify(disk_path)
        ]
        if len(recognized_types) == 0:
            raise TypeError(f"Framework is not able to recognise disk type for disk {disk_path}")
        if len(recognized_types) > 1:
            raise TypeError(
                f"Disk {disk_path} recognized as at least 2 disk types.\n"
                f"Recognized disk types are {recognized_types}"
            )
        return recognized_types[0]

    def create_partitions(self, sizes: [], partition_table_type=disk_utils.PartitionTable.gpt):
        disk_utils.create_partitions(self, sizes, partition_table_type)

    def remove_partition(self, part):
        part_number = int(part.path.split("part")[1])
        disk_utils.remove_parition(self, part_number)
        self.partitions.remove(part)

    def umount_all_partitions(self):
        TestRun.LOGGER.info(f"Unmounting all partitions from: {self.path}")
        cmd = f"umount -l {fs_utils.readlink(self.path)}*?"
        TestRun.executor.run(cmd)

    def remove_partitions(self):
        for part in self.partitions:
            if part.is_mounted():
                part.unmount()
        if disk_utils.remove_partitions(self):
            self.partitions.clear()

    def is_detected(self):
        if self.serial_number:
            serial_numbers = Disk.get_all_serial_numbers()
            return self.serial_number in serial_numbers
        elif self.path:
            output = fs_utils.ls_item(f"{self.path}")
            return fs_utils.parse_ls_output(output)[0] is not None
        raise Exception("Couldn't check if device is detected by the system")

    def wait_for_plug_status(self, should_be_visible):
        if not wait(
            lambda: should_be_visible == self.is_detected(),
            timedelta(minutes=1),
            timedelta(seconds=1),
        ):
            raise Exception(
                f"Timeout occurred while trying to "
                f"{'plug' if should_be_visible else 'unplug'} disk."
            )

    @classmethod
    def plug_all(cls):
        raise NotImplementedError

    def plug(self):
        raise NotImplementedError

    def unplug(self):
        if not self.is_detected():
            return
        self.__unplug()
        self.device_id = None
        self.wait_for_plug_status(False)

    def __unplug(self):
        raise NotImplementedError

    def __str__(self):
        disk_str = (
            f"system path: {self.path}, type: {self.disk_type.name}, "
            f"serial: {self.serial_number}, size: {self.size}, "
            f"block size: {self.block_size}, pci address: {self.pci_address}, partitions:\n"
        )
        for part in self.partitions:
            disk_str += f"\t{part}"
        return disk_str

    @staticmethod
    def create_disk(disk_path: str, disk_type: DiskType, serial_number: str, block_size: Unit):
        resolved_disk_type = Disk.resolve_type(disk_path=disk_path)
        return resolved_disk_type(disk_path, disk_type, serial_number, block_size)

    @classmethod
    def plug_all_disks(cls):
        for disk_type in cls.types_registry:
            disk_type.plug_all()

    @staticmethod
    def get_all_serial_numbers():
        serial_numbers = {}
        block_devices = get_block_devices_list()
        for dev in block_devices:
            serial = Disk.get_disk_serial_number(dev)
            try:
                path = resolve_to_by_id_link(dev)
            except Exception:
                continue
            if serial:
                serial_numbers[serial] = path
            else:
                TestRun.LOGGER.warning(f"Device {path} ({dev}) does not have a serial number.")
                serial_numbers[path] = path
        return serial_numbers

    @staticmethod
    def get_disk_serial_number(dev_path):
        commands = [
            f"(udevadm info --query=all --name={dev_path} | grep 'SCSI.*_SERIAL' || "
            f"udevadm info --query=all --name={dev_path} | grep 'ID_SERIAL_SHORT') | "
            "awk -F '=' '{print $NF}'",
            f"sg_inq {dev_path} 2> /dev/null | grep '[Ss]erial number:' | "
            "awk '{print $NF}'",
            f"udevadm info --query=all --name={dev_path} | grep 'ID_SERIAL' | "
            "awk -F '=' '{print $NF}'"
        ]
        for command in commands:
            serial = TestRun.executor.run(command).stdout
            if serial:
                return serial.split('\n')[0]
        return None


@static_init
class NvmeDisk(Disk):
    def __init__(self, path, disk_type, serial_number, block_size):
        super().__init__(path, disk_type, serial_number, block_size)
        self.__pci_address = self.get_pci_address(device_id=self.device_id)

    @classmethod
    def static_init(cls):
        Disk.register_type(new_type=cls)

    @classmethod
    def plug_all(cls) -> Output:
        command = "echo 1 > /sys/bus/pci/rescan"
        output = TestRun.executor.run_expect_success(command)
        return output

    def unplug(self) -> Output:
        command = (
            f"echo 1 > /sys/block/{self.device_id}/device/remove || echo 1 > /sys/block/"
            f"{self.device_id}/device/device/remove"
        )
        output = TestRun.executor.run(command)
        return output

    def format_disk(
        self, metadata_size=None, block_size=None, force=True, format_params=None, reset=True
    ):
        nvme_cli.format_disk(self, metadata_size, block_size, force, format_params, reset)

    def get_lba_formats(self):
        return nvme_cli.get_lba_formats(self)

    def get_lba_format_in_use(self):
        return nvme_cli.get_lba_format_in_use(self)

    @staticmethod
    def get_unplug_path(device_id) -> str:
        base = f"/sys/block/{device_id}/device"
        for suffix in ["/remove", "/device/remove"]:
            try:
                output = fs_utils.ls_item(base + suffix)
                fs_utils.parse_ls_output(output)[0]
            except TypeError:
                continue
            return base + suffix
        raise Exception(f"Couldn't create unplug path for {device_id}")

    @staticmethod
    def get_pci_address(device_id) -> str:
        return TestRun.executor.run(f"cat /sys/block/{device_id}/device/address").stdout

    @staticmethod
    def identify(device_path: str) -> bool:
        device_name = TestRun.executor.run(f"realpath {device_path}").stdout.split("/")[2]
        output = TestRun.executor.run(
            f"realpath /sys/block/{device_name}/device/driver | grep nvme"
        )
        return output.exit_code == 0


@static_init
class SataDisk(Disk):
    def __init__(self, path, disk_type, serial_number, block_size):
        super().__init__(path, disk_type, serial_number, block_size)
        self.__pci_address = self.get_pci_address(device_id=self.device_id)

    @classmethod
    def static_init(cls):
        Disk.register_type(new_type=cls)

    @classmethod
    def plug_all(cls) -> Output:
        cmd = (
            "find -H /sys/devices/ -path '*/scsi_host/*/scan' -type f |"
            " xargs -P20 -I % sh -c \"echo '- - -' | tee %\""
        )
        output = TestRun.executor.run_expect_success(cmd)
        return output

    def unplug(self) -> Output:
        cmd = f"echo 1 > {self.get_unplug_path(device_id=self.device_id)}"
        output = TestRun.executor.run(cmd)
        return output

    def get_unplug_path(self, device_id) -> str:
        sysfs_addr = self.get_sysfs_addr(device_id)
        try:
            self.get_pci_address(device_id)
        except Exception as e:
            raise Exception(f"Failed to find controller for {device_id}.\n{e}")

        return sysfs_addr + "/device/delete"

    @staticmethod
    def get_sysfs_addr(device_id):
        ls_command = f"$(find -H /sys/devices/ -name {device_id} -type d)"
        output = fs_utils.ls_item(f"{ls_command}")
        sysfs_addr = fs_utils.parse_ls_output(output)[0]
        if not sysfs_addr:
            raise Exception(f"Failed to find sysfs address: ls -l {ls_command}")
        return sysfs_addr.full_path

    @staticmethod
    def get_pci_address(device_id):
        sysfs_addr = SataDisk.get_sysfs_addr(device_id)
        pci_address = re.findall(r"\d+:\d+:\d+.\d+", sysfs_addr)

        if not pci_address:
            raise Exception(f"Failed to get the pci address of {device_id} device.")

        return pci_address[-1]

    @staticmethod
    def identify(device_path: str) -> bool:
        device_name = TestRun.executor.run(f"realpath {device_path}").stdout.split("/")[2]
        output = TestRun.executor.run(
            f"realpath /sys/block/{device_name}/device/driver | grep scsi"
        )
        return output.exit_code == 0


@static_init
class VirtioDisk(Disk):
    def __init__(self, path, disk_type, serial_number, block_size):
        super().__init__(path, disk_type, serial_number, block_size)
        self.__pci_address = self.get_pci_address(device_id=self.device_id)

    @classmethod
    def static_init(cls) -> None:
        Disk.register_type(new_type=cls)

    @classmethod
    def plug_all(cls) -> Output:
        cmd = "echo 1 > /sys/bus/pci/rescan"
        output = TestRun.executor.run_expect_success(cmd)
        return output

    def unplug(self) -> Output:
        cmd = f"echo 1 > {self.get_unplug_path(device_id=self.device_id)}"
        output = TestRun.executor.run(cmd)
        return output

    @staticmethod
    def get_unplug_path(device_id) -> str:
        sysfs_path = VirtioDisk.get_sysfs_addr(device_id)
        pci_addr = VirtioDisk.get_pci_address(device_id)
        unplug_path = re.search(f".*{pci_addr}", sysfs_path)
        if not unplug_path:
            raise Exception(f"Failed to find controller for {device_id}")
        return unplug_path.group(0) + "/remove"

    @classmethod
    def get_pci_address(cls, device_id) -> str:
        sysfs_addr = cls.get_sysfs_addr(device_id)
        pci_address = re.findall(r"\d+:[\da-f]+:[\da-f]+.\d+", sysfs_addr)
        if not pci_address:
            raise Exception(f"Failed to get the pci address of {device_id} device.")

        return pci_address[-1]

    @staticmethod
    def get_sysfs_addr(device_id: str) -> str:
        ls_command = f"$(find -H /sys/devices/ -name {device_id} -type d)"
        output = fs_utils.ls_item(f"{ls_command}")
        sysfs_addr = fs_utils.parse_ls_output(output)[0]
        if not sysfs_addr:
            raise Exception(f"Failed to find sysfs address: ls -l {ls_command}")

        return sysfs_addr.full_path

    @staticmethod
    def identify(device_path: str) -> bool:
        device_name = TestRun.executor.run(f"realpath {device_path}").stdout.split("/")[2]
        output = TestRun.executor.run(
            f"realpath /sys/block/{device_name}/device/driver | grep virtio"
        )
        return output.exit_code == 0
