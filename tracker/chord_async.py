from tracker.chord import ChordNodeReference, getShaRepr
import logging
import asyncio
import random
import socket

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

logger = logging.getLogger('__main__')

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

        self.start_server()
        self.stabilize()
        self.check_predecessor()
        self.fix_fingers()

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
        logger.debug(f'Insert a new node in network.')

        if node:
            self.pred = None
            self.succ = node.find_successor(self.id)
            self.succ.notify(self.ref)

    async def stabilize(self):
        """Regular check for correct Chord structure."""
        while True:
            try:
                self.succ.check_conn()
                print("here1")
                # print(self.succ)
                x = self.succ.pred
                # print(x)
                if x.id != self.id:
                    if x and self._inbetween(x.id, self.id, self.succ.id):
                        if self.succ:
                            try:
                                self.succ.check_conn()
                                self.succ.delete_replicate(self.id)
                            except Exception as e:
                                logger.debug(f'Failed to comunicate with {self.succ.ip} by {e}')

                        self.succ.update_reference(x)
                    self.succ.notify(self.ref)

                    # continue # TODO Check this continue
            except ConnectionRefusedError as e:
                logger.debug("Connection refused in Stabilize")
                self.succ.update_reference(self.ref)
                continue
            except Exception as e:
                logger.debug(f"Error in stabilize: {e}")
            
            print('here2')
            try:
                logger.debug(f"successor : {self.succ} predecessor {self.pred}")
                if len(self.values) > 0:
                    for key in list(self.values.keys()):
                        self.replicate((key, self.values[key]), self.succ)
            except Exception as e:
                logger.debug(f'{e}')
            asyncio.sleep(10)

    def notify(self, node: "ChordNodeReference"):
        print('here3')
        if node.id == self.id:
            pass
        if not self.pred or self._inbetween(node.id, self.pred.id, self.id):
            try:
                self.pred.check_conn()
                self.replicates.pop(self.pred.id)

            except Exception as e:
                if self.pred:
                    logger.debug(f'Error in notify by {e}')
                    for key, value in self.replicates[self.pred.id]:
                        if self._inbetween(key, node.id, self.id):
                            self.values[key] = value
                        else:
                            node.store_key(key, value)

            self.pred = node

    async def fix_fingers(self):
        """Regularly refresh finger table entries."""
        while True:
            try:
                i = random.randint(0, self.m - 1)
                self.next = (self.id + 2**i) % (2**self.m)
                self.finger[i] = self.find_succ(self.next)
            except Exception as e:
                print(f"Error in fix fingers: {e}")
            asyncio.sleep(10)

    async def check_predecessor(self):
        while True:
            try:
                if self.pred:
                    self.pred.check_conn()
            except Exception as e:
                self.pred = None
            asyncio.sleep(10)

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
        logger.debug(f'Saving {key} in {node.ip}.')
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

    async def start_server(self):
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
                        data_resp = await self.find_succ(id)
                    elif option == FIND_PREDECESSOR:
                        id = int(data[1])
                        data_resp = await self.find_pred(id)
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
                        data_resp = await self.closest_preceding_finger(id)

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
                        
                        times = 0
                        while(not self.pred and times < 12):
                            times += 1
                            asyncio.sleep(10)
                        
                        if self.pred:
                            await self.replicate((key, value), self.pred)
                        else:
                            conn.close()
                            continue

                        times = 0
                        while(not self.succ and times < 12):
                            times += 1
                            asyncio.sleep(10)

                        if self.succ:
                            await self.replicate((key, value), self.succ)
                        else:
                            conn.close()
                            continue

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
    
    def replicate(self, info :tuple, dest: ChordNodeReference):
        # Saving a replic in destiny
        logger.debug(f'Trying to replicate ({info[1]}, {info[1]}) in destiny {dest.ip}')
        while True:
            try:
                dest.check_conn()
                dest.store_key(info[0], info[1], True, self.id)
                break
            except Exception as e:
                logger.debug(f'{e}')
        