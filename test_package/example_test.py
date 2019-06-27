#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import pytest
import time
from test_tools.disk_utils import Filesystem
from utils.dut import Dut
from utils import disk_finder
from utils.size import Size, Unit
from test_package.test_properties import TestProperties
from storage_devices.disk import DiskType


def setup_module():
    TestProperties.LOGGER.warning("Entering setup method")


@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"cache_type": "optane", "cache_count": 2}],
                         indirect=True)
def test_example(prepare_and_cleanup):
    prepare(prepare_and_cleanup)
    TestProperties.LOGGER.info("Test run")
    output = TestProperties.executor.execute("hostname -I | awk '{print $1}'")
    TestProperties.LOGGER.info(output.stdout)
    TestProperties.LOGGER.info(f"DUT info: {TestProperties.dut}")
    assert output.stdout.strip() == TestProperties.dut.ip
    test_disk = TestProperties.dut.disks[0]
    test_disk.create_partitions(Size(150, Unit.MebiByte), 5)
    TestProperties.LOGGER.info(f"DUT info: {TestProperties.dut}")
    test_disk.partitions[0].create_filesystem(Filesystem.ext3)


def prepare(prepare_fixture):
    TestProperties.LOGGER.info("Test prepare")
    dut_info, executor = prepare_fixture
    TestProperties.executor = executor
    dut_info["disks"] = disk_finder.find_disks()
    TestProperties.dut = Dut(dut_info)
