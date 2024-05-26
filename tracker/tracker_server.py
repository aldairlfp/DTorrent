import socket

from tracker.chord import ChordNode, ChordNodeReference, getShaRepr

GET_PEERS = 1
GET_TORRENTS = 2


class TrackerServer:
    def __init__(self, id: int, local_addr=("127.0.0.1", 8080)) -> None:
        self.host = local_addr[0]
        self.port = local_addr[1]
        self.node: ChordNode = ChordNode(id, self.host)
        self.peers = []
        self.torrents = []
        self.tracker_id = 0

    def join(self, node_id, node_ip, node_port):
        self.node.join(ChordNodeReference(node_id, node_ip, node_port))

    def add_torrent(self, torrent):
        self.torrents.append(torrent)

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen(10)
            while True:
                conn, addr = s.accept()
                data = conn.recv(1024).decode().split(",")

                print(f"new connection from {addr} with {data[0]} action")
                data_resp = None
                option = int(data[0])

                if option == GET_PEERS:
                    data_resp = self.peers
                elif option == GET_TORRENTS:
                    data_resp = self.torrents

                data_s = ",".join([str(x) for x in data_resp])
                conn.sendall(data_s.encode())

                conn.close()

    def add_peers(self, elements: list):
        self.peers += elements

    @property
    def id(self):
        return self.node.id
