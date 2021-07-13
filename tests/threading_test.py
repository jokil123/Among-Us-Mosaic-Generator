import concurrent.futures
from concurrent.futures import thread
import time


def thread_function(name):
    print(str(name) + " starting")
    time.sleep(2)
    print(str(name) + " finished")


with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    executor.map(thread_function, range(3))
