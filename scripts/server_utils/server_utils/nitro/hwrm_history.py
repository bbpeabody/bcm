import logging
from ctypes import sizeof, Structure, c_uint8, c_uint32, c_uint16
from server_utils.nitro.grc import GRCRegisterAccess
from server_utils.nitro.shmem import CfwShmemStruct
from server_utils.nitro.address import firmware_to_host_addr, PRIMATE_SHMEM_OFFSET_LOCATION
from server_utils.nitro.hwrm_msg_compact import compact
from time import sleep

log = logging.getLogger(__name__)


class HwrmHistListStruct(Structure):
    SIGNATURE = 0x12345678
    _fields_ = [
        ('signature', c_uint32),
        ('max_entries', c_uint8),
        ('current_index', c_uint8),
        ('filter_mask', c_uint16),
        ('ptr_addr', c_uint32),
        ('non_pf_chnl', c_uint32),
        ('filter_msg', c_uint32),
        ('vf_filter', c_uint32)
    ]


#class HwrmMsgCompact:
#    def __init__(self):
#        self.index = 0
#        self.max_entries = 0
#        self.request = False
#        self.bytes = bytearray()
#        self.channel = 0
#        self.time = ""


class HwrmHistEntryStruct(Structure):
    CHNL_MASK = 0xff80
    CHNL_SFT = 7
    LEN_MASK = 0x7f
    LEN_SFT = 0
    RESP_SIGNATURE = 0xbeef
    REQ_SIZE = 128
    _fields_ = [
        ('time_stamp', c_uint32),
        ('chnl_and_len', c_uint16),
        ('resp_code', c_uint16),
        ('msg', c_uint32 * int(REQ_SIZE / sizeof(c_uint32)))
    ]

    @property
    def is_request(self):
        return not self.is_response

    @property
    def is_response(self):
        if self.resp_code == self.RESP_SIGNATURE:
            return True
        return False

    @property
    def length(self):
        return int((self.chnl_and_len & self.LEN_MASK) >> self.LEN_SFT)

    @property
    def channel(self):
        return int((self.chnl_and_len & self.CHNL_MASK) >> self.CHNL_SFT)

    @property
    def time(self):
        """
        Return time in the format of #W#d##:##:##.#  - W = Week, d = day ##:##:##.! = hour:min:sec.

        timestamp has a resolution of 100msec
        """
        tmp = self.time_stamp
        week = int(tmp / (7 * 24 * 60 * 600))
        tmp %= (7 * 24 * 60 * 600)
        day = int(tmp / (24 * 60 * 600))
        tmp %= (24 * 60 * 600);
        hour = int(tmp / (60 * 600))
        tmp %= (60 * 600);
        min = int(tmp / 600)
        tmp %= 600;
        return f"{week}W{day}d{hour:02d}:{min:02d}:{tmp/10.0:04.1f}"

    @property
    def msg_as_bytes(self):
        bytes = bytearray()
        for i in range(self.REQ_SIZE):
            word_addr = int(i / 4)
            word = self.msg[word_addr]
            byte = int(i % 4)
            bytes.append(int((word >> (byte * 8)) & 0xff))
        return bytes

    def __str__(self):
        buffer = ""
        if self.is_request:
            buffer += "REQUEST"
        else:
            buffer += "RESPONSE"
        buffer += f" chan:{self.channel} length:{self.length} time:{self.time}"
        return buffer


#def compact(index, max_entries, hwrm_ctype):
#    hwrm_compact = HwrmMsgCompact()
#    hwrm_compact.max_entries = max_entries
#    hwrm_compact.index = index
#    hwrm_compact.time = hwrm_ctype.time
#    hwrm_compact.channel = hwrm_ctype.channel
#    hwrm_compact.request = hwrm_ctype.is_request
#    hwrm_compact.bytes = hwrm_ctype.msg_as_bytes
#    return hwrm_compact


