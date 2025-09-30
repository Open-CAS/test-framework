#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024-2025 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import posixpath
import re
import time

from datetime import timedelta
from enum import IntFlag, Enum, StrEnum
from packaging import version

from core.test_run import TestRun
from storage_devices.device import Device
from test_tools.disk_tools import get_sysfs_path
from test_tools.fs_tools import check_if_file_exists, is_mounted
from connection.utils.retry import Retry

DEBUGFS_MOUNT_POINT = "/sys/kernel/debug"
MEMORY_MOUNT_POINT = "/mnt/memspace"


class Distro(StrEnum):
    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    REDHAT = "rhel"
    OPENEULER = "openeuler"
    CENTOS = "centos"
    ROCKY = "rocky"


class DropCachesMode(IntFlag):
    PAGECACHE = 1
    SLAB = 2
    ALL = PAGECACHE | SLAB


class OvercommitMemoryMode(Enum):
    DEFAULT = 0
    ALWAYS = 1
    NEVER = 2


class SystemManagerType(Enum):
    sysv = 0
    systemd = 1


def get_distro():
    output = TestRun.executor.run(
        "cat /etc/os-release | grep -e \"^ID=\" | awk -F= '{print$2}' | tr -d '\"'"
    ).stdout.lower()

    try:
        return Distro(output)
    except ValueError:
        raise ValueError(f"Could not resolve distro name. Command output: {output}")


def drop_caches(level: DropCachesMode = DropCachesMode.ALL):
    TestRun.executor.run_expect_success(
        f"echo {level.value} > /proc/sys/vm/drop_caches")


def get_number_of_processors_from_cpuinfo():
    """Returns number of processors (count) which are listed out in /proc/cpuinfo"""
    cmd = f"cat /proc/cpuinfo | grep processor | wc -l"
    output = TestRun.executor.run(cmd).stdout

    return int(output)


def get_number_of_processes(process_name):
    cmd = f"ps aux | grep {process_name} | grep -v grep | wc -l"
    output = TestRun.executor.run(cmd).stdout

    return int(output)


def get_kernel_version():
    version_string = TestRun.executor.run_expect_success("uname -r").stdout
    version_string = version_string.split('-')[0]
    return version.Version(version_string)


def is_kernel_module_loaded(module_name):
    command = f"lsmod | grep -E '^{module_name}\\b'"
    output = TestRun.executor.run(command)
    return output.exit_code == 0


def load_kernel_module(module_name, module_args: {str, str}=None):
    cmd = f"modprobe {module_name}"
    if module_args is not None:
        for key, value in module_args.items():
            cmd += f" {key}={value}"
    return TestRun.executor.run(cmd)


def unload_kernel_module(module_name):
    cmd = f"modprobe -r {module_name}"
    return TestRun.executor.run_expect_success(cmd)


def get_kernel_module_parameter(module_name, parameter):
    param_file_path = f"/sys/module/{module_name}/parameters/{parameter}"
    if not check_if_file_exists(param_file_path):
        raise FileNotFoundError(f"File {param_file_path} does not exist!")
    return TestRun.executor.run(f"cat {param_file_path}").stdout


def mount_debugfs():
    if not is_mounted(DEBUGFS_MOUNT_POINT):
        TestRun.executor.run_expect_success(f"mount -t debugfs none {DEBUGFS_MOUNT_POINT}")


def reload_kernel_module(module_name, module_args: {str, str}=None):
    if is_kernel_module_loaded(module_name):
        unload_kernel_module(module_name)

    Retry.run_while_false(
        lambda: load_kernel_module(module_name, module_args).exit_code == 0,
        timeout=timedelta(seconds=5)
    )


def get_module_path(module_name):
    cmd = f"modinfo {module_name}"

    # module path is in second column of first line of `modinfo` output
    module_info = TestRun.executor.run_expect_success(cmd).stdout
    module_path = module_info.splitlines()[0].split()[1]

    return module_path


def get_executable_path(exec_name):
    cmd = f"which {exec_name}"

    path = TestRun.executor.run_expect_success(cmd).stdout

    return path


def kill_all_io(graceful=True):
    if graceful:
        # TERM signal should be used in preference to the KILL signal, since a
        # process may install a handler for the TERM signal in order to perform
        # clean-up steps before terminating in an orderly fashion.
        TestRun.executor.run("killall -q --signal TERM dd fio blktrace")
        time.sleep(3)
    TestRun.executor.run("killall -q --signal TERM dd fio blktrace")
    time.sleep(3)
    TestRun.executor.run("killall -q --signal KILL dd fio blktrace")
    TestRun.executor.run("kill -9 `ps aux | grep -i vdbench.* | awk '{ print $2 }'`")

    if TestRun.executor.run("pgrep -x dd").exit_code == 0:
        raise Exception(f"Failed to stop dd!")
    if TestRun.executor.run("pgrep -x fio").exit_code == 0:
        raise Exception(f"Failed to stop fio!")
    if TestRun.executor.run("pgrep -x blktrace").exit_code == 0:
        raise Exception(f"Failed to stop blktrace!")
    if TestRun.executor.run("pgrep vdbench").exit_code == 0:
        raise Exception(f"Failed to stop vdbench!")


def sync():
    TestRun.executor.run_expect_success("sync")


def get_dut_cpu_number():
    return int(TestRun.executor.run_expect_success("nproc").stdout)


def get_dut_cpu_physical_cores():
    """ Get list of CPU numbers that don't share physical cores """
    output = TestRun.executor.run_expect_success("lscpu --all --parse").stdout

    core_list = []
    visited_phys_cores = []
    for line in output.split("\n"):
        if "#" in line:
            continue

        cpu_no, phys_core_no = line.split(",")[:2]
        if phys_core_no not in visited_phys_cores:
            core_list.append(cpu_no)
            visited_phys_cores.append(phys_core_no)

    return core_list


def set_wbt_lat(device: Device, value: int):
    if value < 0:
        raise ValueError("Write back latency can't be negative number")

    wbt_lat_config_path = posixpath.join(
        get_sysfs_path(device.get_device_id()), "queue/wbt_lat_usec"
    )

    return TestRun.executor.run_expect_success(f"echo {value} > {wbt_lat_config_path}")


def get_wbt_lat(device: Device):
    wbt_lat_config_path = posixpath.join(
        get_sysfs_path(device.get_device_id()), "queue/wbt_lat_usec"
    )

    return int(TestRun.executor.run_expect_success(f"cat {wbt_lat_config_path}").stdout)


def get_cores_ids_range(numa_node: int):
    output = TestRun.executor.run_expect_success(f"lscpu --all --parse").stdout
    parse_output = re.findall(r'(\d+),(\d+),(?:\d+),(\d+),,', output, re.I)

    return [element[0] for element in parse_output if int(element[2]) == numa_node]


def create_user(username, additional_params=None):
    command = "useradd "
    if additional_params:
        command += "".join([f"-{p} " for p in additional_params])
    command += username
    return TestRun.executor.run_expect_success(command)


def check_if_user_exists(username):
    return TestRun.executor.run(f"id {username}").exit_code == 0
