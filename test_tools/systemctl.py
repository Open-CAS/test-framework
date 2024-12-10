#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from pathlib import Path
from core.test_run import TestRun

systemd_service_directory = Path("/usr/lib/systemd/system/")

def enable_service(name):
    TestRun.executor.run_expect_success(f"systemctl enable {name}")


def disable_service(name):
    TestRun.executor.run_expect_success(f"systemctl disable {name}")


def reload_daemon():
    TestRun.executor.run_expect_success("systemctl daemon-reload")


def restart_service(name):
    TestRun.executor.run_expect_success(f"systemctl restart {name}")
