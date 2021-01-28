import logging

import requests
from .helpers import poll
from requests.exceptions import ConnectionError

log = logging.getLogger(__name__)


def is_redfish_supported(addr: str, port: int, login: str, password: str) -> bool:
    """Check if Redfish out-of-band management supported on the ip host."""
    redfish_url = f"https://{addr}:{port}/redfish/"
    log.debug(f'Check is Redfish API is supported by the host by checking {redfish_url}')
    try:
        response = requests.get(redfish_url, verify=False, auth=(login, password))
    except ConnectionError:
        log.debug(f'A connection to the {addr}:{port} can`t be established. Please check the Redfish IP:port provided.'
                 'Consider the system as non Redfish enabled.')
        return False

    if response.status_code == 200:
        return True

    log.debug(f'System responded {response.status_code} {response.reason} response has been received. '
             f'Consider the system as non Redfish enabled.')
    return False


class Redfish:

    def __init__(self, addr: str, login: str, password: str, sys_id: str, port: int = 443, sys_name: str = ''):
        """Provide an interface to a server managed via Redfish API.
        Redfish API is a popular standard for Out-of-band management supported by the majority of Server vendors
        e.g. Dell, HP, Supermicrio from 2016. If a server does not support Redfish, please double-check the chassis
        firmware version and update it to the last one.

        Please ensure that the device supports Redfich before use this class. It can be done e.g. in a fixture which
        provides the Redfish instance or in a separate wrapper.

        For Dell servers use the address, port, and credentials of iDRAC out-of-band management system.

        >>> s = Redfish(addr='10.13.253.X',
        >>>             port=443,
        >>>             login='root',
        >>>             password='br0adc0m$',
        >>>             sys_name='Stingray',
        >>>             sys_id='System.Embedded.1')

        >>> print(s.get_power_state())
        on

        :param addr: address of chassis with Redfish API
        :param port: port to access Redfish API
        :param login: login to the Out-of-band management system
        :param password: password to the Out-of-band management system
        :param sys_id: id of the unit to manage in Redfish API
                       e.g.'System.Embedded.1' on Dell or a platform ID 'E1D8B426' on HP devices.
        :param sys_name: name of the system for debug purpose. May be something like 'SUT'.
        """
        self.addr = addr
        self.port = port
        self.login = login
        self.password = password
        self.sys_id = sys_id
        self.name = sys_name or sys_id
        self.sys_id_url = f"https://{self.addr}:{self.port}/redfish/v1/Systems/{sys_id}"

        self.session = requests.Session()
        self.session.auth = (self.login, self.password)
        self.session.verify = False

    def powercycle(self, force: bool = True, max_wait_off: int = 300, max_wait_on: int = 600,
                   check_interval: int = 10) -> None:
        """Perform force power cycle with waiting On state reached in out-of-band system.

        The function does a Shutdown, waits for Off state, executes Power On, and waits for On state.

        `force=False` supposed to trigger GracefulShutdown action but...
        - GracefulShutdown does not work on some servers, e.g. Dell R420 iDRAC 2.70 with CentOS 7.5.
          The iDRAC initiates some shutdown command, but OS is not get rebooted.
        - Some platform does not support GracefulShutdown
        - We could use GracefulRestart if GracefulShutdown is not supported, but GracefulRestart
          does not produce Power Off state, so that we have to rely on "sleep" and assume that
          a restart happened, which makes the system unreliable.
        - "GracefulShutdown" and "GracefulRestart" are OS-specific and may produce unstable results
        depending on OS/Version/OS State.
        - https://github.com/dell/iDRAC-Redfish-Scripting/issues/29

        Conclusion: for Grace restart we should use more sophisticated logic with executing reboot command
        via OS CLI and be able to raise error if a shutdown is not happened.

        `force = True` is kept in the function signature for the readability and visibility and to avoid core
        refactoring when a gracefull option will be added.

        This function relies on Power On reported by the out-of-band system, in this case, means that system boot
        has been started.
        To assert that tcp port is ready to accept connection you can use wait_for_tcp_port_ready() from
        aucommon.helpers.connectivity

        :param force: defines which action to execute.
        :param max_wait_off: max time to wait Off state reported by the out-of-band system.
        :param max_wait_on: max time to wait On state reported by the out-of-band system.
        :param check_interval: defines the intervals between power state checks.
        """
        if force is False:
            raise NotImplementedError('The Graceful powercycle is not implemented. Please use force=True. '
                                      'Read the documentation to get more information.')

        log.debug(f'Powercycle {self.name} with Force Power Off, Power On and wait for Power On state.')
        self.reset_system(reset_type='ForceOff')
        self.wait_for_power_off(max_wait=max_wait_off, check_interval=check_interval)
        self.reset_system(reset_type='On')
        self.wait_for_power_on(max_wait=max_wait_on, check_interval=check_interval)

    def get_power_state(self) -> str:
        """Get a power state of a device using out-of-band management.
        The function sends HTTP GET to the redfish system endpoint and read the power state.
        JSON with key "PowerState" is expected from the out-of-band management.
        """
        resp = self.session.get(self.sys_id_url)

        if resp.status_code == 200:
            power_state = resp.json()['PowerState'].lower()
            log.debug(f'The current power state of {self.name} is: {power_state}.')
            return power_state

        resp.raise_for_status()

    def get_supported_reset_actions(self) -> list:
        """Get a list of Reset Actions supported by out-of-band management.
        If you need more action, please update the FW of your server`s chassis (e.g. iDRAC).
        """
        resp = self.session.get(self.sys_id_url)
        if resp.status_code == 200:
            return resp.json()['Actions']['#ComputerSystem.Reset']['ResetType@Redfish.AllowableValues']

        resp.raise_for_status()

    def is_powered_on(self) -> bool:
        """Check is the power state of a device is On using out-of-band management."""
        if self.get_power_state() == 'on':
            return True

        return False

    def is_powered_off(self) -> bool:
        """Check is the power state of a device is Off using out-of-band management."""
        if self.get_power_state() == 'off':
            return True

        return False

    def reset_system(self, reset_type: str) -> None:
        """Send a reset command to the remote system using out-of-band management interface.

        +------------------+-------------------------------------------------------------------------+
        | ResetType        |  Description                                                            |
        +==================+=========================================================================+
        | ForceOff         | Turn the unit off immediately (non-graceful shutdown).                  |
        +------------------+-------------------------------------------------------------------------+
        | ForceOn          | Turn the unit on immediately.                                           |
        +------------------+-------------------------------------------------------------------------+
        | ForceRestart     | Perform an immediate (non-graceful) shutdown, followed by a restart.    |
        +------------------+-------------------------------------------------------------------------+
        | GracefulRestart  | Perform a graceful shutdown followed by a restart of the system.        |
        +------------------+-------------------------------------------------------------------------+
        | GracefulShutdown | Perform a graceful shutdown and power off.                              |
        +------------------+-------------------------------------------------------------------------+
        | Nmi              | Generate a Diagnostic Interrupt (usually an NMI on x86 systems) to      |
        |                  | cease normal operations, perform diagnostic actions and typically halt  |
        |                  | the system.                                                             |
        +------------------+-------------------------------------------------------------------------+
        | On               | Turn the unit on.                                                       |
        +------------------+-------------------------------------------------------------------------+
        | PowerCycle       |Perform a power cycle of the unit.                                       |
        +------------------+-------------------------------------------------------------------------+
        | PushPowerButton  |Simulate the pressing of the physical power button on this unit.         |
        +------------------+-------------------------------------------------------------------------+

        Different versions and implementation of Redfish standard supports a different set of reset actions.
        e.g., Different devices support different reset system values. And even the same machine with
        different firmware.
        Dell PowerEdge R430 with fw 2.40
        ['On', 'ForceOff', 'GracefulRestart', 'PushPowerButton', 'Nmi]
        Dell PowerEdge R720 with fw 2.65
        ['On', 'ForceOff', 'ForceRestart', 'GracefulShutdown', 'PushPowerButton', 'Nmi']
        Dell PowerEdge R430 with fw 2.70
        ['On', 'ForceOff', 'ForceRestart', 'GracefulShutdown', 'PushPowerButton', 'Nmi']

        :param reset_type: Type of system reset action.
        """
        log.debug(f"Sending Reset Type {reset_type} to {self.name} via {self.addr}:{self.port}.")
        resp = self.session.post(f'{self.sys_id_url}/Actions/ComputerSystem.Reset',
                                 json={'ResetType': reset_type})

        msg = ''
        if resp.status_code == 409:
            msg = f'Looks like {self.name} already in {reset_type} state.'
        elif resp.status_code == 204:
            msg = f'The {reset_type} command has been accepted by {self.name}.'

        log.debug(f'{msg} The Server returned {resp.status_code} "{resp.reason}" for the Reset command.')

    def wait_for_power_on(self, max_wait: float = 600, check_interval: float = 5):
        """Wait for Power On state reported by the out-of-band management tool.
        E.g., in case of a force power cycle.
        This function waits for power status "on". No furthers asserts needed. If ON state is not reached
        in max_wait timeout, the exception will be raised.

        To assert that the TCP port is ready to accept a connection, you can use wait_for_tcp_port_ready().
        """
        if poll(self.get_power_state, expected='on', max_wait=max_wait, check_interval=check_interval):
            log.debug(f'The {self.name} has reached Power State "On".')
            return

        raise UserWarning(f'The system {self.name} on management {self.addr}:{self.port} has not '
                          f'reached Power State "On" after max wait {max_wait} seconds.')

    def wait_for_power_off(self, max_wait: float = 600, check_interval: float = 5):
        """Wait for Power Off state reported by the out-of-band management tool.
        E.g., in case of a force power cycle.
        This function waits for power status "off". No furthers asserts needed. If ON state is not reached
        in max_wait timeout, the exception will be raised.

        To assert that the TCP port is ready to accept a connection, you can use wait_for_tcp_port_ready().
        """
        if poll(self.get_power_state, expected='off', max_wait=max_wait, check_interval=check_interval):
            log.debug(f'The system {self.name} has reached Power State "Off".')
            return

        raise UserWarning(f'The system {self.name} on management {self.addr}:{self.port} has not '
                          f'reached Power State "Off" after max wait {max_wait} seconds.')
