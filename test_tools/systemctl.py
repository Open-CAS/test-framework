#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024-2025 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from pathlib import PurePosixPath

from core.test_run import TestRun

systemd_service_directory = PurePosixPath("/usr/lib/systemd/system/")


def enable_service(name):
    TestRun.executor.run_expect_success(f"systemctl enable {name}")


def disable_service(name):
    TestRun.executor.run_expect_success(f"systemctl disable {name}")


def reload_daemon():
    TestRun.executor.run_expect_success("systemctl daemon-reload")


def restart_service(name):
    TestRun.executor.run_expect_success(f"systemctl restart {name}")


def get_service_path(unit_name):
    cmd = f"systemctl cat {unit_name}"

    # path is in second column of first line of output
    info = TestRun.executor.run_expect_success(cmd).stdout
    path = info.splitlines()[0].split()[1]

    return path
