#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2025 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import logging
import os
import posixpath
import re
import sys
from contextlib import contextmanager
from datetime import datetime
from threading import Lock

import portalocker

from log.html_log_config import HtmlLogConfig
from log.html_log_manager import HtmlLogManager
from log.html_presentation_policy import html_policy
from connection.utils.output import Output
from test_utils.common.singleton import Singleton


def create_log(log_base_path, test_module, additional_args=None):
    Log.setup()
    log_cfg = HtmlLogConfig(base_dir=log_base_path,
                            presentation_policy=html_policy)
    log = Log(log_config=log_cfg)
    test_name = 'TestNameError'
    error_msg = None
    try:
        test_name = test_module
        if additional_args:
            test_name += f"__{'_'.join(additional_args)}"
    except Exception as ex:
        error_msg = f'Detected some problems during calculating test name: {ex}'
    finally:
        log.begin(test_name)
    print(f"\n<LogFile>{os.path.join(log.base_dir, 'main.html')}</LogFile>")
    Log.add_file_logger(log.base_dir)
    if error_msg:
        log.exception(error_msg)
    return log


class Log(HtmlLogManager, metaclass=Singleton):
    logger = None
    LOG_FORMAT = '%(asctime)s %(levelname)s:\t%(message)s'
    DATE_FORMAT = "%Y/%m/%d %H:%M:%S"
    unique_test_identifier = ""
    command_id = 0
    lock = Lock()

    @classmethod
    def destroy(cls):
        del cls._instances[cls]

    @classmethod
    def setup(cls):

        # Get handle to root logger.
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Set paramiko log level to warning
        logging.getLogger('paramiko').setLevel(logging.WARNING)

        # Create Handlers.
        stdout_handler = logging.StreamHandler(sys.stdout)

        # Set logging level on handlers.
        stdout_handler.setLevel(logging.DEBUG)

        # Set log formatting on each handler.
        formatter = logging.Formatter(Log.LOG_FORMAT, Log.DATE_FORMAT)
        stdout_handler.setFormatter(formatter)

        # Attach handlers to root logger.
        logger.handlers = []
        logger.addHandler(stdout_handler)
        cls.logger = logger
        logger.info("Logger successfully initialized.")

    @classmethod
    def add_file_logger(cls, log_path):
        file_handler = logging.FileHandler(os.path.join(log_path, 'stdout.log'))
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(Log.LOG_FORMAT, Log.DATE_FORMAT)
        file_handler.setFormatter(formatter)
        cls.logger.addHandler(file_handler)

    @contextmanager
    def step(self, message):
        self.step_info(message)
        super(Log, self).start_group(message)
        if Log.logger:
            Log.logger.info(message)
        yield
        super(Log, self).end_group()

    @contextmanager
    def group(self, message):
        self.start_group(message)
        yield
        self.end_group()

    def add_build_info(self, msg):
        super(Log, self).add_build_info(msg)
        if Log.logger:
            Log.logger.info(msg)

    def info(self, msg):
        super(Log, self).info(msg)
        if Log.logger:
            Log.logger.info(msg)

    def debug(self, msg):
        super(Log, self).debug(msg)
        if Log.logger:
            Log.logger.debug(msg)

    def error(self, msg):
        super(Log, self).error(msg)
        if Log.logger:
            Log.logger.error(msg)

    def blocked(self, msg):
        super(Log, self).blocked(msg)
        if Log.logger:
            Log.logger.fatal(msg)

    def exception(self, msg):
        super(Log, self).exception(msg)
        if Log.logger:
            Log.logger.exception(msg)

    def critical(self, msg):
        super(Log, self).critical(msg)
        if Log.logger:
            Log.logger.fatal(msg)

    def workaround(self, msg):
        super(Log, self).workaround(msg)
        if Log.logger:
            Log.logger.warning(msg)

    def warning(self, msg):
        super(Log, self).warning(msg)
        if Log.logger:
            Log.logger.warning(msg)

    def get_new_command_id(self):
        self.lock.acquire()
        command_id = self.command_id
        self.command_id += 1
        self.lock.release()
        return command_id

    def write_to_command_log(self, message):
        super(Log, self).debug(message)
        command_log_path = os.path.join(self.base_dir, "dut_info", 'commands.log')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S:%f')
        with portalocker.Lock(command_log_path, "ab+") as command_log:
            line_to_write = f"[{timestamp}] {message}\n"
            command_log.write(line_to_write.encode())

    def write_command_to_command_log(self, command, command_id, info=None):
        added_info = "" if info is None else f"[{info}] "
        self.write_to_command_log(f"{added_info}Command id: {command_id}\n{command}")

    def write_output_to_command_log(self, output: Output, command_id):
        if output is not None:
            line_to_write = f"Command id: {command_id}\n\texit code: {output.exit_code}\n" \
                f"\tstdout: {output.stdout}\n" \
                f"\tstderr: {output.stderr}\n\n\n"
            self.write_to_command_log(line_to_write)
        else:
            self.write_to_command_log(f"Command id: {command_id}\n\tNone output.")

    def step_info(self, step_name):
        from core.test_run import TestRun
        decorator = "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n\n"
        message = f"\n\n\n{decorator}{step_name}\n\n{decorator}\n"

        try:
            serial_monitor = TestRun.plugin_manager.get_plugin("serial_monitor")
            serial_monitor.send_to_serial(message)
        except (KeyError, AttributeError):
            pass
        self.write_to_command_log(message)

    def get_additional_logs(self):
        from core.test_run import TestRun
        from test_tools.fs_tools import check_if_file_exists

        messages_log = "/var/log/messages"
        if not check_if_file_exists(messages_log):
            messages_log = "/var/log/syslog"

        log_files = {"messages.log": posixpath.join(TestRun.TEST_RUN_DATA_PATH, "messages"),
                     "dmesg.log": posixpath.join(TestRun.TEST_RUN_DATA_PATH, "dmesg")}
        extra_logs = TestRun.config.get("extra_logs", {})
        log_files.update(extra_logs)

        # Escape special characters from test identifier to be properly processed by awk
        test_identifier = re.escape(TestRun.LOGGER.unique_test_identifier)

        TestRun.executor.run(
            f"dmesg | awk '/{test_identifier}/,0' > {log_files['dmesg.log']}")
        TestRun.executor.run(
            f"awk '/{test_identifier}/,0' {messages_log} > {log_files['messages.log']}")

        dut_identifier = TestRun.dut.ip if TestRun.dut.ip else TestRun.dut.config["host"]
        for log_name, log_source_path in log_files.items():
            try:
                log_destination_path = os.path.join(
                    self.base_dir, "dut_info", dut_identifier, log_name
                )
                TestRun.executor.copy_from(log_source_path, log_destination_path)
            except Exception as e:
                TestRun.LOGGER.warning(
                    f"There was a problem during gathering {log_name} log.\n{str(e)}"
                )

    def generate_summary(self, item, meta):
        import json
        summary_path = os.path.join(self.base_dir, 'info.json')
        with open(summary_path, "w+") as summary:
            data = {
                'module': os.path.relpath(item.fspath, os.getcwd()),
                'function': item.name,
                'meta': meta,
                'status': self.get_result().name,
                'path': os.path.normpath(self.base_dir),
                'stage_status': {
                    'setup': getattr(item, "rep_setup", {}),
                    'call': getattr(item, "rep_call", {}),
                    'teardown': getattr(item, "rep_teardown", {})
                }
            }
            json.dump(data, summary)

    def print_test_identifier_to_logs(self):
        from core.test_run import TestRun
        # Add test identifier to dmesg
        TestRun.executor.run(f"echo {self.unique_test_identifier} > /dev/kmsg")

        # Add test identifier to messages log
        TestRun.executor.run(f"logger {self.unique_test_identifier}")
