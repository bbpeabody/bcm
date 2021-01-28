import logging
import re
from pprint import pformat

from abc import ABC, abstractmethod
from typing import Dict, List, Union

log = logging.getLogger(__name__)


class Inventory(ABC):
    """
    Gathers software, hardware, and interface specifics for a machine.

    This base class should only be inherited by an OS specific class.
    """

    def __init__(self, server):
        """
        :param cli: Callable cli for executing commands and receiving command output.  See process_handler.run()
            for an example.
        """
        self._cli = server.exec
        self.server = server

        self.log = log

        # Used for caching static data
        self._cpu = None
        self._cmdline = None
        self._distribution = None
        self._drivers = None
        self._env = None
        self._ethernet_interfaces = None
        self._hostname = None
        self._interfaces = None
        self._kernel = None
        self._memory = None
        self._mounts = None
        self._nic = None
        self._packages = None
        self._swap = None
        self._pci_configuration_header = {}

    def all_properties(self):
        """
        Pretty print all inventory properties. When a new property is added to the class, add it to the props list.

        :return: Multi-line pretty printed dictionary
        """
        inventory = dict()
        props = [
            'cmdline',
            'cpu',
            'distribution',
            'drivers',
            'env',
            'ethernet_interfaces',
            'hostname',
            'hostname_short',
            'interfaces',
            'kernel',
            'memory',
            'mounts',
            'nic',
            'os',
            'packages',
        ]
        for prop_name in props:
            prop = getattr(self, prop_name)
            inventory[prop_name] = prop
        # Add some additional detail for ethernet interfaces
        for ethernet_interface in self.ethernet_interfaces:
            d = dict(
                nic=self.get_ethernet_nic(ethernet_interface),
                supported_speeds=self.get_ethernet_supported_speeds(ethernet_interface)
                )
            inventory[f"ethernet_interface_{ethernet_interface}"] = d
        return pformat(inventory)

    def clear_cache(self):
        """
        Inventory data is only collected once and cached. Call this method to clear cache and force a re-read of
        inventory data the next time any property is accessed.
        """
        self._cpu = None
        self._cmdline = None
        self._distribution = None
        self._drivers = None
        self._env = None
        self._ethernet_interfaces = None
        self._hostname = None
        self._interfaces = None
        self._kernel = None
        self._memory = None
        self._mounts = None
        self._nic = None
        self._packages = None
        self._swap = None

    def cli(self, command: str, check: bool = False, **kwargs) -> str:
        """
        Wrap cli command, so default arguments can be set.

        :param command: Command to execute on local or remote cli
        :param check: If true, raise exception on non-zero exit status
        """
        return "\n".join(self._cli(command, check=check, **kwargs))

    @property
    @abstractmethod
    def cmdline(self) -> Dict[str, Union[str, bool]]:
        """Returns the boot cmdline as a dict"""
        pass

    @property
    @abstractmethod
    def cpu(self) -> Dict[str, Union[str, float, int]]:
        """
        Returns cpu info as a Dict

        :return: Dict - Example: {'architecture': 'x86_64',
                                  'bogomips': '7000.00',
                                  'byte_order': 'Little Endian',
                                  'cores_per_socket': 8,
                                  'cpu_family': 6,
                                  'cpu_max_mhz': '4200.0000',
                                  'cpu_mhz': '1393.676',
                                  'cpu_min_mhz': '1200.0000',
                                  'cpu_op_modes': '32-bit, 64-bit',
                                  'cpus': 8,
                                  'flags': 'fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca '
                                           'cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm '
                                           'pbe syscall nx pdpe1gb rdtscp lm constant_tsc art '
                                           'arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc '
                                           'aperfmperf eagerfpu pni pclmulqdq dtes64 monitor ds_cpl vmx '
                                           'smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid dca sse4_1 '
                                           'sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx '
                                           'f16c rdrand lahf_lm abm 3dnowprefetch epb cat_l3 cdp_l3 '
                                           'invpcid_single intel_ppin intel_pt ssbd mba ibrs ibpb stibp '
                                           'tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust '
                                           'bmi1 hle avx2 smep bmi2 erms invpcid rtm cqm mpx rdt_a '
                                           'avx512f avx512dq rdseed adx smap clflushopt clwb avx512cd '
                                           'avx512bw avx512vl xsaveopt xsavec xgetbv1 cqm_llc '
                                           'cqm_occup_llc cqm_mbm_total cqm_mbm_local dtherm ida arat '
                                           'pln pts pku ospke md_clear spec_ctrl intel_stibp flush_l1d',
                                  'l1d_cache': '32K',
                                  'l1i_cache': '32K',
                                  'l2_cache': '1024K',
                                  'l3_cache': '25344K',
                                  'model': 85,
                                  'model_name': 'Intel(R) Xeon(R) Gold 6144 CPU @ 3.50GHz',
                                  'numa_node0_cpus': '0-7',
                                  'numa_nodes': 1,
                                  'on_line_cpus_list': '0-7',
                                  'sockets': 1,
                                  'stepping': 4,
                                  'threads_per_core': 1,
                                  'vendor_id': 'GenuineIntel',
                                  'virtualization': 'VT-x'},
        """
        pass

    @property
    @abstractmethod
    def distribution(self) -> Dict[str, str]:
        """
        Returns dict with distribution details

        :return: Dictionary with keys: name, major_version, release, version
        """
        pass

    @property
    def distribution_desc(self) -> str:
        """Returns long description of distribution - name + version + release"""
        return self.distribution.get("long_name", "")

    @property
    @abstractmethod
    def drivers(self) -> Dict[str, str]:
        """
        Queries system for set of drivers.  Returns dict with driver name -> version.
        Getting a list of installed drivers is an OS specific task.
        """
        pass

    def get_driver_version(self, name: str) -> str:
        """
        Returns the version of a driver

        :return: Empty string if not installed, "0.0" if driver has no version, otherwise version of driver
        """
        return self.drivers.get(name, "")

    def is_driver_installed(self, name: str, min_ver: str = "0.0") -> bool:
        """
        Returns True if the driver is installed and version is >= min_ver

        :param name: Name of the driver
        :param min_ver: Minimum version number
        :return: True if driver is installed and version >= min_ver.
        """
        version = self.get_driver_version(name)
        if not version:
            return False
        if self._cmp_ver(version, min_ver) >= 0:
            return True
        return False

    @property
    @abstractmethod
    def env(self) -> Dict[str, str]:
        """Returns a dict of all environment variables"""
        pass

    @property
    def ethernet_interfaces(self) -> List[str]:
        """
        Returns list of physical Ethernet interfaces
        """
        if not self._ethernet_interfaces:
            eth_list = list()
            for interface in self.interfaces.keys():
                if self.get_interface_type(interface) != "ether":
                    continue
                if interface.startswith('v'):
                    continue
                eth_list.append(interface)
            self._ethernet_interfaces = eth_list
        return self._ethernet_interfaces

    def get_ethernet_nic(self, interface: str) -> str:
        """
        Return description of the NIC card that provides the Ethernet interface.

        :param interface: Name of the Ethernet interface.
        :return: Returns description of the NIC card.  Returns empty string if interface is not ethernet.
        """
        if self.get_interface_type(interface) != "ether":
            return ""
        pciid = self.get_interface_pciid(interface)
        return f"{pciid}: {self.get_nic_desc(pciid)}"

    @abstractmethod
    def get_ethernet_supported_speeds(self, interface: str) -> List[str]:
        """
        Returns list of supported speeds for Ethernet interface. Returns empty list if ethtool is not installed or
        interface is not Ethernet
        """
        pass

    @property
    @abstractmethod
    def hostname(self) -> str:
        """Return FQDN if it exists, else return short hostname"""
        pass

    @property
    def hostname_short(self) -> str:
        return self.hostname.split('.')[0]

    @property
    @abstractmethod
    def interfaces(self) -> Dict[str, Dict[str, str]]:
        """Returns dict of interfaces with interface settings. If a setting is not set, empty string will be returned.

        :return: {interface1: {broadcast: ipv4_broadcast_address
                               device:  interface_name,
                               ip4_addr: ipv4_address
                               ip4_cidr: ipv4_cidr
                               ip4_scope: ipv4_scope,
                               ip6_addr: ipv6_addr
                               ip6_cidr: ipv6_cidr
                               ip6_scope: ipv6_scope
                               mac: mac_address,
                               path: device_ path,
                               type: device_type},
                  interface2: {...},
                 }
                 Example return:
                {'em4': {'broadcast': '10.27.215.255',
                         'device': 'em4',
                         'ip4_addr': '10.27.215.99',
                         'ip4_cidr': '24',
                         'ip4_scope': 'global',
                         'ip6_addr': 'fe80::b226:28ff:fe16:77d5',
                         'ip6_cidr': '64',
                         'ip6_scope': 'link',
                         'mac': 'b0:26:28:16:77:d5',
                         'path': '/sys/devices/pci0000:00/0000:00:1c.0/0000:01:00.1/net/em4',
                         'type': 'ether'},
                 'lo': {'broadcast': '',
                        'device': 'lo',
                        'ip4_addr': '',
                        'ip4_cidr': '',
                        'ip4_scope': '',
                        'ip6_addr': '::1',
                        'ip6_cidr': '128',
                        'ip6_scope': 'host',
                        'mac': '00:00:00:00:00:00',
                        'path': '/sys/devices/virtual/net/lo',
                        'type': 'loopback'},
                }
        """
        pass

    def get_interface_ip(self, interface: str, version: int = 4) -> str:
        """
        Returns ipv4 or ipv6 address

        :param interface: Name of network interface
        :param version: Either 4 or 6 for ipv4 or ipv6
        """
        int_dict = self.interfaces.get(interface, dict())
        return int_dict.get(f"ip{version}_addr", "")

    def get_interface_mac(self, interface: str) -> str:
        """
        Return mac address

        :param interface: Name of network interface
        """
        int_dict = self.interfaces.get(interface, dict())
        return int_dict.get("mac", "")

    def get_interface_pciid(self, interface: str) -> str:
        """
        Return interface PCI ID

        :param interface: Name of the network interface
        """
        dev_path_parts = self.interfaces.get(interface, dict()).get("path", "").split('/')
        for part in reversed(dev_path_parts):
            match = re.search(r'[a-f0-9]{4}:[a-f0-9]{2}:[a-f0-9]{2}\.[a-f0-9]', part)
            if match:
                return match.group()
        return ""

    def get_interface_type(self, interface: str) -> str:
        """
        Return interface type

        :param interface: Name of network interface
        """
        return self.interfaces.get(interface, dict()).get("type", "")

    @property
    @abstractmethod
    def kernel(self) -> str:
        """Returns the kernel version"""
        pass

    @property
    @abstractmethod
    def memory(self) -> Dict[str, int]:
        """Returns memory in MB - mem_total, mem_free, mem_available, swap_total, swap_free"""
        pass

    @property
    @abstractmethod
    def mounts(self) -> Dict[str, Dict[str, Union[str, int]]]:
        """
        Returns dictionary with key = mountpoint.

        :return: {mountpoint1: {available: Available space on mount in bytes: int,
                                device: Device name: str,
                                mountpoint: mountpoint: str,
                                percent_used: Used space on mount as percent: int,
                                total: Total space on mount in bytes: int,
                                used: Used space on mount in bytes: int},
                  mountpoint2: {...},
                 }
                Example return:
                {'/boot': {'available': 741359616,
                           'device': 'sda2',
                           'mountpoint': '/boot',
                           'percent_used': 23,
                           'total': 1023303680,
                           'used': 211480576},
                 '/boot/efi': {'available': 197926912,
                               'device': 'sda1',
                               'mountpoint': '/boot/efi',
                               'percent_used': 6,
                               'total': 209489920,
                }              'used': 11563008},
        """
        pass

    @property
    @abstractmethod
    def nic(self) -> Dict[str, Dict[str, str]]:
        """
        Returns dictionary with NIC parameter.
        OS specific
        """
        pass

    def get_nic_desc(self, pciid: str) -> str:
        """
        Return the description for NIC card given the PCI ID

        :param pciid: Example: 0000:65:00
        """
        desc = ""
        pciid = pciid.lower()
        match = re.search(r'^[a-f0-9]{4}:[a-f0-9]{2}:[a-f09]{2}', pciid)
        if match:
            pciid = match.group()
            nic = self.nic.get(pciid)
            prod_name = nic.get('product_name')
            subsystem = nic.get('subsystem')
            device_desc = nic.get('device_desc')
            if prod_name:
                desc = prod_name
            elif subsystem:
                desc = subsystem
            elif device_desc:
                desc = device_desc
            desc += f" {nic.get('part_number', '')}"
            link_speed = nic.get('link_status_speed')
            link_width = nic.get('link_status_width')
            if link_speed and link_width:
                desc += f" {link_speed} x {link_width}"
        return desc

    @property
    @abstractmethod
    def os(self):
        pass

    @property
    @abstractmethod
    def packages(self) -> Dict[str, str]:
        """Queries system for set of packages.  Returns dict with package name -> version."""
        pass

    def get_package_version(self, package) -> str:
        return self.packages.get(package, "")

    def is_package_installed(self, name: str, min_ver: str = "0.0") -> bool:
        """
        Returns True if the package is installed and version is >= min_ver

        :param name: Name of the package
        :param min_ver: Minimum version number
        :return: True if package is installed and version >= min_ver.
        """
        version = self.get_package_version(name)
        if version:
            if self._cmp_ver(version, min_ver) >= 0:
                return True
        return False

    @abstractmethod
    def get_pci_configuration_header(self, pci_bdf: str) -> List[int]:
        """
        Returns the PCI Configuration Space Header given a PCI BDF(Bus, Device, Function) address.

        :param pci_bdf: PCI Bus, Device, Function in the format BB:DD.F or optionally prefaced with the Domain.
        i. e. 0000:63:00.0 or 63:00.0
        :return: List of 64 8-bit integers
        """
        pass

    def get_pci_vid(self, pci_bdf: str) -> str:
        """Returns PCI Vendor ID in hex given a PCI BDF."""
        hdr = self.get_pci_configuration_header(pci_bdf)
        return f"{(hdr[1] << 8) + hdr[0]:04x}"

    def get_pci_did(self, pci_bdf: str) -> str:
        """Returns PCI Device ID in hex given a PCI BDF."""
        hdr = self.get_pci_configuration_header(pci_bdf)
        return f"{(hdr[3] << 8) + hdr[2]:04x}"

    def get_pci_svid(self, pci_bdf: str) -> str:
        """Returns PCI Subsystem ID in hex given a PCI BDF."""
        hdr = self.get_pci_configuration_header(pci_bdf)
        return f"{(hdr[45] << 8) + hdr[44]:04x}"

    def get_pci_ssid(self, pci_bdf: str) -> str:
        """Returns PCI Subsystem Vendor ID in hex given a PCI BDF."""
        hdr = self.get_pci_configuration_header(pci_bdf)
        return f"{(hdr[47] << 8) + hdr[46]:04x}"

    @staticmethod
    def _cmp_ver(ver_a: str, ver_b: str) -> int:
        """
        Compare two version strings in digits with dots format.
        If ver_a is greater than ver_b, returns 1
        If ver_a is equal to ver_b, returns 0
        if ver_a is less than ver_b, returns -1
        Example: ver_a = 3.4.1, ver_b = 3.4.2.3, returns -1
        """
        vers = [ver_a, ver_b]
        for i, ver in enumerate(vers):
            if '.' in ver:
                match = re.search(r'(\d+\.)+\d+', ver)
                if match:
                    vers[i] = match.group()
                else:
                    raise ValueError(f"Cannot extract decimal dotted version from '{ver}'")
        a = vers[0].split('.')
        b = vers[1].split('.')
        len_a = len(a)
        len_b = len(b)
        length = len_a
        if len_a > len_b:
            # Pad b with zeros
            for i in range(len_b, len_a):
                b.append('0')
        elif len_b > len_a:
            # Pad a with zeros
            for i in range(len_a, len_b):
                a.append('0')
            length = len_b
        for i in range(length):
            da = int(a[i])
            db = int(b[i])
            if da > db:
                return 1
            elif da < db:
                return -1
        return 0

    @staticmethod
    def _parse(regexs: Dict, lines: List[str]) -> Dict[str, str]:
        """
        Iterate over lines and match to regexs

        :param regexs: Dictionary - Key = Tuple[fields: str] or single field string
                                    Value = Regex with matching groups.  Number of matched groups must match number
                                    of fields in Tuple or be 1 for single string.
        :return: Dictionary with parsed Field:Value
        """
        # Initialize dict with all empty strings
        d = dict()
        for fields in regexs.keys():
            if isinstance(fields, tuple):
                for field in fields:
                    d[field] = ''
            else:
                d[fields] = ''
        # Search for fields in list of lines
        for line in lines:
            for fields, regex in regexs.items():
                match = re.search(regex, line)
                if match:
                    if isinstance(fields, tuple):
                        group = 1
                        for field in fields:
                            while field in d and d[field]:
                                # Field already exists
                                match1 = re.search(r'(.*)_(\d+)$', field)
                                if match1:
                                    field = f"{match1.group(1)}_{int(match1.group(2)) + 1}"
                                else:
                                    field = f"{field}_1"
                            d[field] = match.group(group)
                            group += 1
                    else:
                        while fields in d and d[fields]:
                            # Field already exists
                            match1 = re.search(r'(.*)_(\d+)$', fields)
                            if match1:
                                fields = f"{match1.group(1)}_{int(match1.group(2)) + 1}"
                            else:
                                fields = f"{fields}_1"
                        d[fields] = match.group(1)
        return d

    def __str__(self):
        """
        Override __str__ method with a pretty print of an abbreviated inventory

        :return: single line short inventory description
            hostname: distribution, # vcpus, mem in GB, / root mount available %, /home home mount available %
            Example: h173: CentOS 7.3 Core, 14 vcpus, mem 62.6 GB, / 9%
        """
        out = ""
        out += f"{self.hostname_short}: "
        out += f"{self.distribution_desc}"
        out += f", {self.cpu.get('cpus')} cpus"
        out += f", mem {self.memory.get('mem_total')/1024:.1f} GB"
        for mountpoint, d in self.mounts.items():
            if mountpoint == '/' or mountpoint == '/home':
                out += f", {mountpoint} {d.get('percent_used')}%"
        return out


