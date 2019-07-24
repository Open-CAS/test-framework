#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import ntpath
from test_tools import fs_utils


class FsItem:
    def __init__(self, full_path):
        self.full_path = full_path
        self.parent_dir = self.get_parent_dir(self.full_path)
        self.name = self.get_name(self.full_path)
        self.modification_time = None
        self.owner = None
        self.group = None
        self.permissions = FsPermissions()
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

    def chmod_numerical(self, permissions: [int], recursive: bool = False):
        if fs_utils.chmod_numerical(self.full_path, permissions, recursive):
            self.permissions.user = fs_utils.Permissions.int_to_enum_list(permissions[0])
            if len(permissions) > 1:
                self.permissions.group = fs_utils.Permissions.int_to_enum_list(permissions[1])
            if len(permissions) > 2:
                self.permissions.other = fs_utils.Permissions.int_to_enum_list(permissions[2])

    def chmod(self,
              permissions: [fs_utils.Permissions],
              add: bool = True,
              recursive: bool = False):
        if fs_utils.chmod(self.full_path, permissions, add=add, recursive=recursive):
            for p in permissions:
                if p not in self.permissions.user and add:
                    self.permissions.user.append(p)
                if p not in self.permissions.group and p != fs_utils.Permissions.write and add:
                    self.permissions.group.append(p)
                if p not in self.permissions.other and p != fs_utils.Permissions.write and add:
                    self.permissions.other.append(p)
                if not add:
                    try:
                        self.permissions.user.remove(p)
                        self.permissions.group.remove(p)
                        self.permissions.other.remove(p)
                    except Exception:
                        pass

    def chown(self, owner, group, recursive: bool = False):
        if fs_utils.chown(self.full_path, owner, group, recursive):
            self.owner = owner
            self.group = group


class FsPermissions:
    def __init__(self, user=[], group=[], other=[]):
        self.user = user
        self.group = group
        self.other = other
