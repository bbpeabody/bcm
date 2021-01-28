import logging
from time import sleep

#log = logging.getLogger(__name__.split('.')[0])
logging.raiseExceptions = False

from multiprocessing import Queue
queue = Queue()
from logging.handlers import SocketHandler, DEFAULT_TCP_LOGGING_PORT
def setup_logger(dest_ip):
    # Configure logging
    print(f"dest_ip = {dest_ip}  dest_port= {DEFAULT_TCP_LOGGING_PORT}")
    socket_handler = logging.handlers.SocketHandler(dest_ip, DEFAULT_TCP_LOGGING_PORT)
    socket_handler.setLevel(logging.DEBUG)
    # don't bother with a formatter, since a socket handler sends the event as
    # an unformatted pickle
    #root_logger = logging.getLogger()
    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)
    log.addHandler(socket_handler)
    print(log.name)
    #queue_handler = QueueHandler(queue)
    #log.addHandler(queue_handler)

    #stream_handler = logging.StreamHandler(pipe)
    #log.addHandler(stream_handler)
    #rlog.addHandler(stream_handler)
    #ch.setLevel(verbosity)
    #from server_utils.helpers import LogFormatter
    #formatter = LogFormatter(None)
    #stream_handler.setFormatter(formatter)
    #from logging.handlers import QueueListener
    #listener = QueueListener(queue, stream_handler)
    #listener.start()

def get_log():
    logs = []
    while not queue.empty():
        logs.append(queue.get())
    return logs

#from logging.handlers import QueueHandler
#from multiprocessing import Queue
#from threading import Thread
#def batch_enqueue(fast_queue, slow_queue):
#    while True:
#        batch = []
#        while not fast_queue.empty():
#            batch.append(fast_queue.get())
#        if batch:
#            slow_queue.put_nowait(batch)
#        sleep(.1)
#
#
#def batch_dequeue(fast_queue, slow_queue):
#    while True:
#        batch = slow_queue.get()
#        for obj in batch:
#            fast_queue.put(obj)
#
#class MyQueueHandler(QueueHandler):
#    def __init__(self, queue):
#        QueueHandler.__init__(self, queue)
#        self.fast_queue = Queue()
#        thread = Thread(target=batch_enqueue, args = [self.fast_queue, self.queue])
#        thread.start()
#
#    def enqueue(self, record) -> None:
#        self.fast_queue.put(record)
#
#from logging.handlers import QueueListener
#class MyQueueListener(QueueListener):
#    def __init__(self, queue, *handlers, respect_handler_level=False):
#        #self.queue = queue
#        self.handlers = handlers
#        self._thread = None
#        self.respect_handler_level = respect_handler_level
#        #QueueListener.__init__(self, queue, handlers, respect_handler_level)
#        self.records = []
#        self.queue = Queue()
#        thread = Thread(target=batch_dequeue, args = [self.queue, queue])
#        thread.start()
#
#    #def next_record(self, block):
#    #    if not self.records:
#    #        self.records = self.queue.get(block)
#    #    return self.records.pop(0)
#
#    #def dequeue(self, block):
#    #    return self.next_record(True)
