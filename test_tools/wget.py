#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#

from core.test_run import TestRun
from test_utils.filesystem.file import File


def download_file(url, destination_dir="/tmp"):
    # TODO use wget module instead
    command = ("wget --tries=3 --timeout=5 --continue --quiet "
               f"--directory-prefix={destination_dir} {url}")
    TestRun.executor.run_expect_success(command)
    path = f"{destination_dir.rstrip('/')}/{File.get_name(url)}"
    return File(path)
