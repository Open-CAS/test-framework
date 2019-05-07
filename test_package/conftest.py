#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import pytest
import os
import sys
import importlib
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

# User should provide config/configuration.py with path to own test_wrapper,
# or in case there is no test_wrapper, add blank path.
import config.configuration as c
from connection.ssh_executor import SshExecutor
from connection.local_executor import LocalExecutor
if os.path.exists(c.test_wrapper_dir):
    sys.path.append(os.path.abspath(c.test_wrapper_dir))
    import test_wrapper


@pytest.fixture()
def prepare_and_cleanup(request):
    """
    This fixture returns the dictionary, which contains DUT ip, IPMI, spider, list of disks
    """

    # There should be dut config file added to config package and
    # pytest should be executed with option --config=conf_name'.
    #
    # 'ip' field should be filled with valid IP string to use remote ssh executor
    # or it should be commented out when user want to execute tests on local machine
    #
    # User can also have own test wrapper, which runs test prepare, cleanup, etc.
    # Then in the config/configuration.py file there should be added path to it: test_wrapper_dir = 'wrapper_path'

    try:
        dut_config = importlib.import_module(f"config.{request.config.option.config}")
    except:
        dut_config = None

    if os.path.exists(c.test_wrapper_dir):
        if hasattr(dut_config, 'ip'):
            if not is_valid_ip(dut_config.ip):
                raise Exception("IP address from configuration file is in invalid format.")
        yield from test_wrapper.run_test_wrapper(request, dut_config)
    elif dut_config is not None:
        if hasattr(dut_config, 'ip'):
            if is_valid_ip(dut_config.ip):
                yield {'ip': dut_config.ip, 'disks': dut_config.disks}, SshExecutor(dut_config.ip, c.user, c.password)
            else:
                raise Exception("IP address from configuration file is in invalid format.")
        else:
            yield {'disks': dut_config.disks}, LocalExecutor()
    else:
        raise Exception("There is neither configuration file nor test wrapper attached to tests execution.")


def pytest_addoption(parser):
    parser.addoption("--config", action="store", default="config/configuration.py")
    parser.addoption("--repo-tag", action="store", default="master")


def is_valid_ip(ip):
    try:
        return ip.count('.') == 3 and all(0 <= int(num) < 256 for num in ip.rstrip().split('.'))
    except:
        return False
