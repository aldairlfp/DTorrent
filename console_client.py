import hashlib
import os
import socket
import urllib.parse

from bcoding import bdecode, bencode
from client.torrent import Torrent
from client.piece_manager import PieceManager


class ConsoleClient:
    def __init__(self) -> None:
        self.torrents: list[Torrent] = []
        self.piece_manager: list[PieceManager] = []
        self.paths = {}

    def run_client(self):
        while True:
            # Select a piece manager to download a piece
            # This will be for multiple downloads
            for piecem in self.piece_manager:
                if not piecem.have_all_pieces():
                    # TODO: Chooke Algorith

                    # Take a piece to try downloading
                    for piece in piecem.pieces:
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
                f"GET /?{info_h}&{peer_i}&{uploaded}&{downloaded}&{port_param}&{l} HTTP/1.1\r\nHost: {host}/\r\n\r\n".encode()
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
                f"GET /?{info_hash_param}&{peer_id}&{uploaded}&{downloaded}&{port_param}&{left} HTTP/1.1\r\nHost: {host}/\r\n\r\n".encode()
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
    # ip = "127.0.0.1"
    ip = "172.17.0.2"
    ip = "192.168.9.229"
    ip = "10.2.0.2"
    port = 8000
    tracker = ConsoleClient()
    # tracker.connect_tracker((ip, 8080))
    # tracker.create_torrent(
    #     (ip, 8080),
    #     "C:\\Users\\aldai\\yugi\\Edison Machina",
    #     [f"http://{ip}:8080"],
    #     "WOW335 data",
    # )
    tracker.create_torrent(
        (ip, 8002),
        "torrents",
        [f"http://{ip}:{port}"],
        "torrents",
    )
    torrent = load_torrent()

    # piece_manager = PieceManager(torrent)
    # print(piece_manager)
    # tracker.torrents.append(torrent)
    # peers = tracker.get_peers(
    #     (ip, 8000),
    #     torrent.info_hash,
    #     torrent.peer_id,
    #     torrent.selected_total_length,
    # )

    # threading.Thread(target=download_piece, args=(peers[0][1], peers[0][2])).start()

    # send_piece(tracker, torrent, peers[0][1], peers[0][2], torrent.pieces[0]["path"])
