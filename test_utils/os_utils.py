#
# Copyright(c) 2019-2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
import math
import os
import time
from datetime import timedelta, datetime

from aenum import IntFlag, Enum, IntEnum
from packaging import version

from core.test_run import TestRun
from storage_devices.device import Device
from test_tools.dd import Dd
from test_tools.fs_utils import (
    check_if_directory_exists, FileType, find, create_directory, ls, parse_ls_output, read_file,
    check_if_file_exists
)
from test_tools.disk_utils import get_sysfs_path
from test_utils.filesystem.file import File
from test_utils.output import CmdException
from test_utils.size import Size, Unit

DEBUGFS_MOUNT_POINT = "/sys/kernel/debug"
MEMORY_MOUNT_POINT = "/mnt/memspace"


class DropCachesMode(IntFlag):
    PAGECACHE = 1
    SLAB = 2
    ALL = PAGECACHE | SLAB


class OvercommitMemoryMode(Enum):
    DEFAULT = 0
    ALWAYS = 1
    NEVER = 2


class Runlevel(IntEnum):
    """
        Halt the system.
        SysV Runlevel: 0
        systemd Target: runlevel0.target, poweroff.target
    """
    runlevel0 = 0

    """
        Single user mode.
        SysV Runlevel: 1, s, single
        systemd Target: runlevel1.target, rescue.target
    """
    runlevel1 = 1

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

    """
        Multi-user, graphical. Usually has all the services of runlevel 3 plus a graphical login.
        SysV Runlevel: 5
        systemd Target: runlevel5.target, graphical.target
    """
    runlevel5 = 5

    """
        Reboot
        SysV Runlevel: 6
        systemd Target: runlevel6.target, reboot.target
    """
    runlevel6 = 6

    """
        Emergency shell
        SysV Runlevel: emergency
        systemd Target: emergency.target
    """
    emergency = 7


class SystemManagerType(Enum):
    sysv = 0
    systemd = 1


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
    result = TestRun.executor.run_expect_success("runlevel")
    try:
        split_output = result.stdout.split()
        runlevel = Runlevel(int(split_output[1]))
        return runlevel
    except Exception:
        raise Exception(f"Cannot parse '{result.output}' to runlevel.")


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


def drop_caches(level: DropCachesMode = DropCachesMode.PAGECACHE):
    TestRun.executor.run_expect_success(
        f"echo {level.value} > /proc/sys/vm/drop_caches")


