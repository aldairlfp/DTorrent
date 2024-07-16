import random
import socket
import threading
import time
import hashlib
import logging

logger = logging.getLogger("__main__")

# Operation codes
FIND_SUCCESSOR = 1
FIND_PREDECESSOR = 2
GET_SUCCESSOR = 3
GET_PREDECESSOR = 4
NOTIFY = 5

CLOSEST_PRECEDING_FINGER = 7
GET_VALUE = 8
GET_KEYS = 9
STORE_KEY = 10
UPDATE_KEY = 11
DELETE_KEY = 12
GET_REPLICATE = 13
STORE_REPLICATE = 14
UPDATE_REPLICATE = 15
DELETE_REPLICATE = 16
CHECK_CONN = 17


def getShaRepr(data: str):
    return int.from_bytes(hashlib.sha1(data.encode()).digest())


class ChordNodeReference:
    def __init__(self, id: int, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

    def _send_data(self, op: int, data: str = None) -> bytes:
        logger.debug(f"Trying to send data to {self.ip}:{self.port}")
        while True:
            # print(f"Send data {self.ip} with op -> {op}")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.ip, self.port))
                    s.sendall(f"{op},{data}".encode("utf-8"))
                    logger.debug(f"Data sent succesfuly to {self.ip}:{self.port}")
                    return s.recv(4096)
            except ConnectionRefusedError as e:
                print(f"Connection refused in _send_data by {self.ip} with op: {op}")
                # print(f"Error in sending data to {self.ip}")
                time.sleep(5)
            except Exception as e:
                print(f"Error sending data: {e}")
                return b""

    def check_conn(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.ip, self.port))
            s.sendall(f"{CHECK_CONN},error".encode("utf-8"))

    def update_reference(self, node: "ChordNodeReference"):
        self.id = node.id
        self.ip = node.ip
        self.port = node.port

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

    def store_key(self, key: int, value: str, is_replicate=False, owner=()):
        (
            self._send_data(STORE_REPLICATE, f"{owner},{key},{value}")
            if is_replicate
            else self._send_data(STORE_KEY, f"{key},{value}")
        )

    def update_key(self, key: int, value: str):
        self._send_data(UPDATE_KEY, f"{key},{value}")

    def delete_key(self, key: int):
        self._send_data(DELETE_KEY, str(key))

    def get_repliccate(self, owner: int, key: int):
        response = self._send_data(GET_REPLICATE, f"{owner},{key}").decode()
        return eval(response) if response != "[]" else []

    def update_replicate(self, owner: int, key: int, value: str):
        self._send_data(UPDATE_REPLICATE, f"{owner},{key},{value}")

    def delete_replicate(self, owner: int):
        self._send_data(DELETE_REPLICATE, f"{owner}")

    def __str__(self) -> str:
        return f"{self.id},{self.ip},{self.port}"

    def __repr__(self) -> str:
        return str(self)