#def get_platform(cli: Callable = None) -> str:
#    """
#    Determines if cli is Windows, linux, or esxi
#
#    :param cli: Callable cli for executing commands and receiving command output.  See process_handler.run()
#        for an example.
#    :return: "linux", "windows", "exsi", or None
#    """
#    cli = cli if cli else process_handler.run
#
#    # Try linux first
#    cmd = 'uname -s'
#    try:
#        output = cli(command=cmd, check=False)
#        if "linux" in output.lower():
#            return "linux"
#    except (AuthenticationException, NoValidConnectionsError, socket_timeout) as error:
#        log.debug(f'Not a linux system. Received exception: {error} in {__name__} when executing {cmd}')
#
#    # Try Windows
#    # TODO: Implement windows cli check
#
#    # Try ESXI
#    # TODO: Implement ESXI cli check
#
#    # Fall thru
#    log.warning('Unable to determine OS')
#    return ""


def create_inventory(platform: str, **kwargs) -> Inventory:
    if platform == "linux":
        from .linux_inventory import LinuxInventory
        return LinuxInventory(**kwargs)
    elif platform == "windows":
        raise NotImplementedError(f'{__name__} for {platform} is not implemented')
    elif platform == "esxi":
        raise NotImplementedError(f'{__name__} for {platform} is not implemented')


