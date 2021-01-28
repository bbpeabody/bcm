import logging
import re
import mmap
from typing import List
from ctypes import sizeof
from server_utils.nitro.pci_bar0 import NitroPFBar0Struct
from threading import Lock
#from posix_ipc import Semaphore, O_CREAT, BusyError

log = logging.getLogger(__name__)

# Create a lock for GRC register access.  Multiple threads may access the same window on the PCI BAR. This lock will
# synchronize access to the window.
grc_lock = Lock()

def validate_bdf(pci_bdf):
    """Given a PCI BDF, return the linux path formatted BDF"""
    pci_bdf_parts = re.split(f':|\.', pci_bdf)
    if len(pci_bdf_parts) == 3:
        # Insert default domain of zero if not included in BDF (Bus, Device, Function)
        pci_bdf_parts.insert(0, "0")
    if len(pci_bdf_parts) != 4:
        raise ValueError(f"Improperly formatted PCI BDF {pci_bdf}. Example: 65:00.0 or 0000:65:00.0")
    # Format BDF in the style of linux /sys/bus/pci/devices
    domain = int(pci_bdf_parts[0], 16)
    bus = int(pci_bdf_parts[1], 16)
    device = int(pci_bdf_parts[2], 16)
    function = int(pci_bdf_parts[3], 16)
    return f"{domain:04x}:{bus:02x}:{device:02x}.{function:01x}".lower()


class GRCRegisterAccess:
    WINDOW = 14
    SEM_NAME = "SERVER_UTILS_SEM"
    SEM_TIMEOUT = 10

    def __init__(self, pci_bdf):
        self.pci_bdf = pci_bdf
        pci_bdf = validate_bdf(pci_bdf)
        bar_file = open('/sys/bus/pci/devices/' + pci_bdf + '/resource0', 'r+b')
        try:
            bar_map = mmap.mmap(bar_file.fileno(), 0, )#flags=mmap.MAP_PRIVATE)
        except OSError as err:
            log.critical("Unable to map the PCI bar registers. Try using option --driver-unload. This will unload the"
                         " driver and then attempt to map the PCI bar.  You can then reload the driver.")
            raise err
        self.bar = NitroPFBar0Struct.from_buffer(bar_map)
        try:
            self.window = self.WINDOW
        except IndexError:
            raise IndexError("Cannot create GRCRegisterAccess.  Out of windows.")
        self.window_size = int(sizeof(self.bar.window[self.window]))
        self.window_offset_mask = self.window_size - 1
        self.window_base_mask = int((1 << 32) - self.window_size)
        #self.sem = Semaphore(self.SEM_NAME, flags=O_CREAT, initial_value=1)

    #def _sem_wait(self):
    #    try:
    #        self.sem.acquire(timeout=self.SEM_TIMEOUT)
    #    except BusyError:
    #        log.critical(f"Waited {self.SEM_TIMEOUT} for POSIX semaphore.")

    #def _sem_post(self):
    #    self.sem.release()

    def set_window_base(self, window: int, base: int) -> int:
        self.bar.base[window] = int(base & self.window_base_mask)
        return int(base & self.window_offset_mask)

    def read_words(self, addr: int, length: int = 1) -> List[int]:
        """Read 4-byte word from GRC register space."""
        if addr & 0x3:
            raise ValueError(f"Address 0x{addr:08x} must be on a 4-byte boundary")
        words = []
        grc_lock.acquire()
        #self._sem_wait()
        for addr in range(addr, addr + (length * 4), 4):
            index = int(self.set_window_base(self.window, addr) / 4)
            words.append(self.bar.window[self.window][index])
        #self._sem_post()
        grc_lock.release()
        return words

    def read_word(self, addr: int) -> int:
        return self.read_words(addr, 1)[0]

    def read_bytes(self, addr: int, num_bytes: int) -> bytearray:
        bytes = bytearray()
        end_addr = int(addr + num_bytes - 1)
        #self._sem_wait()
        grc_lock.acquire()
        offset = int(self.set_window_base(self.window, addr))
        index = int(offset / 4)
        word = self.bar.window[self.window][index]
        while addr <= end_addr:
            byte_addr = addr & 0x3
            bytes.append(int((word >> (byte_addr * 8)) & 0xff))
            addr += 1
            offset += 1
            if offset >= self.window_size:
                offset = self.set_window_base(self.window, addr)
            if not offset % 4:
                index = int(offset / 4)
                word = self.bar.window[self.window][index]
        #self._sem_post()
        grc_lock.release()
        return bytes

    def write_bytes(self, addr: int, data: bytes):
        data = bytearray(data)
        end_addr = int(addr + len(data) - 1)
        grc_lock.acquire()
        offset = int(self.set_window_base(self.window, addr))
        index = int(offset / 4)
        word = self.bar.window[self.window][index]
        while addr <= end_addr:
            byte_addr = addr & 0x3
            if byte_addr == 0:
                index = int(offset / 4)
                word = self.bar.window[self.window][index]
            byte_mask = 0xffffffff - (0xff << (byte_addr * 8))
            word &= byte_mask
            word |= data.pop() << (byte_addr * 8)
            if byte_addr == 3 or addr == end_addr:
                index = int(offset / 4)
                self.bar.window[self.window][index] = word
            addr += 1
            offset += 1
            if offset >= self.window_size:
                offset = self.set_window_base(self.window, addr)
        grc_lock.release()
