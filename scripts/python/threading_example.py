import threading
from aucommon.host import Host
from datetime import datetime

sut = Host("10.27.215.84", "sut", "root", "brcm", "linux")
sut.delete_module('sut_import')
sut.add_module('sut_import', 'sut_import.py')
sut_import = sut.import_common('sut_import')
#cmd_outputs = sut_import.run_parallel_commands(['du -sh /home', 'du -sh /etc'])
start_time = datetime.now()
cmd_outputs = sut_import.run_parallel_commands(['sleep 5 && du -sh /home', 'sleep 5 && du -sh /etc'])
elapsed_time = datetime.now() - start_time
print(f"elapsed time = {elapsed_time}")
print(cmd_outputs)
