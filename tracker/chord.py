import random
import socket
import threading
import sys
import time
import hashlib

# Operation codes
FIND_SUCCESSOR = 1
FIND_PREDECESSOR = 2
GET_SUCCESSOR = 3
GET_PREDECESSOR = 4
NOTIFY = 5
CHECK_PREDECESSOR = 6
CLOSEST_PRECEDING_FINGER = 7
GET_VALUE = 8
GET_KEYS = 9
ADD_VALUE = 10


def getShaRepr(data: str):
    return int.from_bytes(hashlib.sha1(data.encode()).digest())


class ChordNodeReference:
    def __init__(self, id: int, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

    def _send_data(self, op: int, data: str = None) -> bytes:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.ip, self.port))
                s.sendall(f"{op},{data}".encode("utf-8"))
                return s.recv(4096)
        except ConnectionRefusedError as e:
            raise ConnectionRefusedError(e.strerror)
        except Exception as e:
            print(f"Error sending data: {e}")
            return b""

    def find_successor(self, id: int) -> "ChordNodeReference":
        response = self._send_data(FIND_SUCCESSOR, str(id)).decode().split(",")
        return ChordNodeReference(int(response[0]), response[1], self.port)

    def find_predecessor(self, id: int) -> "ChordNodeReference":
        response = self._send_data(FIND_PREDECESSOR, str(id)).decode().split(",")
        return ChordNodeReference(int(response[0]), response[1], self.port)

    @property
    def succ(self) -> "ChordNodeReference":
        response = self._send_data(GET_SUCCESSOR).decode().split(",")
        return ChordNodeReference(int(response[0]), response[1], self.port)

    @property
    def pred(self) -> "ChordNodeReference":
        response = self._send_data(GET_PREDECESSOR).decode().split(",")
        return ChordNodeReference(int(response[0]), response[1], self.port)

    def notify(self, node: "ChordNodeReference"):
        self._send_data(NOTIFY, f"{node.id},{node.ip}")

    def check_predecessor(self):
        self._send_data(CHECK_PREDECESSOR)

    def closest_preceding_finger(self, id: int) -> "ChordNodeReference":
        response = (
            self._send_data(CLOSEST_PRECEDING_FINGER, str(id)).decode().split(",")
        )
        return ChordNodeReference(int(response[0]), response[1], self.port)

    def get_value(self, key: int) -> dict:
        response = self._send_data(GET_VALUE, str(key)).decode()
        return eval(response) if response != "[]" else []

    def get_keys(self) -> list:
        response = self._send_data(GET_KEYS).decode()
        return eval(response) if response != "" else []

    def add_value(self, key: int, value: str):
        self._send_data(ADD_VALUE, f"{key},{value}")

    def __str__(self) -> str:
        return f"{self.id},{self.ip},{self.port}"

    def __repr__(self) -> str:
        return str(self)


