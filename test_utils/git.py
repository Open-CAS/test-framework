#
# Copyright(c) 2019-2022 Intel Corporation
# Copyright(c) 2024 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: BSD-3-Clause
#
import itertools
import os
import posixpath

from core.test_run import TestRun
from connection.local_executor import LocalExecutor
from test_utils.output import CmdException


def __get_executor_and_repo_path(from_dut):
    executor = TestRun.executor if from_dut else LocalExecutor()
    repo_path = TestRun.usr.working_dir if from_dut else TestRun.usr.repo_dir

    return executor, repo_path


def get_submodules_paths(from_dut: bool = False):
    executor, repo_path = __get_executor_and_repo_path(from_dut)
    git_params = "config --file .gitmodules --get-regexp path | cut -d' ' -f2"

    output = executor.run(f"git -C {repo_path} {git_params}")
    if output.exit_code != 0:
        raise CmdException("Failed to get submodules paths", output)

    return output.stdout.splitlines()


def __get_repo_files(branch, repo_path, executor, with_dirs):
    git_params = f"ls-tree -r --name-only --full-tree {branch}"

    output = executor.run(f"git -C {repo_path} {git_params}")
    if output.exit_code != 0:
        raise CmdException(f"Failed to get {repo_path} repo files list", output)

    files = [posixpath.join(repo_path, file) for file in output.stdout.splitlines() if file]

    if with_dirs:
        dirs = set(os.path.dirname(file) for file in files)
        files.extend(dirs)

    return files


def get_repo_files(
    branch: str = "HEAD",
    with_submodules: bool = True,
    with_dirs: bool = False,
    from_dut: bool = False,
):
    executor, repo_path = __get_executor_and_repo_path(from_dut)
    repos_to_list = [repo_path]

    if with_submodules:
        repos_to_list.extend(
            [posixpath.join(repo_path, path) for path in get_submodules_paths(from_dut)]
        )

    files_lists = [file_list for file_list in
                   [__get_repo_files(branch, path, executor, with_dirs) for path in repos_to_list]]
    # At this point we have a list of lists which must be flattened
    files = list(itertools.chain.from_iterable(files_lists))

    return files


def get_current_commit_hash(from_dut: bool = False):
    executor, repo_path = __get_executor_and_repo_path(from_dut)

    return executor.run(
        f"cd {repo_path} &&"
        f'git show HEAD -s --pretty=format:"%H"').stdout


def get_current_commit_message():
    local_executor = LocalExecutor()
    return local_executor.run(
        f"cd {TestRun.usr.repo_dir} &&"
        f'git show HEAD -s --pretty=format:"%B"').stdout


def get_commit_hash(version, from_dut: bool = False):
    executor, repo_path = __get_executor_and_repo_path(from_dut)

    output = executor.run(
        f"cd {repo_path} && "
        f"git rev-parse {version}")
    if output.exit_code != 0:
        raise CmdException(f"Failed to resolve '{version}' to commit hash", output)

    TestRun.LOGGER.info(f"Resolved '{version}' as commit {output.stdout}")

    return output.stdout


def get_release_tags(forbidden_characters: list = None):
    repo_path = os.path.join(TestRun.usr.working_dir, ".git")
    output = TestRun.executor.run_expect_success(f"git --git-dir={repo_path} tag").stdout

    if not forbidden_characters:
        return output.splitlines()
    else:
        return [v for v in output.splitlines() if all(c not in v for c in forbidden_characters)]


def checkout_version(version):
    commit_hash = get_commit_hash(version)
    TestRun.LOGGER.info(f"Checkout to {commit_hash}")

    output = TestRun.executor.run(
        f"cd {TestRun.usr.working_dir} && "
        f"git checkout --force {commit_hash}")
    if output.exit_code != 0:
        raise CmdException(f"Failed to checkout to {commit_hash}", output)

    output = TestRun.executor.run(
        f"cd {TestRun.usr.working_dir} && "
        f"git submodule update --force")
    if output.exit_code != 0:
        raise CmdException(f"Failed to update submodules", output)
