#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2023-2025 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import posixpath
import re
import time
from enum import Enum
from typing import List

from core.test_run import TestRun
from test_tools.dd import Dd
from test_tools.fs_tools import readlink, parse_ls_output, ls, check_if_directory_exists, \
    create_directory, wipefs, is_mounted
from test_tools.udev import Udev
from type_def.size import Size, Unit

SECTOR_SIZE = 512


class PartitionTable(Enum):
    msdos = 0
    gpt = 1


class PartitionType(Enum):
    efi = 0
    primary = 1
    extended = 2
    logical = 3
    lvm = 4
    msr = 5
    swap = 6
    standard = 7
    unknown = 8


def create_partition_table(device, partition_table_type: PartitionTable = PartitionTable.gpt):
    TestRun.LOGGER.info(
        f"Creating partition table ({partition_table_type.name}) for device: {device.path}")
    cmd = f'parted --script {device.path} mklabel {partition_table_type.name}'
    TestRun.executor.run_expect_success(cmd)
    device.partition_table = partition_table_type
    TestRun.LOGGER.info(
        f"Successfully created {partition_table_type.name} "
        f"partition table on device: {device.path}")


def get_partition_path(parent_dev, number):
    # TODO: change this to be less specific hw dependent (kernel)
    if "dev/cas" not in parent_dev:
        id_separator = '-part'
    else:
        id_separator = 'p'  # "cas1-1p1"
    return f'{parent_dev}{id_separator}{number}'


def discover_partition(device) -> list:
    cmd = (
        f"lsblk -ln -o NAME,TYPE {device.path} " + r"""| awk '$2 == "part" { print "/dev/" $1 }'"""
    )

    output = TestRun.executor.run(cmd).stdout
    partition_list = [line for line in output.split("\n") if line]
    if not partition_list:
        return []

    device_name = re.search(r"^(/dev/\S+)(?=\d+)", partition_list[0]).group()
    if "nvme" in partition_list[0]:
        device_name = device_name[:-1]

    # needs to be placed here (circular dependency)
    from storage_devices.partition import Partition

    partitions_on_device_list = []

    cmd = f"fdisk -l --bytes {device_name}" + r"| grep -E '^/dev/[a-z]+[0-9]+'"
    output = TestRun.executor.run(cmd).stdout.split("\n")

    for partition in partition_list:
        disk_params = [
            x for x in next(param for param in output if partition in param).split(" ") if x
        ]
        partition_number = int(re.search(r"(\d+)(?!.*\d)", disk_params[0]).group())

        part_number = int(partition_number)
        begin = Size(int(disk_params[1]), Unit.Byte)
        end = Size(
            (int(disk_params[2])),
            Unit.Byte,
        )
        partitions_on_device_list.append(
            Partition(
                parent_dev=device,
                type=PartitionType.logical,
                number=part_number,
                begin=begin,
                end=end,
            )
        )

    return partitions_on_device_list


def remove_parition(device, part_number):
    TestRun.LOGGER.info(f"Removing part {part_number} from {device.path}")
    cmd = f'parted --script {device.path} rm {part_number}'
    output = TestRun.executor.run(cmd)

    if output.exit_code != 0:
        TestRun.executor.run_expect_success("partprobe")


def create_partition(
        device,
        part_size,
        part_number,
        part_type: PartitionType = PartitionType.primary,
        unit=Unit.MebiByte,
        aligned: bool = True):
    TestRun.LOGGER.info(
        f"Creating {part_type.name} partition on device: {device.path}")

    begin = get_first_partition_offset(device, aligned)
    for part in device.partitions:
        begin += part.size
        if part.type == PartitionType.logical:
            begin += Size(1, Unit.MebiByte if not aligned else device.block_size)

    if part_type == PartitionType.logical:
        begin += Size(1, Unit.MebiByte if not aligned else device.block_size)

    if part_size != Size.zero():
        end = (begin + part_size)
        end_cmd = f'{end.get_value(unit)}{unit_to_string(unit)}'
    else:
        end_cmd = '100%'

    cmd = f'parted --script {device.path} mkpart ' \
          f'{part_type.name} ' \
          f'{begin.get_value(unit)}{unit_to_string(unit)} ' \
          f'{end_cmd}'
    output = TestRun.executor.run(cmd)

    if output.exit_code != 0:
        TestRun.executor.run_expect_success("partprobe")

    TestRun.executor.run_expect_success("udevadm settle")
    if not check_partition_after_create(
            size=part_size,
            part_number=part_number,
            parent_dev_path=device.path,
            part_type=part_type,
            aligned=aligned):
        raise Exception("Could not create partition!")

    if part_type != PartitionType.extended:
        from storage_devices.partition import Partition
        new_part = Partition(device,
                             part_type,
                             part_number,
                             begin,
                             end if type(end) is Size else device.size)
        dd = Dd().input("/dev/zero") \
                 .output(new_part.path) \
                 .count(1) \
                 .block_size(Size(1, Unit.Blocks4096)) \
                 .oflag("direct")
        dd.run()
        device.partitions.append(new_part)

    TestRun.LOGGER.info(f"Successfully created {part_type.name} partition on {device.path}")


