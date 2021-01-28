import logging
import os
import socket
import sys
import weakref
from functools import wraps
from logging.handlers import QueueListener
from multiprocessing import Queue
from time import sleep
from threading import current_thread

import rpyc

from server_utils.config import config
from server_utils.rpyc_server import RPyCServer

log = logging.getLogger(__name__)


class RPyCSession:

    def __init__(self, server, timeout: int = 120):
        """Creates RPyC Session object to maintain RPyC connection to the remote host.
        The session establishes and maintains an rpyc client connection to an rpyc server.

        Before executing a command, the client checks if the rpyc connection exists.
        If no connection established, the connection will be established automatically on command execution.

        For now, it supports only blocking execution using one connection.
        """
        self.server = server
        self.address = server.ip
        self.port = config['rpyc']['port'].as_number()
        self.timeout = timeout
        self.conn = None
        self._finalizer = weakref.finalize(self, self.close)
        if config['rpyc']['restart'].get(bool):
            self.restart_server()

    @property
    def local_ip(self):
        laddr, lport = self.conn._channel.stream.sock.getsockname()
        return laddr

    def close(self) -> None:
        """Close RPyC connection. This function will be called automatically by Python garbage collector."""
        if self.conn:
            log.debug(f'Close RPyC connection to {self.address}:{self.port}.')
            self.conn.close()

    def connect(self, max_attempts: int = 3):
        """Create an RPyC connection to the remote host.

        :param max_attempts: Number of connection attempts.
        """

        if self.is_active:
            return

        restarted_server = False
        while(True):
            att_timeout = 3
            for attempt in range(1, max_attempts + 1):
                self.close()

                try:
                    log.debug(f'Trying to establish RPyC connection to {self.address}:{self.port}.')
                    self.conn = rpyc.classic.connect(self.address, port=self.port)
                except socket.timeout as err:
                    msg = f'Timeout. Try {attempt} of {max_attempts}'
                    if attempt == max_attempts:
                        if restarted_server:
                            log.error(msg)
                            raise err
                        else:
                            log.warning(msg)
                    else:
                        log.warning(msg)
                except socket.error as err:
                    msg = f"Socket error: {os.strerror(err.errno)}. Try {attempt} of {max_attempts}"
                    if attempt == max_attempts:
                        if restarted_server:
                            log.error(msg)
                            raise err
                        else:
                            log.warning(msg)
                    else:
                        log.warning(msg)
                else:
                    self.conn._config['sync_request_timeout'] = self.timeout
                    log.info(f"RPyC connected to {self.address}:{self.port}")
                    self.setup_remote()
                    return
                log.debug(f'Sleep {att_timeout} before next connection attempt.')
                sleep(att_timeout)
            if not restarted_server:
                restarted_server = True
                self.restart_server()

    def connected_only(func, *args, **kwargs):
        """Wrapper for methods which require an active RPyC connection."""
        @wraps(func)
        def conn_check(self, *args, **kwargs):
            if self.is_active is False:
                self.connect()
            return func(self, *args, **kwargs)
        return conn_check

    @connected_only
    def import_module(self, module: str):
        """Import module on remote and return reference to module

        :param module: Module to import. Example aucommon.tools.bnxtnvm.bnxtnvm
        """
        return self.conn.modules[module]

    @connected_only
    def add_module(self, module_name: str, python_file: str):
        """Add a python source code file to the remote systems global module space

        The python_file will be compiled using the compiler on the remote system.  The compiled object will then be
        added to a new module object.  The new module object will be added to the global module namespace on the remote.

        :param module_name: Name of the new module. This will be used in import statements.
        :param python_file: Name of the python file containing the python source for the new module.
        """
        sys = self.import_module('sys')
        if module_name in sys.modules:
            raise ValueError(f"Module {module_name} already exists.")
        imp = self.import_module('imp')
        remote_compile = self.conn.builtins.compile
        remote_exec = self.conn.builtins.exec
        module = imp.new_module(module_name)
        with open(python_file, "r") as f:
            module_code = f.read()
        compiled_obj = remote_compile(module_code, python_file, "exec")
        remote_exec(compiled_obj, module.__dict__)
        sys.modules[module_name] = module

    @connected_only
    def delete_module(self, module_name: str):
        """Delete a module from the global module space.

        :param module_name: Name of the module to be deleted.
        """
        sys = self.import_module('sys')
        if module_name not in sys.modules:
            # Nothing to delete
            return
        module = sys.modules[module_name]
        del module
        del sys.modules[module_name]

    @property
    def is_active(self) -> bool:
        if self.conn:
            if self.conn.closed:
                return False
            try:
                self.conn.ping()
                return True
            except (rpyc.core.protocol.PingError,
                    rpyc.core.AsyncResultTimeout,
                    EOFError,
                    socket.error):
                log.debug(f"RPyC connection to {self.address} failed ping test. Connection not active.")
        return False

    @connected_only
    def upload(self, srcpath: str, dstpath: str) -> None:
        rpyc.utils.classic.upload(self.conn, srcpath, dstpath)

    def restart_server(self):
        log.info(f"Restarting RPyC server on {self.server.ip}.")
        rpyc_server = RPyCServer(self.server)
        rpyc_server.sync()
        rpyc_server.create_venv()
        rpyc_server.restart_rpyc()

    def setup_remote(self):
        # Insert root path into module search path
        rsys = self.conn.modules.sys
        rthreading = self.import_module("threading")
        rroot = config['rpyc']['remote_path'].as_str()
        if rroot not in rsys.path:
            rsys.path.insert(0, rroot)
        # Redirect remote stdout and stderr to local
        rsys.stdout = sys.stdout
        rsys.stderr = sys.stderr
        self.thread_prefix = current_thread().name + "-rpyc-"
        # Configure logging
        self.setup_logging()
        self.register_thread(rthreading.current_thread())

    def setup_logging(self):
        # Configure logging
        queue = Queue()
        verbosity = config['verbose'].get(int)
        rhelpers = self.import_module("server_utils.helpers")
        rlogging = self.import_module("logging")
        rlogging_handlers = self.import_module("logging.handlers")
        rlogging.raiseExceptions = False
        rlog = rlogging.getLogger(__name__.split('.')[0])
        queue_handler = rlogging_handlers.QueueHandler(queue)
        queue_handler.setLevel(verbosity)
        filter = rhelpers.ThreadNameFilter()
        queue_handler.addFilter(filter)
        rlog.addHandler(queue_handler)
        handlers = logging.getLogger(__name__.split('.')[0]).handlers
        listener = QueueListener(queue, *handlers)
        listener.start()
        self._logging_filter = filter


    def register_thread(self, thread):
        """
        Register a remote thread with this RPyC session.
        This will name the thread and add a filter to the logger so logging events originating from the thread only
        go to this seesion
        """
        thread.name = (self.thread_prefix + thread.name).lower()
        self._logging_filter.add_thread_name(thread.name)
