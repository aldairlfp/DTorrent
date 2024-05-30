import socket

from tracker.chord import ChordNode, ChordNodeReference, getShaRepr


class TrackerServer:
    def __init__(self, id: int, local_addr=("127.0.0.1", 8080)) -> None:
        self.host = local_addr[0]
        self.port = local_addr[1]
        self.node: ChordNode = ChordNode(id, self.host)
        self.info_hashs = {}
        self.tracker_id = 0

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

                if request_data[0] == "GET / HTTP/1.1":
                    params = request_data[1].split("?")[1].split("&")
                    info_hash = params[0].split(": ")[1][2:-1].encode()
                    peer_id = params[1].split(": ")[1]
                    uploaded = params[2].split(": ")[1]
                    downloaded = params[3].split(": ")[1]
                    port = params[4].split(": ")[1]
                    left = params[5].split(": ")[1]

                    print(f"info_hash: {info_hash}")
                    print(f"peer_id: {peer_id}")
                    print(f"uploaded: {uploaded}")
                    print(f"downloaded: {downloaded}")
                    print(f"port: {port}")
                    print(f"left: {left}")

                    data_resp = self.info_hashs[info_hash]

                    if data_resp:
                        data_resp = f"HTTP/1.1 200 OK\r\nContent-Length: {len(data_resp)}\r\n\r\n{data_resp}"
                    else:
                        data_resp = "HTTP/1.1 404 Not Found\r\n\r\n"
                        
                    conn.sendall(data_resp.encode())

                conn.close()

    def add_peers(self, elements: list):
        self.peers += elements

    @property
    def id(self):
        return self.node.id
