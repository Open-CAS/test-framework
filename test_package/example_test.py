#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import logging
import pytest
import time
from utils.dut import Dut
from test_package.test_properties import TestProperties


LOGGER = logging.getLogger(__name__)


def setup_module():
    LOGGER.warning("Entering setup method")


@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"cache_type": "optane", "cache_count": 2}],
                         indirect=True)
def test_example(prepare_and_cleanup):
    prepare(prepare_and_cleanup)
    LOGGER.info("Test run")
    LOGGER.info(f"DUT info: {TestProperties.dut}")
    output = TestProperties.executor.execute("hostname -I | awk '{print $1}'")
    LOGGER.info(output.stdout)
    assert output.stdout.strip() == TestProperties.dut.ip
    time.sleep(5)


def prepare(prepare_fixture):
    LOGGER.info("Test prepare")
    dut_info, executor = prepare_fixture
    TestProperties.executor = executor
    TestProperties.dut = Dut(dut_info)
