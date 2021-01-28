import logging
import os
import sys

from server_utils.config import config

log = logging.getLogger(__name__)


class Aurora:
    RPYC_SCRIPT = "aucommon/au_rpyc_server.py"
    VENV_ACTIVATE = "venv/bin/activate"

    def __init__(self, server, local, remote):
        self.server = server
        self.local = local
        self.remote = remote
        self.rpyc_script = os.path.join(remote, self.RPYC_SCRIPT)
        self.venv_activate = os.path.join(remote, self.VENV_ACTIVATE)

    def remote_exists(self):
        return self.server.exec_success(f'ls {self.remote}')

    def delete(self):
        if self.remote_exists():
            self.kill_rpyc()
            self.server.exec(f'rm -fr {self.remote}')

    def sync(self):
        if not self.remote_exists():
            self.kill_rpyc()
            self.clone()
            self.create_venv()
        local_path = os.path.join(self.local, "aucommon")
        for path in ["aucommon", "venv/lib/python3.6/site-packages/aucommon",
                     "venv/lib/python3.7/site-packages/aucommon"]:
            remote_path = os.path.join(self.remote, path)
            if self.server.exec_success(f'ls {remote_path}'):
                self.server.rsync(local_path, remote_path, '--exclude', "'__pycache__/'")

    def restart_rpyc(self):
        self.kill_rpyc()
        self.start_rpyc()

    def start_rpyc(self):
        output = self.server.run_script(f"""
            source {self.venv_activate}
            python3 {self.rpyc_script} --port 3737 --host 0.0.0.0 &
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
            if self.RPYC_SCRIPT in line:
                pid = line.split()[1]
                break
        if pid:
            self.server.exec(f'kill {pid}')

    def clone(self):
        log.debug("Cloning au-common repo.")
        self.server.exec(f"git clone {config['aurora']['repo_url'].as_str()} {self.remote}")

    def create_venv(self):
        log.debug("Creating virtual environment.")
        self.server.run_script(f"cd {self.remote} && ./create_venv; exit;\n")

