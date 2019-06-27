#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import time


def wait(predicate, timeout, interval=None):
    start = time.time()
    result = False
    while time.time() - start < timeout:
        result = predicate()
        if result:
            break
        if interval is not None:
            time.sleep(interval)
    return result