def available_disk_size(device):
    dev = f"/dev/{device.get_device_id()}"
    # get number of device's sectors
    disk_sectors = int(TestRun.executor.run(f"fdisk -l {dev} | grep {dev} | grep sectors "
                                            f"| awk '{{print $7 }}' ").stdout)
    # get last occupied sector
    last_occupied_sector = int(TestRun.executor.run(f"fdisk -l {dev} | grep {dev} "
                                                    f"| awk '{{print $3 }}' | tail -1").stdout)
    available_disk_sectors = disk_sectors - last_occupied_sector
    return Size(available_disk_sectors, Unit(get_block_size(device)))


def create_partitions(device, sizes: [], partition_table_type=PartitionTable.gpt):
    create_partition_table(device, partition_table_type)
    partition_type = PartitionType.primary
    partition_number_offset = 0
    msdos_part_max_size = Size(2, Unit.TeraByte)

    for s in sizes:
        size = Size(
            s.get_value(device.block_size) - 1, device.block_size)
        if partition_table_type == PartitionTable.msdos and \
                len(sizes) > 4 and len(device.partitions) == 3:
            if available_disk_size(device) > msdos_part_max_size:
                part_size = msdos_part_max_size
            else:
                part_size = Size.zero()
            create_partition(device,
                             part_size,
                             4,
                             PartitionType.extended)
            partition_type = PartitionType.logical
            partition_number_offset = 1

        partition_number = len(device.partitions) + 1 + partition_number_offset
        create_partition(device=device,
                         part_size=size,
                         part_number=partition_number,
                         part_type=partition_type,
                         unit=device.block_size,
                         aligned=True)


def get_block_size(device):
    try:
        block_size = float(TestRun.executor.run(
            f"cat {get_sysfs_path(device)}/queue/hw_sector_size").stdout)
    except ValueError:
        block_size = Unit.Blocks512.value
    return block_size


def get_size(device):
    output = TestRun.executor.run_expect_success(f"cat {get_sysfs_path(device)}/size")
    blocks_count = int(output.stdout)
    return blocks_count * SECTOR_SIZE


def get_sysfs_path(device):
    sysfs_path = f"/sys/class/block/{device}"
    if TestRun.executor.run(f"test -d {sysfs_path}").exit_code != 0:
        sysfs_path = f"/sys/block/{device}"
    return sysfs_path


def get_pci_address(device):
    pci_address = TestRun.executor.run(f"cat /sys/block/{device}/device/address").stdout
    return pci_address


def check_partition_after_create(size: Size, part_number: int, parent_dev_path: str,
                                 part_type: PartitionType, aligned: bool):
    partition_path = get_partition_path(parent_dev_path, part_number)
    if "dev/cas" not in partition_path:
        cmd = f"find {partition_path} -type l"
    else:
        cmd = f"find {partition_path}"
    output = TestRun.executor.run_expect_success(cmd).stdout
    if partition_path not in output:
        TestRun.LOGGER.info(
            "Partition created, but could not find it in system, trying 'hdparm -z'")
        TestRun.executor.run_expect_success(f"hdparm -z {parent_dev_path}")
        output_after_hdparm = TestRun.executor.run_expect_success(
            f"parted --script {parent_dev_path} print").stdout
        TestRun.LOGGER.info(output_after_hdparm)

    counter = 0
    while partition_path not in output and counter < 10:
        time.sleep(2)
        output = TestRun.executor.run(cmd).stdout
        counter += 1

    if len(output.split('\n')) > 1 or partition_path not in output:
        return False

    if aligned and part_type != PartitionType.extended \
            and size.get_value(Unit.Byte) % Unit.Blocks4096.value != 0:
        TestRun.LOGGER.warning(
            f"Partition {partition_path} is not 4k aligned: {size.get_value(Unit.KibiByte)}KiB")

    partition_size = get_size(readlink(partition_path).split('/')[-1])
    if part_type == PartitionType.extended or \
            partition_size == size.get_value(Unit.Byte):
        return True

    TestRun.LOGGER.warning(
        f"Partition size {partition_size} does not match expected {size.get_value(Unit.Byte)} size."
    )
    return True


