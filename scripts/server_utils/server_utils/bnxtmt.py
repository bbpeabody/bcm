import logging
import os
import re
import sys
from copy import copy
import signal

from pexpect import spawn
from pexpect.exceptions import TIMEOUT as Timeout

from server_utils.nic import Nic

log = logging.getLogger(__name__)


def prompt(device: int) -> str:
    """Return the expected bnxtmt prompt given the device number."""
    return f"bnxtmt {device}:> "


def slow_sendline(exp: spawn, string: str):
    """Send one character at a time and wait for echo. The expect session deadlocks if we don't do this."""
    for i in range(len(string)):
        exp.send(string[i])
        exp.expect_exact(string[i])
    exp.send('\n')


class Bnxtmt:
    def __init__(self, sit, server):
        self.sit = sit
        self.server = server
        self._path = None
        self._last_buffer_hash = None
        self._trace_buffer = None
        self._pci_bdf = None
        self._device = None

    @property
    def path(self) -> str:
        """Return the path on the remote server to the bnxtmt directory."""
        if self._path is None:
            lines = self.server.exec(f"find {self.sit.path} -maxdepth 1 -type d")
            for line in lines:
                dir_name = os.path.basename(line)
                if dir_name.startswith("bnxtmt"):
                    self._path = os.path.join(self.sit.path, line)
                    log.debug(f"SIT path = {self._path}")
            if self._path is None:
                raise FileNotFoundError(f"Cannot find bnxtmt directory on server {self.server.name} at SIT path"
                                        f" {self.sit.path}")
        return self._path

    def killall(self):
        """Kill all bnxtmt processes on the remote server."""
        log.debug("Killing all bnxtmt processes.")
        self.server.exec("killall bnxtmt", False)

    def get_device_num(self, pci_bdf: str) -> int:
        """Given a PCI addresss, return the corresponding bnxtmt device number"""
        pci_bdf_parts = re.split(f':|\.', pci_bdf)
        if len(pci_bdf_parts) == 3:
            # Insert default domain of zero if not included in BDF (Bus, Device, Function)
            pci_bdf_parts.insert(0, "0")
        if len(pci_bdf_parts) != 4:
            raise ValueError(f"Improperly formatted PCI BDF {pci_bdf}. Example: 65:00.0 or 0000:65:00.0")
        # Format BDF in the style of bnxtmt
        domain = int(pci_bdf_parts[0], 16)
        bus = int(pci_bdf_parts[1], 16)
        device = int(pci_bdf_parts[2], 16)
        function = int(pci_bdf_parts[3], 16)
        pci_bdf = f"{domain:02X}:{bus:02X}:{device:02X}:{function:02X}"
        log.debug(f"Searching for {pci_bdf} in bnxtmt output.")
        self.killall()
        script = f'''
            cd {self.path}
            ./load.sh -eval " "
            exit
        '''
        lines = self.server.run_script(script)
        for line in lines:
            line = line.strip()
            match = re.match(rf'(\d+)\s+:.*\s+{pci_bdf}\s+', line)
            if match:
                return int(match.group(1))
        raise ValueError(f"Cannot find bnxtmt device number for PCI BDF {pci_bdf} on server {self.server.name}")

    def install_pkg(self, pkg_file_name: str, nic: Nic):
        """
        Install firmware on the NIC.

        File is copied to the server and then bnxtmt is used to install the package to the NIC.

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

        The appropriate SIT package file is found on the server and then bnxtmt is used to install the package to the
        NIC.

        :param nic: NIC to install to
        :return: None
        """
        remote_pkg_file_name = self.sit.find_pkg(nic.sit_package_filename)
        self._install_pkg(remote_pkg_file_name, nic)

    def _install_pkg(self, pkg_file_name: str, nic: Nic):
        """
        Install firmware on the NIC.

        bnxtmt is used to install the firmware on the NIC.

        :param pkg_file_name: filename on the remote server
        :param nic: NIC to install to
        :return: None
        """
        log.debug(f"Remote package file name = {pkg_file_name}")
        self.killall()
        script = f'''
            cd {self.path}
            ./load.sh -eval "device {nic.bnxtmt_device}; nvm pkginstall {pkg_file_name}; reset all"
            exit
        '''
        lines = self.server.run_script(script)
        failed = True
        for line in lines:
            line = line.lower()
            if "failure" in line or "failed" in line:
                failed = True
                break
            if "clearing fastboot registers" in line:
                failed = False
        if failed:
            raise IOError("Failed to install package.")

    def reset_all(self, nic: Nic):
        """
        Execute the bnxtmt command 'reset all' on the NIC

        :param nic: NIC to be reset.
        """
        self.killall()
        script = f'''
            cd {self.path}
            ./load.sh -eval "device {nic.bnxtmt_device}; reset all"
            exit
        '''
        lines = self.server.run_script(script)
        failed = True
        for line in lines:
            line = line.lower()
            if "clearing fastboot registers" in line:
                failed = False
        if failed:
            raise IOError(f"Failed to reset device {nic.bnxtmt_device}.")

    def reset_cfg(self, nic: Nic):
        """
        Reset the NIC's configuration to factory default.

        Find the SYS_CFG NVM directory entry and erase it.

        :param nic: NIC to reset to factory default
        """
        self.killall()
        dir_entry = self.get_sys_cfg_entry(nic)
        script = f'''
            cd {self.path}
            ./load.sh -eval "device {nic.bnxtmt_device}; nvm erase {dir_entry}"
            exit
        '''
        self.server.run_script(script)
        self.reset_all(nic)

    def get_sys_cfg_entry(self, nic: Nic):
        """Return directory entry number for SYS_CFG"""
        script = f'''
            cd {self.path}
            ./load.sh -eval "device {nic.bnxtmt_device}; nvm dir"
            exit
        '''
        lines = self.server.run_script(script)
        for line in lines:
            match = re.match(r'\s*(\d+)\s+SYS_CFG\s+', line)
            if match:
                return match.group(1)
        raise ValueError("Cannot find SYS_CFG directory entry")

    def unload_driver(self):
        self.server.exec("rmmod bnxtmtdrv", False)

    def unlock_grc(self, nic: Nic):
        """Unlock the PCIE BAR for write access."""
        script = f'''
            cd {self.path}
            ./load.sh -eval "device {nic.bnxtmt_device}; unlock grc"
            exit
        '''
        lines = self.server.run_script(script)
        for line in lines:
            if "GRCP already unlocked" in line or "unlocked GRCP" in line:
                return
        raise ValueError("Failed to unlock GRC registers.")

    def _sigterm_cleanup(self, signum, stack_frame):
        self.killall()
        self.unload_driver()
        sys.exit(1)

    def primate_trace(self, nic: Nic, tail: bool = False):
        signal.signal(signal.SIGTERM, self._sigterm_cleanup)
        self.killall()
        self.unload_driver()
        log.debug(f"Dumping primate trace for device {nic.bnxtmt_device}")
        if not tail:
            print("\n".join(self._get_primate_trace(nic)))
            return
        exp = self.server.get_expect_session()
        exp.sendline(f"cd {self.path}")
        exp.expect(self.server.prompt)
        exp.sendline(f"./load.sh")
        exp.delaybeforesend = None

        exp.expect_exact(prompt(1))
        slow_sendline(exp, f"device {nic.bnxtmt_device}")
        try:
            while True:
                exp.expect_exact(prompt(nic.bnxtmt_device))
                self._echo_trace(exp.before)
                slow_sendline(exp, f"primate trace")
        except Timeout:
            exp.close()
            log.critical("Timed out waiting on bnxtmt.")
            sys.exit(1)

    def _echo_trace(self, buffer: str):
        buffer = buffer.strip()
        if not buffer:
            return
        if self._last_buffer_hash is not None and self._last_buffer_hash == hash(buffer):
            # Buffer hasn't changed since last poll, nothing to do
            return
        self._last_buffer_hash = hash(buffer)
        buffer = buffer.splitlines()
        if not self._trace_buffer:
            self._trace_buffer = copy(buffer)
        else:
            new_trace_buffer = []
            for line in reversed(buffer):
                if line == self._trace_buffer[-1]:
                    break
                new_trace_buffer.insert(0, line)
            self._trace_buffer = new_trace_buffer
        for line in self._trace_buffer:
            match = re.match(r"\d+\.\d+:", line)
            if match:
                print(line)

    def _get_primate_trace(self, nic: Nic):
        script = f'''
            cd {self.path}
            ./load.sh -eval "device {nic.bnxtmt_device}; primate trace"
            exit
        '''
        lines = self.server.run_script(script)
        trace = False
        output = []
        for line in lines:
            if trace:
                output.append(line.strip())
            if "current trace index" in line:
                trace = True
            elif line.strip() == "":
                trace = False
        output.pop()
        return output