class ChordNode:
    def __init__(self, id: int, ip: str, port: int = 8001, m: int = 160, values={}):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.id, self.ip, self.port)
        self.succ = self.ref  # Initial successor is itself
        self.pred = None  # Initially no predecessor
        self.m = m  # Number of bits in the hash/key space
        self.finger = [self.ref] * self.m  # Finger table
        self.next = 0  # Finger table index to fix next
        self.values = values  # Value stored in this node

        threading.Thread(
            target=self.fix_fingers, daemon=True
        ).start()  # Start fix fingers thread
        threading.Thread(
            target=self.check_predecessor, daemon=True
        ).start()  # Start check predecessor thread
        threading.Thread(
            target=self.start_server, daemon=True
        ).start()  # Start server thread
        threading.Thread(
            target=self.stabilize, daemon=True
        ).start()  # Start stabilize thread

    def _inbetween(self, k: int, start: int, end: int) -> bool:
        """Check if k is in the interval (start, end]."""
        if start < end:
            return start < k <= end
        else:  # The interval wraps around 0
            return start < k or k <= end

    def find_succ(self, id: int) -> "ChordNodeReference":
        node = self.find_pred(id)  # Find predecessor of id
        return node.succ  # Return successor of that node

    def find_pred(self, id: int) -> "ChordNodeReference":
        node = self
        while not self._inbetween(id, node.id, node.succ.id):
            node = node.closest_preceding_finger(id)
        return node

    def closest_preceding_finger(self, id: int) -> "ChordNodeReference":
        for i in range(self.m - 1, -1, -1):
            if self.finger[i] and self._inbetween(self.finger[i].id, self.id, id):
                return self.finger[i]
        return self.ref

    def join(self, node: "ChordNodeReference"):
        """Join a Chord network using 'node' as an entry point."""
        if node:
            self.pred = None
            self.succ = node.find_successor(self.id)
            self.succ.notify(self.ref)
        else:
            self.succ = self.ref
            self.pred = None

    def stabilize(self):
        """Regular check for correct Chord structure."""
        while True:
            try:
                x = self.succ.pred
                if x.id != self.id:
                    if x and self._inbetween(x.id, self.id, self.succ.id):
                        self.succ = x
                    self.succ.notify(self.ref)
            except ConnectionRefusedError as e:
                self.succ = self.ref
            except Exception as e:
                print(f"Error in stabilize: {e}")

            print(f"successor : {self.succ} predecessor {self.pred}")
            time.sleep(10)

    def notify(self, node: "ChordNodeReference"):
        if node.id == self.id:
            pass
        if not self.pred or self._inbetween(node.id, self.pred.id, self.id):
            self.pred = node

    def fix_fingers(self):
        """Regularly refresh finger table entries."""
        while True:
            try:
                i = random.randint(0, self.m - 1)
                self.next = (self.id + 2**i) % (2**self.m)
                self.finger[i] = self.find_succ(self.next)
            except Exception as e:
                print(f"Error in fix fingers: {e}")
            time.sleep(10)

    def check_predecessor(self):
        while True:
            try:
                if self.pred:
                    self.pred.check_predecessor()
            except Exception as e:
                self.pred = None
            time.sleep(10)

    def add_value(self, key: int, value):
        node = self.find_succ(key)
        node.add_value(key, str(value))

    def get_all_values(self):
        values = []
        first = self.ref
        while True:
            keys = first.get_keys()
            for key in keys:
                values += first.get_value(key)
            succ = first.succ
            if succ.id == self.ref.id:
                break
            first = succ
        return values

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                conn, addr = s.accept()

                data = b""
                while True:
                    part = conn.recv(4096)
                    data += part
                    if len(part) < 4096:
                        break

                data = data.decode().split(",")

                data_resp = None
                option = int(data[0])

                if option < 8:
                    if option == FIND_SUCCESSOR:
                        id = int(data[1])
                        data_resp = self.find_succ(id)
                    elif option == FIND_PREDECESSOR:
                        id = int(data[1])
                        data_resp = self.find_pred(id)
                    elif option == GET_SUCCESSOR:
                        data_resp = self.succ if self.succ else self.ref
                    elif option == GET_PREDECESSOR:
                        data_resp = self.pred if self.pred else self.ref
                    elif option == NOTIFY:
                        id = int(data[1])
                        ip = data[2]
                        self.notify(ChordNodeReference(id, ip, self.port))
                    elif option == CHECK_PREDECESSOR:
                        pass
                    elif option == CLOSEST_PRECEDING_FINGER:
                        id = int(data[1])
                        data_resp = self.closest_preceding_finger(id)

                else:
                    if option == GET_VALUE:
                        key = int(data[1])
                        data_resp = self.values[key]
                    elif option == GET_KEYS:
                        data_resp = [key for key in self.values.keys()]
                    elif option == ADD_VALUE:
                        key = int(data[1])
                        value = ",".join(data[2:])
                        value = eval(value)
                        if key not in self.values:
                            self.values[key] = [value]
                        else:
                            self.values[key] += [value]

                if data_resp and option < 8:
                    response = f"{data_resp.id},{data_resp.ip}".encode()
                    conn.sendall(response)
                elif data_resp:
                    response = f"{data_resp}".encode()
                    conn.sendall(response)
                conn.close()
