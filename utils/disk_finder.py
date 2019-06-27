from test_package.test_properties import TestProperties
from test_tools import disk_utils


def find_disks():
    block_devices = []
    devices_result = []
    output = TestProperties.executor.execute('isdct')
    if output.exit_code != 0:
        raise Exception(f"Error while executing command: 'isdct'")
    get_block_devices_list(block_devices)
    TestProperties.LOGGER.info(block_devices)
    discover_ssd_devices(block_devices, devices_result)
    discover_hdd_devices(block_devices, devices_result)

    return devices_result


def get_command_output(command):
    output = TestProperties.executor.execute(command)
    return output.stdout


def get_block_devices_list(block_devices):
    devices = get_command_output("ls /sys/block -1").splitlines()
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
            "path": dev,
            "serial": get_command_output(
                f"sg_inq /dev/{dev} | grep 'Unit serial number'").split(': ')[1].strip(),
            "blocksize": block_size,
            "size": disk_utils.get_size(dev)})
    block_devices.clear()


def discover_ssd_devices(block_devices, devices_res):
    ssd_count = int(get_command_output('isdct show -intelssd | grep DevicePath | wc -l'))
    for i in range(0, ssd_count):
        device_path = get_command_output(f"isdct show -intelssd {i} | grep DevicePath").split()[2]
        dev = device_path.replace('/dev/', '')
        serial_number = get_command_output(
            f"isdct show -intelssd {i} | grep SerialNumber").split()[2].strip()
        if 'nvme' not in device_path:
            disk_type = 'sata'
            dev = find_sata_ssd_device_path(serial_number, block_devices)
            if dev is None:
                continue
            if "sg" in device_path:
                device_path = f"/dev/{dev}"
        elif 'Optane' in get_command_output(f"isdct show -intelssd {i} | grep Optane"):
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
        dev_serial = get_command_output(
            f"sg_inq /dev/{dev} | grep 'Unit serial number'").split(': ')[1].strip()
        if dev_serial == serial_number:
            return dev
    return None


def get_system_disk():
    system_partition = get_command_output('mount | grep " / "').split()[0]
    return get_command_output(f'lsblk -no pkname {system_partition}')
