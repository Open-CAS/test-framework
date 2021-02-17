#
# Copyright(c) 2020 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from os.path import join
from core.test_run import TestRun
from test_tools.fs_utils import ls, parse_ls_output


class Rpm:
    def __init__(self, name: str, packages_dir: str = None):
        self.name = name
        self.packages_dir = packages_dir
        self.packages_to_install = set()
        self.update_packages_to_install()
        self.installed_packages = set()
        self.update_installed_packages()

    def __str__(self):
        return self.name

    def make_rpm(self, sources_dir):
        """
        Generate installation packages in default directory with 'Make' script.
        param: sources_dir: directory with make script to generate RPM packages
        """
        TestRun.executor.run_expect_success(f"cd {sources_dir} && make rpm")
        self.packages_dir = join(sources_dir, 'packages')

    def update_packages_to_install(self):
        """
        Get list of installation packages from a directory.
        exception: no packages found
        """
        output = parse_ls_output(ls(self.packages_dir), self.packages_dir)
        if output is not None:
            self.packages_to_install.update(
                [file.full_path for file in output if file.full_path.endswith(".rpm")]
            )
        else:
            raise Exception(
                f"Location {self.packages_dir} doesn't exist. "
                f"Cannot search there for RPM packages to install."
            )

    def install_packages(self, force: bool = True):
        """
        Install/upgrade packages with the RPM.
        param: force: ignore warnings related to package conflicts
        exception: install/upgrade packages failed
        """
        TestRun.LOGGER.info("Installing from RPM packages.")
        if not self.packages_to_install:
            TestRun.LOGGER.info("No packages to install. Installation skipped.")
            return
        cmd = 'rpm --upgrade --hash --verbose '
        cmd += " ".join(self.packages_to_install)
        if force:
            cmd += ' --force'

        try:
            TestRun.executor.run_expect_success(cmd)
        except Exception as exc:
            raise Exception(f"Cannot install/upgrade '{self.packages_to_install}' RPM packages."
                            f"\n{exc}")
        self.update_installed_packages()

    def uninstall_packages(self, allmatches: bool = True):
        """
        Uninstall packages with the RPM.
        param: allmatches: remove dependent packages
        exception: uninstall packages failed
        """
        TestRun.LOGGER.info("Uninstalling RPM packages.")
        cmd = 'rpm --erase --hash --verbose '
        if self.installed_packages:
            cmd += " ".join(self.installed_packages)
        else:
            cmd += self.name
        if allmatches:
            cmd += ' --allmatches'

        try:
            TestRun.executor.run_expect_success(cmd)
        except Exception as exc:
            raise Exception(f"Cannot uninstall '{self.installed_packages}' RPM packages."
                            f"\n{exc}")
        self.installed_packages.clear()
        self.update_packages_to_install()

    def reinstall_packages(self):
        """
        Reinstall packages with the RPM.
        exception: reinstall packages failed
        """
        TestRun.LOGGER.info("Reinstalling RPM packages.")
        if not self.packages_to_install:
            TestRun.LOGGER.info("No packages to reinstall. Installation skipped.")
            return
        cmd = 'rpm --reinstall --hash --verbose '
        cmd += " ".join(self.packages_to_install)

        try:
            TestRun.executor.run_expect_success(cmd)
        except Exception as exc:
            raise Exception(f"Cannot reinstall {' '.join(self.packages_to_install)} "
                            f"RPM packages.\n{exc}")
        self.update_installed_packages()

    def update_installed_packages(self):
        """
        Send a query to the RPM to update list of installed packages.
        """
        for package in self.packages_to_install:
            # only package name is correct argument in query, not whole path
            package = package.split("/")[-1].replace(".rpm", "")
            cmd = f'rpm --query "{package}"'
            try:
                output = TestRun.executor.run_expect_success(cmd)
                self.installed_packages.update(output.stdout)
            except Exception:
                if Rpm.is_package_installed(package):
                    self.installed_packages.remove(output.stdout)
                TestRun.LOGGER.info(
                    f"Cannot retrieve info about installed RPM package '{package}'."
                )

    @staticmethod
    def is_package_installed(name):
        """
        Check if given package is on the RPM's list of installed packages
        return: true if package is on the list, false if not
        """
        cmd = f'rpm --query "{name}"'
        output = TestRun.executor.run(cmd)
        return output.exit_code == 0
