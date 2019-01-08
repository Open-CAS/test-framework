#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import enum


class Unit(enum.Enum):
    Byte = 1
    KiloByte = 1000
    KibiByte = 1024
    MegaByte = 1000 * KiloByte
    MebiByte = 1024 * KibiByte
    GigaByte = 1000 * MegaByte
    GibiByte = 1024 * MebiByte
    TeraByte = 1000 * GigaByte
    TebiByte = 1024 * GibiByte
    Blocks512 = 512
    Blocks4096 = 4096


class Size:
    def __init__(self, value: float, unit: Unit):
        if value < 0:
            raise ValueError("Size has to be positive.")
        self.value = value * unit.value
        self.unit = unit

    def get_value(self, target_unit: Unit):
        return self.value / target_unit.value

    def to_string(self):
        return "{} {}".format(self.get_value(self.unit), self.unit.name)

    def is_zero(self):
        if self.value == 0:
            return True
        else:
            return False

    @staticmethod
    def zero():
        return Size(0, Unit.Byte)

