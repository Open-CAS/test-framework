#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import time
from datetime import timedelta, datetime

from aenum import IntFlag, Enum
from packaging import version

from core.test_run import TestRun
from test_tools.fs_utils import check_if_directory_exists
from test_utils.filesystem.file import File

DEBUGFS_MOUNT_POINT = "/sys/kernel/debug"


class DropCachesMode(IntFlag):
    PAGECACHE = 1
    SLAB = 2
    ALL = PAGECACHE | SLAB


class Udev(object):
    @staticmethod
    def enable():
        TestRun.LOGGER.info("Enabling udev")
        TestRun.executor.run_expect_success("udevadm control --start-exec-queue")

    @staticmethod
    def disable():
        TestRun.LOGGER.info("Disabling udev")
        TestRun.executor.run_expect_success("udevadm control --stop-exec-queue")


def drop_caches(level: DropCachesMode = DropCachesMode.PAGECACHE):
    TestRun.executor.run_expect_success(
        f"echo {level.value} > /proc/sys/vm/drop_caches")


def download_file(url, destination_dir="/tmp"):
    # TODO use wget module instead
    command = ("wget --tries=3 --timeout=5 --continue --quiet "
               f"--directory-prefix={destination_dir} {url}")
    TestRun.executor.run_expect_success(command)
    path = f"{destination_dir.rstrip('/')}/{File.get_name(url)}"
    return File(path)


def get_kernel_version():
    version_string = TestRun.executor.run_expect_success("uname -r").stdout
    version_string = version_string.split('-')[0]
    return version.Version(version_string)


class ModuleRemoveMethod(Enum):
    rmmod = "rmmod"
    modprobe = "modprobe -r"


def is_kernel_module_loaded(module_name):
    output = TestRun.executor.run(f"lsmod | grep ^{module_name}")
    return output.exit_code == 0


def get_sys_block_path():
    sys_block = "/sys/class/block"
    if not check_if_directory_exists(sys_block):
        sys_block = "/sys/block"
    return sys_block


def load_kernel_module(module_name, module_args: {str, str}=None):
    cmd = f"modprobe {module_name}"
    if module_args is not None:
        for key, value in module_args.items():
            cmd += f" {key}={value}"
    return TestRun.executor.run(cmd)


def unload_kernel_module(module_name, unload_method: ModuleRemoveMethod = ModuleRemoveMethod.rmmod):
    cmd = f"{unload_method.value} {module_name}"
    return TestRun.executor.run(cmd)


def is_mounted(path: str):
    if path is None or path.isspace():
        raise Exception("Checked path cannot be empty")
    command = f"mount | grep --fixed-strings '{path.rstrip('/')} '"
    return TestRun.executor.run(command).exit_code == 0


def mount_debugfs():
    if not is_mounted(DEBUGFS_MOUNT_POINT):
        TestRun.executor.run_expect_success(f"mount -t debugfs none {DEBUGFS_MOUNT_POINT}")


def reload_kernel_module(module_name, module_args: {str, str}=None):
    unload_kernel_module(module_name)
    time.sleep(1)
    load_kernel_module(module_name, module_args)


def kill_all_io():
    # TERM signal should be used in preference to the KILL signal, since a
    # process may install a handler for the TERM signal in order to perform
    # clean-up steps before terminating in an orderly fashion.
    TestRun.executor.run("killall -q --signal TERM dd fio")
    time.sleep(3)
    TestRun.executor.run("killall -q --signal KILL dd fio")
    TestRun.executor.run("kill -9 `ps aux | grep -i vdbench.* | awk '{ print $1 }'`")

    if TestRun.executor.run("pgrep -x dd").exit_code == 0:
        raise Exception(f"Failed to stop dd!")
    if TestRun.executor.run("pgrep -x fio").exit_code == 0:
        raise Exception(f"Failed to stop fio!")
    if TestRun.executor.run("pgrep vdbench").exit_code == 0:
        raise Exception(f"Failed to stop vdbench!")


def wait(predicate, timeout: timedelta, interval: timedelta = None):
    start_time = datetime.now()
    result = False
    while start_time + timeout > datetime.now():
        result = predicate()
        if result:
            break
        if interval is not None:
            time.sleep(interval.total_seconds())
    return result


def sync():
    TestRun.executor.run_expect_success("sync")
