import logging
import re
import sys

import paramiko
import pexpect

from server_utils.config import config
from server_utils.helpers import exec
from server_utils.inventory.inventory import create_inventory
from server_utils.rpyc_session import RPyCSession

log = logging.getLogger(__name__)

servers = dict()
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class Server:
    def __init__(self, name, ip, user, password, port=22):
        self.name = name
        self._ip = ip
        self._user = user
        self._password = password
        self._port = port
        self._conn = None
        self._sftp = None
        self._home_dir = None
        self._expect = None
        self.inventory = create_inventory('linux', server=self)
        self._rpyc_session = RPyCSession(self)

    @property
    def ip(self):
        return self._ip

    def _connect(self):
        s = paramiko.SSHClient()
        s.load_system_host_keys()
        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        s.connect(self._ip, self._port, self._user, self._password)
        self._conn = s

    def exec_return_all(self, command):
        stdout_lines = []
        stderr_lines = []
        log.debug(f"Executing command: {command}")
        stdin, stdout, stderr = self.conn.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        for line in stdout.readlines():
            stdout_lines.append(line.strip())
        for line in stderr.readlines():
            stderr_lines.append(line.strip())
        log.debug("STDOUT:\n" + "\n".join(stdout_lines))
        log.debug("STDERR:\n" + "\n".join(stderr_lines))
        stdout.close()
        stdin.close()
        stderr.close()
        return stdout_lines, stderr_lines, exit_status

    def exec(self, command, exit_on_failure=True, **kwargs):
        stdout, stderr, exit_status = self.exec_return_all(command)
        if exit_on_failure and exit_status != 0:
            log.critical(f"ERROR: Non-zero exit status for command {command}\nSTDERR: {stderr}")
            sys.exit(1)
        return stdout

    def exec_success(self, command):
        """Return True if command exits with zero. Else, return False"""
        _, _, exit_status = self.exec_return_all(command)
        if exit_status != 0:
            return False
        return True

    def copy_to(self, local_file, remote_file):
        log.debug(f"Copying local file {local_file} to remote file {remote_file}")
        self.sftp.put(local_file, remote_file)

    def run_script(self, script):
        output = []
        log.debug(f"Executing script:\n{script}")
        channel = self.conn.invoke_shell()
        stdin = channel.makefile('wb')
        stdout = channel.makefile('rb')
        stdin.write(script)
        for line in stdout.readlines():
            line = line.decode("utf-8", "ignore")
            line = ansi_escape.sub('', line)
            output.append(line)
        stdout.close()
        stdin.close()
        log.debug("STDOUT:\n" + '\n'.join(output))
        return output

    @property
    def conn(self):
        if self._conn is None:
            self._connect()
        return self._conn

    @property
    def sftp(self):
        if self._sftp is None:
            self._sftp = self.conn.open_sftp()
        return self._sftp

    @property
    def home_dir(self):
        if self._home_dir is None:
            lines = self.exec("echo $HOME")
            self._home_dir = lines[0]
        return self._home_dir

    def path_exists(self, path):
        try:
            self.sftp.stat(path)
            return True
        except IOError:
            return False
        return False

    def get_expect_session(self):
        ssh_cmd = f"ssh {self._user}@{self._ip}"
        child = pexpect.spawn(ssh_cmd, encoding='utf-8', timeout=10)
        ret = child.expect(['password: ', self.prompt])
        if ret == 0:
            child.sendline(self._password)
            child.expect(self.prompt)
        return child

    @property
    def prompt(self):
        return rf"\[{self._user}@{self.name} .*]# "

    def rsync(self, local_path, remote_path, *args):
        remote_path = f"{self._user}@{self._ip}:{remote_path}"
        rsync_command = ["rsync", "-e", "ssh -o 'StrictHostKeyChecking=no'", "-r"] + list(args) + [f"{local_path}/", remote_path]
        exec(rsync_command)

    def register_thread(self, thread):
        return self._rpyc_session.register_thread(thread)

    def import_module(self, module):
        return self._rpyc_session.import_module(module)

    @property
    def rpyc_timeout(self):
        return self._rpyc_session.timeout

    @rpyc_timeout.setter
    def rpyc_timeout(self, x):
        self._rpyc_session.timeout = x
        self._rpyc_session.connect()
        self._rpyc_session.conn._config['sync_request_timeout'] = x


def get_server(server_name):
    global servers
    if server_name not in servers:
        ip = config['servers'][server_name]['addr'].as_str()
        user = config['servers'][server_name]['user'].as_str()
        password = config['servers'][server_name]['password'].as_str()
        server = Server(server_name, ip, user, password)
        servers[server_name] = server
    return servers.get(server_name)
