import logging
from ctypes import sizeof, Structure, c_uint8, c_uint32, POINTER, cast
from server_utils.nitro.grc import GRCRegisterAccess
from server_utils.nitro.shmem import CfwShmemStruct
from server_utils.nitro.address import firmware_to_host_addr, PRIMATE_SHMEM_OFFSET_LOCATION
from time import sleep

log = logging.getLogger(__name__)

DEBUG_TRACE_SIZE = 0x8000


class TraceHdrStruct(Structure):
    SIGNATURE = 0xabcd1234
    _fields_ = [
        ('signature', c_uint32),
        ('trace_idx', c_uint32)
    ]


class TraceBufStruct(Structure):
    _fields_ = [
        #('trace_hdr', TraceHdrStruct),
        ('trace_buf', c_uint8 * (DEBUG_TRACE_SIZE - sizeof(TraceHdrStruct)))
    ]


class Trace:
    def __init__(self, pci_bdf):
        self.grc = GRCRegisterAccess(pci_bdf)
        self._shmem_ptr = None
        self._shmem = None
        self.last_trace_idx = None

    @property
    def shmem_ptr_ptr(self):
        addr = firmware_to_host_addr(PRIMATE_SHMEM_OFFSET_LOCATION)
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
            bytes = self.grc.read_bytes(self.shmem_ptr, sizeof(CfwShmemStruct))
            shmem = CfwShmemStruct.from_buffer(bytes)
            if shmem.signature != shmem.SIGNATURE:
                raise ValueError('Shared memory struct, CfwShmemStruct, signature is invalid. Expected '
                                 f'0x{shmem.SIGNATURE:08x}. Received 0x{shmem.signature:08x}.')
            log.debug(f"shmem signature = 0x{shmem.signature:08x}.")
            self._shmem = shmem
        return self._shmem

    @property
    def trace_hdr_offset(self):
        return firmware_to_host_addr(self.shmem.trace_buf_offset)

    @property
    def trace_buf_offset(self):
        return int(self.trace_hdr_offset + sizeof(TraceHdrStruct))

    @property
    def trace_buf_size(self):
        return sizeof(TraceBufStruct)

    @property
    def trace_hdr(self):
        while True:
            bytes = self.grc.read_bytes(self.trace_hdr_offset, sizeof(TraceHdrStruct))
            trace_hdr = TraceHdrStruct.from_buffer(bytes)
            if trace_hdr.signature != trace_hdr.SIGNATURE:
                log.warning("Trace header signature check failed.")
            else:
                break
            log.debug(f"trace_hdr signature = 0x{trace_hdr.signature:08x}.")
        return trace_hdr

    def get_trace_buf(self, offset=None, size=None):
        if offset is None and size is None:
            # By default, read the entire buffer
            addr = self.trace_buf_offset
            size = sizeof(TraceBufStruct)
        else:
            addr = self.trace_buf_offset + offset
        bytes = self.grc.read_bytes(addr, size)
        return bytes

    def trace(self, queue, follow):
        while True:
            trace_idx = firmware_to_host_addr(self.trace_hdr.trace_idx)
            trace_offset = trace_idx - self.trace_buf_offset
            if self.last_trace_idx is None:
                last_trace_offset = trace_offset
            elif trace_idx != self.last_trace_idx:
                last_trace_offset = self.last_trace_idx - self.trace_buf_offset
            else:
                sleep(.1)
                continue
            buffer = ""
            if trace_offset > last_trace_offset:
                trace_buf = self.get_trace_buf(last_trace_offset, trace_offset - last_trace_offset)
                for byte in trace_buf:
                    buffer += chr(byte)
            else:
                # Circular buffer has rolled over
                trace_buf = self.get_trace_buf(last_trace_offset, self.trace_buf_size - last_trace_offset)
                for byte in trace_buf:
                    buffer += chr(byte)
                trace_buf = self.get_trace_buf(0, trace_offset)
                for byte in trace_buf:
                    buffer += chr(byte)
            try:
                queue.put(buffer)
            except EOFError:
                # Not sure why, but sometimes get an EOFError exception. Doesn't seem to cause any harm, so ignoring.
                pass
            if not follow:
                break
            self.last_trace_idx = trace_idx