#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


class FioResult:
    def __init__(self, result, job):
        self.result = result
        self.job = job

    def __str__(self):
        result_dict = {
            "Total read I/O [KiB]": self.read_io(),
            "Total read bandwidth [KiB/s]": self.read_bandwidth(),
            "Read bandwidth average [KiB/s]": self.read_bandwidth_average(),
            "Read bandwidth deviation [KiB/s]": self.read_bandwidth_deviation(),
            "Read IOPS": self.read_iops(),
            "Read runtime [ms]": self.read_runtime(),
            "Read average completion latency [us]": self.read_completion_latency_average(),
            "Total write I/O [KiB]": self.write_io(),
            "Total write bandwidth [KiB/s]": self.write_bandwidth(),
            "Write bandwidth average [KiB/s]": self.write_bandwidth_average(),
            "Write bandwidth deviation [KiB/s]": self.write_bandwidth_deviation(),
            "Write IOPS": self.write_iops(),
            "Write runtime [ms]": self.write_runtime(),
            "Write average completion latency [us]": self.write_completion_latency_average(),
        }

        disks_name = self.disks_name()
        if disks_name:
            result_dict.update({'Disk name': ','.join(disks_name)})

        result_dict.update({'Total number of errors': self.total_errors()})

        s = ''
        for key in result_dict.keys():
            s += f"{key}: {result_dict[key]}\n"
        return s

    def total_errors(self):
        if hasattr(self.result, 'total_err'):
            return self.result.total_err
        return 0

    def disks_name(self):
        disks_name = []
        if hasattr(self.result, 'disk_util'):
            for disk in self.result.disk_util:
                disks_name.append(disk.name)
        return disks_name

    def read_io(self):
        return self.job.read.io_kbytes

    def read_bandwidth(self):
        return self.job.read.bw

    def read_bandwidth_average(self):
        return self.job.read.bw_mean

    def read_bandwidth_deviation(self):
        return self.job.read.bw_dev

    def read_iops(self):
        return self.job.read.iops

    def read_runtime(self):
        return self.job.read.runtime

    def read_completion_latency_average(self):
        return self.job.read.clat_ns.mean / 1000

    def write_io(self):
        return self.job.write.io_kbytes

    def write_bandwidth(self):
        return self.job.write.bw

    def write_bandwidth_average(self):
        return self.job.write.bw_mean

    def write_bandwidth_deviation(self):
        return self.job.write.bw_dev

    def write_iops(self):
        return self.job.write.iops

    def write_runtime(self):
        return self.job.write.runtime

    def write_completion_latency_average(self):
        return self.job.write.clat_ns.mean / 1000
