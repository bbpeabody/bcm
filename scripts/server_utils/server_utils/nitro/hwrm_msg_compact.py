"""Compact HWRM message that will be used to pass HWRM messages from the server back to the client via a queue."""


class HwrmMsgCompact:
    def __init__(self):
        self.index = 0
        self.max_entries = 0
        self.request = False
        self.bytes = bytearray()
        self.channel = 0
        self.time = ""


def compact(index, max_entries, hwrm_ctype):
    hwrm_compact = HwrmMsgCompact()
    hwrm_compact.max_entries = max_entries
    hwrm_compact.index = index
    hwrm_compact.time = hwrm_ctype.time
    hwrm_compact.channel = hwrm_ctype.channel
    hwrm_compact.request = hwrm_ctype.is_request
    hwrm_compact.bytes = hwrm_ctype.msg_as_bytes
    return hwrm_compact
