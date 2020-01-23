#!/usr/bin/env python

from multiprocessing.dummy import Pool 
#you should install gevent.
from gevent import Timeout
from gevent import monkey
monkey.patch_all()
import time

def worker(sleep_time):
    try:

        seconds = 5  # max time the worker may run
        timeout = Timeout(seconds)
        timeout.start()
        time.sleep(sleep_time)
        print("%s is a early bird" % sleep_time)
    except Timeout:
        print("%s is late(time out)" % sleep_time)

pool = Pool(4)

pool.map(worker, range(10))
