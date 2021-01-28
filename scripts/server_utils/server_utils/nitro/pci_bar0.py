from ctypes import Structure, c_uint


class CommChannelStruct(Structure):
    """
    HWRM Communications Channel
    512 bytes
    """
    _fields_ = [
        ('comm', c_uint * 32),
        ('reserved0', c_uint * 32),
        ('trigger', c_uint),
        ('reserved1', c_uint * 63)
    ]


class NitroPFBar0Struct(Structure):
    """
    Nitro PF Bar 0/1 Space
    64 kbytes
    """
    _fields_ = [
        # This is the first host communication area in the function. This is valid for both PF and VF functions. This is
        # normally used for HWRM communications used to initialize and configure the L2 features of the NIC.
        ('comm0', CommChannelStruct),       # 0x0000    HWRM Comm Channel 0

        # This is the second host communication area in the function. This is valid for the PF functions only.
        ('comm1', CommChannelStruct),       # 0x0200    HWRM Comm Channel 1

        # GRC(register) access is granted into the chip as needed for each function.This is done by exposing a small
        # number of 4KB windows into the large internal register space. These are the base GRC addresses for each of the
        # 15 PF GRC windows supported in the PF BAR. These values must be programmed before the GRC window is accessed.
        # The offset is byte oriented which means if you put the byte address of the register desired on the GRC, the
        # correct 4KB page will be selected for the corresponding window. This means that bits 31 down to 12 are
        # effective in controlling the window.
        ('base', c_uint * 15),              # 0x0400    Window base registers
        ('reserved0', c_uint * 49),

        # This area provides FW status RO status. The value read from the first 32B of this area is check value that can
        # be used by the driver to validate that the FW is properly authenticated.
        # The value read from the remaining 32B is the dynamic firmware status.
        ('status_immutable', c_uint * 8),   # 0x0500    Status registers
        ('fw_status', c_uint),
        ('status', c_uint * 7),
        ('reserved1', c_uint * 15),

        # This register provides indication if the FW has halted due to un-handled watch dog timeout or bus error
        # (ECC error). If this value is non-zero it indicates that the FW has halted.
        ('fw_halt', c_uint),                # 0x057c    FW Halt
        ('reserved2', c_uint * 32),

        ('comm2', CommChannelStruct),       # 0x0600    HWRM Comm Channel 2
        ('comm3', CommChannelStruct),       # 0x0800    HWRM Comm Channel 3
        ('comm4', CommChannelStruct),       # 0x0A00    HWRM Comm Channel 4
        ('comm5', CommChannelStruct),       # 0x0C00    HWRM Comm Channel 5
        ('reserved3', c_uint * 128),

        # This area is a window into the GRC space of the chip. The address offset is controlled by the corresponding
        # offset in the "base" area. Access to actual registers must be granted by the firmware using the GRC access
        # control mechanism.
        ('window', (c_uint * 1024) * 15)    # 0x1000    Windows 1 to 15 (60K)
    ]
