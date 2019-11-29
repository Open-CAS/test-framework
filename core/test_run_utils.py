#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import pytest
from IPy import IP

from connection.ssh_executor import SshExecutor
from connection.local_executor import LocalExecutor
from test_utils import disk_finder
from test_utils.dut import Dut
import core.test_run
import traceback


TestRun = core.test_run.TestRun


@classmethod
def __configure(cls, config):
    config.addinivalue_line(
        "markers",
        "require_disk(name, type): require disk of specific type, otherwise skip"
    )
    config.addinivalue_line(
        "markers",
        "remote_only: run test only in case of remote execution, otherwise skip"
    )


TestRun.configure = __configure


@classmethod
def __prepare(cls, item):
    cls.item = item
    req_disks = list(map(lambda mark: mark.args, cls.item.iter_markers(name="require_disk")))
    cls.req_disks = dict(req_disks)
    if len(req_disks) != len(cls.req_disks):
        raise Exception("Disk name specified more than once!")


TestRun.prepare = __prepare


@classmethod
def __setup_disk(cls, disk_name, disk_type):
    cls.disks[disk_name] = next(filter(
        lambda disk: disk.disk_type in disk_type.types() and disk not in cls.disks.values(),
        cls.dut.disks
    ))
    if not cls.disks[disk_name]:
        pytest.skip("Unable to find requested disk!")


TestRun.__setup_disk = __setup_disk


@classmethod
def __setup_disks(cls):
    cls.disks = {}
    items = list(cls.req_disks.items())
    while items:
        resolved, unresolved = [], []
        for disk_name, disk_type in items:
            (resolved, unresolved)[not disk_type.resolved()].append((disk_name, disk_type))
        resolved.sort(
            key=lambda disk: (lambda disk_name, disk_type: disk_type)(*disk)
        )
        for disk_name, disk_type in resolved:
            cls.__setup_disk(disk_name, disk_type)
        items = unresolved


TestRun.__setup_disks = __setup_disks


@classmethod
def __setup(cls, dut_config):
    if not dut_config:
        TestRun.block("You need to specify DUT config!")
    if dut_config['type'] == 'ssh':
        try:
            IP(dut_config['ip'])
        except ValueError:
            TestRun.block("IP address from config is in invalid format.")

        port = dut_config.get('port', 22)

        if 'user' in dut_config and 'password' in dut_config:
            cls.executor = SshExecutor(
                dut_config['ip'],
                dut_config['user'],
                dut_config['password'],
                port
            )
        else:
            TestRun.block("There are no credentials in config.")
    elif dut_config['type'] == 'local':
        cls.executor = LocalExecutor()
    else:
        TestRun.block("Execution type (local/ssh) is missing in DUT config!")

    if list(cls.item.iter_markers(name="remote_only")):
        if not cls.executor.is_remote():
            pytest.skip()

    if dut_config.get('allow_disk_autoselect', False):
        dut_config["disks"] = disk_finder.find_disks()

    try:
        cls.dut = Dut(dut_config)
    except Exception as ex:
        raise Exception(f"Failed to setup DUT instance:\n"
                        f"{str(ex)}\n{traceback.format_exc()}")
    cls.__setup_disks()


TestRun.setup = __setup


@classmethod
def __makereport(cls, item, call, res):
    cls.outcome = res.outcome

    from _pytest.outcomes import Failed
    from core.test_run import Blocked
    if res.when == "call" and res.failed:
        msg = f"{call.excinfo.type.__name__}: {call.excinfo.value}"
        if call.excinfo.type is Failed:
            cls.LOGGER.error(msg)
        elif call.excinfo.type is Blocked:
            cls.LOGGER.blocked(msg)
        else:
            cls.LOGGER.exception(msg)


TestRun.makereport = __makereport
