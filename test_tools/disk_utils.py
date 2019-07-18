#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from test_package.test_properties import TestProperties
from enum import Enum
from test_utils.size import Size, Unit
from test_tools.dd import Dd
import time
import re


class Filesystem(Enum):
    xfs = 0,
    ext3 = 1,
    ext4 = 2


class PartitionTable(Enum):
    msdos = 0,
    gpt = 1


class PartitionType(Enum):
    efi = 0,
    primary = 1,
    extended = 2,
    logical = 3,
    lvm = 4,
    msr = 5,
    swap = 6,
    standard = 7,
    unknown = 8


def create_filesystem(device, filesystem: Filesystem, force=True, blocksize=None):
    TestProperties.LOGGER.info(
        f"Creating filesystem ({filesystem.name}) on device: {device.system_path}")
    force_param = ' -f ' if filesystem == Filesystem.xfs else ' -F '
    force_param = force_param if force else ''
    block_size_param = f' -b size={blocksize}' if filesystem == Filesystem.xfs \
        else f' -b {blocksize}'
    block_size_param = block_size_param if blocksize else ''
    cmd = f'mkfs.{filesystem.name}{force_param}{device.system_path}{block_size_param}'
    cmd = re.sub(' +', ' ', cmd)
    output = TestProperties.executor.execute(cmd)
    if output.exit_code == 0:
        TestProperties.LOGGER.info(
            f"Successfully created filesystem on device: {device.system_path}")
        return True

    TestProperties.LOGGER.error(
        f"Could not create filesystem: {output.stderr}\n{output.stdout}")
    return False


def create_partition_table(device, partition_table_type: PartitionTable = PartitionTable.msdos):
    TestProperties.LOGGER.info(
        f"Creating partition table ({partition_table_type.name}) for device: {device.system_path}")
    cmd = f'parted --script {device.system_path} mklabel {partition_table_type.name}'
    output = TestProperties.executor.execute(cmd)
    if output.exit_code == 0:
        TestProperties.LOGGER.info(
            f"Successfully created {partition_table_type.name} "
            f"partition table on device: {device.system_path}")
        return True

    TestProperties.LOGGER.error(
        f"Could not create partition table: {output.stderr}\n{output.stdout}")
    return False


def get_partition_path(parent_dev, number):
    # TODO: change this to be less specific hw dependent
    id_separator = 'p' if parent_dev[-1].isdigit() else ''
    return f'{parent_dev}{id_separator}{number}'


def create_partition(
        device,
        part_size,
        part_number,
        part_type: PartitionType = PartitionType.primary,
        unit=Unit.MebiByte,
        aligned: bool = True):
    TestProperties.LOGGER.info(
        f"Creating {part_type.name} partition on device: {device.system_path}")

    begin = get_first_partition_offset(device, aligned).get_value(unit)
    for part in device.partitions:
        begin += part.size.get_value(unit)
        if part.type == PartitionType.logical:
            begin += Size(1, Unit.MebiByte if not aligned else device.block_size).get_value(unit)

    if part_type == PartitionType.logical:
        begin += Size(1, Unit.MebiByte if not aligned else device.block_size).get_value(unit)

    end = f'{begin + part_size.get_value(unit)}{unit_to_string(unit)}' \
        if part_size != Size.zero() else '100%'

    cmd = f'parted --script {device.system_path} mkpart ' \
        f'{part_type.name} {begin}{unit_to_string(unit)} {end}'
    output = TestProperties.executor.execute(cmd)

    if output.exit_code == 0:
        TestProperties.executor.execute("udevadm settle")
        if check_partition_after_create(
                part_size,
                part_number,
                device.system_path,
                part_type,
                aligned):
            TestProperties.LOGGER.info(f"Successfully created partition on {device.system_path}")
            return True
    raise Exception(f"Could not create partition: {output.stderr}\n{output.stdout}")


