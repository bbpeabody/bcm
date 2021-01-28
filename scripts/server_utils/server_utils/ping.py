import logging
from typing import Callable

from server_utils.helpers import exec, poll

log = logging.getLogger(__name__)


def wait_pingable(dst: str, max_wait: int = 300, cli: Callable = None) -> bool:
    return poll(is_pingable, dst, expected=True, max_wait=max_wait, check_interval=1.0)


def is_pingable(dst: str, timeout: int = 3, cli: Callable = None) -> bool:
    """Test if remote machine responds to ping.
    The 'platform' should reflect the platform from which ping command is executed.

    :param dst: ip or resolvable host address
    :param timeout: maximum amount of time (in seconds) to wait for ping response
    :param cli: callable cli shell object, default is subprocess.run
    :return: True if machine responded to ping within timeout.  False otherwise
    """
    packets = 1

    if cli is None:
        cli = exec
    result = ping(dst=dst, packets=packets, timeout=timeout, cli=cli)
    if result['transmitted'] == packets and result['received'] == packets and not result['errors']:
        return True
    return False


def ping(dst: str,
         src: str = '',
         packets: int = 1,
         size: int = None,
         dnf: bool = False,
         ttl: int = 0,
         timeout: int = 0,
         flood: bool = False,
         duration: int = 0,
         options: str = '',
         cli: Callable = None) -> dict:
    """Send ping using provided shell toward destination IP.
    Some ping options are supported as keyword arguments. Arbitrary options may be set in
    'options' argument.

    The function passes 'options' without modification. If 'options' contains the same element
    as in keyword arguments, both will pa passed to the ping command.
    e.g. ping_linux(packets=1, options='-c 2'),

    Packets or duration should be specified. Otherwise, it will be an endless ping,
    unless a background execution with further stop is used.

    :param dst: address to ping.
    :param src: either an address or an interface name to ping.
    :param packets: number of packets to send.
    :param size: the size of the payload to send.
    :param dnf: do not fragment.
    :param ttl: do not fragment.
    :param timeout: Time to wait for a response in seconds.
    :param flood: do not fragment.
    :param duration: a timeout, in seconds, before ping exits regardless of how many packets
                     have been sent or received.
    :param options: any options to be added to the ping command.
    :param callable cli: callable object to execute ping command and return full output as a string.
    :return parsed ping output statistics.
    """

    if cli is None:
        cli = exec

    if size and int(size) > 65507:
        raise ValueError(f'Packet size {size} is too large. Maximum is 65507')

    opt_list = []
    if src:
        opt_list.append(f'-I {src}')
    if packets:
        opt_list.append(f'-c {packets}')
    if size:
        opt_list.append(f'-s {size}')
    if dnf:
        opt_list.append('-M do')
    if ttl:
        opt_list.append(f'-t {ttl}')
    if timeout:
        opt_list.append(f'-W {timeout}')
    if duration:
        opt_list.append(f'-w {duration}')
    if flood:
        opt_list.append('-f')
    if options:
        opt_list.append(options)

    full_options = ' '.join(opt_list)

    log.debug(f'Send ICMP requests using ping to {dst}')
    command = f'ping {full_options} {dst}'

    result = cli(command, False)

    return parse_linux_ping_out(result)