def disable_memory_affecting_functions():
    """Disables system functions affecting memory"""
    # Don't allow sshd to be killed in case of out-of-memory:
    TestRun.executor.run_expect_success(
        "echo '-1000' > /proc/`cat /var/run/sshd.pid`/oom_score_adj"
    )
    TestRun.executor.run_expect_success(
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


def get_free_memory():
    """Returns free amount of memory in bytes"""
    output = TestRun.executor.run_expect_success("free -b")
    output = output.stdout.splitlines()
    for line in output:
        if 'free' in line:
            index = line.split().index('free') + 1  # 1st row has 1 element less than following rows
        if 'Mem' in line:
            mem_line = line.split()

    return Size(int(mem_line[index]))


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


def get_number_of_processors_from_cpuinfo():
    """Returns number of processors which are listed out in /proc/cpuinfo
    and since it's zero-based list that's why +1 operation take a place here"""
    cmd = f"cat /proc/cpuinfo | grep processor | wc -l"
    output = TestRun.executor.run(cmd).stdout
    number_of_processors = int(output) + 1

    return number_of_processors


def get_number_of_processes(process_name):
    cmd = f"ps aux | grep {process_name} | grep -v grep | wc -l"
    output = TestRun.executor.run(cmd).stdout

    return int(output)


def mount_ramfs():
    """Mounts ramfs to enable allocating memory space"""
    if not check_if_directory_exists(MEMORY_MOUNT_POINT):
        create_directory(MEMORY_MOUNT_POINT)
    if not is_mounted(MEMORY_MOUNT_POINT):
        TestRun.executor.run_expect_success(f"mount -t ramfs ramfs {MEMORY_MOUNT_POINT}")


def unmount_ramfs():
    """Unmounts ramfs and releases whole space allocated by it in memory"""
    TestRun.executor.run_expect_success(f"umount {MEMORY_MOUNT_POINT}")


def download_file(url, destination_dir="/tmp"):
    # TODO use wget module instead
    command = ("wget --tries=3 --timeout=5 --continue --quiet "
               f"--directory-prefix={destination_dir} {url}")
    TestRun.executor.run_expect_success(command)
    path = f"{destination_dir.rstrip('/')}/{File.get_name(url)}"
    return File(path)


def get_kernel_version():
    version_string = get_current_kernel_version_str().split('-')[0]
    return version.Version(version_string)


def get_current_kernel_version_str():
    """Return current kernel version"""
    return TestRun.executor.run_expect_success("uname -r").stdout


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
    return TestRun.executor.run_expect_success(cmd)


def get_kernel_module_parameter(module_name, parameter):
    param_file_path = f"/sys/module/{module_name}/parameters/{parameter}"
    if not check_if_file_exists(param_file_path):
        raise FileNotFoundError(f"File {param_file_path} does not exist!")
    return File(param_file_path).read()


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


def get_udev_service_path(unit_name):
    cmd = f"systemctl cat {unit_name}"

    # path is in second column of first line of output
    info = TestRun.executor.run_expect_success(cmd).stdout
    path = info.splitlines()[0].split()[1]

    return path


def kill_all_io():
    # TERM signal should be used in preference to the KILL signal, since a
    # process may install a handler for the TERM signal in order to perform
    # clean-up steps before terminating in an orderly fashion.
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

    wbt_lat_config_path = os.path.join(
        get_sysfs_path(device.get_device_id()), "queue/wbt_lat_usec"
    )

    return TestRun.executor.run_expect_success(f"echo {value} > {wbt_lat_config_path}")


def get_wbt_lat(device: Device):
    wbt_lat_config_path = os.path.join(
        get_sysfs_path(device.get_device_id()), "queue/wbt_lat_usec"
    )

    return int(TestRun.executor.run_expect_success(f"cat {wbt_lat_config_path}").stdout)


def got_compatible_kernels():
    """Check if there are any compatible kernel versions on the DUT"""
    kernels_number = 0
    try:
        kernels_number = _count_kernel_versions(compatible=True)
    except Exception as e:
        raise Exception("Cannot check if there are compatible kernels on DUT\n"
                        f"{e}")
    finally:
        return kernels_number > 1


def got_incompatible_kernels():
    """Check if there are any incompatible kernel versions on the DUT"""
    kernels_number = 0
    try:
        kernels_number = _count_kernel_versions(compatible=False)
    except Exception as e:
        raise Exception("Cannot check if there are incompatible kernels on DUT\n"
                        f"{e}")
    finally:
        return kernels_number > 0


def _count_kernel_versions(compatible: bool):
    """Count how many compatible/incompatible kernel versions are on the DUT"""
    count = 0
    kernel_ver = str(get_kernel_version())
    kernels_list = _get_kernels_entries()

    for kernel in kernels_list:
        if ("rescue" or "recovery") in kernel.lower():
            continue
        if compatible:
            if kernel_ver in kernel:
                count += 1
        else:
            if kernel_ver not in kernel:
                count += 1

    return count


def _get_kernels_entries():
    """
        Collect and print entries of all kernel versions available on the DUT
        Entries from BLS are collected first during boot, then entries from GRUB config are
        collected. Other entries (non-linux) are of no interest to us.
    """
    entries = []

    entries.extend(_get_entries_from_bls())
    entries.extend(_get_entries_from_grub_config(start_number=len(entries)))

    if not entries:
        raise CmdException("Error while listing available kernel versions.")

    TestRun.LOGGER.info(f"Entries in system:")
    for entry in entries:
        TestRun.LOGGER.info(f"{entry}")
    return entries


def _get_entries_from_bls(boot_dir: str = '/boot'):
    """Collect entries of kernel versions from Boot Loader Specification directory"""
    entries = []
    bls_entries_paths = find([boot_dir], 'loader/entries', [FileType.directory])
    for path in bls_entries_paths:
        output = parse_ls_output(ls(path), path)
        if output is not None:
            files = [file.full_path for file in output]
            for i, file in enumerate(files):
                file_content = read_file(file)
                for line in file_content.splitlines():
                    if 'title' in line.lower():
                        entries.append(f"{i} {line.replace('title ', '')}")

    return entries


def _get_entries_from_grub_config(boot_dir: str = '/boot', start_number: int = 0):
    """Collect entries of kernel versions from GRUB config"""
    entries = []
    grub_config_paths = find([boot_dir], 'grub.cfg')

    grub_config_path = _get_right_grub_config_path(grub_config_paths)

    cmd = f'grep "menuentry " {grub_config_path} | cut -f 2 -d "\'" | nl -v {start_number}'
    grub_config_entries = TestRun.executor.run(cmd).stdout.splitlines()
    entries.extend(grub_config_entries)

    return entries


def _get_right_grub_config_path(grub_config_paths: [str]):
    """
        Select correct path to GRUB config
        Firstly check for a config for UEFI system partition
        Secondly check for a config for BIOS boot partition
    """
    import re
    efi = re.compile(r'/efi[\S\s]*/grub.cfg')
    legacy = re.compile(r'/grub(2)?/grub.cfg')
    grub_config_path = None

    for path in grub_config_paths:
        if efi.search(path):
            grub_config_path = path
            break

    if not grub_config_path:
        for path in grub_config_paths:
            if legacy.search(path):
                grub_config_path = path
                break

    return grub_config_path


def switch_kernel(compatible: bool = True, custom: str = None):
    """Switch kernel to compatible/incompatible/directly chosen version on the next boot"""
    available_kernels = _get_kernels_entries()
    grub_entry_number = choose_kernel_version(compatible, available_kernels, custom)
    _set_kernel_for_next_reboot_only(grub_entry_number)


def choose_kernel_version(compatible: bool, available_kernels: [str], custom: str = None):
    """
        Choose one compatible/incompatible/custom kernel version from given list
        and return its entry position or raise exception if not found any
    """
    current_version = get_current_kernel_version_str()
    current_version_main = str(get_kernel_version())
    kernel_position_in_grub_config = None

    if custom and available_kernels:
        for kernel in available_kernels:
            kernel = kernel.split('--')[0]

            if custom in kernel:
                kernel_position_in_grub_config = int(kernel.split()[0])
                return kernel_position_in_grub_config

    elif available_kernels and current_version:
        if compatible:
            compatible_versions = _get_kernels(True, available_kernels, current_version_main)

            for kernel in compatible_versions:
                if current_version not in kernel:
                    kernel_position_in_grub_config = int(kernel.split()[0])
                    break
        else:
            incompatible_versions = _get_kernels(False, available_kernels, current_version_main)
            kernel_position_in_grub_config = int(incompatible_versions[0].split()[0])

    if kernel_position_in_grub_config is None:
        raise Exception("Didn't found any suitable record in grub config.")
    else:
        return kernel_position_in_grub_config


def _get_kernels(compatible: bool, kernel_versions: [str], main_version: str):
    """Choose compatible/incompatible kernel versions from given list and return them"""
    kernels = []

    for kernel_version in kernel_versions:
        if ("rescue" or "recovery") in kernel_version.lower():
            continue

        if compatible:
            if main_version in kernel_version:
                kernels.append(kernel_version)
        else:
            if main_version not in kernel_version:
                kernels.append(kernel_version)

    return kernels


def _set_kernel_for_next_reboot_only(grub_entry_number: int):
    """
        Set given GRUB entry number to be booted to only during the next boot
        Check grub2-reboot (grub-reboot) help for details
    """
    grub_version = _get_grub_version()
    TestRun.executor.run(f"{grub_version}-reboot {grub_entry_number}")


def _get_grub_version():
    """Return GRUB version"""
    return TestRun.executor.run("ls /boot | grep grub").stdout.splitlines()[-1]