class ChordNode:
    def __init__(self, ip: str, port: int = 8001, m: int = 160, values={}):

        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.id, self.ip, self.port)
        self.succ = ChordNodeReference(
            self.id, self.ip, self.port
        )  # Initial successor is itself
        self.pred = None  # Initially no predecessor
        self.m = m  # Number of bits in the hash/key space
        self.finger = [self.ref] * self.m  # Finger table
        self.next = 0  # Finger table index to fix next
        self.succ_list = []  # List of successors
        self.values: dict = values  # Value stored in this node
        self.replicates = {}

        logger.debug(f"Fixing fingers")
        threading.Thread(
            target=self.fix_fingers, daemon=True
        ).start()  # Start fix fingers threa

        logger.debug(f"Checking predecessor")
        threading.Thread(
            target=self.check_predecessor, daemon=True
        ).start()  # Start check predecessor thread

        logger.debug(f"Initializing server.")
        threading.Thread(
            target=self.start_server, daemon=True
        ).start()  # Start server thread

        logger.debug(f"Stabilize ring")
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
            succ = node.find_successor(self.id)
            if succ.ip != self.ip:
                self.succ.update_reference(succ)
                # print(f"Notify his succesor {self.succ.id}")
                self.succ.notify(self.ref)
                # print(f"join: succ -> {self.succ}, pred -> {self.pred}")

    def stabilize(self):
        """Regular check for correct Chord structure."""
        while True:
            # print('Estabilizing')
            try:
                self.succ.check_conn()
                x = self.succ.pred
                if x.id != self.id:
                    if x and self._inbetween(x.id, self.id, self.succ.id):
                        try:
                            self.succ.delete_replicate(self.id)
                        except Exception as e:
                            print(f"Failed to comunicate with {self.succ.ip} by {e}")

                        self.succ.update_reference(x)
                        self.succ.notify(self.ref)

                if len(self.values) > 0 and self.succ.id != self.id:
                    for key in list(self.values.keys()):
                        self.replicate((key, self.values[key]), self.succ)

            except ConnectionRefusedError as e:
                self.succ.update_reference(self.ref)

            except Exception as e:
                print(f"Error in stabilize: {e}")

            # print(self.succ_list)
            print(f"successor : {self.succ}, predecessor: {self.pred}")

            time.sleep(10)

    def maintain_succ_list(self):
        # Maintain the succ list for stabilizing
        while True:
            try:
                first = self.ref
                while True:
                    self.succ_list.append(first)
                    if first.id == self.succ.id:
                        break
                    first = first.succ
            except Exception as e:
                print(f"Error in maintaining succ_list: {e}")

            time.sleep(15)

    def notify(self, node: "ChordNodeReference"):
        # print(
        #     f"Node: {node.id} IP: {node.ip} notify to Node: {self.id} IP: {self.ip}, as predeccesor "
        # )
        if node.id == self.id:
            pass
        if not self.pred or self._inbetween(node.id, self.pred.id, self.id):
            try:
                self.pred.check_conn()
                self.replicates.pop(self.pred.id)

            except Exception as e:
                if self.pred:
                    logger.debug(f"Node: {self.id} has not replic from {self.pred.id}")
                    if self.pred.id in self.replicates:
                        for key in list(self.replicates[self.pred.id].keys()):
                            value = self.replicates[self.pred.id][key]
                            if self._inbetween(key, node.id, self.id):
                                self.values[key] = value
                                self.replicate((key, value), node)
                            else:
                                node.store_key(key, value)

            # try:
            self.pred = node
            # if len(self.values) > 0:
            #     for key in list(self.values.keys()):
            #         self.replicate((key, self.values[key]), self.pred)
            # except Exception as e:
            #     print(f"Error in notify by {e}")

    def fix_fingers(self):
        """Regularly refresh finger table entries."""
        while True:
            # print('Fixing fingers')
            try:
                i = random.randint(0, self.m - 1)
                self.next = (self.id + 2**i) % (2**self.m)
                self.finger[i] = self.find_succ(self.next)
            except Exception as e:
                print(f"Error in fix fingers: {e}")
            time.sleep(10)

    def check_predecessor(self):
        while True:
            # print('Checking predecessor')
            try:
                if self.pred:
                    self.pred.check_conn()
            except Exception as e:
                try:
                    rep = self.replicates[self.pred.id]
                    # print(f"rep: {rep}")
                    for key in rep:
                        self.values[key] = rep[key]
                    self.replicates.pop(self.pred.id)
                except KeyError:
                    print(f"Error in check predecessor by {e}")
                self.pred = None
            time.sleep(10)

    def find(self, key: int):
        return key in self.find_succ(key).get_keys()

    def find_node(self, ip):
        sha_key = getShaRepr(ip)
        first = self.ref
        current = self.succ

        while current.ip != first.ip:
            if current.id == sha_key:
                return True
            else:
                current = current.succ

        return False if self.id != sha_key else True

    def store_key(self, key: int, value):
        node = self.find_succ(key)
        logger.debug(f"Saving {key} in {node.ip}.")
        node.store_key(key, str(value))

    def get_all(self):
        hashs = {}
        first = self.ref
        while True:
            keys = first.get_keys()
            values = []
            for key in keys:
                values += first.get_value(key)
                hashs[key] = values
            succ = first.succ
            if succ.id == self.ref.id:
                break
            first = succ
        return hashs

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                # print(f"Start_server: {self.ip}")

                conn, addr = s.accept()

                data = b""
                while True:
                    part = conn.recv(4096)
                    data += part
                    if len(part) < 4096:
                        break

                data = data.decode().split(",")

                # print(f"Data: {data}")

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
                    elif option == CLOSEST_PRECEDING_FINGER:
                        id = int(data[1])
                        data_resp = self.closest_preceding_finger(id)

                else:
                    if option == GET_VALUE:
                        key = int(data[1])
                        data_resp = self.values[key]
                    elif option == GET_KEYS:
                        data_resp = [key for key in self.values.keys()]
                    elif option == STORE_KEY:
                        key = int(data[1])
                        value = ",".join(data[2:])
                        value = eval(value)

                        # print(f'Trying to save data with Key: {key} in Node: {self.id}')
                        if key not in self.values:
                            self.values[key] = [value]
                        else:
                            self.values[key] += [value]

                        # print(f'Data with Key: {key} saved succesfuly in Node: {self.id}')

                        if self.pred:
                            self.replicate((key, value), self.pred)

                        if self.succ and self.succ.id != self.id:
                            self.replicate((key, value), self.succ)

                    elif option == UPDATE_KEY:
                        # print(f'Trying to update key: {key}')
                        key = int(data[1])
                        value = ",".join(data[2:])
                        value = eval(value)
                        self.values[key] = value
                        # print(f'Key:{key} updated succesfuly')

                    elif option == DELETE_KEY:
                        # print(f'Trying to delete key: {key}')
                        key = int(data[1])
                        del self.values[key]
                        # print(f'Key: {key} deleted succesfuly')

                    elif option == STORE_REPLICATE:
                        key = int(data[2])
                        owner = int(data[1])
                        value = ",".join(data[3:])
                        # print(f'Trying to save replic from Node: {owner} in Node: {self.id} using key: {key}')
                        value = eval(value)

                        self.save_replic(key, value, owner)
                        # print(f'Replic saved succesfuly in Node: {self.id} using key: {key}')

                    elif option == GET_REPLICATE:
                        # print(f'Searching for replic with Owner: {owner} and Key: {key} in Node: {self.id}')
                        key = int(data[2])
                        owner = int(data[1])
                        data_resp = self.replicates[key]
                        # print(f'Replic with Key: {key} already founded in Node: {self.id}')

                    elif option == UPDATE_REPLICATE:
                        # print(f'Trying to update replic from Owner: {owner} and Key: {key} in Node: {self.id}')
                        owner = int(data[1])
                        key = int(data[2])
                        value = ",".join(data[3:])
                        value = eval(value)
                        self.replicates[owner][key] = value
                        if self.pred:
                            self.replicate((key, value), self.pred)
                        if self.succ and self.succ.id != self.id:
                            self.replicate((key, value), self.succ)
                        # print(f'Replic from Owner: {owner} and Key: {key} up to date succesfuly in Node: {self.id}')
                    elif option == DELETE_REPLICATE:
                        # print(f'Trying to delete replic from Owner: {owner} and Key: {key} in Node: {self.id}')
                        # key = int(data[2])
                        owner = int(data[1])
                        if owner in self.replicates:
                            del self.replicates[owner]
                        # print(f'Replic from Owner: {owner} and Key: {key} up to date succesfuly in Node: {self.id}')

                if data_resp and option < 8:
                    response = f"{data_resp.id},{data_resp.ip}".encode()
                    conn.sendall(response)
                elif data_resp:
                    response = f"{data_resp}".encode()
                    conn.sendall(response)

                # print("The end")
                conn.close()

    def save_replic(self, key, value, owner):
        if not owner in self.replicates:
            self.replicates[owner] = {}

        self.replicates[owner][key] = value

        # print(f'Replication succesfuly from {owner}')

    def replicate(self, info: tuple, dest: ChordNodeReference):
        # print(f'Trying to replicate ({info[1]}, {info[1]}) in destiny {dest.ip} as neighboor.')
        while True:
            # print(f"Replicate 3")
            try:
                dest.check_conn()
                dest.store_key(info[0], info[1], True, self.ref.id)
                break
            except Exception as e:
                print(f"Error in replicate {e}")
