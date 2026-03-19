#
# Copyright(c) 2020-2022 Intel Corporation
# Copyright(c) 2026 Unvertical
# SPDX-License-Identifier: BSD-3-Clause
#

import re
from time import sleep

from connection.utils.output import CmdException
from core.test_run import TestRun
from storage_devices.device import Device
from test_tools.os_tools import (
    get_syslog_path,
    is_kernel_module_loaded,
    load_kernel_module,
    unload_kernel_module,
)

MODULE_NAME = "scsi_debug"

FLUSH = re.compile(r"scsi_debug:[\s\S]*cmd 35")
FUA = re.compile(r"scsi_debug:[\s\S]*cmd 2a 08")


class ScsiDebug:
    def __init__(self, params):
        self.params = params
        self.syslog_path = None
        self.last_read_line = 0
        self.reload()

    def reload(self):
        self.unload()
        sleep(1)
        load_output = load_kernel_module(MODULE_NAME, self.params)
        if load_output.exit_code != 0:
            raise CmdException(f"Failed to load {MODULE_NAME} module", load_output)
        TestRun.LOGGER.info(f"{MODULE_NAME} loaded successfully.")
        sleep(10)

    @staticmethod
    def unload():
        if is_kernel_module_loaded(MODULE_NAME):
            unload_kernel_module(MODULE_NAME)

    def get_devices(self):
        scsi_debug_devices = TestRun.executor.run_expect_success(
            "lsscsi --scsi_id | grep scsi_debug").stdout
        return [Device(f'/dev/disk/by-id/scsi-{device.split()[-1]}')
                for device in scsi_debug_devices.splitlines()]

    def reset_stats(self):
        """Set syslog position to current end so subsequent reads only see new entries."""
        if self.syslog_path is None:
            self.syslog_path = get_syslog_path()

        line_count = TestRun.executor.run_expect_success(
            f"wc -l < {self.syslog_path}"
        ).stdout.strip()
        self.last_read_line = int(line_count)

    def get_flush_count(self):
        log_lines = self._read_syslog()
        flush_count, _ = self._count_logs(log_lines)
        return flush_count

    def get_fua_count(self):
        log_lines = self._read_syslog()
        _, fua_count = self._count_logs(log_lines)
        return fua_count

    def _read_syslog(self):
        """Read syslog lines since last mark and advance the position."""
        if self.syslog_path is None:
            self.syslog_path = get_syslog_path()

        start_line = self.last_read_line + 1
        log_lines = TestRun.executor.run_expect_success(
            f"tail -qn +{start_line} {self.syslog_path}"
        ).stdout.splitlines()
        self.last_read_line += len(log_lines)
        return log_lines

    @staticmethod
    def _count_logs(log_lines):
        flush_count = 0
        fua_count = 0
        for line in log_lines:
            if FLUSH.search(line):
                flush_count += 1
            if FUA.search(line):
                fua_count += 1
        return flush_count, fua_count
