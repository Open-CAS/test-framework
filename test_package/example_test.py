#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import logging
import pytest
import time


LOGGER = logging.getLogger(__name__)


def setup_module():
    LOGGER.warning("Entering setup method")


@pytest.mark.parametrize('prepare_and_cleanup', [{"core_type": "hdd", "core_count": 4}], indirect=True)
def test_example(prepare_and_cleanup):
    dut_info, executor = prepare_and_cleanup
    LOGGER.info("RUN method")
    LOGGER.info(dut_info)
    output = executor.execute("hostname -I | awk '{print $1}'")
    LOGGER.info(output.stdout)
    assert output.stdout.strip() == dut_info['ip']
    time.sleep(5)
