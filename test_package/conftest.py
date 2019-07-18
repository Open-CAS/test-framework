#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import logging
import pytest
import os
import sys
import importlib
from IPy import IP
from test_utils import disk_finder
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

# User should provide config/configuration.py with path to own test_wrapper,
# or in case there is no test_wrapper, add blank path.
import config.configuration as c
from connection.ssh_executor import SshExecutor
from connection.local_executor import LocalExecutor
from test_package.test_properties import TestProperties
from test_utils.dut import Dut
if os.path.exists(c.test_wrapper_dir):
    sys.path.append(os.path.abspath(c.test_wrapper_dir))
    import test_wrapper
from installers import installer as installer
from api.cas import casadm
from test_tools import disk_utils

LOGGER = logging.getLogger(__name__)


@pytest.fixture()
def prepare_and_cleanup(request):
    """
    This fixture returns the dictionary, which contains DUT ip, IPMI, spider, list of disks.
    This fixture also returns the executor of commands
    """

    # There should be dut config file added to config package and
    # pytest should be executed with option --dut-config=conf_name'.
    #
    # 'ip' field should be filled with valid IP string to use remote ssh executor
    # or it should be commented out when user want to execute tests on local machine
    #
    # User can also have own test wrapper, which runs test prepare, cleanup, etc.
    # Then in the config/configuration.py file there should be added path to it:
    # test_wrapper_dir = 'wrapper_path'

    try:
        dut_config = importlib.import_module(f"config.{request.config.getoption('--dut-config')}")
    except:
        dut_config = None

    if os.path.exists(c.test_wrapper_dir):
        if hasattr(dut_config, 'ip'):
            try:
                IP(dut_config.ip)
            except ValueError:
                raise Exception("IP address from configuration file is in invalid format.")
        TestProperties.dut = Dut(test_wrapper.prepare(request, dut_config))
    elif dut_config is not None:
        if hasattr(dut_config, 'ip'):
            try:
                IP(dut_config.ip)
                if hasattr(dut_config, 'user') and hasattr(dut_config, 'password'):
                    executor = SshExecutor(dut_config.ip, dut_config.user, dut_config.password)
                    TestProperties.executor = executor
                else:
                    raise Exception("There is no credentials in config file.")
                if hasattr(dut_config, 'disks'):
                    TestProperties.dut = Dut({'ip': dut_config.ip, 'disks': dut_config.disks})
                else:
                    TestProperties.dut = Dut(
                        {'ip': dut_config.ip, 'disks': disk_finder.find_disks()})
            except ValueError:
                raise Exception("IP address from configuration file is in invalid format.")
        elif hasattr(dut_config, 'disks'):
            TestProperties.executor = LocalExecutor()
            TestProperties.dut = Dut({'disks': dut_config.disks})
        else:
            TestProperties.executor = LocalExecutor()
            TestProperties.dut = Dut({'disks': disk_finder.find_disks()})
    else:
        raise Exception(
            "There is neither configuration file nor test wrapper attached to tests execution.")
    yield
    TestProperties.LOGGER.info("Test cleanup")
    casadm.stop_all_caches()
    if os.path.exists(c.test_wrapper_dir):
        test_wrapper.cleanup(TestProperties.dut)


def pytest_addoption(parser):
    parser.addoption("--dut-config", action="store", default="None")
    parser.addoption("--remote", action="store", default="origin")
    parser.addoption("--repo-tag", action="store", default="master")
    parser.addoption("--force-reinstall", action="store_true", default="False")
    # TODO: investigate whether it is possible to pass the last param as bool


def get_remote():
    return pytest.config.getoption("--remote")


def get_branch():
    return pytest.config.getoption("--repo-tag")


def get_force_param():
    return pytest.config.getoption("--force-reinstall")


def base_prepare():
    LOGGER.info("Base test prepare")
    LOGGER.info(f"DUT info: {TestProperties.dut}")
    LOGGER.info("Removing partitions")
    for disk in TestProperties.dut.disks:
        disk_utils.remove_partitions(disk)
    if get_force_param() is not "False" and not hasattr(c, "already_updated"):
        installer.reinstall_opencas()
    elif not installer.check_if_installed():
        installer.install_opencas()
    c.already_updated = True  # to skip reinstall every test
    casadm.stop_all_caches()
