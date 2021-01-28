import logging
import os
import re
import shutil
import tempfile
from functools import cmp_to_key

import requests
import urllib3
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def list_sit_versions(url):
    page = requests.get(url, verify=False).text
    soup = BeautifulSoup(page, 'html.parser')
    return [node.get('href').strip('/') for node in soup.find_all('a') if re.match(rf'(\d+\.*)+\/', node.get('href'))]


def dir_listing(url):
    page = requests.get(url, verify=False).text
    soup = BeautifulSoup(page, 'html.parser')
    return [node.get('href').strip('/') for node in soup.find_all('a')]


def compare_sit_versions(ver_a, ver_b, num_fields=None):
    if not isinstance(ver_a, list):
        ver_a = ver_a.split('.')
    if not isinstance(ver_b, list):
        ver_b = ver_b.split('.')
    if len(ver_a) < len(ver_b):
        for _ in range(len(ver_b) - len(ver_a)):
            ver_a.append(0)
    elif len(ver_b) < len(ver_a):
        for _ in range(len(ver_a) - len(ver_b)):
            ver_b.append(0)
    if num_fields is None:
        num_fields = len(ver_a)
    for i in range(num_fields):
        if int(ver_a[i]) < int(ver_b[i]):
            return -1
        if int(ver_a[i]) > int(ver_b[i]):
            return 1
    return 0


def get_sit_version(url, requested_sit_version):
    top_sit_versions = sorted(list_sit_versions(url), key=cmp_to_key(compare_sit_versions), reverse=True)
    match_2 = ""
    match_3 = ""
    for sit_version in top_sit_versions:
        if compare_sit_versions(sit_version, requested_sit_version, 3) == 0:
            match_3 = sit_version
        if compare_sit_versions(sit_version, requested_sit_version, 2) == 0:
            match_2 = sit_version
    if match_3:
        url3 = f"{url}/{match_3}"
        sit_versions = sorted(list_sit_versions(url3), key=cmp_to_key(compare_sit_versions), reverse=True)
        for sit_version in sit_versions:
            if compare_sit_versions(requested_sit_version, sit_version) >= 0:
                return url3, sit_version
    if match_2:
        url2 = f"{url}/{match_2}"
        sit_versions = sorted(list_sit_versions(url2), key=cmp_to_key(compare_sit_versions), reverse=True)
        for sit_version in sit_versions:
            if compare_sit_versions(requested_sit_version, sit_version) >= 0:
                return url2, sit_version
    top_sit_versions = [version for version in top_sit_versions if len(version.split('.')) == 2 or (
            len(version.split('.')) == 3 and version.split('.')[2] == "0")]
    for sit_version in top_sit_versions:
        if compare_sit_versions(requested_sit_version, sit_version, 2) >= 0:
            url2 = f"{url}/{sit_version}"
            sit_versions = sorted(list_sit_versions(url2), key=cmp_to_key(compare_sit_versions), reverse=True)
            for sit_version in sit_versions:
                if compare_sit_versions(requested_sit_version, sit_version) >= 0:
                    return url2, sit_version
    raise ValueError(f"Cannot find SIT version for {requested_sit_version}")


