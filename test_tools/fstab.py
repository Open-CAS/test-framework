#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from test_tools.fs_tools import append_line, remove_lines
from test_tools.systemctl import reload_daemon, restart_service


def add_mountpoint(device, mount_point, fs_type, mount_now=True):
    append_line("/etc/fstab",
                f"{device.path} {mount_point} {fs_type.name} defaults 0 0")
    reload_daemon()
    if mount_now:
        restart_service("local-fs.target")


def remove_mountpoint(device):
    remove_lines("/etc/fstab", device.path)
    reload_daemon()
