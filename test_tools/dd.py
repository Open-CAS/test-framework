#
# Copyright(c) 2019-2021 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# Copyright(c) 2026 Unvertical
# SPDX-License-Identifier: BSD-3-Clause
#

import type_def.size as size
from core.test_run import TestRun
from connection.utils.output import CmdException
from test_tools.common.linux_command import LinuxCommand


# TODO: Remove it when it's fixed in uutils.
#
# The uutils coreutils `dd` (the default `dd` on some recent distros, e.g.
# Ubuntu 26.04) does not page-align its O_DIRECT buffer to bdev block size.
# As a result iflag=direct / oflag=direct transfers are unreliable.
# On kernel 7.0 there is a strict BIO alignment check, which makes I/O
# fail, sometimes in very nasty ways, especially in bio-based block device
# drivers.
#
# As a temporary solution, fall back to gnu-coreutils.
_gnu_dd_binary = {}


def _resolve_gnu_dd():
    executor = TestRun.executor
    cached = _gnu_dd_binary.get(id(executor))
    if cached:
        return cached

    output = None
    for candidate in ("dd", "gnudd"):
        output = executor.run(f"{candidate} --version")
        version = f"{output.stdout}\n{output.stderr}".lower()
        if output.exit_code == 0 and "coreutils" in version and "uutils" not in version:
            _gnu_dd_binary[id(executor)] = candidate
            return candidate

    raise CmdException(
        "GNU dd not found. The system 'dd' is not GNU coreutils (likely a uutils "
        "reimplementation, which mis-aligns O_DIRECT buffers) and no 'gnudd' binary "
        "is available. Install the GNU coreutils package on the DUT (e.g. "
        "'gnu-coreutils', which provides the 'gnudd' binary).",
        output,
    )


class Dd(LinuxCommand):
    def __init__(self):
        LinuxCommand.__init__(self, TestRun.executor, _resolve_gnu_dd())

    def block_size(self, value: size.Size):
        return self.set_param('bs', int(value.get_value()))

    def count(self, value):
        return self.set_param('count', value)

    def input(self, value):
        return self.set_param('if', value)

    def iflag(self, *values):
        return self.set_param('iflag', *values)

    def oflag(self, *values):
        return self.set_param('oflag', *values)

    def conv(self, *values):
        return self.set_param('conv', *values)

    def output(self, value):
        return self.set_param('of', value)

    def seek(self, value):
        return self.set_param('seek', value)

    def skip(self, value):
        return self.set_param('skip', value)
