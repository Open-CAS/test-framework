#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


class FioResult:
    def __init__(self, result, job):
        self.result_dict = {
            "Total read I/O [KiB]": job.read.io_kbytes,
            "Total read bandwidth [KiB/s]": job.read.bw,
            "Read bandwidth average [KiB/s]": job.read.bw_mean,
            "Read bandwidth deviation [KiB/s]": job.read.bw_dev,
            "Read IOPS": job.read.iops,
            "Read runtime [ms]": job.read.runtime,
            "Read average completion latency [us]": job.read.clat_ns.mean / 1000,
            "Total write I/O [KiB]": job.write.io_kbytes,
            "Total write bandwidth [KiB/s]": job.write.bw,
            "Write bandwidth average [KiB/s]": job.write.bw_mean,
            "Write bandwidth deviation [KiB/s]": job.write.bw_dev,
            "Write IOPS": job.write.iops,
            "Write runtime [ms]": job.write.runtime,
            "Write average completion latency [us]": job.write.clat_ns.mean / 1000
        }

        self.disks_name = []
        if hasattr(result, 'disk_util'):
            for disk in result.disk_util:
                self.disks_name.append(disk.name)
            self.result_dict.update({'Disk name': ','.join(self.disks_name)})

        self.result_dict.update({'Total number of errors': 0})
        if hasattr(result, 'total_err'):
            self.result_dict['Total number of errors'] = result.total_err

    def __str__(self):
        s = ''
        for key in self.result_dict.keys():
            s += f"{key}: {self.result_dict[key]}\n"
        return s

    def read_io(self):
        return self.result_dict["Total read I/O [KiB]"]

    def read_bandwidth(self):
        return self.result_dict["Total read bandwidth [KiB/s]"]

    def read_bandwidth_average(self):
        return self.result_dict["Read bandwidth average [KiB/s]"]

    def read_bandwidth_deviation(self):
        return self.result_dict["Read bandwidth deviation [KiB/s]"]

    def read_iops(self):
        return self.result_dict["Read IOPS"]

    def read_runtime(self):
        return self.result_dict["Read runtime [ms]"]

    def read_completion_latency_average(self):
        return self.result_dict["Read average completion latency [us]"]

    def write_io(self):
        return self.result_dict["Total write I/O [KiB]"]

    def write_bandwidth(self):
        return self.result_dict["Total write bandwidth [KiB/s]"]

    def write_bandwidth_average(self):
        return self.result_dict["Write bandwidth average [KiB/s]"]

    def write_bandwidth_deviation(self):
        return self.result_dict["Write bandwidth deviation [KiB/s]"]

    def write_iops(self):
        return self.result_dict["Write IOPS"]

    def write_runtime(self):
        return self.result_dict["Write runtime [ms]"]

    def write_completion_latency_average(self):
        return self.result_dict["Write average completion latency [us]"]
