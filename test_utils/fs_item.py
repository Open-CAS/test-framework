#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import ntpath
from test_tools import fs_utils
from multimethod import multimethod


class FsItem:
    def __init__(self, full_path):
        self.full_path = full_path
        self.parent_dir = self.get_parent_dir(self.full_path)
        self.name = self.get_name(self.full_path)
        self.modification_time = None
        self.owner = None
        self.group = None
        self.permissions = None
        self.size = None

    @staticmethod
    def get_name(path):
        head, tail = ntpath.split(path)
        return tail or ntpath.basename(head)

    @staticmethod
    def get_parent_dir(path):
        head, tail = ntpath.split(path)
        if tail:
            return head
        else:
            head, tail = ntpath.split(head)
            return head

    def __str__(self):
        return self.full_path

    @multimethod
    def chmod(self, permissions: fs_utils.Permissions, recursive):
        if fs_utils.chmod(self.full_path, permissions, recursive=recursive):
            self.permissions = permissions

    @multimethod
    def chmod(self, permissions: fs_utils.Permissions, add, recursive):
        if fs_utils.chmod(self.full_path, permissions, add, recursive):
            self.permissions = permissions

    def chown(self, owner, group, recursive: bool = False):
        if fs_utils.chown(self.full_path, owner, group, recursive):
            self.owner = owner
            self.group = group
