#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


class Dut:
    def __init__(self, dut_info):
        self.ip = dut_info['ip']
        self.disks = dut_info['disks']
        self.ipmi = dut_info['ipmiip'] if 'ipmiip' in dut_info else None
        self.spider = dut_info['spiderip'] if 'spiderip' in dut_info else None
        self.wps = dut_info['wpsid'] if 'wpsid' in dut_info else None
        self.wps_port = dut_info['wpsport'] if 'wpsport' in dut_info else None

    def __str__(self):
        dut_str = f'ip: {self.ip}\n'
        dut_str += f'disks:\n'
        for disk in self.disks:
            dut_str += f'\ttype: {disk["type"]}, serial: {disk["serial"]}, ' \
                f'size: {disk["size"]}, blocksize: {disk["blocksize"]}\n'
        dut_str += f'ipmi: {self.ipmi}\n' if self.ipmi is not None else ''
        dut_str += f'spider: {self.spider}\n' if self.spider is not None else ''
        dut_str += f'wps: {self.wps}\n' if self.wps is not None else ''
        dut_str += f'wps port: {self.wps_port}\n' if self.wps_port is not None else ''
        return dut_str
