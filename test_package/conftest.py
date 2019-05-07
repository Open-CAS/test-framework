#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import pytest
import os
import sys
sys.path.append(os.path.abspath('../psg_cas_l-opencas_val'))
import test_wrapper


@pytest.fixture()
def prepare_and_cleanup(request):
    """
    This fixture returns the dictionary, which contains DUT ip, IPMI, spider, list of disks
    """
    yield from test_wrapper.run_test_wrapper(request)
