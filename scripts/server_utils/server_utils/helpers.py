import logging
import subprocess
import sys
import time
from threading import current_thread
from typing import Callable, Any
from logging import Filter

log = logging.getLogger(__name__)


def exec(command, check=True, shell=False):
    """Execute command, return stdout on success.  Raise exception on failure."""
    if not isinstance(command, list):
        command = command.split(" ")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    stdout, stderr = process.communicate()
    return_code = process.poll()
    if return_code != 0 and check:
        log.error(f"Command '{' '.join(command)}' returned {return_code}.\nSTDERR: {stderr.decode('utf-8')}")
        sys.exit(return_code)
    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')
    log.debug(f"Executing locally: {command}")
    log.debug(f"STDOUT: {stdout}")
    log.debug(f"STDERR: {stderr}")
    return stdout


class LogFormatter(logging.Formatter):
    """
    Custom logger formatter for indenting multiline log messages
    """

    def __init__(self, fmt):
        super(LogFormatter, self).__init__('{relativeCreated:.1f}s {levelname} [{threadName}] ', style='{')

    def format(self, record):
        # Recalculate the relative creation time of the record, so that records received from remotes servers are synced
        # up with the local time.
        record.relativeCreated = time.time() - logging._startTime
        header = super(LogFormatter, self).format(record)
        message = record.getMessage().split("\n")
        message[:] = [header + line for line in message]
        return "\n".join(message).strip()


class ThreadNameFilter(Filter):
    def __init__(self):
        Filter.__init__(self)
        self.thread_names = []

    def add_thread_name(self, thread_name):
        self.thread_names.append(thread_name)

    def filter(self, record):
        if record.threadName in self.thread_names:
            return True
        return False


def list_to_string(values, conjuction="and"):
    if not isinstance(values, list):
        return str(values)
    num_items = len(values)
    if num_items == 0:
        return ""
    if num_items == 1:
        return str(values[0])
    if num_items == 2:
        return f"{values[0]} {conjuction} {values[1]}"
    text = ""
    for value in values:
        if value == values[-1]:
            text += f"{conjuction} {value}"
        else:
            text += f"{value}, "
    return text


def check_timing_values(max_wait, check_interval):
    if max_wait < check_interval:
        raise ValueError(f'Max wait for polling {max_wait} should be more more than '
                         f'the check interval {check_interval}.')
    if check_interval < 0.2:
        raise ValueError(f'The check interval {check_interval} is less than minimum allowed 0.2 second.')


def poll(func: Callable, *args, expected: Any = True, max_wait: float = 300.0,
         check_interval: float = 10.0, **kwargs) -> bool:
    """Execute c given function until it returns the provided expected value within given max_time - return True,
    else return False.
    This is a straight forward blocking implementation. Please use something else if you need async polling,
    event-based execution, or any other form of concurrency.

    *args and **kwargs will be passed to the function.

    .. note::

        This implementation is about time to spend to poll a function rather than the exact number of attempts.
        Please choose the max_wait and check_interval wisely. If you need at least 4 execution attempts and
        the func call usually takes less than 1-second try max_wait=20 and check_interval=4, then in most cases
        there will be 5 attempts.
        Due to some reasons, e.g., bug or high load or high network/CPU usage, the func() call may take different
        amount of time.

    .. note::

        The poll() does not limits a func() execution time nor interrupt the func call.
        If func execution will take more them max_wait the function will be executed at least once.

    :param func: Callable object which return value will be evaluated to determine success.
    :param expected: the value of any type which we expect from the function to consider "success" and stop polling.
                     With an instance of a user defined class, please ensure that __eq__ and __ne__ are implemented.
    :param max_wait: time to poll the function before return False
    :param check_interval: desired time in seconds between each func call. Func call won`t be interrupted if takes
                           more than the check interval.
    """
    check_timing_values(max_wait, check_interval)

    max_time = time.time() + max_wait

    loop_start = time.time()
    while loop_start < max_time:
        if func(*args, **kwargs) == expected:
            return True

        possible_wait = check_interval - (time.time() - loop_start)
        if possible_wait > 0:
            time.sleep(possible_wait)

        loop_start = time.time()

    return False


def setup_logging(log, verbosity, stream=sys.stdout):
    logging.raiseExceptions = False
    log.setLevel(verbosity)
    ch = logging.StreamHandler(stream)
    ch.setLevel(verbosity)
    formatter = LogFormatter(None)
    ch.setFormatter(formatter)
    log.addHandler(ch)
