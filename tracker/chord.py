import random
import socket
import threading
import time
import hashlib
import logging
import Pyro5.api
import subprocess

logger = logging.getLogger("__main__")

# Inicializar sistema de nombres Pyro5
# Definir el comando para ejecutar el servidor de nombres Pyro5
print("Creating NS")
command = [
    "pyro5-ns",
    "-n",
    f"{socket.gethostbyname(socket.gethostname())}",
    "-p",
    f"5554",
    #   "--bchost",f"{ broadcast}",
    #   "--bcport",f"{int(args.port)-3}"
]

# Ejecutar el comando en un proceso aparte
subprocess.Popen(command)

# Esperar 1 segundo para que el servidor de nombres se inicie
time.sleep(1)


def getShaRepr(data: str):
    return int.from_bytes(hashlib.sha1(data.encode()).digest())


class ChordNodeReference:
    def __init__(self, id: int, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

    def get_server_uri(self):
        name_server = Pyro5.api.locate_ns(self.ip, 5554)
        return name_server.lookup(str(self.id))

    def check_conn(self):
        server_uri = self.get_server_uri()
        # print("llegue aqui 1")
        with Pyro5.api.Proxy(server_uri) as server:
            # print("llegue aqui 2")
            server._pyroReconnect()

    def update_reference(self, node: "ChordNodeReference"):
        self.id = node.id
        self.ip = node.ip
        self.port = node.port

    def find_successor(self, id: int) -> "ChordNodeReference":
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            succesor = server.find_succ(id)
            return ChordNodeReference(succesor.id, succesor.ip, succesor.port)

    def find_predecessor(self, id: int) -> "ChordNodeReference":
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            predecesor = server.find_pred(id)
            return ChordNodeReference(predecesor.id, predecesor.ip, predecesor.port)

    @property
    def succ(self) -> "ChordNodeReference":
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            succ = server.succ
            return (
                ChordNodeReference(succ.id, succ.ip, succ.port)
                if succ
                else ChordNodeReference(self.id, self.ip, self.port)
            )

    @property
    def pred(self) -> "ChordNodeReference":
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            pred = server.pred
            return (
                ChordNodeReference(pred.id, pred.ip, pred.port)
                if pred
                else ChordNodeReference(self.id, self.ip, self.port)
            )

    def notify(self, node: "ChordNodeReference"):
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            server.notify(node)

    def closest_preceding_finger(self, id: int) -> "ChordNodeReference":
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            return server.closest_preceding_finger(id)

    def get_value(self, key: int) -> dict:
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            return server.get_value(key)

    def get_keys(self) -> list:
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            return server.get_keys()

    def store_key(self, key: int, value: str, is_replicate=False, owner=()):
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            server.store_key(key, value, is_replicate, owner)

    def update_key(self, key: int, value: str):
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            server.update_key(key, value)

    def delete_key(self, key: int):
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            server.delete_key(key)

    def get_replicate(self, owner: int, key: int):
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            return server.get_replicate(owner, key)

    def update_replicate(self, owner: int, key: int, value: str):
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            server.update_replicate(owner, key, value)

    def delete_replicate(self, owner: int):
        server_uri = self.get_server_uri()
        with Pyro5.api.Proxy(server_uri) as server:
            server.delete_replicate(owner)

    def __str__(self) -> str:
        return f"{self.id},{self.ip},{self.port}"

    def __repr__(self) -> str:
        return str(self)


class ChordNode:
    def __init__(self, ip: str, port: int = 8001, m: int = 160, values={}):

        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

        daemon = Pyro5.api.Daemon(host=self.ip, port=self.port)
        uri = daemon.register(self)

        nameserver = Pyro5.api.locate_ns()
        nameserver.register(str(self.id), uri)

        self.ref = ChordNodeReference(self.id, self.ip, self.port)
        self._succ = ChordNodeReference(
            self.id, self.ip, self.port
        )  # Initial successor is itself
        self._pred = None  # Initially no predecessor
        self.m = m  # Number of bits in the hash/key space
        self.finger = [self.ref] * self.m  # Finger table
        self.next = 0  # Finger table index to fix next
        self.succ_list = []  # List of successors
        self.values: dict = values  # Value stored in this node
        self.replicates = {}

        threading.Thread(target=daemon.requestLoop).start()

        logger.debug(f"Fixing fingers")
        threading.Thread(
            target=self.fix_fingers, daemon=True
        ).start()  # Start fix fingers threa

        logger.debug(f"Checking predecessor")
        threading.Thread(
            target=self.check_predecessor, daemon=True
        ).start()  # Start check predecessor thread

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

    @Pyro5.api.expose
    @property
    def pred(self):
        return self._pred

    @Pyro5.api.expose
    @property
    def succ(self):
        return self._succ

    @Pyro5.api.expose
    def find_succ(self, id: int) -> "ChordNodeReference":
        node = self.find_pred(id)  # Find predecessor of id
        return node.succ  # Return successor of that node

    @Pyro5.api.expose
    def find_pred(self, id: int) -> "ChordNodeReference":
        node = self
        while not self._inbetween(id, node.id, node.succ.id):
            node = node.closest_preceding_finger(id)
        return node

    @Pyro5.api.expose
    def closest_preceding_finger(self, id: int) -> "ChordNodeReference":
        for i in range(self.m - 1, -1, -1):
            if self.finger[i] and self._inbetween(self.finger[i].id, self.id, id):
                return self.finger[i]
        return self.ref

    @Pyro5.api.expose
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
            # try:
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

            # except ConnectionRefusedError as e:
            #     print(f"Connection refuse in stabilize: {e}")
            #     self.succ.update_reference(self.ref)

            # except Exception as e:
            #     print(f"Error in stabilize: {e}")

            # # print(self.succ_list)
            # print(f"successor : {self.succ}, predecessor: {self.pred}")

            time.sleep(10)

    @Pyro5.api.expose
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

    @Pyro5.api.expose
    def get_value(self, key: int) -> dict:
        return self.values[key]

    @Pyro5.api.expose
    def get_keys(self) -> list:
        return list(self.values.keys())

    @Pyro5.api.expose
    def store_key(self, key: int, value: str, is_replicate=False, owner=()):
        self.values[key] = value
        if not is_replicate:
            self.replicate((key, value), self.succ)
        else:
            self.save_replic(key, value, owner)

    @Pyro5.api.expose
    def update_key(self, key: int, value: str):
        self.values[key] = value

    @Pyro5.api.expose
    def delete_key(self, key: int):
        self.values.pop(key)

    @Pyro5.api.expose
    def get_replicate(self, owner: int, key: int):
        return self.replicates[owner][key]

    @Pyro5.api.expose
    def update_replicate(self, owner: int, key: int, value: str):
        self.replicates[owner][key] = value

    @Pyro5.api.expose
    def delete_replicate(self, owner: int):
        self.replicates.pop(owner)

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

    @Pyro5.api.expose
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
