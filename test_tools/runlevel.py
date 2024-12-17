#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from enum import IntEnum

from core.test_run import TestRun
from test_tools.os_tools import SystemManagerType


class Runlevel(IntEnum):
    """
        Halt the system.
        SysV Runlevel: 0
        systemd Target: runlevel0.target, poweroff.target
    """
    runlevel0 = 0
    poweroff = runlevel0

    """
        Single user mode.
        SysV Runlevel: 1, s, single
        systemd Target: runlevel1.target, rescue.target
    """
    runlevel1 = 1
    rescue = runlevel1

    """
        User-defined/Site-specific runlevels. By default, identical to 3.
        SysV Runlevel: 2, 4
        systemd Target: runlevel2.target, runlevel4.target, multi-user.target
    """
    runlevel2 = 2

    """
        Multi-user, non-graphical. Users can usually login via multiple consoles or via the network.
        SysV Runlevel: 3
        systemd Target: runlevel3.target, multi-user.target
    """
    runlevel3 = 3
    multi_user = runlevel3

    """
        Multi-user, graphical. Usually has all the services of runlevel 3 plus a graphical login.
        SysV Runlevel: 5
        systemd Target: runlevel5.target, graphical.target
    """
    runlevel5 = 5
    graphical = runlevel5

    """
        Reboot
        SysV Runlevel: 6
        systemd Target: runlevel6.target, reboot.target
    """
    runlevel6 = 6
    reboot = runlevel6

    """
        Emergency shell
        SysV Runlevel: emergency
        systemd Target: emergency.target
    """
    runlevel7 = 7
    emergency = runlevel7


def get_system_manager():
    output = TestRun.executor.run_expect_success("ps -p 1").stdout
    type = output.split('\n')[1].split()[3]
    if type == "init":
        return SystemManagerType.sysv
    elif type == "systemd":
        return SystemManagerType.systemd
    raise Exception(f"Unknown system manager type ({type}).")


def change_runlevel(runlevel: Runlevel):
    if runlevel == get_runlevel():
        return
    if Runlevel.runlevel0 < runlevel < Runlevel.runlevel6:
        system_manager = get_system_manager()
        if system_manager == SystemManagerType.systemd:
            TestRun.executor.run_expect_success(f"systemctl set-default {runlevel.name}.target")
        else:
            TestRun.executor.run_expect_success(
                f"sed -i 's/^.*id:.*$/id:{runlevel.value}:initdefault: /' /etc/inittab")
            TestRun.executor.run_expect_success(f"init {runlevel.value}")


def get_runlevel():
    system_manager = get_system_manager()
    if system_manager == SystemManagerType.systemd:
        result = TestRun.executor.run_expect_success("systemctl get-default")
        try:
            name = result.stdout.split(".")[0].replace("-", "_")
            return Runlevel[name]
        except Exception:
            raise Exception(f"Cannot parse '{result.output}' to runlevel.")
    else:
        result = TestRun.executor.run_expect_success("runlevel")
        try:
            split_output = result.stdout.split()
            runlevel = Runlevel(int(split_output[1]))
            return runlevel
        except Exception:
            raise Exception(f"Cannot parse '{result.output}' to runlevel.")
