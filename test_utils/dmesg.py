#
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from core.test_run import TestRun
from test_utils.output import Output


def get_dmesg() -> str:
    return TestRun.executor.run("dmesg").stdout


def clear_dmesg() -> Output:
    return TestRun.executor.run("dmesg -C")
