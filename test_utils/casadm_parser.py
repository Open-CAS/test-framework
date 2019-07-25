#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
from api.cas import casadm
from api.cas.casadm import StatsFilter
from test_package.test_properties import TestProperties
from typing import List
import logging

LOGGER = logging.getLogger(__name__)


def get_statistics(
    cache_id: int,
    core_id: int = None,
    per_io_class: bool = False,
    io_class_id: int = None,
    filter: List[casadm.StatsFilter] = None,
    percentage_val: bool = False,
    perform_sync: bool = False,
):
    csv_stats = casadm.print_statistics(
        cache_id=cache_id,
        core_id=core_id,
        per_io_class=per_io_class,
        io_class_id=io_class_id,
        filter=[StatsFilter.usage, StatsFilter.blk, StatsFilter.err, StatsFilter.req],
        output_format=casadm.OutputFormat.csv,
        perform_sync=perform_sync,
    ).stdout
    # Conf statistics have different unit or may have no unit at all. For parsing
    # convenience they are gathered separetly. As this is only configuration stats
    # there is no risk they are divergent.
    conf_stats = casadm.print_statistics(
        cache_id=cache_id,
        core_id=core_id,
        per_io_class=per_io_class,
        io_class_id=io_class_id,
        filter=[StatsFilter.conf],
        output_format=casadm.OutputFormat.csv,
    ).stdout

    stats = {}
    [stat_keys, stat_values] = csv_stats.split("\n")
    for (name, val) in zip(stat_keys.split(","), stat_values.split(",")):
        if percentage_val and "[%]" in name:
            stats[name.split(" [")[0]] = val
        elif not percentage_val and "[%]" not in name:
            stats[name.split(" [")[0]] = val

    [stat_keys, stat_values] = conf_stats.split("\n")
    for (name, val) in zip(stat_keys.split(","), stat_values.split(",")):
        stats[name.split(" [")[0]] = val

    return stats
