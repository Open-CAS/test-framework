#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging
import pytest
from api.cas import casadm
from api.cas import ioclass_config
from test_utils import casadm_parser
from test_tools.dd import Dd
from cas_configuration.cache_config import CacheMode, CleaningPolicy
from test_package.conftest import base_prepare
from test_package.test_properties import TestProperties
from storage_devices.disk import DiskType
from storage_devices.device import Device
from test_tools.disk_utils import Filesystem, create_filesystem, mount, unmount
from test_utils.size import Size, Unit

LOGGER = logging.getLogger(__name__)
ioclass_config_path = "/tmp/opencas_ioclass.conf"
mountpoint = "/tmp/cas1-1"
exported_obj_path = "/dev/cas1-1"
cache_id = 1


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_file_extension(prepare_and_cleanup):
    prepare()
    iterations = 50
    ioclass_id = 1
    tested_extension = "tmp"
    wrong_extensions = ["tm", "tmpx", "txt", "t", "", "123"]
    dd_size = Size(4, Unit.KibiByte)
    dd_count = 10

    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"extension:{tested_extension}&done",
        ioclass_config_path=ioclass_config_path,
    )
    casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

    exported_obj = Device(exported_obj_path)
    create_filesystem(exported_obj, Filesystem.ext3)
    mount(exported_obj, mountpoint)

    casadm.flush(cache_id=cache_id)
    sync()
    stats = casadm_parser.get_statistics(
        cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
    )
    assert int(stats["Dirty"]) == 0

    # Check if file with proper extension is cached
    dd = (
        Dd()
        .input("/dev/zero")
        .output(f"{mountpoint}/test_file.{tested_extension}")
        .count(dd_count)
        .block_size(dd_size)
    )
    for i in range(iterations):
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id,
            per_io_class=True,
            io_class_id=ioclass_id
        )
        assert int(stats["Dirty"]) == (i + 1) * dd_count

    casadm.flush(cache_id=cache_id)
    sync()
    stats = casadm_parser.get_statistics(
        cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
    )
    assert int(stats["Dirty"]) == 0

    # Check if file with improper extension is not cached
    for ext in wrong_extensions:
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{mountpoint}/test_file.{ext}")
            .count(dd_count)
            .block_size(dd_size)
        )
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id,
            per_io_class=True,
            io_class_id=ioclass_id
        )
        assert int(stats["Dirty"]) == 0

    unmount(exported_obj)


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_file_extension_preexisting_filesystem(prepare_and_cleanup):
    """Create files on filesystem, add device with filesystem as a core,
        write data to files and check if they are cached properly"""
    core_device = prepare()
    iterations = 50
    ioclass_id = 1
    extensions = ["tmp", "tm", "out", "txt", "log", "123"]
    dd_size = Size(4, Unit.KibiByte)
    dd_count = 10

    casadm.remove_core(cache_id=cache_id, core_id=1)
    create_filesystem(core_device, Filesystem.ext3)
    mount(core_device, mountpoint)

    # Prepare files
    for ext in extensions:
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{mountpoint}/test_file.{ext}")
            .count(dd_count)
            .block_size(dd_size)
        )
        dd.run()
    unmount(core_device)

    # Prepare ioclass config
    rule = "|".join([f"extension:{ext}" for ext in extensions])
    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"{rule}&done",
        ioclass_config_path=ioclass_config_path,
    )

    # Prepare cache for test
    casadm.add_core(cache_id=cache_id, core_dev=core_device)
    casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

    exported_obj = Device(exported_obj_path)
    create_filesystem(exported_obj, Filesystem.ext3)
    mount(exported_obj, mountpoint)

    casadm.flush(cache_id=cache_id)
    sync()
    stats = casadm_parser.get_statistics(
        cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
    )
    assert int(stats["Dirty"]) == 0

    # Check if files with proper extension are cached
    for ext in extensions:
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{mountpoint}/test_file.{ext}")
            .count(dd_count)
            .block_size(dd_size)
        )
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id,
            per_io_class=True,
            io_class_id=ioclass_id
        )
        assert int(stats["Dirty"]) == (extensions.index(ext) + 1) * dd_count

    unmount(exported_obj)


def sync():
    output = TestProperties.executor.execute("sync")
    if output.exit_code != 0:
        raise Exception(
            f"Sync command failed. stdout: {output.stdout} \n stderr :{output.stderr}")


def prepare():
    base_prepare()
    ioclass_config.remove_ioclass_config()
    cache_device = next(
        disk
        for disk in TestProperties.dut.disks
        if disk.disk_type in [DiskType.optane]
    )
    core_device = next(
        disk
        for disk in TestProperties.dut.disks
        if (
            disk.disk_type.value > cache_device.disk_type.value and disk != cache_device
        )
    )

    cache_device.create_partitions([Size(500, Unit.MebiByte)])
    core_device.create_partitions([Size(1, Unit.GigaByte)])

    cache_device = cache_device.partitions[0]
    core_device = core_device.partitions[0]

    casadm.start_cache(cache_device, cache_mode=CacheMode.WB, force=True)
    casadm.set_param_cleaning(cache_id=cache_id, policy=CleaningPolicy.nop)
    casadm.add_core(cache_id=cache_id, core_dev=core_device)

    ioclass_config.create_ioclass_config(ioclass_config_path=ioclass_config_path)

    output = TestProperties.executor.execute(f"mkdir -p {mountpoint}")
    if output.exit_code != 0:
        raise Exception(f"Failed to create mountpoint")

    return core_device
