import multiprocessing
import socket
import hashlib
import threading
import time
import urllib.parse
import json

from http.server import BaseHTTPRequestHandler, HTTPServer
from bcoding import bencode, bdecode
from tracker.chord import ChordNodeReference, getShaRepr, ChordNode

import tracker.leader_election as leader_election

PORT = "8000"
BCASTPORT = "8004"


def bcast_call(port, msg):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(msg.encode(), ("255.255.255.255", port))


class TrackerServerHandlerRequests(BaseHTTPRequestHandler):
    def do_GET(self):
        params = self.path.split("?")[1].split("&")

        peer_id = params[1].split("=")[1]
        uploaded = params[2].split("=")[1]
        downloaded = params[3].split("=")[1]
        port = params[4].split("=")[1]
        left = params[5].split("=")[1]

        info_hash = params[0].split("=")[1]
        info_hash = urllib.parse.unquote(info_hash)
        info_hash = int(info_hash, 16)

        data_resp = {}
        data_resp["interval"] = 10
        data_resp["peers"] = []

        if (
            downloaded == "0"
            and left != "0"
            and self.server.tracker_server.find(info_hash)
        ):
            data_resp = self.server.tracker_server.get_peers(info_hash)
        elif (
            downloaded == "0"
            and left == "0"
            and not self.server.tracker_server.find(info_hash)
        ):
            self.server.tracker_server.add_peer(
                peer_id, self.client_address[0], port, info_hash
            )

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        self.wfile.write(json.dumps(data_resp).encode())


class TrackerServer:
    def __init__(self, local_addr=("127.0.0.1", PORT)) -> None:
        self.host = local_addr[0]
        self.port = local_addr[1]
        self.bcast_port = BCASTPORT
        self.node: ChordNode = ChordNode(self.host)
        self.elector: leader_election.BroadcastPowElector = (
            leader_election.BroadcastPowElector(leader_election.PORT)
        )

        self.httpd = HTTPServer((self.host, self.port), TrackerServerHandlerRequests)
        self.httpd.tracker_server = self

        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def join(self, node_id, node_ip, node_port=8001):
        self.node.join(ChordNodeReference(node_id, node_ip, node_port))

    def add_torrent(self, torrent):
        self.torrents.append(torrent)

    def loop(self):
        t1 = threading.Thread(target=self.server_thread)  # TODO:
        # t1.start()

        # t2 = threading.Thread(target=self.get_requests)
        # t2.start()

        t3 = threading.Thread(target=self.elector.loop)
        # t3.start()

        try:
            while True:
                p = multiprocessing.Process(
                    target=bcast_call,
                    args=(int(self.bcast_port), "JOIN"),
                )
                p.start()

                print(f"Keys: {self.node.values}")
                print(f"Replicates: {self.node.replicates}")

                time.sleep(5)
        except KeyboardInterrupt as e:
            print("The server will close")
        except Exception as e:
            print(f"Error in tracker.loop: {e}")

    def server_thread(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(("", int(self.bcast_port)))

            while True:
                try:
                    msg, sender = s.recvfrom(1024)
                    if not msg:
                        continue

                    if msg == b"JOIN":
                        if (
                            self.host != sender[0]
                            and not self.node.find_node(sender[0])
                            and self.elector.ImTheLeader
                        ):
                            # print(
                            #     f"Am I the leader: {self.elector.ImTheLeader} and the sender is {sender[0]}"
                            # )
                            self.join(sender[0], sender[0])

                except Exception as e:
                    print(f"Error in run: {e}")

    def get_requests(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, int(self.port)))
            print(f"Bind in {self.host}:{self.port}")
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
                    data_resp["interval"] = 10
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
        self.node.store_key(info_hash, [peer_id, peer_ip, peer_port])

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
