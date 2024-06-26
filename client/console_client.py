import hashlib
import os
import socket
import urllib.parse

from bcoding import bdecode, bencode
from torrent import Torrent
from piece_manager import PieceManager


class ConsoleClient:
    def __init__(self) -> None:
        self.torrents: list[Torrent] = []
        self.piece_manager: list[PieceManager] = []
        self.paths = {}

    def run_client(self):
        while True:
            for pm in self.piece_manager:
                if not pm.have_all_pieces():
                    # Make the download
                    for p in pm.pieces:
                        pass

    def add_torrent(self, torrent_file: str):
        torrent = Torrent().load_from_path(torrent_file)
        self.torrents.append(torrent)
        self.piece_manager.append(PieceManager(torrent))

    def get_peers(self, server_addr, info_hash, peer_id, left):
        host: str = server_addr[0]
        port: int = server_addr[1]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))

            info_h = urllib.parse.quote(info_hash.hex())
            info_h = f"info_hash={info_h}"
            peer_i = f"peer_id={peer_id}"
            uploaded = "uploaded=0"
            downloaded = "downloaded=0"
            port_param = f"port={port}"
            l = f"left={left}"
            s.sendall(
                f"GET / HTTP/1.1\r\nHost: {host}/?{info_h}&{peer_i}&{uploaded}&{downloaded}&{port_param}&{l}\r\n\r\n".encode()
            )

            response = s.recv(1024)
            response = response.decode()
            response = response.split("\r\n")

            if response[0] == "HTTP/1.1 200 OK":
                data = bdecode(response[3][2:-1].encode())
                return data
            else:
                print("Torrent not found in tracker")

    def create_torrent(self, server_addr, path, annouce_list, name):
        torrent_file = Torrent().create_torrent(path, annouce_list, name)

        host = server_addr[0]
        port = server_addr[1]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, 8000))

            info_hash = urllib.parse.quote(
                hashlib.sha1(bencode(torrent_file["info"])).digest().hex()
            )
            info_hash_param = f"info_hash={info_hash}"
            peer_id = f"peer_id={Torrent().generate_peer_id()}"
            uploaded = "uploaded=0"
            downloaded = "downloaded=0"
            port_param = f"port={port}"
            left = f"left=0"
            s.sendall(
                f"GET / HTTP/1.1\r\nHost: {host}/?{info_hash_param}&{peer_id}&{uploaded}&{downloaded}&{port_param}&{left}\r\n\r\n".encode()
            )

            response = s.recv(1024).decode()
            response = response.split("\r\n")

            print(response[0])
            self.paths[hashlib.sha1(bencode(torrent_file["info"])).digest()] = (
                os.path.abspath(path)
            )


def load_torrent():
    return Torrent().load_from_path("torrents/razdacha-ne-suschestvuet.torrent")


if __name__ == "__main__":
    ip = "127.0.0.1"
    port = 8000
    tracker = ConsoleClient()