def get_first_partition_offset(device, aligned: bool):
    if aligned:
        return Size(1, Unit.MebiByte)
    # 33 sectors are reserved for the backup GPT
    return Size(34, Unit(device.blocksize)) \
        if device.partition_table == PartitionTable.gpt else Size(1, device.blocksize)


def remove_partitions(device):
    if is_mounted(device.path):
        device.unmount()

    for partition in device.partitions:
        unmount(partition)

    TestRun.LOGGER.info(f"Removing partitions from device: {device.path} "
                        f"({device.get_device_id()}).")
    wipefs(device)
    Udev.trigger()
    Udev.settle()
    output = TestRun.executor.run(f"ls {device.path}* -1")
    if len(output.stdout.split('\n')) > 1:
        TestRun.LOGGER.error(f"Could not remove partitions from device {device.path}")
        return False
    return True


def mount(device, mount_point, options: [str] = None):
    if not check_if_directory_exists(mount_point):
        create_directory(mount_point, True)
    TestRun.LOGGER.info(f"Mounting device {device.path} ({device.get_device_id()}) "
                        f"to {mount_point}.")
    cmd = f"mount {device.path} {mount_point}"
    if options:
        cmd = f"{cmd} -o {','.join(options)}"
    output = TestRun.executor.run(cmd)
    if output.exit_code != 0:
        raise Exception(f"Failed to mount {device.path} to {mount_point}")
    device.mount_point = mount_point


def unmount(device):
    TestRun.LOGGER.info(f"Unmounting device {device.path} ({device.get_device_id()}).")
    if device.mount_point is not None:
        output = TestRun.executor.run(f"umount {device.mount_point}")
        if output.exit_code != 0:
            TestRun.LOGGER.error("Could not unmount device.")
            return False
        return True
    else:
        TestRun.LOGGER.info("Device is not mounted.")
        return True


def unit_to_string(unit):
    unit_string = {
        Unit.Byte: 'B',
        Unit.Blocks512: 's',
        Unit.Blocks4096: 's',
        Unit.KibiByte: 'KiB',
        Unit.MebiByte: 'MiB',
        Unit.GibiByte: 'GiB',
        Unit.TebiByte: 'TiB',
        Unit.KiloByte: 'kB',
        Unit.MegaByte: 'MB',
        Unit.GigaByte: 'GB',
        Unit.TeraByte: 'TB'
    }
    return unit_string.get(unit, "Invalid unit.")


def check_if_device_supports_trim(device):
    if device.get_device_id().startswith("nvme"):
        return True
    command_output = TestRun.executor.run(f'hdparm -I {device.path} | grep "TRIM supported"')
    if command_output.exit_code == 0:
        return True
    command_output = TestRun.executor.run(
        f"lsblk -dn {device.path} -o DISC-MAX | grep -o \'[0-9]\\+\'"
    )
    return int(command_output.stdout) > 0


def _is_by_id_path(path: str):
    """check if given path already is proper by-id path"""
    dev_by_id_dir = "/dev/disk/by-id"
    by_id_paths = parse_ls_output(ls(dev_by_id_dir), dev_by_id_dir)
    return path in [posixpath.join(dev_by_id_dir, id_path.full_path) for id_path in by_id_paths]


def _is_dev_path_whitelisted(path: str):
    """check if given path is whitelisted"""
    whitelisted_paths = [
        r"/dev/ram\d+",
        r"/nullb\d+",
        r"/dev/drbd\d+",
        r"cas\d+-\d+",
        r"/dev/dm-\d+"
    ]

    for whitelisted_path in whitelisted_paths:
        if re.search(whitelisted_path, path) is not None:
            return True

    return False


def validate_dev_path(path: str):
    if not posixpath.isabs(path):
        raise ValueError(f'Given path "{path}" is not absolute.')

    if _is_dev_path_whitelisted(path):
        return path

    if _is_by_id_path(path):
        return path

    raise ValueError(f'By-id device link {path} is broken.')


def get_block_device_names_list(exclude_list: List[int] = None) -> List[str]:
    cmd = "lsblk -lo NAME"
    if exclude_list is not None:
        cmd += f" -e {','.join(str(type_id) for type_id in exclude_list)}"
    devices = TestRun.executor.run_expect_success(cmd).stdout
    devices_list = devices.splitlines()
    devices_list.sort()
    return devices_list
