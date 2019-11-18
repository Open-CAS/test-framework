#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import time

from aenum import IntFlag, Enum
from packaging import version

from core.test_run import TestRun
from test_utils.filesystem.file import File
from test_tools import fs_utils


class DropCachesMode(IntFlag):
    PAGECACHE = 1
    SLAB = 2
    ALL = PAGECACHE | SLAB


class Udev(object):
    @staticmethod
    def enable():
        TestRun.LOGGER.info("Enabling udev")
        output = TestRun.executor.run("udevadm control --start-exec-queue")
        if output.exit_code != 0:
            raise Exception(
                f"Enabling udev failed. stdout: {output.stdout} \n stderr :{output.stderr}"
            )

    @staticmethod
    def disable():
        TestRun.LOGGER.info("Disabling udev")
        output = TestRun.executor.run("udevadm control --stop-exec-queue")
        if output.exit_code != 0:
            raise Exception(
                f"Disabling udev failed. stdout: {output.stdout} \n stderr :{output.stderr}"
            )


def drop_caches(level: DropCachesMode = DropCachesMode.PAGECACHE):
    TestRun.executor.run_expect_success(
        f"echo {level.value} > /proc/sys/vm/drop_caches")


def download_file(url, destination_dir="/tmp"):
    command = ("wget --tries=3 --timeout=5 --continue --quiet "
               f"--directory-prefix={destination_dir} {url}")
    output = TestRun.executor.run(command)
    if output.exit_code != 0:
        raise Exception(
            f"Download failed. stdout: {output.stdout} \n stderr :{output.stderr}")
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


def load_kernel_module(module_name, module_args: {str, str}=None):
    cmd = f"modprobe {module_name}"
    if module_args is not None:
        for key, value in module_args.items():
            cmd += f" {key}={value}"
    return TestRun.executor.run(cmd)


def unload_kernel_module(module_name, unload_method: ModuleRemoveMethod = ModuleRemoveMethod.rmmod):
    cmd = f"{unload_method.value} {module_name}"
    return TestRun.executor.run(cmd)


def reload_kernel_module(module_name, module_args: {str, str}=None):
    unload_kernel_module(module_name)
    time.sleep(1)
    load_kernel_module(module_name, module_args)


def wait(predicate, timeout, interval=None):
    start = time.time()
    result = False
    while time.time() - start < timeout:
        result = predicate()
        if result:
            break
        if interval is not None:
            time.sleep(interval)
    return result


def sync():
    output = TestRun.executor.run("sync")
    if output.exit_code != 0:
        raise Exception(
            f"Sync command failed. stdout: {output.stdout} \n stderr :{output.stderr}")


def check_files(core, size_before, permissions_before, md5_before, mount_point='/big/cas/',
                test_file_path=f"/mnt/cas/test_file"):
    TestRun.LOGGER.info("Checking file md5.")
    core.mount(mount_point)
    file_after = fs_utils.parse_ls_output(fs_utils.ls(test_file_path))[0]
    md5_after = file_after.md5sum()
    if md5_before != md5_after:
        TestRun.LOGGER.error(f"Md5 before ({md5_before}) and after ({md5_after}) are different.")

    if permissions_before.user == file_after.permissions.user:
        TestRun.LOGGER.error(f"User permissions before ({permissions_before.user}) "
                             f"and after ({file_after.permissions.user}) are different.")
    if permissions_before.group != file_after.permissions.group:
        TestRun.LOGGER.error(f"Group permissions before ({permissions_before.group}) "
                             f"and after ({file_after.permissions.group}) are different.")
    if permissions_before.other != file_after.permissions.other:
        TestRun.LOGGER.error(f"Other permissions before ({permissions_before.other}) "
                             f"and after ({file_after.permissions.other}) are different.")
    if size_before != file_after.size:
        TestRun.LOGGER.error(f"Size before ({size_before}) and after ({file_after.size}) "
                             f"are different.")
    core.unmount()
