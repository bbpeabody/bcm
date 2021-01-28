from ctypes import Structure, c_int8, c_uint8, c_uint16, c_uint32


class CfwShmemStruct(Structure):
    SIGNATURE = 0xbeef1234
    _fields_ = [
        ('signature', c_uint32),
        ('size', c_uint16),
        ('rsvd1', c_uint16),
        ('trace_buf_offset', c_uint32),
        ('fw_version', c_uint32),
        ('bc_gloval_data_offset', c_uint32),
        ('rsvd2', c_uint16),
        ('flags', c_uint8),
        ('utc_offset', c_int8),
        ('hwrm_version', c_uint32),
        ('asic_version', c_uint32),
        ('trace_buf_size', c_uint16),
        ('ext_bss_size', c_uint16),
        ('fw_heartbeat', c_uint32),
        ('hwrm_history_offset', c_uint32)
    ]