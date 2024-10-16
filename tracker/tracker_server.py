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

        # if (
        #     downloaded == "0"
        #     and left != "0"
        #     and self.server.tracker_server.find(info_hash)
        # ):
        #     data_resp["peers"] = self.server.tracker_server.get_peers(info_hash)
        if (
            # downloaded == "0"
            left == "0"
            # and not self.server.tracker_server.find(info_hash)
        ):
            self.server.tracker_server.add_peer(
                peer_id, self.client_address[0], port, info_hash
            )

        data_resp["peers"] = self.server.tracker_server.get_peers(info_hash)
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
            leader_election.BroadcastPowElector(leader_election.PORT, difficulty=5)
        )

        self.joining_list = []

        self.httpd = HTTPServer((self.host, self.port), TrackerServerHandlerRequests)
        self.httpd.tracker_server = self

        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def loop(self):
        t1 = threading.Thread(target=self.server_thread)  # TODO:
        t1.start()

        # t2 = threading.Thread(target=self.get_requests)
        # t2.start()
        t2 = threading.Thread(target=self.join_pool)
        t2.start()

        t3 = threading.Thread(target=self.elector.loop)
        t3.start()

        try:
            while True:
                p = multiprocessing.Process(
                    target=bcast_call,
                    args=(int(self.bcast_port), f"JOIN,{self.elector.Leader}"),
                )
                p.start()

                print(f"Keys: {self.node.values}")
                print(f"Replicates: {self.node.replicates}")
                # print(f"Succ -> {self.node.succ}")
                # print(f"Pred -> {self.node.pred}")

                time.sleep(10)
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
                    msg = msg.decode().split(",")
                    if not msg:
                        continue

                    if msg[0] == "JOIN":
                        if (
                            msg[1] != "None"
                            and self.host != msg[1]
                            # and not self.node.is_stabilizing
                        ):
                            # print(
                            #     f"Am I the leader: {self.elector.ImTheLeader} and the sender is {sender[0]}"
                            # )
                            # print(self.host != sender[0])
                            if not msg[1] in self.joining_list:
                                self.joining_list.append(msg[1])
                            # self.join(msg[1])

                # except Exception as e:
                #     print(f"Error in run: {e}")
                finally:
                    pass

    def join_pool(self):
        while True:
            if len(self.joining_list) > 0:
                self.join(self.joining_list.pop())
            time.sleep(5)

    def join(self, node_ip, node_port=8001):
        retry_on_connection_refused(
            self.node.join, ChordNodeReference(node_ip, node_ip, node_port)
        )

    def find(self, info_hash):
        return retry_on_connection_refused(self.node.find, info_hash)

    def get_peers(self, info_hash):
        return retry_on_connection_refused(self.node.find_succ, info_hash).get_value(
            info_hash
        )

    def add_peer(self, peer_id, peer_ip, peer_port, info_hash):
        retry_on_connection_refused(
            self.node.store_key, info_hash, [peer_id, peer_ip, peer_port]
        )

    def get_all(self):
        return retry_on_connection_refused(self.get_all)

    @property
    def id(self):
        return self.node.id


def retry_on_connection_refused(func, *args, max_retries=5, delay=3, **kwargs):
    """
    Tries to execute the function 'func' with the given arguments.
    If a connection refused exception occurs, it retries the execution.

    :param func: The function to execute.
    :param args: Positional arguments for the function.
    :param max_retries: Maximum number of retries.
    :param delay: Delay time between retries (in seconds).
    :param kwargs: Keyword arguments for the function.
    :return: The result of the function if successful, None if it fails after retries.
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except ConnectionRefusedError as e:
            print(
                f"Connection refused in function '{func.__name__}'. Attempt {attempt + 1} of {max_retries}."
            )
            time.sleep(delay)  # Wait before retrying
    print("Maximum number of retries reached. Function failed.")
    return None
