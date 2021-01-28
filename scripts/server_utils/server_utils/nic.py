import logging
from typing import List

from server_utils.sit import pciid_to_pkg_file

log = logging.getLogger(__name__)


class Nic:
    def __init__(self, pci_bdf: str, interfaces: List[str], bnxtmt: 'Bnxtmt', inventory: 'Inventory'):
        self._pci_bdf = pci_bdf
        self._interfaces = interfaces
        self._bnxtmt = bnxtmt
        self._inventory = inventory
        self._bnxtmt_device = None
        self._vid = None
        self._did = None
        self._svid = None
        self._ssid = None
        self._package_filename = None

    @property
    def pci_bdf(self):
        return self._pci_bdf

    @property
    def interfaces(self):
        return self._interfaces

    @property
    def bnxtmt_device(self):
        """Return the bnxtmt device number for the NIC card. NIC PCI address is used to find device number."""
        if self._bnxtmt_device is None:
            self._bnxtmt_device = self._bnxtmt.get_device_num(self.pci_bdf)
        return self._bnxtmt_device

    @property
    def vid(self):
        """Return the Vendor ID"""
        if not self._vid:
            self._vid = self._inventory.get_pci_vid(self.pci_bdf)
        return self._vid

    @property
    def did(self):
        """Return the Device ID"""
        if not self._did:
            self._did = self._inventory.get_pci_did(self.pci_bdf)
        return self._did

    @property
    def svid(self):
        """Return the Subsystem Vendor ID"""
        if not self._svid:
            self._svid = self._inventory.get_pci_svid(self.pci_bdf)
        return self._svid

    @property
    def ssid(self):
        """Return the Subsystem ID"""
        if not self._ssid:
            self._ssid = self._inventory.get_pci_ssid(self.pci_bdf)
        return self._ssid

    @property
    def sit_package_filename(self):
        """Return the SIT package filename appropriate for this NIC"""
        if not self._package_filename:
            self._package_filename = pciid_to_pkg_file(self.vid, self.did, self.svid, self.ssid)
        return self._package_filename

