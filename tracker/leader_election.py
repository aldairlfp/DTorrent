import socket
import threading
import time
import multiprocessing

PORT = "8002"
MCASTADDR = "224.0.0.2"
ID = str(socket.gethostbyname(socket.gethostname()))

OK = 2
ELECTION = 1
WINNER = 3


def mcast_call(message, mcast_addr, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    s.sendto(message.encode(), (mcast_addr, port))
    s.close()


class BullyMulticastElector:

    def __init__(self, Port, Mcast_Addr):
        self.id = str(socket.gethostbyname(socket.gethostname()))
        self.port = int(Port)
        self.Leader = None
        self.mcast_adrr = Mcast_Addr
        self.InElection = False
        self.ImTheLeader = True

    def bully(self, id, otherId):
        return int(id.split(".")[-1]) > int(otherId.split(".")[-1])

    def election_call(self):
        p = multiprocessing.Process(
            target=mcast_call, args=(f"{ELECTION}", self.mcast_adrr, self.port)
        )
        p.start()
        print("Election Started")

    def winner_call(self):
        p = multiprocessing.Process(
            target=mcast_call, args=(f"{WINNER}", self.mcast_adrr, self.port)
        )
        p.start()

    def loop(self):
        t = threading.Thread(target=self.server_thread)
        t.start()

        counter = 0
        while True:
            if not self.Leader and not self.InElection:
                self.election_call()
                self.InElection = True

            elif self.InElection:
                counter += 1
                if counter == 10:
                    if not self.Leader and self.ImTheLeader:
                        self.ImTheLeader = True
                        self.Leader = self.id
                        self.InElection = False
                        self.winner_call()
                    counter = 0
                    self.InElection = False

            # else:
            #     print(f"Leader: {self.Leader}")

            # print(f"{counter} waiting")
            # print(f"Leader til now {self.Leader}")
            time.sleep(1)

    def server_thread(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            membership = socket.inet_aton(self.mcast_adrr) + socket.inet_aton("0.0.0.0")
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            s.bind(("", int(PORT)))

            while True:
                try:
                    msg, sender = s.recvfrom(1024)
                    if not msg:
                        continue  # Ignorar mensajes vacíos

                    newId = sender[0]
                    msg = msg.decode("utf-8")

                    if msg.isdigit():
                        # print(f"Server_thread message: {msg}")
                        msg = int(msg)
                        if msg == ELECTION and not self.InElection:
                            # print(f"Election message received from: {newId}")

                            if not self.InElection:
                                self.InElection = True
                                self.Leader = None
                                self.election_call()

                            if self.bully(self.id, newId):
                                with socket.socket(
                                    socket.AF_INET, socket.SOCK_DGRAM
                                ) as s_send:
                                    s_send.sendto(f"{OK}".encode(), (newId, self.port))

                        elif msg == OK:
                            # print(f"OK message received from: {newId}")
                            if self.Leader and self.bully(newId, self.Leader):
                                self.Leader = newId
                            self.ImTheLeader = False

                        elif msg == WINNER:
                            print(f"Winner message received from: {newId}")
                            if not self.bully(self.id, newId) and (
                                not self.Leader or self.bully(newId, self.Leader)
                            ):
                                self.Leader = newId
                                if self.Leader != self.id:
                                    self.ImTheLeader = False
                                self.InElection = False

                except Exception as e:
                    print(f"Error in server_thread: {e}")