def pciid_to_pkg_file(vid: str, did: str, svid: str, ssid: str) -> str:
    """
    Given a PCI Vendor ID, Device ID, Subsystem Vendor ID, and Subsystem ID, return the package filename
    appropriate for the hardware.

    :param vid: 4-digit hex string for Vendor ID
    :param did: 4-digit hex string for Device ID
    :param svid: 4-digit hex string for Subsystem Vendor ID
    :param ssic: 4-digit hex string for Subsystem ID
    :return: Package filename for the card
    """
    lookup_key = f"{vid}-{did}-{svid}-{ssid}"
    packages = {
        # dell
        "14e4-1751-14e4-5045": "LoN57504_4x25.pkg",
        "14e4-1751-14e4-5250": "FeM57504_4x25.pkg",
        "14e4-1751-1028-09d4": "BaL57504_4x25.pkg",
        "14e4-1750-14e4-5209": "BCM957508-N2100D.pkg",
        # lenovo
        "14e4-1750-17aa-404c": "BCM957508-P2100L.pkg",
        # smc
        "14e4-1750-15d9-1b3e": "AOC-S100G-b2C.pkg",
        "14e4-1750-15d9-1b81": "AOC-A100G-b2c.pkg",
        # brcm
        "14e4-1751-14e4-1100": "BCM957504-M1100G.pkg",
        "14e4-1751-14e4-5100": "BCM957504-N1100G.pkg",
        "14e4-1750-14e4-2100": "BCM957508-P2100G.pkg",
        "14e4-1750-14e4-2200": "BCM957508-P2200G.pkg",
        "14e4-1751-14e4-5046": "BCM957504-N250G.pkg",
        "14e4-1752-14e4-5410": "BCM957502-N410GBT.pkg",
        "14e4-1750-14e4-5208": "BCM957508-N2100G.pkg",
        "14e4-1751-14e4-5047": "BCM957504-N410G.pkg",
        "14e4-1752-14e4-1002": "BCM957502-P410GBT.pkg",
        "14e4-1751-14e4-4250": "BCM957504-P425G.pkg",
        "14e4-1751-14e4-5425": "BCM957504-N425G.pkg",
        "14e4-1752-14e4-1003": "BCM957502-P410G.pkg",
        "14e4-1751-14e4-5049": "BCM957504-P250G.pkg",
        "14e4-1752-14e4-5150": "BCM957502-N150G.pkg",
        "14e4-1751-14e4-1116": "BCM957504-M1100G16.pkg",
        # facebook
        "14e4-1751-14e4-5104": "BCM957504-N1100FS.pkg",
        "14e4-1751-14e4-5101": "BCM957504-N1100FX.pkg",
        "14e4-1751-14e4-5102": "BCM957504-N1100FY.pkg",
        "14e4-1751-14e4-5103": "BCM957504-N1100FZ.pkg",
        "14e4-1752-14e4-5151": "BCM957502-N150FY.pkg",
        "14e4-1752-14e4-5152": "BCM957502-N150FZ.pkg",
        "14e4-1752-14e4-5153": "BCM957502-N150FS.pkg",
        "14e4-1752-14e4-5154": "BCM957502-N150FG.pkg",
        "14e4-1752-14e4-1150": "BCM957502-M150G.pkg",
        "14e4-1751-14e4-1128": "BCM957504-M1100G8.pkg"
    }
    filename = packages.get(lookup_key)
    if filename is None:
        raise ValueError(f"Cannot find package file for PCI ID {lookup_key}.")
    return filename


