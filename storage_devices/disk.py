#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from enum import Enum
from utils.size import Size, Unit
from test_tools import disk_utils
from storage_devices.partition import Partition
from storage_devices.device import Device


class DiskType(Enum):
    optane = 0
    nand = 1
    sata = 2
    hdd4k = 3
    hdd = 4


class Disk(Device):
    def __init__(self, path, disk_type: DiskType, serial_number, block_size):
        Device.__init__(self, path)
        self.serial_number = serial_number
        self.block_size = Unit(block_size)
        self.disk_type = disk_type
        self.partition_table = None
        self.partitions = []

    @classmethod
    def cast_to_disk(cls, disk):
        return cls(disk.system_path, disk.disk_type, disk.serial_number, disk.size, disk.block_size)

    def create_partitions(
            self,
            size: Size,
            partitions_count=1,
            partition_table_type=disk_utils.PartitionTable.msdos
    ):
        if disk_utils.create_partition_table(self, partition_table_type):
            self.partition_table = partition_table_type
            partition_type = disk_utils.PartitionType.primary

            size = Size(
                size.get_value(self.block_size) - self.block_size.value, self.block_size)
            partition_number_offset = 0
            for i in range(partitions_count):
                if partition_table_type == disk_utils.PartitionTable.msdos and \
                        partitions_count > 4 and len(self.partitions) == 3:
                    disk_utils.create_partition(self,
                                                Size.zero(),
                                                4,
                                                disk_utils.PartitionType.extended,
                                                Unit.MebiByte,
                                                True)
                    partition_type = disk_utils.PartitionType.logical
                    partition_number_offset = 1

                partition_number = len(self.partitions) + 1 + partition_number_offset
                if disk_utils.create_partition(self,
                                               size,
                                               partition_number,
                                               partition_type,
                                               Unit.MebiByte,
                                               True):
                    new_part = Partition(self,
                                         partition_type,
                                         partition_number)
                    self.partitions.append(new_part)

    def remove_partitions(self):
        if disk_utils.remove_partitions(self):
            self.partitions.clear()

    def __str__(self):
        disk_str = f'system path: {self.system_path}, type: {self.disk_type}, ' \
            f'serial: {self.serial_number}, size: {self.size}, ' \
            f'block size: {self.block_size}, partitions:\n'
        for part in self.partitions:
            disk_str += f'\t{part}'
        return disk_str
