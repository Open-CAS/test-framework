#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from core.test_run import TestRun


class Udev(object):
    @staticmethod
    def enable():
        TestRun.LOGGER.info("Enabling udev")
        TestRun.executor.run_expect_success("udevadm control --start-exec-queue")

    @staticmethod
    def disable():
        TestRun.LOGGER.info("Disabling udev")
        TestRun.executor.run_expect_success("udevadm control --stop-exec-queue")

    @staticmethod
    def trigger():
        TestRun.executor.run_expect_success("udevadm trigger")

    @staticmethod
    def settle():
        TestRun.executor.run_expect_success("udevadm settle")
