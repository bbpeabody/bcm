"""
Define static addresses used by Nitro IP. These are taken directly from #defines chimp_shmem.h
"""
PRIMATE_SRAM_SIZE                       = 0x00400000      # 4Mbytes
PRIMATE_VIEW_SRAM_BASE                  = 0x20000000
PRIMATE_USHI_SIG_LOCATION               = PRIMATE_VIEW_SRAM_BASE + 0x30
PRIMATE_USHI_PTR_LOCATIION              = PRIMATE_VIEW_SRAM_BASE + 0x34
PRIMATE_SRT_CPU_SHMEM_OFFSET_LOCATION   = PRIMATE_VIEW_SRAM_BASE + 0x38
PRIMATE_SHMEM_OFFSET_LOCATION           = PRIMATE_VIEW_SRAM_BASE + 0x3C

def firmware_to_host_addr(firmware_addr: int) -> int:
    """Return the equivalent host address given the firmware address"""
    return int(firmware_addr ^ 0x80000000)
