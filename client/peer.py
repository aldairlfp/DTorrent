class Peer:
    def __init__(self, number_of_pieces, ip, port=6881):
        self.ip = ip
        self.port = port
        self.number_of_pieces = number_of_pieces