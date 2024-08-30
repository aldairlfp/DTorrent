import socket

from tracker.chord import getShaRepr
from tracker.tracker_server import TrackerServer
import logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = "%H:%M:%S"

    logging.basicConfig(
        filename= f'logs_for_DTorrent.log',
        format= log_format,
        datefmt= date_format,
        filemode= 'w')
    
    logger.setLevel(logging.DEBUG)

    ip = socket.gethostbyname(socket.gethostname())
    tracker = TrackerServer((ip, 8000))

    dhash = getShaRepr(ip)
    # tracker.add_peer(1, 1, 1, dhash)
    tracker.loop()
    