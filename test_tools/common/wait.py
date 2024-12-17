#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

import time
from datetime import timedelta, datetime


def wait(predicate, timeout: timedelta, interval: timedelta = None):
    start_time = datetime.now()
    result = False
    while start_time + timeout > datetime.now():
        result = predicate()
        if result:
            break
        if interval is not None:
            time.sleep(interval.total_seconds())
    return result
