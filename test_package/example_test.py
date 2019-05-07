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


@pytest.mark.parametrize('prepare_and_cleanup', [{"disk_type": "optane", "count": 2}], indirect=True)
def test_create_partition(prepare_and_cleanup):
    LOGGER.info("RUN method")
    dut_info = prepare_and_cleanup['ip']
    LOGGER.info(dut_info)
    time.sleep(5)


