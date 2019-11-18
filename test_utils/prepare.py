#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from api.cas import casadm
from test_tools.disk_utils import Filesystem
from test_utils.filesystem.file import File
from core.test_run import TestRun
from test_utils.size import Size, Unit


def prepare():
    cache_dev = TestRun.disks['cache']
    cache_dev.create_partitions([Size(2, Unit.GibiByte)])
    core_dev = TestRun.disks['core']
    core_dev.create_partitions([Size(1, Unit.GibiByte)])
    return cache_dev.partitions[0], core_dev.partitions[0]


def prepare_with_file_creation(config, mount_point="/mnt/cas", test_file_path=f"/mnt/cas/test_file",
                               fs=Filesystem.ext3):
    TestRun.LOGGER.info("Prepare cache and core. Start Open CAS.")
    cache_dev, core_dev = prepare()
    cache = casadm.start_cache(cache_dev, config, force=True)
    TestRun.LOGGER.info("Add core device, create filesystem and mount core.")
    core = cache.add_core(core_dev)
    core.create_filesystem(fs)
    core.mount(mount_point)
    TestRun.LOGGER.info(f"Create test file in {mount_point} directory and count its md5 sum.")
    file = File.create_file(test_file_path)
    file.write("Test content")
    md5_before_load = file.md5sum()
    size_before_load = file.size
    permissions_before_load = file.permissions
    TestRun.LOGGER.info("Release core.")
    core.unmount()
    return cache, core, md5_before_load, size_before_load, \
        permissions_before_load, core_dev
