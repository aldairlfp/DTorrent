import socket

from tracker.chord import getShaRepr
from tracker.tracker_server import TrackerServer

if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    tracker = TrackerServer((ip, 8000))
    tracker.loop()