#if __name__ == "__main__":
#    import argparse
#    import sys
#    from aucommon.helpers.remote_mgmt.ssh import SSHSession
#    parser = argparse.ArgumentParser(description="Retrieve inventory from system.")
#    parser.add_argument('-i', '--ip_addr', type=str, help="IP address", default=None)
#    parser.add_argument('-u', '--user', type=str, help="Username", default="root")
#    parser.add_argument('-p', '--password', type=str, help="Password", default="root")
#    parser.add_argument('-f', '--file', type=str, help="File with space delimited list of: IP User Password",
#                        default=None)
#    args = parser.parse_args()
#    if args.ip_addr:
#        systems = [(args.ip_addr, args.user, args.password)]
#    elif args.file:
#        systems = []
#        with open(args.file, 'r') as f:
#            for line in f:
#                params = line.split()
#                if len(params) == 3:
#                    systems.append(params)
#    else:
#        sys.exit("Error: At a minimum, you need option --ip_addr or --file.")
#    h = logging.StreamHandler()
#    h.setLevel(logging.DEBUG)
#    log.setLevel(logging.INFO)
#    log.addHandler(h)
#    for system in systems:
#        print("IP: {} USER: {} PASSWORD: {}".format(*system))
#        ssh = SSHSession(address=system[0], username=system[1], password=system[2])
#        if get_platform(ssh.exec_command) != "linux":
#            print("Skipping non-linux system")
#            continue
#        inv = create_inventory('linux', cli=ssh.exec_command)
#        print(inv.all_properties())
#        print(inv)
