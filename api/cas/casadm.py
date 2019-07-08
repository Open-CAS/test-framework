#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from .cli import *
from .casctl import stop as casctl_stop
from test_package.test_properties import TestProperties


def help(shortcut: bool = False):
    return TestProperties.executor.execute(help_cmd(shortcut))


# TODO:In the future cache_dev will probably be more complex than string value
def start_cache(cache_dev: str, cache_mode=None, cache_line_size=None,
                cache_id=None, force=False, load=False, shortcut=False):
    output = TestProperties.executor.execute(start_cmd(
        cache_dev, cache_mode, cache_line_size, cache_id, force, load, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to start cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def stop_cache(cache_id: int, no_data_flush: bool = False, shortcut: bool = False):
    output = TestProperties.executor.execute(stop_cmd(cache_id, no_data_flush, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to stop cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def add_core(cache_id: int, core_dev: str, core_id: int = None, shortcut: bool = False):
    output = TestProperties.executor.execute(add_core_cmd(cache_id, core_dev, core_id, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to add core. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def remove_core(cache_id: int, core_id: int, force: bool = False, shortcut: bool = False):
    output = TestProperties.executor.execute(remove_core_cmd(cache_id, core_id, force, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to remove core. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def load_cache(cache_dev: str, shortcut: bool = False):
    output = TestProperties.executor.execute(load_cmd(cache_dev, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to load cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def list_caches(output_format: str = None, shortcut: bool = False):
    output = TestProperties.executor.execute(list_cmd(output_format, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to list caches. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def stop_all_caches():
    if "No caches running" in list_caches().stdout:
        return
    LOGGER.info("Stop all caches")
    casctl_stop()
    output = list_caches()
    if "No caches running" not in output.stdout:
        raise Exception(
            f"Error while stopping caches. stdout: {output.stdout} \n stderr :{output.stderr}")


def parse_list_caches():
    parsed_output = {"caches": {}, "cores": {}}
    lines = list_caches("csv").stdout.split('\n')
    for line in lines:
        args = line.split(',')
        if args[0] == "cache":
            parsed_output["caches"] =\
                {args[1]: {"path": args[2], "state": args[3], "mode": args[4]}}
        elif args[0] == "core":
            parsed_output["cores"] = \
                {args[1]: {"path": args[2], "state": args[3], "device": args[5]}}
    return parsed_output
