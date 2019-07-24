#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import pytest
from test_tools.disk_utils import Filesystem
from test_utils.size import Size, Unit
from test_package.test_properties import TestProperties
from test_package.conftest import base_prepare
from test_utils.filesystem.file import File
from test_utils.filesystem.directory import Directory
from test_tools import fs_utils


def setup_module():
    TestProperties.LOGGER.warning("Entering setup method")


@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"cache_type": "optane", "cache_count": 1}],
                         indirect=True)
def test_example(prepare_and_cleanup):
    prepare()
    TestProperties.LOGGER.info("Test run")
    TestProperties.LOGGER.info(f"DUT info: {TestProperties.dut}")
    output = TestProperties.executor.execute("hostname -I | awk '{print $1}'")
    TestProperties.LOGGER.info(output.stdout)
    assert output.stdout.strip() == TestProperties.dut.ip


@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"cache_type": "nand", "cache_count": 1}],
                         indirect=True)
def test_create_example_partitions(prepare_and_cleanup):
    prepare()
    TestProperties.LOGGER.info("Test run")
    output = TestProperties.executor.execute("hostname -I | awk '{print $1}'")
    TestProperties.LOGGER.info(output.stdout)
    TestProperties.LOGGER.info(f"DUT info: {TestProperties.dut}")
    assert output.stdout.strip() == TestProperties.dut.ip
    test_disk = TestProperties.dut.disks[0]
    part_sizes = []
    for i in range(1, 6):
        part_sizes.append(Size(10 * i + 100, Unit.MebiByte))
    test_disk.create_partitions(part_sizes)
    TestProperties.LOGGER.info(f"DUT info: {TestProperties.dut}")
    test_disk.partitions[0].create_filesystem(Filesystem.ext3)


@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"cache_type": "nand", "cache_count": 1}],
                         indirect=True)
def test_create_example_files(prepare_and_cleanup):
    prepare()
    TestProperties.LOGGER.info("Test run")
    file1 = File.create_file("/home/user/example_file")
    file1.write("Test file\ncontent line\ncontent")
    TestProperties.LOGGER.info(f"File content: {file1.read()}")
    fs_utils.replace_in_lines(file1, 'content line', 'replaced line')
    file2 = file1.copy('/tmp', force=True)
    assert file1.md5sum() == file2.md5sum()
    file2.chmod_numerical([1, 2, 3])
    fs_utils.remove(file2.full_path, True)
    dir1 = Directory("/home/user")
    dir_content = dir1.ls()
    file1.chmod([fs_utils.Permissions.write, fs_utils.Permissions.read])
    for item in dir_content:
        TestProperties.LOGGER.info(f"Item {str(item)} - {type(item).__name__}")


def prepare():
    base_prepare()
