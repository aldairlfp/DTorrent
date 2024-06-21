import socket
import hashlib
import threading
import time
import urllib.parse

from bcoding import bencode, bdecode
from tracker.chord import ChordNode, ChordNodeReference, getShaRepr


class TrackerServer:
    def __init__(self, id: int, local_addr=("127.0.0.1", 8080)) -> None:
        self.host = local_addr[0]
        self.port = local_addr[1]
        self.node: ChordNode = ChordNode(id, self.host)
        self.info_hashs = {}
        self.tracker_id = 0
        threading.Thread(target=self.run, daemon=True).start()

    def join(self, node_id, node_ip, node_port):
        self.node.join(ChordNodeReference(node_id, node_ip, node_port))

    def add_torrent(self, torrent):
        self.torrents.append(torrent)

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(10)
            print(f"Listening in {self.host}:{self.port}")
            while True:
                conn, addr = s.accept()

                request_data = b""
                while True:
                    part = conn.recv(4096)
                    request_data += part
                    if len(part) < 4096:
                        break

                data_resp = None

                request_data = request_data.decode().split("\r\n")

                if request_data[0] == "GET / HTTP/1.1" and "?" in request_data[1]:
                    params = request_data[1].split("?")[1].split("&")

                    peer_id = params[1].split("=")[1]
                    uploaded = params[2].split("=")[1]
                    downloaded = params[3].split("=")[1]
                    port = params[4].split("=")[1]
                    left = params[5].split("=")[1]

                    info_hash = params[0].split("=")[1]
                    info_hash = urllib.parse.unquote(info_hash)
                    info_hash = int(info_hash, 16)

                    data_resp = {}
                    data_resp["interval"] = 5
                    data_resp["peers"] = []

                    if downloaded == "0" and left != "0" and self.find(info_hash):
                        data_resp = self.get_peers(info_hash)
                    elif downloaded == "0" and left == "0" and not self.find(info_hash):
                        self.add_peer(peer_id, addr[0], port, info_hash)

                    response = f"HTTP/1.1 200 OK\r\nContent-Length: {len(data_resp)}\r\n\r\n{bencode(data_resp)}"

                    conn.sendall(response.encode())

                conn.close()

    def find(self, info_hash):
        return self.node.find(info_hash)

    def get_peers(self, info_hash):
        return self.node.find_succ(info_hash).get_value(info_hash)

    def add_peer(self, peer_id, peer_ip, peer_port, info_hash):
        self.node.add_value(info_hash, [peer_id, peer_ip, peer_port])

    def peer_has_info(self, peer_id, info_hash):
        if info_hash in self.info_hashs:
            for peer in self.info_hashs[info_hash]:
                if peer[0] == peer_id:
                    return True
        return False

    def get_all(self):
        return self.node.get_all()

    @property
    def id(self):
        return self.node.id
