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
import time

LOGGER = logging.getLogger(__name__)
ioclass_config_path = "/tmp/opencas_ioclass.conf"
mountpoint = "/tmp/cas1-1"
exported_obj_path = "/dev/cas1-1"
cache_id = 1


@pytest.mark.parametrize(
    "prepare_and_cleanup",
    [{"core_count": 1, "core_type": "nand", "cache_count": 1, "cache_type": "optane"}],
    indirect=True,
)
def test_ioclass_file_extension(prepare_and_cleanup):
    cache_device, core_device = prepare()
    ioclass_id = 1
    tested_extension = "tmp"

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

    stats = casadm_parser.get_statistics(
        cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id, perform_sync=True
    )
    assert int(stats["Dirty"]) == 0

    dd = (
        Dd()
        .input("/dev/zero")
        .output(f"{mountpoint}/test_file.{tested_extension}")
        .count(10)
        .block_size(Size(4, Unit.KibiByte))
    )
    dd.run()

    stats = casadm_parser.get_statistics(
        cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id, perform_sync=True
    )
    assert int(stats["Dirty"]) == 10

    unmount(exported_obj)


def prepare():
    base_prepare()
    ioclass_config.remove_ioclass_config()
    cache_device = next(
        disk for disk in TestProperties.dut.disks if disk.disk_type == DiskType.optane
    )
    core_device = next(
        disk for disk in TestProperties.dut.disks if disk.disk_type == DiskType.nand
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

    return cache_device, core_device
