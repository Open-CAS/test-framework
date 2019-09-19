#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import pytest
from api.cas import casadm, casadm_parser
from test_package.conftest import base_prepare
from test_package.test_properties import TestProperties
from storage_devices.disk import DiskType
from test_utils.size import Size, Unit


@pytest.mark.parametrize("shortcut", [True, False])
@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_cli_start_stop_default_value(prepare_and_cleanup, shortcut):
    """
        1. Start new cache instance (don't specify cache id)
        2. Add core to newly create cache.
        3. Stop cache instance.
        4. Start new cache instance on another device (don't specify cache id).
        5. Try to load metadata from first device.
            * Loaded instance shold have id equal 2.
    """
    prepare()

    cache_device = next(
        disk
        for disk in TestProperties.dut.disks
        if disk.disk_type in [DiskType.optane, DiskType.nand]
    )
    core_device = next(
        disk
        for disk in TestProperties.dut.disks
        if (
            disk.disk_type.value > cache_device.disk_type.value and disk != cache_device
        )
    )

    TestProperties.LOGGER.info("Creating partitons for test")
    cache_device.create_partitions([Size(500, Unit.MebiByte), Size(500, Unit.MebiByte)])
    core_device.create_partitions([Size(1, Unit.GibiByte)])

    cache_device_1 = cache_device.partitions[0]
    cache_device_2 = cache_device.partitions[1]
    core_device = core_device.partitions[0]

    TestProperties.LOGGER.info("Starting cache with default id and one core")
    cache1 = casadm.start_cache(cache_device_1, force=True)
    cache1.add_core(core_device)

    TestProperties.LOGGER.info("Stopping cache")
    cache1.stop()

    TestProperties.LOGGER.info("Starting cache with default id on different device")
    cache2 = casadm.start_cache(cache_device_2, force=True)

    TestProperties.LOGGER.info("Loading metadata from first cache device")
    casadm.load_cache(cache_device_1)

    caches = casadm_parser.get_caches()
    assert len(caches) == 2, "Inappropirate number of caches after load!"
    assert caches[0].cache_device.system_path == cache_device_2.system_path
    assert caches[0].cache_id == 1
    assert caches[1].cache_device.system_path == cache_device_1.system_path
    assert caches[1].cache_id == 2, "Loaded cache has invalid id!"

    cores = caches[0].get_core_devices()
    assert len(cores) == 0

    cores = caches[1].get_core_devices()
    assert len(cores) == 1, "Core is missing in loaded cache!"
    assert cores[0].core_device.system_path == core_device.system_path, (
        "Loaded cache " "has invaild path!"
    )


def prepare():
    base_prepare()
