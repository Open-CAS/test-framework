#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import math

from connection.utils.output import CmdException
from core.test_run import TestRun
from test_tools.dd import Dd
from test_tools.fs_tools import check_if_directory_exists, create_directory, is_mounted
from test_tools.os_tools import OvercommitMemoryMode, drop_caches, DropCachesMode, \
    MEMORY_MOUNT_POINT
from type_def.size import Size, Unit


def disable_memory_affecting_functions():
    """Disables system functions affecting memory"""
    # Don't allow sshd to be killed in case of out-of-memory:
    TestRun.executor.run(
        "echo '-1000' > /proc/`cat /var/run/sshd.pid`/oom_score_adj"
    )
    TestRun.executor.run(
        "echo -17 > /proc/`cat /var/run/sshd.pid`/oom_adj"
    )  # deprecated
    TestRun.executor.run_expect_success(
        f"echo {OvercommitMemoryMode.NEVER.value} > /proc/sys/vm/overcommit_memory"
    )
    TestRun.executor.run_expect_success("echo '100' > /proc/sys/vm/overcommit_ratio")
    TestRun.executor.run_expect_success(
        "echo '64      64      32' > /proc/sys/vm/lowmem_reserve_ratio"
    )
    TestRun.executor.run_expect_success("swapoff --all")
    drop_caches(DropCachesMode.SLAB)


def defaultize_memory_affecting_functions():
    """Sets default values to system functions affecting memory"""
    TestRun.executor.run_expect_success(
        f"echo {OvercommitMemoryMode.DEFAULT.value} > /proc/sys/vm/overcommit_memory"
    )
    TestRun.executor.run_expect_success("echo 50 > /proc/sys/vm/overcommit_ratio")
    TestRun.executor.run_expect_success(
        "echo '256     256     32' > /proc/sys/vm/lowmem_reserve_ratio"
    )
    TestRun.executor.run_expect_success("swapon --all")


def get_mem_free():
    """Returns free amount of memory in bytes"""
    output = TestRun.executor.run_expect_success("free -b")
    output = output.stdout.splitlines()
    for line in output:
        if 'free' in line:
            index = line.split().index('free') + 1  # 1st row has 1 element less than following rows
        if 'Mem' in line:
            mem_line = line.split()

    return Size(int(mem_line[index]))


def get_mem_available():
    """Returns amount of available memory from /proc/meminfo"""
    cmd = "cat /proc/meminfo | grep MemAvailable | awk '{ print $2 }'"
    mem_available = TestRun.executor.run(cmd).stdout

    return Size(int(mem_available), Unit.KibiByte)


def get_module_mem_footprint(module_name):
    """Returns allocated size of specific module's metadata from /proc/vmallocinfo"""
    cmd = f"cat /proc/vmallocinfo | grep {module_name} | awk '{{ print $2 }}' "
    output_lines = TestRun.executor.run(cmd).stdout.splitlines()
    memory_used = 0
    for line in output_lines:
        memory_used += int(line)

    return Size(memory_used)


def allocate_memory(size: Size):
    """Allocates given amount of memory"""
    mount_ramfs()
    TestRun.LOGGER.info(f"Allocating {size.get_value(Unit.MiB):0.2f} MiB of memory.")
    bs = Size(1, Unit.Blocks512)
    dd = (
        Dd()
        .block_size(bs)
        .count(math.ceil(size / bs))
        .input("/dev/zero")
        .output(f"{MEMORY_MOUNT_POINT}/data")
    )
    output = dd.run()
    if output.exit_code != 0:
        raise CmdException("Allocating memory failed.", output)


def mount_ramfs():
    """Mounts ramfs to enable allocating memory space"""
    if not check_if_directory_exists(MEMORY_MOUNT_POINT):
        create_directory(MEMORY_MOUNT_POINT)
    if not is_mounted(MEMORY_MOUNT_POINT):
        TestRun.executor.run_expect_success(f"mount -t ramfs ramfs {MEMORY_MOUNT_POINT}")


def unmount_ramfs():
    """Unmounts ramfs and releases whole space allocated by it in memory"""
    TestRun.executor.run_expect_success(f"umount {MEMORY_MOUNT_POINT}")
