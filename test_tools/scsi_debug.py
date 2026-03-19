#
# Copyright(c) 2022 Intel Corporation
# Copyright(c) 2026 Unvertical
# SPDX-License-Identifier: BSD-3-Clause
#

import re

from core.test_run import TestRun
from test_tools.os_tools import get_syslog_path


class Logs:
    last_read_line = 0
    syslog_path = None
    FLUSH = re.compile(r"scsi_debug:[\s\S]*cmd 35")
    FUA = re.compile(r"scsi_debug:[\s\S]*cmd 2a 08")

    @staticmethod
    def mark():
        """Set syslog position to current end so subsequent reads only see new entries."""
        if Logs.syslog_path is None:
            Logs.syslog_path = get_syslog_path()

        line_count = TestRun.executor.run_expect_success(
            f"wc -l < {Logs.syslog_path}"
        ).stdout.strip()
        Logs.last_read_line = int(line_count)

    @staticmethod
    def check_syslog_for_signals():
        log_lines = Logs._read_syslog()
        flush_count = Logs._count_logs(log_lines, Logs.FLUSH)
        fua_count = Logs._count_logs(log_lines, Logs.FUA)
        Logs._validate_logs_amount(fua_count, "FUA")
        Logs._validate_logs_amount(flush_count, "FLUSH")

    @staticmethod
    def check_syslog_for_flush():
        """Check syslog for FLUSH logs"""
        log_lines = Logs._read_syslog()
        flush_logs_counter = Logs._count_logs(log_lines, Logs.FLUSH)
        Logs._validate_logs_amount(flush_logs_counter, "FLUSH")

    @staticmethod
    def check_syslog_for_fua():
        """Check syslog for FUA logs"""
        log_lines = Logs._read_syslog()
        fua_logs_counter = Logs._count_logs(log_lines, Logs.FUA)
        Logs._validate_logs_amount(fua_logs_counter, "FUA")

    @staticmethod
    def _read_syslog():
        """Read syslog lines since last mark and advance the position."""
        if Logs.syslog_path is None:
            Logs.syslog_path = get_syslog_path()

        start_line = Logs.last_read_line + 1
        log_lines = TestRun.executor.run_expect_success(
            f"tail -qn +{start_line} {Logs.syslog_path}"
        ).stdout.splitlines()
        Logs.last_read_line += len(log_lines)
        return log_lines

    @staticmethod
    def _count_logs(log_lines: list, expected_log):
        """Count specified log in list and return its amount."""
        logs_counter = 0
        for line in log_lines:
            if expected_log.search(line) is not None:
                logs_counter += 1
        return logs_counter

    @staticmethod
    def _validate_logs_amount(logs_counter: int, log_type: str):
        """Validate amount of logs."""
        if logs_counter == 0:
            if log_type == "FLUSH":
                TestRun.LOGGER.error(f"{log_type} log not occured")
            else:
                TestRun.LOGGER.warning(f"{log_type} log not occured")
        elif logs_counter == 1:
            TestRun.LOGGER.warning(f"{log_type} log occured only once.")
        else:
            TestRun.LOGGER.info(f"{log_type} log occured {logs_counter} times.")
