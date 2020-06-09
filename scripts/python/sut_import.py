import threading
from aucommon.helpers.process_handler import run

class threadedCommand (threading.Thread):

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.output = None

    def run(self):
        self.output = run(self.command, shell=True)

def run_parallel_commands(cmds):
    threads = []
    for cmd in cmds:
        thread = threadedCommand(cmd)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    return [thread.output for thread in threads]
