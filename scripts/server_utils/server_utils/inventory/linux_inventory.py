import logging
import re
from typing import Dict, List, Tuple, Union

from server_utils.ethtool import Ethtool
from server_utils.inventory.inventory import Inventory

log = logging.getLogger(__name__)


class LinuxInventory(Inventory):

    @property
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
        if not self._cpu:
            # Parse the command 'lscpu' and return dict
            cmd = 'lscpu'
            output = self.cli(cmd).splitlines()
            cpu_dict = dict(
                architecture='',
                bogomips=0.0,
                byte_order='',
                cores_per_socket=0,
                cpu_family=0,
                cpu_max_mhz=0.0,
                cpu_mhz=0.0,
                cpu_min_mhz=0.0,
                cpu_op_modes='',
                cpus=0,
                flags='',
                l1d_cache='',
                l1i_cache='',
                l2_cache='',
                l3_cache='',
                model=0,
                model_name='',
                numa_node0_cpus='',
                numa_nodes=0,
                on_line_cpus_list='',
                sockets=0,
                stepping=0,
                threads_per_core=0,
                vendor_id='',
                virtualization=''
            )
            for line in output:
                match = re.search(r'^([^:]+):\s*(.*)$', line)
                if match:
                    key, value = match.group(1), match.group(2)
                    key = key.lower().replace('(', '').replace(')', '').replace(' ', '_').replace('-', '_')
                    if key not in cpu_dict:
                        continue
                    if value.isnumeric():
                        value = float(value)
                        if value.is_integer():
                            cpu_dict[key] = int(value)
                        else:
                            cpu_dict[key] = value
                    else:
                        cpu_dict[key] = value
            self._cpu = cpu_dict
        return self._cpu

    @property
    def cmdline(self) -> Dict[str, str]:
        """
        Returns the boot cmdline as a dict
        """
        if not self._cmdline:
            cmdline_dict = dict()
            # Get the output of cat /proc/cmdline
            cmd = 'cat /proc/cmdline'
            parts = self.cli(cmd).strip().split(' ')
            for part in parts:
                key_val = part.split('=', 1)
                if len(key_val) == 2:
                    key, val = key_val
                else:
                    key = key_val[0]
                    val = True
                cmdline_dict[key] = val
            self._cmdline = cmdline_dict
        return self._cmdline

    @property
    def distribution(self) -> Dict[str, str]:
        """
        Returns dict with distribution details

        :return: Dictionary with keys: long_name, name, version
        """
        if not self._distribution:
            dist_dict = {}
            cmd = "cat /etc/*-release"
            output = self.cli(cmd, shell=True).splitlines()
            name = ""
            ver = ""
            long_name = ""
            combined_name = ""
            for line in output:
                match = re.search(r'^(NAME|DISTRIB_ID|ID)=(.*)$', line)
                if match:
                    new_name = match.group(2).replace('"', '')
                    if len(new_name) > len(name):
                        name = new_name
                        combined_name = f"{name} {ver}"
                match = re.search(r'^(VERSION|DISTRIB_RELEASE|VERSION_ID)=(.*)$', line)
                if match:
                    new_ver = match.group(2).replace('"', '')
                    if len(new_ver) > len(ver):
                        ver = new_ver
                        combined_name = f"{name} {ver}"
                match = re.search(r'^(DISTRIB_DESCRIPTION|PRETTY_NAME)=(.*)$', line)
                if match:
                    new_long_name = match.group(2).replace('"', '')
                    if len(new_long_name) > len(long_name):
                        long_name = new_long_name
                match = re.search(r'^(centos|redhat|ubuntu|debian).*', line, re.IGNORECASE)
                if match:
                    new_long_name = match.group(0).replace('"', '')
                    if len(new_long_name) > len(long_name):
                        long_name = new_long_name
            if len(long_name) > len(combined_name):
                dist_dict["long_name"] = long_name
            else:
                dist_dict["long_name"] = combined_name
            dist_dict["name"] = name
            dist_dict["version"] = ver
            self._distribution = dist_dict
        return self._distribution

    @property
    def env(self) -> Dict[str, str]:
        """Returns a dict of all environment variables. {Environment Variable Name: Value}"""
        if not self._env:
            # Parse the command 'env' and return dictionary of environment variables
            cmd = "env"
            output = self.cli(cmd).splitlines()
            env_dict = dict()
            for line in output:
                match = re.search(r'^(\w+)=(.*)$', line)
                if match:
                    key = match.group(1)
                    val = match.group(2)
                    env_dict[key] = val
            self._env = env_dict
        return self._env

    def get_ethernet_supported_speeds(self, interface: str) -> List[Tuple[str, str]]:
        """
        Returns list of supported speeds for Ethernet interface. Returns empty list if ethtool is not installed or
        interface is not Ethernet

        :param interface: Name of network interface
        :return: list of tuples (speed, duplex)
        """
        if self.get_interface_type(interface) != "ether" or not self.is_package_installed('ethtool', '3.0'):
            return list()
        ethtool = Ethtool(self.server)
        return ethtool.supported_speeds(interface)

    @property
    def drivers(self) -> Dict[str, str]:
        """
        Return dict of driver name: version
        """
        # First, check if the driver is cached
        if not self._drivers:
            self._drivers = dict()
            cmd = "for mod in `lsmod | sed -n '1!p' | cut -f1 -d ' '`; do echo $mod `modinfo -F version $mod`; done;"
            output = self.cli(cmd).splitlines()
            for line in output:
                info = line.split(" ")
                if len(info) == 1:
                    driver = info[0]
                    version = "0.0"
                elif len(info) == 2:
                    driver = info[0]
                    version = info[1]
                else:
                    continue
                self._drivers[driver] = version
        return self._drivers

    @property
    def hostname(self) -> str:
        """Return FQDN if it exists, else return short hostname"""
        if not self._hostname:
            # Parse the command 'hostname -f'
            cmd = 'hostname -f'
            output = self.cli(cmd).strip()
            self._hostname = output
        return self._hostname

    @property
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
        if not self._interfaces:
            cmd = 'ls -la /sys/class/net/'
            output = self.cli(cmd).splitlines()
            interface_dict = dict()
            for line in output:
                match = re.search(r'\s(\S+)\s+->\s+(.*)$', line)
                if match:
                    device, path = match.group(1), match.group(2)
                    d = dict(
                        broadcast='',
                        device=device,
                        ip4_addr='',
                        ip4_cidr='',
                        ip4_scope='',
                        ip6_addr='',
                        ip6_cidr='',
                        ip6_scope='',
                        mac='',
                        path=path.replace('../../', '/sys/'),
                        type='',
                        )
                    interface_dict[device] = d
            cmd = 'ip addr show'
            output = self.cli(cmd).strip().splitlines()
            ipaddr_output = list()
            for line in output:
                match = re.search(r'^\d+:\s+([^:]+)', line)
                if match:
                    self._ip_parse(ipaddr_output, interface_dict)
                    ipaddr_output = list()
                ipaddr_output.append(line)
            self._ip_parse(ipaddr_output, interface_dict)
            self._interfaces = interface_dict
        return self._interfaces

    @property
    def kernel(self) -> str:
        """Returns the kernel version"""
        if not self._kernel:
            # Get the output of 'uname -r'
            cmd = 'uname -r'
            output = self.cli(cmd)
            self._kernel = output.strip()
        return self._kernel

    @property
    def memory(self) -> Dict[str, int]:
        """Returns memory in MB - mem_total, mem_free, mem_available, swap_total, swap_free"""
        if not self._memory:
            # Parse the command 'cat /proc/meminfo' and return dict
            cmd = 'cat /proc/meminfo'
            output = self.cli(cmd).splitlines()
            regexs = {
                'mem_total': r'^MemTotal:\s*(\d+)\s*kB$',
                'mem_free': r'^MemFree:\s*(\d+)\s*kB$',
                'mem_available': r'^MemAvailable:\s*(\d+)\s*kB$',
                'swap_total': r'^SwapTotal:\s*(\d+)\s*kB$',
                'swap_free': r'^SwapFree:\s*(\d+)\s*kB$',
            }
            d = self._parse(regexs, output)
            # Convert all memory values to integers and convert to MB
            d = {key: round(int(value)/1024) for (key, value) in d.items()}
            self._memory = d
        return self._memory

    @property
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
        if not self._mounts:
            mount_dict = dict()
            cmd = "lsblk -o KNAME,TYPE,MOUNTPOINT"
            output = self.cli(cmd).strip().splitlines()
            for line in output:
                match = re.search(r'^(\S+)\s+(\S+)\s+(.*)$', line)
                if match:
                    dev, dev_type, mountpoint = match.group(1), match.group(2), match.group(3)
                    if dev_type == 'part' and mountpoint and 'swap' not in mountpoint.lower():
                        mount_dict[mountpoint] = dict(
                            available=0,
                            device=dev,
                            mountpoint=mountpoint,
                            percent_used=0,
                            total=0,
                            used=0,
                        )
            cmd = "df"
            output = self.cli(cmd).strip().splitlines()
            for line in output:
                match = re.search(r'^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%\s+(.*)$', line)
                if match:
                    filesystem = match.group(1)
                    total = int(match.group(2))*1024
                    used = int(match.group(3))*1024
                    available = int(match.group(4))*1024
                    percent = int(match.group(5))
                    mountpoint = match.group(6)
                    for mount in mount_dict.values():
                        if mount['device'] in filesystem and mount['mountpoint'] == mountpoint:
                            mount['total'] = total
                            mount['used'] = used
                            mount['available'] = available
                            mount['percent_used'] = percent
            self._mounts = mount_dict
        return self._mounts

    @property
    def nic(self) -> Dict[str, Dict[str, str]]:
        """
        Returns list of dicts with NIC parameters

        :return: Dict with key=PCI ID of NIC - Example:
            {'0000:65:00': {'device_desc': 'Ethernet controller',
                            'device_type': '0',
                            'firmware_ver': '216.1.217.0',
                            'kernel_driver': 'bnxt_en',
                            'kernel_modules': 'bnxt_en',
                            'link_capability_speed': '16GT/s',
                            'link_capability_width': '16',
                            'link_status_speed': '8GT/s',
                            'link_status_width': '16',
                            'part_number': 'BCM957508-P2100G',
                            'pciid': '0000:65:00',
                            'product_name': 'Broadcom NetXtreme-E Dual-port 100Gb '
                                            'Ethernet PCIe Adapter',
                            'subsystem': 'Broadcom Inc. and subsidiaries Device '
                                         '2100'}}
        """
        if not self._nic:
            # Parse the command 'lspci' and return list of dictionaries with ethernet controller parameters
            nic_dict = dict()
            cmd = "lspci -Dvv"
            output = self.cli(cmd).splitlines()
            dev_output = list()
            ethernet = False
            for line in output:
                # Look for start of new PCI device
                match = re.search(r'^[a-f0-9]{4}:[a-f0-9]{2}:[a-f0-9]{2}\.([a-f0-9])\s+([^:]+):\s*(.*)', line)
                if match:
                    device_num = match.group(1)
                    device_type = match.group(2).lower()
                    device_desc = match.group(3).lower()
                    d = self._nic_parse(dev_output)
                    if d['pciid']:
                        key = d['pciid']
                        nic_dict[key] = d
                    dev_output = list()
                    if device_num == "0" and "ethernet" in device_type and "virtual" not in device_desc:
                        ethernet = True
                    else:
                        ethernet = False
                if ethernet:
                    dev_output.append(line)
            d = self._nic_parse(dev_output)
            if d['pciid']:
                key = d['pciid']
                nic_dict[key] = d
            self._nic = nic_dict
        return self._nic

    @property
    def os(self):
        return "linux"

    @property
    def packages(self) -> Dict[str, str]:
        """Queries system for set of packages.  Returns dict with package name -> version."""
        if not self._packages:
            distro = self.distribution_desc.lower()
            if "ubuntu" in distro or "debian" in distro:
                self._packages = self._get_dpkg_packages()
            elif "redhat" in distro or "centos" in distro or "suse" in distro:
                self._packages = self._get_rpm_packages()
            else:
                self._packages = dict()
        return self._packages

    def get_pci_configuration_header(self, pci_bdf: str) -> List[int]:
        """
        Returns the PCI Configuration Space Header given a PCI BDF(Bus, Device, Function) address.

        :param pci_bdf: PCI Bus, Device, Function in the format BB:DD.F or optionally prefaced with the Domain.
        i. e. 0000:63:00.0 or 63:00.0
        :return: List of 64 8-bit integers
        """
        bdf = re.match(r'^[a-fA-F0-9]{2}:[a-fA-F0-9]{2}\.[a-fA-F0-9]+', pci_bdf)
        domain_plus_bdf = re.match(r'^[a-fA-F0-9]{4}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}\.[a-fA-F0-9]+', pci_bdf)
        if not bdf and not domain_plus_bdf:
            raise ValueError(f"Improperly formatted BDF {pci_bdf}.")
        elif bdf:
            pci_bdf = "0000:" + pci_bdf
        if not self._pci_configuration_header.get(pci_bdf):
            cmd = f"lspci -s {pci_bdf} -x"
            output = self.cli(cmd).strip().splitlines()
            header_bytes = [0] * 64
            for line in output:
                parts = line.split()
                if len(parts) == 17 and parts[0].endswith(":"):
                    offset = int(parts.pop(0).split(":")[0], 16)
                    for i, part in enumerate(parts):
                        header_bytes[offset+i] = int(part, 16)
            self._pci_configuration_header[pci_bdf] = header_bytes
        return self._pci_configuration_header[pci_bdf]

    def _get_dpkg_packages(self) -> Dict[str, str]:
        """Return dict of packages for Ubuntu/Debian distros"""
        pkg_dict = dict()
        cmd = 'dpkg-query --show'
        output = self.cli(cmd).strip().splitlines()
        for line in output:
            pkg, ver = line.split('\t')
            pkg_dict[pkg] = ver
        return pkg_dict

    def _get_rpm_packages(self) -> Dict[str, str]:
        """Return dict of packages for Redhat/CentOs distros"""
        pkg_dict = dict()
        cmd = 'rpm -qa --queryformat "%{NAME}\t%{VERSION}\n"'
        output = self.cli(cmd).strip().splitlines()
        for line in output:
            pkg, ver = line.split('\t')
            pkg_dict[pkg] = ver
        return pkg_dict

    @classmethod
    def _ip_parse(cls, lines, interfaces_dict) -> None:
        """
        Parse nmcli output and add to the net_dict dictionary

        :return: None
        """
        regexs = {
            # Key is a tuple of fields or a single field.  Value is a regex with 1 or more match groups. The   number
            # of match groups must match the length of the tuple, or only one match group for a single field.
            'device': r'^\d+:\s+([^:]+)',
            ('type', 'mac'): r'^\s*link\/(\S+)\s+([a-fA-F0-9:]+)',
            ('ip4_addr', 'ip4_cidr', 'broadcast', 'ip4_scope'):
                r'^\s*inet\s+([0-9\.]+)\/(\d+)\s+brd\s+([0-9\.]+).*\s+scope\s+(\S+)',
            ('ip6_addr', 'ip6_cidr', 'ip6_scope'): r'^\s*inet6\s+([a-fA-F0-9:]+)\/(\d+).*\s+scope\s+(\S+)',
        }
        d = cls._parse(regexs, lines)
        device = d.get('device', "")
        if device in interfaces_dict:
            interfaces_dict[device].update(d)

    @classmethod
    def _nic_parse(cls, lines) -> Dict[str, str]:
        """
        Parse Ethernet devices from lspci --vv output and return dict.
        """
        regexs = {
            # Key is a tuple of fields or a single field.  Value is a regex with 1 or more match groups. The number
            # of match groups must match the length of the tuple, or only one match group for a single field.
            ('pciid', 'device_type', 'device_desc'):
                r'^([a-f0-9]{4}:[a-f0-9]{2}:[a-f0-9]{2})\.([a-f0-9])\s+([^:]+):\s*(.*)$',
            'subsystem': r'^\s*Subsystem:\s*(.*)$',
            'product_name': r'^\s*Product Name:\s*(.*)$',
            'part_number': r'^\s*\[PN]\s*Part number:\s*(.*)$',
            'firmware_ver': r'^\s*\[V0]\s*Vendor specific:\s*(.*)$',
            'kernel_driver': r'^\s*Kernel driver in use:\s*(.*)$',
            'kernel_modules': r'^\s*Kernel modules:\s*(.*)$',
            ('link_capability_speed', 'link_capability_width'): r'^\s*LnkCap:.*Speed\s*([^,]+).*Width\s*x(\d+)',
            ('link_status_speed', 'link_status_width'): r'^\s*LnkSta:.*Speed\s*([^,]+).*Width\s*x(\d+)',
        }
        return cls._parse(regexs, lines)
