import hashlib, socket, time, multiprocessing

HOST = "0.0.0.0"
PORT = "8002"


class BroadcastPowElector:
    def __init__(
        self,
        port=PORT,
        base_hash=hashlib.sha256("Hello world for POW".encode()).hexdigest(),
        difficulty=6,
        iteration=1,
    ):
        self.id = str(socket.gethostbyname(socket.gethostname()))
        self.port = port
        self.ImTheLeader = False
        self.Leader = None

        self.base_hash = base_hash
        self.difficulty = difficulty
        self.iteration = iteration

    def _make_pow(self, iteration, initial_hash, difficulty, id, port):
        print("pow started")
        nonce = 0
        sha = hashlib.sha256()
        sha.update(str(initial_hash).encode() + str(nonce).encode())
        prev_hash = sha.hexdigest()
        while prev_hash[0:difficulty] != "0" * difficulty:
            nonce += 1
            sha = hashlib.sha256()
            sha.update(str(initial_hash).encode() + str(nonce).encode())
            prev_hash = sha.hexdigest()

        print(f"{id},{iteration},{initial_hash},{nonce},{prev_hash}")

        s = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(
            f"{id},{iteration},{initial_hash},{nonce},{prev_hash}".encode(),
            ("255.255.255.255", int(port)),
        )
        time.sleep(3)
        s.close()

    def loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(("", int(self.port)))
            while True:
                p = multiprocessing.Process(
                    target=self._make_pow,
                    args=(
                        self.iteration,
                        self.base_hash,
                        self.difficulty,
                        self.id,
                        self.port,
                    ),
                )
                p.start()

                timer = 20
                while True:
                    msg, winner = s.recvfrom(1024)
                    id, iteration, initial_hash, nonce, curr_hash = msg.decode().split(
                        ","
                    )

                    print(
                        "Recieved: ",
                        id,
                        iteration,
                        initial_hash,
                        nonce,
                        curr_hash,
                        "from",
                        winner,
                    )

                    sha = hashlib.sha256()
                    sha.update(str(initial_hash).encode() + str(nonce).encode())
                    hash = sha.hexdigest()
                    if (
                        hash == curr_hash
                        and hash[0 : self.difficulty] == "0" * self.difficulty
                    ):
                        print(f"Leader Elected: {winner}")
                        self.Leader = winner
                        # we have a winner
                        if id == self.id:
                            print("I'm the leader")
                            self.ImTheLeader = True
                            time.sleep(4)
                            timer = 16
                        # for a valid hash and a more recent iteration, we update the new iteration
                        elif int(iteration) > self.iteration:
                            self.iteration = int(iteration)
                        self.iteration += 1
                        p.terminate()
                        p.join()
                        time.sleep(timer)
                        break
