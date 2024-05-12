import math
import hashlib
import logging
import os
import time

from client.bencoder import bdecode, bencode
from client.parser_torrent import parse_torrent_file


class Torrent:
    def __init__(self) -> None:
        self.torrent_file = {}
        self.total_length: int = 0
        self.piece_length: int = 0
        self.pieces: int = 0
        self.info_hash: str = ""
        self.peer_id: str = ""
        self.announce_list = ""
        self.file_names = []
        self.name: str = ""
        self.number_of_pieces: int = 0

    def load_from_path(self, path):
        contents = parse_torrent_file(path)

        self.torrent_file = contents
        self.piece_length = self.torrent_file["info"]["piece_length"]
        self.pieces = self.torrent_file["info"]["files"]
        raw_info_hash = bencode(self.torrent_file["info"])
        self.info_hash = hashlib.sha1(raw_info_hash).digest()
        self.peer_id = self.generate_peer_id()
        self.announce_list = self.get_trakers()
        self.name = self.torrent_file["info"]["name"]
        self.number_of_pieces = math.ceil(self.total_length / self.piece_length)
        logging.debug(self.announce_list)
        logging.debug(self.file_names)

        return self

    def init_files(self):
        root = self.torrent_file["info"]["name"]

        if "files" in self.torrent_file["info"]:
            if not os.path.exists(root):
                os.mkdir(root, 0o0766)

            for file in self.torrent_file["info"]["files"]:
                path_file = os.path.join(root, *file["path"])

                if not os.path.exists(os.path.dirname(path_file)):
                    os.makedirs(os.path.dirname(path_file))

                self.file_names.append({"path": path_file, "length": file["length"]})
                self.total_length += file["length"]

        else:
            self.file_names.append(
                {"path": root, "length": self.torrent_file["info"]["length"]}
            )
            self.total_length = self.torrent_file["info"]["length"]

    def get_trakers(self):
        if "announce-list" in self.torrent_file:
            return self.torrent_file["announce-list"]
        else:
            return [[self.torrent_file["announce"]]]

    def generate_peer_id(self):
        seed = str(time.time())
        return hashlib.sha1(seed.encode("utf-8")).digest()