def parse_linux_ping_out(ping_out: str) -> dict:
    """Parse ping output into dict.

    .. note::

        Linux ping output does not print rtt timings in next cases:
            - payload size is less that 16,
            - a src interface is used.
        So that you will see only transmitted, received, loss stats and total time.

    ipg/ewma are moving average and will be filled only if presented in the output.
    To get them - use flood mode.

    >>> result = {
    >>>     'transmitted': 1,
    >>>     'received': 1,
    >>>     'loss': 0,
    >>>     'time': 0,
    >>>     'errors': 0,
    >>>     'rtt_min': 0,
    >>>     'rtt_max': 0,
    >>>     'rtt_avg': 0,
    >>>     'rtt_mdev': 0,
    >>>     'ipg': 0,
    >>>     'ewma': 0  # exponential moving average
    >>> }

    [root@client ~]# ping6 -M do -c 1 -s 1452 fd11::1
    PING fd11::1(fd11::1) 1452 data bytes
    1460 bytes from fd11::1: icmp_seq=1 ttl=64 time=0.113 ms

    --- fd11::1 ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 0.113/0.113/0.113/0.000 ms


    In case of flood ping is used, the time statistic is a little bit different:

    PING 127.0.0.1 (127.0.0.1) 20(48) bytes of data.

    --- 127.0.0.1 ping statistics ---
    10 packets transmitted, 10 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 0.009/0.013/0.044/0.011 ms, ipg/ewma 0.028/0.020 ms

    Output with MTU error
    [root@client ~]# ping6 -M do -c 1 -s 14522 fd11::1
    PING fd11::1(fd11::1) 14522 data bytes
    ping: local error: Message too long, mtu=1500

    --- fd11::1 ping statistics ---
    1 packets transmitted, 0 received, +1 errors, 100% packet loss, time 0ms

    Output with Net unreachable
    [root@client ~]# ping 172.172.172.182 -c 1
    PING 172.172.172.182 (172.172.172.182) 56(84) bytes of data.
    From 98.174.159.185 icmp_seq=1 Destination Net Unreachable

    --- 172.172.172.182 ping statistics ---
    1 packets transmitted, 0 received, +1 errors, 100% packet loss, time 0ms

    :param ping_out: Ping output statistics.
    :return: dict with ping statistics or error types.
    """
    if 'Usage:' in ping_out:
        UserWarning('Can`t parse ping statistics. Maybe the command has been executed without proper parameters?')

    result = {
        'transmitted': None,
        'received': None,
        'loss': None,
        'time': None,
        'errors': None,
        'rtt_min': None,
        'rtt_avg': None,
        'rtt_max': None,
        'rtt_mdev': None,
        'error_type': []
    }
    possible_errors = [
        ('Message is bigger than MTU', 'Message too long'),
        ('Destination unreachable', 'Destination Net Unreachable'),
        ('Can not resolve/parse destination.', 'Name or service not known'),
        ('Responses payload less than sent', '(truncated)')
    ]

    for error in possible_errors:
        if error[1] in ping_out:
            result['error_type'].append(error[0])

    ping_stat_mark = 'ping statistics'
    stats_offset = ping_out.find(ping_stat_mark)
    if stats_offset > 0:
        result.update(parse_ping_stats(ping_out[stats_offset:]))

    return result


def parse_ping_stats(ping_out: str) -> dict:
    """Parse ping statistics.

    Expected input:
    'ping statistics ---
    2 packets transmitted, 2 received, 0% packet loss, time 999ms\n
    rtt min/avg/max/mdev = 0.105/0.105/0.106/0.010 ms\n'

    or
    'ping statistics ---
    10 packets transmitted, 10 received, 0% packet loss, time 0ms\n
    rtt min/avg/max/mdev = 0.009/0.013/0.044/0.011 ms, ipg/ewma 0.028/0.020 ms\n'

    :param str ping_out: output of ping command which contains a ping statistic.
    :return: dict with packets and rtt statistics.
    """
    result = dict()
    pkts_offset = ping_out.find('packets transmitted,')
    if pkts_offset > 0:
        pkts_offset = ping_out.rindex('\n', 0, pkts_offset) + 1
        pkts_line = ping_out[pkts_offset: ping_out.index('\n', pkts_offset)].replace('ms', '').replace('%', '')
        pkts_stats = [field.strip(' +\n') for field in pkts_line.split(',')]
        if len(pkts_stats) < 3:
            raise UserWarning(f'Can`t parse packets stats in ping output.\n{ping_out}')
        for stat in pkts_stats:
            parsed_stat = stat.split(' ')
            if parsed_stat[0] == 'time':
                result['time'] = round(float(parsed_stat[-1]))
            else:
                result[parsed_stat[-1]] = round(float(parsed_stat[0]))

    rtt_offset = ping_out.find(' min')
    if rtt_offset > 0:
        rtt_line = ping_out[rtt_offset: ping_out.index('\n', rtt_offset)]
        if ',' in rtt_line:
            time_stats = rtt_line.split(',')
            rtt_line = time_stats[0]
            if 'ipg/ewma' in time_stats[-1]:
                ipg_line = time_stats[-1].strip(' ms\n')
                ipg_times = ipg_line.split(' ')[1].split('/')
                if len(ipg_times) != 2:
                    raise UserWarning(f'Can`t parse ipg/ewma stats in ping output.\n{ping_out}')
                result['ipg'] = float(ipg_times[0])
                result['ewma'] = float(ipg_times[1])

        rtt_times = rtt_line.split('=')[1].strip(' ms\n').split('/')
        if len(rtt_times) != 4:
            raise UserWarning(f'Can`t parse RTT stats in ping output.\n{ping_out}')
        result['rtt_min'] = float(rtt_times[0])
        result['rtt_avg'] = float(rtt_times[1])
        result['rtt_max'] = float(rtt_times[2])
        result['rtt_mdev'] = float(rtt_times[3])

    return result
