#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from core.test_run import TestRun
from test_tools import disk_utils


def find_disks():
    block_devices = []
    devices_result = []

    TestRun.LOGGER.info("Finding platform's disks.")

    # TODO: isdct should be implemented as a separate tool in the future.
    #  There will be isdct installator in case, when it is not installed
    output = TestRun.executor.run('isdct')
    if output.exit_code != 0:
        raise Exception(f"Error while executing command: 'isdct'.\n"
                        f"stdout: {output.stdout}\nstderr: {output.stderr}")
    get_block_devices_list(block_devices)
    try:
        discover_ssd_devices(block_devices, devices_result)
        discover_hdd_devices(block_devices, devices_result)
    except Exception as e:
        raise Exception(f"Exception occurred while looking for disks: {str(e)}")

    return devices_result


def get_block_devices_list(block_devices):
    devices = TestRun.executor.run_expect_success("ls /sys/block -1").stdout.splitlines()
    os_disk = get_system_disk()

    for dev in devices:
        if ('sd' in dev or 'nvme' in dev) and dev != os_disk:
            block_devices.append(dev)


def discover_hdd_devices(block_devices, devices_res):
    for dev in block_devices:
        block_size = disk_utils.get_block_size(dev)
        if int(block_size) == 4096:
            disk_type = 'hdd4k'
        else:
            disk_type = 'hdd'
        devices_res.append({
            "type": disk_type,
            "path": f"/dev/{dev}",
            "serial": TestRun.executor.run_expect_success(
                f"sg_inq /dev/{dev} | grep 'Unit serial number'").stdout.split(': ')[1].strip(),
            "blocksize": block_size,
            "size": disk_utils.get_size(dev)})
    block_devices.clear()


# This method discovers only Intel SSD devices
def discover_ssd_devices(block_devices, devices_res):
    ssd_count = int(TestRun.executor.run_expect_success(
        'isdct show -intelssd | grep DevicePath | wc -l').stdout)
    for i in range(0, ssd_count):
        device_path = TestRun.executor.run_expect_success(
            f"isdct show -intelssd {i} | grep DevicePath").stdout.split()[2]
        dev = device_path.replace('/dev/', '')
        serial_number = TestRun.executor.run_expect_success(
            f"isdct show -intelssd {i} | grep SerialNumber").stdout.split()[2].strip()
        if 'nvme' not in device_path:
            disk_type = 'sata'
            dev = find_sata_ssd_device_path(serial_number, block_devices)
            if dev is None:
                continue
            if "sg" in device_path:
                device_path = f"/dev/{dev}"
        elif TestRun.executor.run(
                f"isdct show -intelssd {i} | grep Optane").exit_code == 0:
            disk_type = 'optane'
        else:
            disk_type = 'nand'

        devices_res.append({
            "type": disk_type,
            "path": device_path,
            "serial": serial_number,
            "blocksize": disk_utils.get_block_size(dev),
            "size": disk_utils.get_size(dev)})
        block_devices.remove(dev)


def find_sata_ssd_device_path(serial_number, block_devices):
    for dev in block_devices:
        dev_serial = TestRun.executor.run_expect_success(
            f"sg_inq /dev/{dev} | grep 'Unit serial number'").stdout.split(': ')[1].strip()
        if dev_serial == serial_number:
            return dev
    return None


def get_system_disk():
    system_partition = TestRun.executor.run_expect_success('mount | grep " / "').stdout.split()[0]
    return TestRun.executor.run_expect_success(f'lsblk -no pkname {system_partition}').stdout
