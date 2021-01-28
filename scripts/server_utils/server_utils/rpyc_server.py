import logging
import os
import pathlib
import sys

from server_utils.config import config

log = logging.getLogger(__name__)


class RPyCServer:
    VENV_BIN = "venv/bin"
    VENV_ACTIVATE = VENV_BIN + "/activate"
    RPYC_SERVER = VENV_BIN + "/rpyc_classic.py"

    def __init__(self, server):
        """Syncs python modules to remote server. Updates and activates virtual environment on remote. Starts RPyC
        server on remote.
        """
        self.server = server
        self.port = config['rpyc']['port'].as_number()
        self.remote = config['rpyc']['remote_path'].as_str()
        my_path = os.path.abspath(pathlib.Path(__file__))
        server_utils_index = my_path.find('server_utils/venv')
        if server_utils_index < 0:
            raise FileNotFoundError("Cannot find the top-level server_utils path.")
        server_utils_path = my_path[0:server_utils_index] + 'server_utils'
        self.local = server_utils_path
        self.rpyc_server = os.path.join(self.remote, self.RPYC_SERVER)
        self.venv_activate = os.path.join(self.remote, self.VENV_ACTIVATE)

    def remote_exists(self):
        return self.server.exec_success(f'ls {self.remote}')

    def delete(self):
        if self.remote_exists():
            self.kill_rpyc()
            self.server.exec(f'rm -fr {self.remote}')

    def sync(self):
        self.server.rsync(self.local, self.remote, '--exclude', "__pycache__/", '--exclude', "/venv")

    def restart_rpyc(self):
        self.kill_rpyc()
        self.start_rpyc()

    def start_rpyc(self):
        output = self.server.run_script(f"""
            source {self.venv_activate}
            python3 {self.rpyc_server} --port {self.port} --host 0.0.0.0 --mode threaded &
            sleep 1
            exit
        """)
        for line in output:
            if "server started" in line:
                return
        log.error(f"Failed to start RPyC server on '{self.server.name}'")
        sys.exit(1)

    def kill_rpyc(self):
        lines = self.server.exec('ps -ef')
        pid = None
        for line in lines:
            if self.RPYC_SERVER in line:
                pid = line.split()[1]
                if pid:
                    self.server.exec(f'kill {pid}')

    def create_venv(self):
        log.debug("Creating virtual environment.")
        script = f"cd {self.remote} && ./create_venv --server; exit;\n"
        stdout_lines = self.server.run_script(script)
        for line in stdout_lines:
            if "virtualenv has been created and project installed" in line:
                log.info("Successfully created python virtual environment on server.")
                return
        log.critical(f"Failed to install virtual environment on server. Log into server and run {script} to see"
                     "what went wrong.")
        log.critical(''.join(stdout_lines))
        sys.exit(1)


