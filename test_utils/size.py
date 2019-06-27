#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import enum
import math
from multimethod import multimethod


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
    def __init__(self, value: float, unit: Unit = Unit.Byte):
        if value < 0:
            raise ValueError("Size has to be positive.")
        self.value = value * unit.value
        self.unit = unit

    def __str__(self):
        return f"{self.get_value(self.unit)} {self.unit.name}"

    def __int__(self):
        return int(self.get_value())

    def __add__(self, other):
        return Size(self.get_value() + other.get_value())

    def __lt__(self, other):
        return self.get_value() < other.get_value()

    def __le__(self, other):
        return self.get_value() <= other.get_value()

    def __eq__(self, other):
        return self.get_value() == other.get_value()

    def __ne__(self, other):
        return self.get_value() != other.get_value()

    def __gt__(self, other):
        return self.get_value() > other.get_value()

    def __ge__(self, other):
        return self.get_value() >= other.get_value()

    def __sub__(self, other):
        if self < other:
            raise ValueError("Subtracted value is too big. Result size cannot be negative.")
        return Size(self.get_value() - other.get_value())

    def __mul__(self, other: int):
        return Size(math.ceil(self.get_value() * other))

    @multimethod
    def __truediv__(self, other):
        if other.get_value() == 0:
            raise ValueError("Divisor must not be equal to 0.")
        return self.get_value() / other.get_value()

    @multimethod
    def __truediv__(self, other: int):
        if other == 0:
            raise ValueError("Divisor must not be equal to 0.")
        return Size(math.ceil(self.get_value() / other))

    def get_value(self, target_unit: Unit = Unit.Byte):
        return self.value / target_unit.value

    def is_zero(self):
        if self.value == 0:
            return True
        else:
            return False

    @staticmethod
    def zero():
        return Size(0)
