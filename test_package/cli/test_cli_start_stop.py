#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging
import pytest
from api.cas import casadm
from test_package.conftest import base_prepare


LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("shortcut", [True, False])
@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"core_count": 1, "cache_count": 1}],
                         indirect=True)
def test_cli_start_stop_default_value(prepare_and_cleanup, shortcut):
    prepare(prepare_and_cleanup)

    casadm.start_cache("/dev/nvme0n1p1", shortcut=shortcut)

    parsed_output = casadm.parse_list_caches()
    assert len(parsed_output["caches"]) == 1
    assert parsed_output["caches"]["1"]["path"] == "/dev/nvme0n1p1"

    casadm.stop_cache(cache_id=1, shortcut=shortcut)

    output = casadm.list_caches(shortcut=shortcut)
    assert len(casadm.parse_list_caches()["caches"]) == 0
    assert output.stdout == "No caches running"


@pytest.mark.parametrize("shortcut", [True, False])
@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"core_count": 1, "cache_count": 1}],
                         indirect=True)
def test_cli_add_remove_default_value(prepare_and_cleanup, shortcut):
    prepare(prepare_and_cleanup)

    casadm.start_cache("/dev/nvme0n1p1", shortcut=shortcut)

    casadm.add_core(1, "/dev/sdb2", shortcut=shortcut)

    parsed_output = casadm.parse_list_caches()
    assert len(parsed_output["cores"]) == 1
    assert parsed_output["cores"]["1"]["path"] == "/dev/sdb2"

    casadm.remove_core(1, 1, shortcut=shortcut)
    parsed_output = casadm.parse_list_caches()
    assert len(parsed_output["caches"]) == 1
    assert len(parsed_output["cores"]) == 0

    casadm.stop_cache(cache_id=1, shortcut=shortcut)

    output = casadm.list_caches(shortcut=shortcut)
    parsed_output = casadm.parse_list_caches()
    assert len(parsed_output["caches"]) == 0
    assert len(parsed_output["cores"]) == 0
    assert output.stdout == "No caches running"


def prepare(prepare_fixture):
    base_prepare(prepare_fixture)
