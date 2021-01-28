import logging
import re

log = logging.getLogger(__name__)


class Ethtool:
    def __init__(self, server):
        self.server = server

    def highest_supported_speed(self, interface):
        supported_speeds = [int(speed) for speed, _ in self.supported_speeds(interface)]
        return max(supported_speeds)

    def forced_speed(self, interface, speed):
        self.server.exec(f"ethtool -s {interface} autoneg off speed {speed}")

    def autoneg(self, interface, speeds=None):
        advertise_mask = 0
        if speeds is not None:
            if not isinstance(speeds, list):
                speeds = [speeds]
            for speed in speeds:
                advertise_mask |= self.speed_to_advertise(speed)
        if advertise_mask:
            self.server.exec(f"ethtool -s {interface} autoneg on advertise {advertise_mask}")
        else:
            self.server.exec(f"ethtool -s {interface} autoneg on")

    def speed(self, interface):
        lines = self.server.exec(f'ethtool {interface}')
        speed = re.findall(r'Speed:\s+(\d+)Mb/s', "\n".join(lines))
        if len(speed) == 1:
            speed = int(int(speed[0])/1000)
            return f"{speed}G"
        raise ValueError(f"Cannot determine speed of interface {interface}")

    def supported_speeds(self, interface):
        lines = self.server.exec(f'ethtool {interface}')
        speeds = re.findall(r'(\d+).*/(Full|Half)', "\n".join(lines))
        if len(speeds) > 0:
            return list(set(speeds))

    def speed_to_advertise(self, speed):
        ethtool_advertise_bits = {
            "10baseT Half": 0x001,
            "10baseT Full": 0x002,
            "100baseT Half": 0x004,
            "100baseT Full": 0x008,
            "1000baseT Half": 0x010,
            "1000baseT Full": 0x020,
            "1000baseKX Full": 0x20000,
            "1000baseX Full": 0x20000000000,
            "2500baseT Full": 0x800000000000,
            "2500baseX Full": 0x8000,
            "5000baseT Full": 0x1000000000000,
            "10000baseT Full": 0x1000,
            "10000baseKX4 Full": 0x40000,
            "10000baseKR Full": 0x80000,
            "10000baseCR Full": 0x40000000000,
            "10000baseSR Full": 0x80000000000,
            "10000baseLR Full": 0x100000000000,
            "10000baseLRM Full": 0x200000000000,
            "10000baseER Full": 0x400000000000,
            "20000baseMLD2 Full": 0x200000,
            "20000baseKR2 Full": 0x400000,
            "25000baseCR Full": 0x80000000,
            "25000baseKR Full": 0x100000000,
            "25000baseSR Full": 0x200000000,
            "40000baseKR4 Full": 0x800000,
            "40000baseCR4 Full": 0x1000000,
            "40000baseSR4 Full": 0x2000000,
            "40000baseLR4 Full": 0x4000000,
            "50000baseCR2 Full": 0x400000000,
            "50000baseKR2 Full": 0x800000000,
            "50000baseSR2 Full": 0x10000000000,
            "56000baseKR4 Full": 0x8000000,
            "56000baseCR4 Full": 0x10000000,
            "56000baseSR4 Full": 0x20000000,
            "56000baseLR4 Full": 0x40000000,
            "100000baseKR4 Full": 0x1000000000,
            "100000baseSR4 Full": 0x2000000000,
            "100000baseCR4 Full": 0x4000000000,
            "100000baseLR4_ER4 Full": 0x8000000000,
            "200000baseKR4 Full": 0x4000000000000000,
            "200000baseSR4 Full": 0x8000000000000000,
            "200000baseLR4_ER4_FR4 Full": 0x10000000000000000,
            "200000baseDR4 Full": 0x20000000000000000,
            "200000baseCR4 Full": 0x40000000000000000,
        }
        speed_map = {
            1000: "1000baseT Full",
            10000: "10000baseT Full",
            25000: "25000baseCR Full",
            40000: "40000baseCR4 Full",
            50000: "50000baseCR2 Full",
            100000: "100000baseCR4 Full",
            200000: "200000baseCR4 Full"
        }
        ethtool_speed = speed_map.get(speed)
        if ethtool_speed is None:
            raise ValueError(f"Unknown speed mapping for speed {speed}.")
        ethtool_bits = ethtool_advertise_bits.get(ethtool_speed)
        if ethtool_bits is None:
            raise ValueError(f"Unknown ethtool speed mapping for speed {ethtool_speed}.")
        return ethtool_bits

