import logging
import os
import sys

log = logging.getLogger(__name__)


class Driver:
    def __init__(self, sit, server):
        self.sit = sit
        self.server = server
        self._path = None

    @property
    def path(self):
        if self._path is None:
            lines = self.server.exec(f"find {self.sit.path} -maxdepth 1 -type d")
            for line in lines:
                dir_name = os.path.basename(line)
                if dir_name.startswith("bnxt_en"):
                    self._path = os.path.join(self.sit.path, line, "bnxt_en.ko")
            if self._path is None or not self.server.path_exists(self._path):
                raise FileNotFoundError(f"Cannot find bnxt_en directory on server {self.server.name} at SIT path"
                                        f" {self.sit.path}")
        return self._path

    def load(self):
        if not self.is_loaded():
            self.server.exec("modprobe devlink", False)
            self.server.exec(f"insmod {self.path}")
            #self.server.exec("modprobe bnxt_re", False)
            #self.server.exec("modprobe bnxt_re", False)

    @property
    def loaded_modules(self):
        lines = self.server.exec("lsmod")
        return set([line.split()[0] for line in lines])

    @property
    def builtin_modules(self):
        lines = self.server.exec("cat /lib/modules/$(uname -r)/modules.builtin")
        return set([line.split('/')[-1].split('.')[0] for line in lines])

    @property
    def all_modules(self):
        return self.loaded_modules.union(self.builtin_modules)

    def remove_module(self, module):
        command = f"rmmod {module}"
        stdout, stderr, exit_status = self.server.exec_return_all(command)
        if exit_status != 0:
            if "is builtin" in "".join(stderr):
                log.warning(f"Unable to unload driver {module} because it is built-in to the kernel.")
                raise ValueError()
            else:
                log.critical(f"ERROR: Non-zero exit status for {command}")
                log.critical(f"STDERR: {''.join(stderr)}")
                sys.exit(1)

    def unload(self):
        all_modules = self.all_modules
        unload_modules = [
            "bnxt_re",
            "bnxt_en",
            "bnxtmtdrv",
            "devlink"
        ]
        for module in unload_modules:
            if module in all_modules:
                try:
                    self.remove_module(module)
                except ValueError:
                    return False
        return True

    def is_loaded(self):
        if "bnxt_en" in self.all_modules:
            return True
        return False
