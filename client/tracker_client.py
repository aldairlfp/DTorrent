import hashlib
import socket
import sys

from bcoding import bdecode, bencode
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

            info_hash = f"info_hash={current.info_hash}"
            peer_id = f"peer_id={current.peer_id}"
            uploaded = "uploaded=0"
            downloaded = "downloaded=0"
            port_param = f"port={port}"
            left = f"left={current.selected_total_length}"
            s.sendall(
                f"GET / HTTP/1.1\r\nHost: {host}/?{info_hash}&{peer_id}&{uploaded}&{downloaded}&{port_param}&{left}\r\n\r\n".encode()
            )

            response = s.recv(1024)
            response = response.decode()
            response = response.split("\r\n")

            if response[0] == "HTTP/1.1 200 OK":
                data = bdecode(response[3][2:-1].encode())
                print(data)
            else:
                print("Torrent not found in tracker")

    def create_torrent(self, server_addr, path, annouce_list, name):
        torrent_file = Torrent().create_torrent(path, annouce_list, name)

        host = server_addr[0]
        port = server_addr[1]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))

            info_hash = (
                f"info_hash={hashlib.sha1(bencode(torrent_file['info'])).digest()}"
            )
            peer_id = f"peer_id={Torrent().generate_peer_id()}"
            uploaded = "uploaded=0"
            downloaded = "downloaded=0"
            port_param = f"port={port}"
            left = f"left=0"
            s.sendall(
                f"GET / HTTP/1.1\r\nHost: {host}/?{info_hash}&{peer_id}&{uploaded}&{downloaded}&{port_param}&{left}\r\n\r\n".encode()
            )

            response = s.recv(1024).decode()
            response = response.split("\r\n")

            print(response[0])


if __name__ == "__main__":
    # ip = sys.argv[1]
    ip = "10.2.0.2"
    # ip = "172.17.0.2"
    tracker = TrackerClient()
    tracker.connect_tracker((ip, 8080))
    tracker.create_torrent(
        (ip, 8080),
        "C:\\Users\\aldai\\yugi\\Edison Machina",
        [f"http://{ip}:8080"],
        "WOW335 data",
    )