class Sit:
    def __init__(self, server, version, url):
        self.server = server
        self.version = version
        self.url = url
        self._path = None
        self._tmp_dir = None

    def sit_exists(self):
        """Does SIT directory already exist on server"""
        lines = self.server.exec(f"find {self.server.home_dir} -maxdepth 1 -type d")
        for line in lines:
            dir_name = os.path.basename(line)
            if dir_name == self.version:
                return True
        return False

    def sit_install(self):
        """Download and make SIT on remote server."""
        self.server.exec(f"mkdir {self._path}")
        self._install_bnxtnvm()
        self._install_bnxtmt()
        self._install_driver()
        #self._install_pkg()
        #self._install_cfg()
        if not self.server.path_exists(self._path):
            raise IOError(f"Remote sit directory {self._path} does not exist.")

    def _download(self, file):
        filename = file.split('/')[-1]
        fd, local_filename = tempfile.mkstemp(filename)
        url = f"{self.url}/{file}"
        with requests.get(url, stream=True, verify=False) as r:
            with os.fdopen(fd, "wb") as f:
                shutil.copyfileobj(r.raw, f)
        return local_filename

    def _install_bnxtnvm(self):
        log.info("Retrieving bnxtnvm from SIT server.")
        local_path = self._download("bnxtnvm/Linux/Release/bnxtnvm")
        remote_path = os.path.join(self._path, "bnxtnvm")
        self.server.copy_to(local_path, remote_path)
        os.unlink(local_path)
        self.server.exec(f"chmod a+x {remote_path}")

    def _install_bnxtmt(self):
        log.info("Retrieving bnxtmt from SIT server.")
        bnxtmt_path = "bnxtmt/Linux/TH_A"
        kernel_parts = self.server.inventory.kernel.split('.')
        if len(kernel_parts) >= 2:
            kernel_version = float('.'.join(kernel_parts[0:2]))
        else:
            kernel_version = 0.0
        if kernel_version >= 4.06:
            file_suffix = "x86_64.k406.tar.gz"
        else:
            file_suffix = "x86_64.tar.gz"
        remote_path = None
        for file in dir_listing(f"{self.url}/{bnxtmt_path}"):
            if file.startswith("bnxtmt") and file.endswith(file_suffix):
                bnxtmt_path += "/" + file
                remote_path = os.path.join(self._path, file)
                remote_bnxtmt = file
        if remote_path is None:
            log.warning("Cannot find bnxtmt, skipping installation.")
            return
        local_path = self._download(bnxtmt_path)
        self.server.copy_to(local_path, remote_path)
        os.unlink(local_path)
        log.info("Building bnxtmt.")
        self.server.run_script(f"""
            cd {self._path}
            tar -xzvf {remote_bnxtmt}
            rm -f {remote_bnxtmt}
            cd bnxtmt*
            make
            exit
        """)

    def _install_driver(self):
        log.info("Retrieving driver from SIT server.")
        driver_path = "Linux_Driver"
        for file in dir_listing(f"{self.url}/{driver_path}"):
            if file.startswith("bnxt_en") and file.endswith(".tar.gz"):
                driver_path += "/" + file
                remote_path = os.path.join(self._path, file)
                remote_driver = file
        local_path = self._download(driver_path)
        self.server.copy_to(local_path, remote_path)
        os.unlink(local_path)
        log.info("Building driver.")
        gcc_version_parts = self.server.inventory.get_package_version("gcc").split('.')
        if len(gcc_version_parts) > 0:
            if ":" in gcc_version_parts[0]:
                gcc_version = float(gcc_version_parts[0].split(":")[1])
            else:
                gcc_version = float(gcc_version_parts[0])
        else:
            gcc_version = 0
        if gcc_version >= 7:
            # GCC version 7 introduced a new error.  Need to disable it.
            extra_cflags = "EXTRA_CFLAGS=\"-Wno-error=implicit-fallthrough\""
        else:
            extra_cflags = ""
        self.server.run_script(f"""
            cd {self._path}
            tar -xzvf {remote_driver}
            rm -f {remote_driver}
            cd bnxt_en*
            make {extra_cflags}
            exit
        """)

    def _install_pkg(self, pkg_file_name=None):
        if pkg_file_name is not None:
            log.info(f"Retrieving THOR package {pkg_file_name} from SIT server.")
        else:
            log.info("Retrieving all THOR packages from SIT server.")
        brd_pkg_files = dir_listing(f"{self.url}/Board_Pkg_files")
        if "THOR_B0" in brd_pkg_files:
            # 218.1.44.0 and earlier use this path
            pkg_path = "Board_Pkg_files/THOR_B0/Signed/ABPROD-SRT"
        elif "THOR" in brd_pkg_files:
            # 218.1.45.0 and later use this path
            pkg_path = "Board_Pkg_files/THOR/Signed/ABPROD-SRT"
        else:
            pkg_path = "Board_Pkg_files"
        #else:
        #    raise FileNotFoundError("Cannot find SIT THOR package directory.")
        self.server.exec(f"mkdir -p {self._path}/pkg")
        files_to_copy = []
        pkg_paths = [
            pkg_path,
            f"{pkg_path}/Dell",
            f"{pkg_path}/Facebook",
            f"{pkg_path}/Lenovo",
            f"{pkg_path}/Smc"
        ]
        for pkg_path in pkg_paths:
            for file in dir_listing(f"{self.url}/{pkg_path}"):
                if file.endswith(".pkg"):
                    pkg = pkg_path + "/" + file
                    remote_path = os.path.join(self._path, "pkg", file)
                    local_path = self._download(pkg)
                    if pkg_file_name is None:
                        files_to_copy.append((local_path, remote_path))
                    elif file.startswith(pkg_file_name):
                        files_to_copy.append((local_path, remote_path))
                        break
            if pkg_file_name and files_to_copy:
                break
        if pkg_file_name and not files_to_copy:
            raise FileNotFoundError(f"Cannot file SIT package for {pkg_file_name}.")
        for local_path, remote_path in files_to_copy:
            self.server.copy_to(local_path, remote_path)
            os.unlink(local_path)

    def _install_cfg(self):
        log.info("Retrieving THOR configs from SIT server.")
        cfg_path = "Board_Pkg_files/NVRAM_Config/thor"
        self.server.exec(f"mkdir {self._path}/cfg")
        for file in dir_listing(f"{self.url}/{cfg_path}"):
            if file.lower().endswith(".cfg"):
                cfg = cfg_path + "/" + file
                remote_path = os.path.join(self._path, "cfg", file)
                local_path = self._download(cfg)
                self.server.copy_to(local_path, remote_path)
                os.unlink(local_path)

    def find_pkg(self, pkg_file_name):
        if not pkg_file_name.endswith(".pkg"):
            pkg_file_name += ".pkg"
        """Find a package in the downloaded SIT for the board given the part number."""
        lines = self.server.exec(f"find {self.path} -iname {pkg_file_name}")
        if lines:
            return os.path.join(self.server.home_dir, lines[0])
        # Did not find pkg on server, attempt to download from SIT
        self._install_pkg(pkg_file_name)
        lines = self.server.exec(f"find {self.path} -iname {pkg_file_name}")
        if lines:
            return os.path.join(self.server.home_dir, lines[0])
        raise FileNotFoundError(f"Cannot find package {pkg_file_name} on server {self.server.name}")

    @property
    def path(self):
        if self._path is None:
            self._path = os.path.join(self.server.home_dir, self.version)
            if not self.sit_exists():
                self.sit_install()
        return self._path
