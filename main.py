import socket

from tracker.chord import getShaRepr
from tracker.tracker_server import TrackerServer
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename='DTorrent.log', encoding='utf-8', level=logging.DEBUG)

if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    tracker = TrackerServer((ip, 8000))
    tracker.loop()
