import socket
import sys
import time

from tracker.chord import getShaRepr
from tracker.tracker_server import TrackerServer

if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    tracker = TrackerServer(ip, (ip, 8000))
    tracker.loop()
    while True:
        print(tracker.get_all())
        time.sleep(5)
