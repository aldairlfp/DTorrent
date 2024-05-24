import socket
import sys

from tracker.chord import getShaRepr
from tracker.tracker_server import TrackerServer

if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    tracker = TrackerServer(ip, (ip, 8080))
    if len(sys.argv) >= 2:
        other_ip = sys.argv[1]
        tracker.join(other_ip, other_ip, tracker.node.port)

    tracker.run()
