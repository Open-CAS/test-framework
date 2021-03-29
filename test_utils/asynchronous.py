#
# Copyright(c) 2020-2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import asyncio


def start_async_func(func, *args):
    """
    Starts asynchronous task and returns an awaitable Future object, which in turn returns an
    actual result after being awaited.
    """
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, args)
