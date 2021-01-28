import os
import logging
from server_utils.nic import Nic

log = logging.getLogger(__name__)


class Bnxtnvm:
    def __init__(self, sit, server):
        self.sit = sit
        self.server = server
        self._path = None

    @property
    def path(self):
        """Return the path to the bnxtnvm binary on the remote server."""
        if self._path is None:
            lines = self.server.exec(f"find {self.sit.path} -maxdepth 1")
            for line in lines:
                file_name = os.path.basename(line)
                if file_name.startswith("bnxtnvm"):
                    self._path = os.path.join(self.sit.path, line)
                    log.debug(f"bnxtnvm path = {self._path}")
            if self._path is None:
                raise FileNotFoundError(f"Cannot find bnxtnvm binary on server {self.server.name} at SIT path"
                                        f" {self.sit.path}")
        return self._path

    def killall(self):
        """Kill all bnxtnvm processes on the remote server."""
        log.debug("Killing all bnxtnvm processes.")
        self.server.exec("killall bnxtvnm", False)

    def install_pkg(self, pkg_file_name, nic: Nic):
        """
        Install firmware on the NIC.

        File is copied to the server and then bnxtnvm is used to install the package to the NIC.

        :param pkg_file_name: local package filename
        :param nic: NIC to install to
        :return: None
        """
        remote_pkg_file_name = os.path.join(self.server.home_dir, os.path.basename(pkg_file_name))
        self.server.copy_to(pkg_file_name, remote_pkg_file_name)
        self._install_pkg(remote_pkg_file_name, nic)

    def install_sit(self, nic: Nic):
        """
        Install SIT firmware on the NIC

        The appropriate SIT package file is found on the server and then bnxtnvm is used to install the package to the
        NIC.

        :param nic: NIC to install to
        :return: None
        """
        remote_pkg_file_name = self.sit.find_pkg(nic.sit_package_filename)
        self._install_pkg(remote_pkg_file_name, nic)

    def _install_pkg(self, pkg_file_name: str, nic: Nic):
        """
        Install firmware on the NIC.

        bnxtnvm is used to install the firmware on the NIC.

        :param pkg_file_name: filename on the remote server
        :param nic: NIC to install to
        :return: None
        """
        log.debug(f"Remote package file name = {pkg_file_name}")
        self.killall()
        first_interface = nic.interfaces[0]
        cmd = f"{self.path} -dev={first_interface} install {pkg_file_name} -live -force -y"
        stdout, stderr, return_code = self.server.exec_return_all(cmd)
        failed = True
        need_reboot = False
        for line in stdout + stderr:
            if "Firmware update is completed." in line:
                failed = False
            if "system reboot is needed" in line:
                need_reboot = True
        if failed:
            raise IOError("Failed to install package.")
        log.warning("Manual system reboot is needed for firmware update to take effect.")
