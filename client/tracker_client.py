import socket
import sys

from torrent import Torrent


class TrackerClient:
    def __init__(self) -> None:
        self.torrents: list[Torrent] = []

    def connect_tracker(self, server_addr=("127.0.0.1", 8080)):
        host: str = server_addr[0]
        port: int = server_addr[1]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            self.torrents += [self.load_torrent()]
            current = self.torrents[len(self.torrents) - 1]

            info_hash = f"info_hash: {current.info_hash}"
            peer_id = f"peer_id: {current.peer_id}"
            uploaded = "uploaded: 0"
            downloaded = "downloaded: 0"
            port = f"port: {port}"
            left = f"left: {current.selected_total_length}"
            s.sendall(
                f"GET / HTTP/1.1\r\nHost: {host}/?{info_hash}&{peer_id}&{uploaded}&{downloaded}&{port}&{left}\r\n\r\n".encode()
            )
            data = s.recv(1024).decode()
            print(data)

    def load_torrent(self):
        return Torrent().load_from_path("torrents/razdacha-ne-suschestvuet.torrent")


if __name__ == "__main__":
    ip = sys.argv[1]
    tracker = TrackerClient()
    tracker.connect_tracker((ip, 8080))
