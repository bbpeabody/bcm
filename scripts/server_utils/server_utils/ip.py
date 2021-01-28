import logging
import re

from server_utils.helpers import poll

log = logging.getLogger(__name__)


class Ip:
    def __init__(self, server):
        self.server = server

    def link_down(self, interface):
        self.server.exec(f"ip link set down {interface}")

    def link_up(self, interface):
        self.server.exec(f"ip link set up {interface}")

    def is_link_up(self, interface):
        if self.get_link(interface) == "up":
            return True
        return False

    def get_link(self, interface):
        """Return "State" of the interface in lower case: up|down."""
        output = self.server.exec(f'ip link show dev {interface}')
        match = re.search(r'state\s(\w+)\s', '\n'.join(output))
        if match:
            try:
                return match.group(1).lower()
            except IndexError:
                pass
        raise ValueError(f'Cannot find link state information for interface {interface}.')

    def wait_link_up(self, interface):
        return poll(self.is_link_up, interface, expected=True, max_wait=10.0, check_interval=1.0)

