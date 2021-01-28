import logging

#from server_utils.config import config
from server_utils.helpers import setup_logging
from typing import Callable, List, Any
import threading
import ctypes
from time import sleep


class KillableThread(threading.Thread):

    def __init__(self, run_func, run_args=None, cleanup_func=None, cleanup_args=None):
        threading.Thread.__init__(self)
        self.run_func = run_func
        self.run_args = run_args
        self.cleanup_func = cleanup_func
        self.cleanup_args = cleanup_args
        self.daemon = True

    def run(self):
        try:
            if self.run_args:
                self.run_func(*self.run_args)
            else:
                self.run_func()
        except SystemExit:
            self.cleanup()

    def cleanup(self):
        if self.cleanup_func:
            if self.cleanup_args:
                self.cleanup_func(*self.cleanup_args)
            else:
                self.cleanup_func()

    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def raise_exception(self, exc):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(exc))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, None)
            print('Exception raise failure')

    def terminate(self):
        self.raise_exception(SystemExit)


class ServerJob(KillableThread):
    def __init__(self, target, args, server_name):
        # Create the server object
        from server_utils.server import get_server
        server = get_server(server_name)
        KillableThread.__init__(self, target, [server])
        self.name = server_name

def start_threads(target: Callable, servers: List[str], args: Any):
    """
    Start a separate thread for each server in the list.

    :param target: target function for the server thread
    :param servers: list of servers
    :param args: parsed command line options from argparse
    :return: None
    """
    # Setup logging for the server_utils application.
    log = logging.getLogger(__name__.split('.')[0])
    setup_logging(log, args.verbose)

    threads = []
    for server in servers:
        thread = ServerJob(target, args, server)
        threads.append(thread)
    for thread in threads:
        thread.start()
    try:
        while True:
            threads_alive = False
            for thread in threads:
                threads_alive = threads_alive or thread.is_alive()
            if not threads_alive:
                break
            sleep(.1)
    except KeyboardInterrupt:
        for thread in threads:
            thread.terminate()
    sleep(.1)
    for thread in threads:
        thread.join()
