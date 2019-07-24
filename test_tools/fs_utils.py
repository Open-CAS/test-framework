#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from test_package.test_properties import TestProperties
from aenum import Enum
import base64
import textwrap
from test_utils.size import Size, Unit
from datetime import datetime


class Permissions(Enum):
    read = 4, 'r'
    write = 2, 'w'
    execute = 1, 'x'

    def __str__(self):
        return self.value[1]

    @staticmethod
    def int_to_enum_list(permission: int):
        permissions_list = []
        for p in Permissions:
            if permission - p.value[0] >= 0:
                permission = permission - p.value[0]
                permissions_list.append(p)
        return permissions_list

    @staticmethod
    def char_to_enum(permission_char):
        for p in Permissions:
            if p.value[1] == permission_char:
                return p
            elif permission_char == '-':
                return None
        raise Exception(f"Cannot parse '{permission_char}' to permission enum.")


def create_directory(path, parents: bool = False):
    cmd = f"mkdir {'--parents ' if parents else ''}{path}"
    return TestProperties.execute_command_and_check(cmd)[0]


def check_if_directory_exists(path):
    return TestProperties.executor.execute(f"test -d {path}").exit_code == 0


def check_if_file_exists(path):
    return TestProperties.executor.execute(f"test -e {path}").exit_code == 0


def copy(source: str,
         destination: str,
         force: bool = False,
         recursive: bool = False,
         dereference: bool = False):
    cmd = f"cp{' --force' if force else ''}" \
        f"{' --recursive' if recursive else ''}" \
        f"{' --dereference' if dereference else ''} " \
        f"{source} {destination}"
    return TestProperties.execute_command_and_check(cmd)[0]


def move(source, destination, force: bool = False):
    cmd = f"mv{' --force' if force else ''} {source} {destination}"
    return TestProperties.execute_command_and_check(cmd)[0]


def remove(path, force: bool = False, recursive: bool = False, ignore_errors: bool = False):
    cmd = f"rm{' --force' if force else ''}{' --recursive' if recursive else ''} {path}"
    success, output = TestProperties.execute_command_and_check(cmd)
    if not success and not ignore_errors:
        raise Exception(f"Could not remove file {path}."
                        f"\nstdout: {output.stdout}\nstderr: {output.stderr}")
    return success


def chmod(path, permissions: [Permissions], add: bool = True, recursive: bool = False):
    if len(permissions) > 3:
        raise Exception("Too many permission values given.")
    permission_str = ''
    for p in permissions:
        permission_str += str(p)
    cmd = f"chmod{' --recursive' if recursive else ''} " \
        f"{'+' if add else '-'}{permission_str} {path}"
    result = TestProperties.execute_command_and_check(cmd)
    if "new permissions are" in result[1].stderr:
        result[0] = True
    return result[0]


def chmod_numerical(path, permissions: [int], recursive: bool = False):
    if len(permissions) > 3:
        raise Exception("Too many permission values given.")
    permission_srt = ''
    for i in permissions:
        if i > 7:
            raise Exception("Permission numerical value cannot be greater than 7.")
        permission_srt += str(i)
    cmd = f"chmod{' --recursive' if recursive else ''} {permission_srt} {path}"
    return TestProperties.execute_command_and_check(cmd)[0]


def chown(path, owner, group, recursive):
    cmd = f"chown {'-R ' if recursive else ''}{owner}:{group} {path}"
    return TestProperties.execute_command_and_check(cmd)[0]


def create_file(path):
    if not path.strip():
        raise ValueError("Path cannot be empty or whitespaces.")
    cmd = f"touch '{path}'"
    return TestProperties.execute_command_and_check(cmd)[0]


def compare(file, other_file, options=None):
    output = TestProperties.executor.execute(
        f"cmp --silent {options if options else ''} {file} {other_file}")
    if output.exit_code == 0:
        return True
    elif output.exit_code > 1:
        raise Exception(f"Compare command execution failed. {output.stdout}\n{output.stderr}")
    else:
        return False


def diff(file, other_file, options=None):
    output = TestProperties.executor.execute(
        f"diff {options if options else ''} {file} {other_file}")
    if output.exit_code == 0:
        return None
    elif output.exit_code > 1:
        raise Exception(f"Diff command execution failed. {output.stdout}\n{output.stderr}")
    else:
        return output.stderr


# The separator in sed command could not be used in string, which is given as a sed parameter
def get_sed_separator(first_pattern, second_pattern=None):
    sed_separators = ['/', ':', ';', ',', '.']
    if second_pattern is None:
        second_pattern = ''
    for char in sed_separators:
        if char in first_pattern or char in second_pattern:
            continue
        else:
            return char
    raise ValueError("Sed separator cannot be empty.")


