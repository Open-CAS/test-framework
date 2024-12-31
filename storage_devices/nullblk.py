#
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from core.test_run import TestRun
from storage_devices.device import Device
from test_tools.fs_tools import ls, parse_ls_output
from test_tools.os_tools import (
    unload_kernel_module,
    is_kernel_module_loaded,
    reload_kernel_module,
)


class NullBlk(Device):
    _module = "null_blk"

    @classmethod
    def create(
        cls, completion_nsec: int = 10000, size_gb: int = 250, nr_devices: int = 1, bs: int = 512
    ):
        TestRun.LOGGER.info("Configure null_blk...")
        params = {
            "completion_nsec": str(completion_nsec),
            "gb": str(size_gb),
            "nr_devices": str(nr_devices),
            "bs": str(bs),
        }

        reload_kernel_module(cls._module, params)
        return cls.list()

    @classmethod
    def remove_all(cls):
        if not is_kernel_module_loaded(cls._module):
            return
        TestRun.LOGGER.info("Removing null_blk ")
        unload_kernel_module(module_name=cls._module)

    @classmethod
    def list(cls):
        return [cls(null_blk.full_path) for null_blk in cls._list_devices()]

    @staticmethod
    def _list_devices():
        ls_output = ls(f"/dev/nullb*")
        if "No such file or directory" in ls_output:
            return []
        return parse_ls_output(ls_output)
