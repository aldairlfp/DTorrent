from http.server import BaseHTTPRequestHandler


class ChordNodeRequestHandler(BaseHTTPRequestHandler):  # TODO: review this class
    def do_GET(self):
        if self.path == "/":
            params = self.path.split("?")[1].split("&")
            response = None
            
        
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = json.loads(self.rfile.read(content_length))
        logger_rh.debug(f"Request path {self.path}")
        logger_rh.debug(f"Handling the following request \n{post_data}")

        response = None

        if self.path == "/register":
            username = post_data["username"]
            password = post_data["password"]
            user = User(username, password)
            self.server.node.store_user(
                user
            )  # FIXME: This is calling to the node succesor and storing data in it independently it the succesor should store it or not
            response = {"status": "success"}

        elif self.path == "/store_user":
            username = post_data["username"]
            password = post_data["password"]
            user = User(username, password)
            self.server.node.data[getShaRepr(username)] = (
                user.to_dict()
            )  # FIXME: call to a node function
            response = {"status": "success"}

        if self.path == "/find_successor":
            response = self.server.node.find_succ(post_data["id"])
        elif self.path == "/find_predecessor":
            response = self.server.node.find_pred(post_data["id"])
        elif self.path == "/get_successor":
            response = self.server.node.succ
        elif self.path == "/get_predecessor":
            response = self.server.node.pred
            logger_rh.debug(f"Response for get_predecesor request:\n{response}")
        elif self.path == "/notify":
            node = ChordNodeReference(post_data["id"], post_data["ip"])
            self.server.node.notify(node)
        elif self.path == "/check_predecessor":
            # No action needed, this is a ping to check if the node is alive
            pass
        elif self.path == "/closest_preceding_finger":
            response = self.server.node.closest_preceding_finger(post_data["id"])

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        if response:
            self.wfile.write(
                json.dumps({"id": response.id, "ip": response.ip}).encode()
            )
        else:
            self.wfile.write(json.dumps({"id": None, "ip": None}).encode())


class ChordNode:
    def __init__(self, ip: str, port: int = 8001, m: int = 160):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.id, self.ip, self.port)
        self.succ = self.ref  # Initial successor is itself
        # self.pred = None #TODO: Remove this logic
        self.pred = self.ref
        self.m = m  # Number of bits in the hash/key space
        self.finger = [self.ref] * self.m  # Finger table
        self.next = 0  # Finger table index to fix next

        self.data = {}

        server_address = (self.ip, self.port)
        self.httpd = HTTPServer(server_address, ChordNodeRequestHandler)
        self.httpd.node = self

        logger.info(f"node_addr: {ip}:{port}")

        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        logger.info(f"Http serving comenced")

        threading.Thread(
            target=self.stabilize, daemon=True
        ).start()  # Start stabilize thread
        threading.Thread(
            target=self.fix_fingers, daemon=True
        ).start()  # Start fix fingers thread
        threading.Thread(
            target=self.check_predecessor, daemon=True
        ).start()  # Start check predecessor thread