def insert_line_before_pattern(file, pattern, new_line):
    separator = get_sed_separator(pattern)
    pattern = pattern.replace("'", "\\x27")
    new_line = new_line.replace("'", "\\x27")
    cmd = f"sed -i '{separator}{pattern}{separator}i {new_line}' {file}"
    return TestProperties.execute_command_and_check(cmd)[0]


def replace_first_pattern_occurance(file, pattern, new_line):
    separator = get_sed_separator(pattern, new_line)
    pattern = pattern.replace("'", "\\x27")
    new_line = new_line.replace("'", "\\x27")
    cmd = f"sed -i '0,{separator}{pattern}{separator}s" \
        f"{separator}{pattern}{separator}{new_line}{separator}' {file}"
    return TestProperties.execute_command_and_check(cmd)[0]


def replace_in_lines(file, pattern, new_line, regexp=False):
    separator = get_sed_separator(pattern, new_line)
    pattern = pattern.replace("'", "\\x27")
    new_line = new_line.replace("'", "\\x27")
    cmd = f"sed -i{' -r' if regexp else ''} " \
        f"'s{separator}{pattern}{separator}{new_line}{separator}g' {file}"
    return TestProperties.execute_command_and_check(cmd)[0]


def read_file(file):
    if not file.strip():
        raise ValueError("File path cannot be empty or whitespace.")
    output = TestProperties.execute_command_and_check(f"cat {file}")
    return output[1].stdout


def write_file(file, content, overwrite: bool = True, unix_line_end: bool = True):
    if not file.strip():
        raise ValueError("File path cannot be empty or whitespace.")
    if not content:
        raise ValueError("Content cannot be empty.")
    if unix_line_end:
        content.replace('\r', '')
    content += '\n'
    max_length = 60000
    split_content = textwrap.TextWrapper(width=max_length, replace_whitespace=False).wrap(content)
    split_content[-1] += '\n'
    for s in split_content:
        redirection_char = '>' if overwrite else '>>'
        overwrite = False
        encoded_content = base64.b64encode(s.encode("utf-8"))
        cmd = f"printf '{encoded_content.decode('utf-8')}' " \
            f"| base64 --decode {redirection_char} {file}"
        TestProperties.execute_command_and_check(cmd)


def __wrap(text, max_len):
    split_text = text.split('\n')
    lines = [line for para in split_text for line in textwrap.TextWrapper(
        width=max_len, replace_whitespace=False).wrap(para)]
    return lines


def ls(path, options=''):
    default_options = "-lA --time-style=+'%Y-%m-%d %H:%M:%S'"
    output = TestProperties.execute_command_and_check(
        f"ls {default_options} {' '.join(options)} {path}")
    return output[1].stdout


def parse_ls_output(ls_output, dir_path=''):
    split_output = ls_output.split('\n')
    fs_items = []
    for line in split_output:
        if not line.strip():
            continue
        line_fields = list(filter(None, line.split()))
        if len(line_fields) != 8:
            continue
        file_type = line[0]
        if file_type not in ['-', 'd', 'l', 'b', 'c', 'p', 's']:
            continue
        permissions = line_fields[0][1:].replace('.', '')
        owner = line_fields[2]
        group = line_fields[3]
        size = Size(float(line_fields[4]), Unit.Byte)
        split_date = line_fields[5].split('-')
        split_time = line_fields[6].split(':')
        modification_time = datetime(int(split_date[0]), int(split_date[1]), int(split_date[2]),
                                     int(split_time[0]), int(split_time[1]), int(split_time[2]))
        if dir_path:
            full_path = '/'.join([dir_path, line_fields[7]])
        else:
            full_path = line_fields[7]

        from test_utils.filesystem.file import File, FsItem
        from test_utils.filesystem.directory import Directory

        if file_type == '-':
            fs_item = File(full_path)
        elif file_type == 'd':
            fs_item = Directory(full_path)
        else:
            fs_item = FsItem(full_path)

        for i in range(3):
            user = Permissions.char_to_enum(permissions[i])
            if user is not None:
                fs_item.permissions.user.append(user)
            group = Permissions.char_to_enum(permissions[i + 3])
            if group is not None:
                fs_item.permissions.group.append(group)
            other = Permissions.char_to_enum(permissions[i + 6])
            if other is not None:
                fs_item.permissions.other.append(other)

        fs_item.owner = owner
        fs_item.group = group
        fs_item.size = size
        fs_item.modification_time = modification_time
        fs_items.append(fs_item)
    return fs_items