def get_block_size(device):
    try:
        block_size = float(TestProperties.executor.execute(
            f"cat {get_sysfs_path(device)}/queue/hw_sector_size").stdout)
    except ValueError:
        block_size = Unit.Blocks512.value
    return block_size


def get_size(device):
    blocks_count = int(TestProperties.executor.execute(f"cat {get_sysfs_path(device)}/size").stdout)
    return blocks_count * int(get_block_size(device))


def get_sysfs_path(device):
    sysfs_path = f"/sys/class/block/{device}"
    if TestProperties.executor.execute(f"test -d {sysfs_path}").exit_code != 0:
        sysfs_path = f"/sys/block/{device}"
    return sysfs_path


def check_partition_after_create(size, part_number, parent_dev_path, part_type, aligned):
    partition_path = get_partition_path(parent_dev_path, part_number)
    cmd = f"find {partition_path} -type b"
    output = TestProperties.executor.execute(cmd).stdout
    if partition_path not in output:
        TestProperties.LOGGER.info(
            "Partition created, but could not find it in system, trying 'hdparm -z'")
        TestProperties.executor.execute(f"hdparm -z {parent_dev_path}")
        output_after_hdparm = TestProperties.executor.execute(
            f"parted --script {parent_dev_path} print")
        TestProperties.LOGGER.info(output_after_hdparm)

    counter = 0
    while partition_path not in output and counter < 10:
        time.sleep(2)
        output = TestProperties.executor.execute(cmd).stdout
        counter += 1

    if len(output.split('\n')) > 1 or partition_path not in output:
        return False

    if aligned and part_type != PartitionType.extended \
            and size.get_value(Unit.Byte) % Unit.Blocks4096.value != 0:
        TestProperties.LOGGER.warn(
            f"Partition {partition_path} is not 4k aligned: {size.get_value(Unit.KibiByte)}KiB")

    if part_type == PartitionType.extended or \
            get_size(partition_path.replace('/dev/', '')) == size.get_value(Unit.Byte):
        return True

    TestProperties.LOGGER.warn(
        f"Partition size {get_size(partition_path.replace('/dev/', ''))} does not match expected "
        f"{size.get_value(Unit.Byte)} size.")
    return True


def get_first_partition_offset(device, aligned: bool):
    if aligned:
        return Size(1, Unit.MebiByte)
    # 33 sectors are reserved for the backup GPT
    return Size(34, Unit(device.blocksize)) \
        if device.partition_table == PartitionTable.gpt else Size(1, device.blocksize)


def remove_partitions(device):
    if device.is_mounted():
        device.unmount()

    for partition in device.partitions:
        unmount(partition)

    TestProperties.LOGGER.info(f"Removing partitions from device: {device.system_path}.")
    dd = Dd().input("/dev/zero") \
        .output(device.system_path) \
        .count(1) \
        .block_size(Size(device.block_size.value, Unit.Byte))
    dd.run()
    output = TestProperties.executor.execute(f"ls {device.system_path}* -1")
    if len(output.stdout.split('\n')) > 1:
        TestProperties.LOGGER.error(f"Could not remove partitions from device {device.system_path}")
        return False
    return True


def mount(device, mount_point):
    TestProperties.LOGGER(f"Mounting device {device.system_path} to {mount_point}.")
    cmd = f"mount {device.system_path} {mount_point}"
    output = TestProperties.executor.execute(cmd)
    if output.exit_code != 0:
        TestProperties.LOGGER.error(f"Failed to mount {device.system_path} to {mount_point}")
        return False
    return True


def unmount(device):
    TestProperties.LOGGER(f"Unmounting device {device.system_path}.")
    if device.mount_point is not None:
        output = TestProperties.executor.execute(f"umount {device.mount_point}")
        if output.exit_code != 0:
            TestProperties.LOGGER.error("Could not unmount device.")
            return False
        return True
    else:
        TestProperties.LOGGER.info("Device is not mounted.")
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
