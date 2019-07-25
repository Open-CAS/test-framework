#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import logging
from test_package.test_properties import TestProperties
import os

default_config_file_path = "/tmp/opencas_ioclass.conf"


def create_ioclass_config(
    add_default_rule: bool = True, ioclass_config_path: str = default_config_file_path
):
    output = TestProperties.executor.execute(
        'echo "IO class id,IO class name,Eviction priority,Allocation" '
        + f"> {ioclass_config_path}"
    )
    if output.exit_code != 0:
        raise Exception(
            "Failed to create ioclass config file. "
            + f"stdout: {output.stdout} \n stderr :{output.stderr}"
        )
    if add_default_rule:
        output = TestProperties.executor.execute(
            f'echo "0,unclassified,22,0" >> {ioclass_config_path}'
        )
        if output.exit_code != 0:
            raise Exception(
                "Failed to create ioclass config file. "
                + f"stdout: {output.stdout} \n stderr :{output.stderr}"
            )


def remove_ioclass_config(ioclass_config_path: str = default_config_file_path):
    try:
        os.remove(ioclass_config_path)
    except OSError:
        TestProperties.LOGGER.warning(
            f"Failed to remove ioclass config file {ioclass_config_path}"
        )


def add_ioclass(
    ioclass_id: int,
    rule: str,
    eviction_priority: int,
    allocation: bool,
    ioclass_config_path: str = default_config_file_path,
):
    new_ioclass = f"{ioclass_id},{rule},{eviction_priority},{int(allocation)}"

    output = TestProperties.executor.execute(
        f'echo "{new_ioclass}" >> {ioclass_config_path}'
    )
    if output.exit_code != 0:
        raise Exception(
            "Failed to append ioclass to config file. "
            + f"stdout: {output.stdout} \n stderr :{output.stderr}"
        )


def get_ioclass(ioclass_id: int, ioclass_config_path: str = default_config_file_path):
    output = TestProperties.executor.execute(f"cat {ioclass_config_path}")
    if output.exit_code != 0:
        raise Exception(
            "Failed to read ioclass config file. "
            + f"stdout: {output.stdout} \n stderr :{output.stderr}"
        )

    for ioclass in output.stdout:
        if int(ioclass.split(",")[0]) == ioclass_id:
            return ioclass


def remove_ioclass(
    ioclass_id: int, ioclass_config_path: str = default_config_file_path
):
    output = TestProperties.executor.execute(f"cat {ioclass_config_path}")
    if output.exit_code != 0:
        raise Exception(
            "Failed to read ioclass config file. "
            + f"stdout: {output.stdout} \n stderr :{output.stderr}"
        )

    old_ioclass_config = output.stdout.splitlines()
    config_header = old_ioclass_config.old[0]

    new_ioclass_config = [
        x for x in old_ioclass_config[1:0] if int(x.split(",")[0]) != ioclass_id
    ]

    new_ioclass_config.insert(0, config_header)

    if len(new_ioclass_config) == len(old_ioclass_config):
        raise Exception(
            f"Failed to remove ioclass {ioclass_config_path} from config file {ioclass_config_path}"
        )

    output = TestProperties.executor.execute(
        f'echo "{new_ioclass_config}" > {ioclass_config_path}'
    )
    if output.exit_code != 0:
        raise Exception(
            "Failed to store new ioclass config file. "
            + f"stdout: {output.stdout} \n stderr :{output.stderr}"
        )
