import random
import socket
import threading
import time
import hashlib

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
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.ip, self.port))
                    s.sendall(f"{op},{data}".encode("utf-8"))
                    return s.recv(4096)
            except ConnectionRefusedError as e:
                print(f"Connection refused in _send_data with op: {op}")
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

    def store_key(self, key: int, value: str, is_replicate=False, owner = ()):
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

    def delete_replicate(self, owner: int, key: int):
        self._send_data(DELETE_REPLICATE, f"{owner},{key}")

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
        self.values :dict = values  # Value stored in this node
        self.replicates = {}

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

            
            # for key in self.succ.get_keys():
            #     if not self._inbetween(key, self.id, self.succ.id):
            #         self.values[key] = self.succ.get_value(key)
            #         self.succ.delete_key(key)

            # # If there's only 2 nodes in the ring
            # if self.ip == self.succ.succ.ip and self.ip != self.succ.ip:
            #     self.replicates[key] = self.succ.get_value(key)

          
            # TODO: Stabilize when joining nodes with keys in them
            # first = self.ref
            # last = self.succ
            # while last.succ.ip != first.ip:
            #     for key in self.values.keys():
            #         replicates = last.get_repliccate(key)
            #         if len(replicates) > 0:
            #             replicates = self.values[key]
            #         else:
                        
                
            #     last = last.succ
            
            
            
            
            # else:
            #     for key in self.succ.get_keys():
            #         if not self._inbetween(key, self.id, self.succ.id):
            #             self.values[key] = self.succ.get_value(key)
            #             self.replicate_values(key, self.succ.get_value(key), self.succ)
            #             self.succ.delete_key(key)

            #             # If there's 3 or more nodes in the ring
            #             if self.ip != self.succ.succ.ip:
            #                 # Delete the key from the susecor and the replicate
            #                 # from the last node in the ring with the replicate
            #                 self.succ.delete_key(key)
            #                 last.delete_replicate(key)

            # for key in self.values.keys():
            #     self.replicate_values(key, self.values[key], self.succ)

            # print(f"{self.ip} will notify {self.succ.ip}")

    def stabilize(self):
        """Regular check for correct Chord structure."""
        while True:
            try:
                self.succ.check_conn()
                print(self.succ)
                x = self.succ.pred
                if x.id != self.id:
                    if x and self._inbetween(x.id, self.id, self.succ.id):
                        if self.succ:
                            try:
                                self.succ.delete_replicate(self.id)
                            except Exception as e:
                                print(e)

                        self.succ.update_reference(x)
                    self.succ.notify(self.ref)
                    # continue # TODO Check this continue
            except ConnectionRefusedError as e:
                print("Connection refused in Stabilize")
                self.succ.update_reference(self.ref)
                continue
            except Exception as e:
                print(f"Error in stabilize: {e}")

            print(f"successor : {self.succ} predecessor {self.pred}")
            if len(self.values) > 0:
                for key, value in self.values:
                    self._async_replication((key, value))
            time.sleep(10)

        

    def notify(self, node: "ChordNodeReference"):
        if node.id == self.id:
            pass
        if not self.pred or self._inbetween(node.id, self.pred.id, self.id):
            try:
                self.pred.check_conn()
                self.replicates.pop(self.pred.id)

            except Exception as e:
                for key, value in self.replicates[self.pred.id]:
                    if self._inbetween(key, node.id, self.id):
                        self.values[key] = value
                    else:
                        node.store_key(key, value)

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
                    self.pred.check_conn()
            except Exception as e:
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

    # TODO: Check the stability of the method
    def store_key(self, key: int, value):
        node = self.find_succ(key)
        node.store_key(key, str(value))

        self._async_replication(self.id, (key, str(value)), self.pred)
        self._async_replication(self.id, (key, str(value)), self.succ)

        # first = self.ref
        # current = self.succ
        # If there's only 2 nodes in the ring
        # if current.succ.ip == first.ip and current.ip != first.ip:
        #     self.replicate_values(key, value, current)
        # else:
        #     # Replicate the value in all the nodes in the ring
        #     # except in the pred of the node that has the key
        #     while current.succ.ip != first.ip:
        #         current.replicate_values(key, value, current)
        #         current = current.succ

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
                        if key not in self.values:
                            self.values[key] = [value]
                        else:
                            self.values[key] += [value]
                    elif option == UPDATE_KEY:
                        key = int(data[1])
                        value = ",".join(data[2:])
                        value = eval(value)
                        self.values[key] = value

                    elif option == DELETE_KEY:
                        key = int(data[1])
                        del self.values[key]
                    elif option == STORE_REPLICATE:
                        key = int(data[2])
                        owner = int(data[1])
                        value = ",".join(data[3:])
                        value = eval(value)

                        self.save_replic(key, value, owner)

                    elif option == GET_REPLICATE:
                        key = int(data[1])
                        data_resp = self.replicates[key]
                    elif option == UPDATE_REPLICATE:
                        owner = int(data[1])
                        key = int(data[2])
                        value = ",".join(data[3:])
                        value = eval(value)
                        self.replicates[owner][key] = value
                    elif option == DELETE_REPLICATE:
                        key = int(data[1])
                        del self.replicates[key]

                if data_resp and option < 8:
                    response = f"{data_resp.id},{data_resp.ip}".encode()
                    conn.sendall(response)
                elif data_resp:
                    response = f"{data_resp}".encode()
                    conn.sendall(response)
                conn.close()

    def save_replic(self, key, value, owner): 
        if not self.replicates[owner]:
            self.replicates[owner] = {}
        
        self.replicates[owner][key] = value
    
    async def _async_replication(self, info :tuple, dest: ChordNodeReference):
        # Saving a replic in destiny
        while True:
            try:
                dest.store_key(info[0], info[1], True, self.id)
                break
            except Exception as e:
                print(e)
        