class HwrmHistory:
    def __init__(self, pci_bdf, filter_mask=0xf000):
        self.grc = GRCRegisterAccess(pci_bdf)
        self._shmem_ptr = None
        self._shmem = None
        self.last_index = None
        self.filter_mask = filter_mask
        self.set_filter()

    def set_filter(self):
        self.grc.write_bytes(self.hwrm_history_offset + HwrmHistListStruct.filter_mask.offset,
                             bytes([self.filter_mask >> 8, self.filter_mask & 0xff]))

    @property
    def shmem_ptr_ptr(self):
        addr = firmware_to_host_addr(PRIMATE_SHMEM_OFFSET_LOCATION)
        log.debug(f"does this work?")
        log.debug(f"shmem ptr addr = 0x{addr:08x}.")
        return addr

    @property
    def shmem_ptr(self):
        if not self._shmem_ptr:
            self._shmem_ptr = firmware_to_host_addr(self.grc.read_word(self.shmem_ptr_ptr))
            log.debug(f"shmem ptr = 0x{self._shmem_ptr:08x}.")
        return self._shmem_ptr

    @property
    def shmem(self):
        if not self._shmem:
            while True:
                bytes = self.grc.read_bytes(self.shmem_ptr, sizeof(CfwShmemStruct))
                shmem = CfwShmemStruct.from_buffer(bytes)
                log.debug(f"shmem signature = 0x{shmem.signature:08x}.")
                if shmem.signature != shmem.SIGNATURE:
                    log.warning('Shared memory struct, CfwShmemStruct, signature is invalid. Expected '
                                f'0x{shmem.SIGNATURE:08x}. Received 0x{shmem.signature:08x}.')
                    self._shmem_ptr = None
                else:
                    self._shmem = shmem
                    break
        return self._shmem

    @property
    def hwrm_history_offset(self):
        return firmware_to_host_addr(self.shmem.hwrm_history_offset)

    @property
    def hwrm_history_list(self):
        while True:
            self.set_filter()
            bytes = self.grc.read_bytes(self.hwrm_history_offset, sizeof(HwrmHistListStruct))
            hwrm_hist_list = HwrmHistListStruct.from_buffer(bytes)
            log.debug(f"hwrm_hist_list signature = 0x{hwrm_hist_list.signature:08x}.")
            log.debug(f"HWRM filter = 0x{hwrm_hist_list.filter_mask:04x}.")
            if hwrm_hist_list.signature != hwrm_hist_list.SIGNATURE:
                log.warning("HWRM history list signature check failed. Resetting history.")
                self._shmem = None
                self.last_index = None
                sleep(.1)
            else:
                break
        return hwrm_hist_list

    def get_newest_index(self, bytes, max_entries):
        """Return the index for the newest entry"""
        max_timestamp = -1
        newest_index = -1
        for i in range(max_entries):
            hwrm_entry = HwrmHistEntryStruct.from_buffer(bytes, sizeof(HwrmHistEntryStruct) * i)
            if hwrm_entry.time_stamp >= max_timestamp:
                max_timestamp = hwrm_entry.time_stamp
                newest_index = i
        return newest_index

    def get_history(self, queue, follow):
        while True:
            hwrm_history_list = self.hwrm_history_list
            ptr_addr = firmware_to_host_addr(hwrm_history_list.ptr_addr)
            max_entries = hwrm_history_list.max_entries
            bytes = self.grc.read_bytes(ptr_addr, sizeof(HwrmHistEntryStruct) * max_entries)
            newest_index = self.get_newest_index(bytes, max_entries)
            if newest_index < 0:
                sleep(.1)
                continue
            elif self.last_index is None:
                self.last_index = newest_index
            elif not follow:
                break
            elif newest_index == self.last_index:
                sleep(.1)
                continue
            buffer = []
            if newest_index > self.last_index:
                for i in range(self.last_index + 1, newest_index + 1):
                    hwrm_entry = HwrmHistEntryStruct.from_buffer(bytes, sizeof(HwrmHistEntryStruct) * i)
                    buffer.append(compact(i, max_entries, hwrm_entry))
            else:
                # Circular buffer has rolled over
                if self.last_index + 1 < max_entries:
                    for i in range(self.last_index + 1, max_entries):
                        hwrm_entry = HwrmHistEntryStruct.from_buffer(bytes, sizeof(HwrmHistEntryStruct) * i)
                        buffer.append(compact(i, max_entries, hwrm_entry))
                for i in range(0, newest_index + 1):
                    hwrm_entry = HwrmHistEntryStruct.from_buffer(bytes, sizeof(HwrmHistEntryStruct) * i)
                    buffer.append(compact(i, max_entries, hwrm_entry))
            queue.put(buffer)
            self.last_index = newest_index