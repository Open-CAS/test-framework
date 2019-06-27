#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from enum import IntEnum, Enum
from test_utils.size import Size, Unit


class CacheLineSize(IntEnum):
    LINE_4KiB = Size(4, Unit.KibiByte)
    LINE_8KiB = Size(8, Unit.KibiByte)
    LINE_16KiB = Size(16, Unit.KibiByte)
    LINE_32KiB = Size(32, Unit.KibiByte)
    LINE_64KiB = Size(64, Unit.KibiByte)
    DEFAULT = LINE_4KiB


class CacheMode(Enum):
    WT = 0
    WB = 1
    WA = 2
    PT = 3
    WO = 4
    DEFAULT = WT


class SeqCutOffPolicy(Enum):
    full = 0
    always = 1
    never = 2
    DEFAULT = full


class CleaningPolicy(Enum):
    alru = 0
    nop = 1
    acp = 2
    DEFAULT = alru


# TODO: Use case for this will be to iterate over configurations (kernel params such as
# TODO: such as io scheduler, metadata layout) and prepare env before starting cache
class CacheConfig:
    def __init__(self):
        pass
