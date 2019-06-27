#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from test_package.test_properties import TestProperties
import logging
from config import configuration

LOGGER = logging.getLogger(__name__)

opencas_repo_name = "open-cas-linux"


def install_opencas():
    LOGGER.info("Cloning Open CAS repository.")
    TestProperties.executor.execute(configuration.proxy_command)
    TestProperties.executor.execute(f"cd {configuration.opencas_repo_path}")
    TestProperties.executor.execute(f"if [ -d {opencas_repo_name} ]; "
                                    f"then rm -rf {opencas_repo_name}; fi")
    output = TestProperties.executor.execute(
        "git clone --recursive https://github.com/Open-CAS/open-cas-linux.git")
    if output.exit_code != 0:
        raise Exception(f"Error while cloning repository: {output.stdout}\n{output.stderr}")

    LOGGER.info("Open CAS make and make install.")
    output = TestProperties.executor.execute("cd open-cas-linux/ && ./configure && make")
    if output.exit_code != 0:
        raise Exception(
            f"Make command executed with nonzero status: {output.stdout}\n{output.stderr}")

    output = TestProperties.executor.execute("make install")
    if output.exit_code != 0:
        raise Exception(
            f"Error while installing Open CAS: {output.stdout}\n{output.stderr}")

    LOGGER.info("Check if casadm is properly installed.")
    output = TestProperties.executor.execute("casadm -V")
    if output.exit_code != 0:
        raise Exception(
            "'casadm -V' command returned an error: {output.stdout}\n{output.stderr}")
    else:
        LOGGER.info(output.stdout)


def uninstall_opencas():
    LOGGER.info("Uninstalling Open CAS.")
    output = TestProperties.executor.execute("casadm -V")
    if output.exit_code != 0:
        raise Exception("Open CAS is not properly installed.")
    else:
        TestProperties.executor.execute(f"cd {configuration.opencas_repo_path}/{opencas_repo_name}")
        output = TestProperties.executor.execute("make uninstall")
        if output.exit_code != 0:
            raise Exception(
                f"There was an error during uninstall process: {output.stdout}\n{output.stderr}")
