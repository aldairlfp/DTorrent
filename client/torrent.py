import math

import hashlib
import time
import logging
import os

from bcoding import bencode, bdecode

from client.block import BLOCK_SIZE


class Torrent(object):
    def __init__(self):
        self.torrent_file = {}
        self.total_length: int = 0
        self.piece_length: int = 0
        self.pieces: int = 0
        self.info_hash: str = ""
        self.peer_id: str = ""
        self.announce_list = ""
        self.file_names = []
        self.number_of_pieces: int = 0
        self.name: str = ""
        self.selected_files = []
        self.selected_total_length = 0

    def __str__(self):
        rsult = f'peer_id: {self.peer_id}\ninfo_hash: {self.info_hash}\n'

        return rsult



    def load_from_path(self, path):
        with open(path, "rb") as file:
            contents = bdecode(file.read())

        self.torrent_file = contents
        self.comment = contents["comment"] if "comment" in contents else ""
        self.piece_length = self.torrent_file["info"]["piece length"]
        self.pieces = self.torrent_file["info"]["pieces"]
        raw_info_hash = bencode(self.torrent_file["info"])
        self.info_hash = hashlib.sha1(raw_info_hash).digest()
        self.peer_id = self.generate_peer_id()
        self.announce_list = self.get_trakers()
        self.name = self.torrent_file["info"]["name"]
        self.init_files()
        self.number_of_pieces = math.ceil(self.total_length / self.piece_length)
        self.selected_files = list(range(len(self.file_names)))
        self.selected_total_length = self.total_length
        logging.debug(self.announce_list)
        logging.debug(self.file_names)

        assert self.total_length > 0
        assert len(self.file_names) > 0

        return self

    def init_files(self):
        root = self.torrent_file["info"]["name"]

        if "files" in self.torrent_file["info"]:
            for file in self.torrent_file["info"]["files"]:
                path_file = file["path"]

                self.file_names.append({"path": path_file, "length": file["length"]})
                self.total_length += file["length"]

        else:
            self.file_names.append(
                {"path": root, "length": self.torrent_file["info"]["length"]}
            )
            self.total_length = self.torrent_file["info"]["length"]

    def select_files(self, selected_files):
        self.selected_files = []
        k = 0
        for i in range(len(self.file_names)):
            if selected_files[k] == self.file_names[k]["path"]:
                self.selected_files.append(k)
                k += 1
        self.selected_total_length = 0
        for file in self.selected_files:
            self.selected_total_length += self.file_names[file]["length"]
        self.number_of_pieces = math.ceil(
            self.selected_total_length / self.piece_length
        )

    def create_torrent(self, folder_path, announce_list, name):
        self.torrent_file = {
            "announce": announce_list,
            "creation date": int(time.time()),
            "info": {
                "length": os.path.getsize(folder_path),
                "name": name,
                "piece length": BLOCK_SIZE,
                "files": [],
            },
        }

        base_name = len(os.path.basename(folder_path))
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root[base_name + 1 :], file)
                file_info = {
                    "length": os.path.getsize(os.path.join(root, file)),
                    "path": file_path.split("\\"),
                }
                self.torrent_file["info"]["files"] += [file_info]

        self.torrent_file["info"]["pieces"] = self._generate_pieces_key_for_folder(
            folder_path, self.piece_length
        )
        for root, _, files in os.walk(folder_path):
            for file in files:
                with open(os.path.join(root, file), "rb") as f:
                    self.torrent_file["info"]["pieces"] += hashlib.sha1(
                        f.read()
                    ).digest()

        with open(f"torrents/{name}.torrent", "wb") as file:
            file.write(bencode(self.torrent_file))

        return self.torrent_file

    def _generate_pieces_key_for_folder(self, folder_path, piece_size):
        def read_in_pieces(file_path, piece_size):
            with open(file_path, "rb") as f:
                while True:
                    piece = f.read(piece_size)
                    if not piece:
                        break
                    yield piece

        pieces = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                for piece in read_in_pieces(file_path, piece_size):
                    sha1 = hashlib.sha1()
                    sha1.update(piece)
                    pieces.append(sha1.digest())
        return b"".join(pieces)

    def get_trakers(self):
        if "announce-list" in self.torrent_file:
            return self.torrent_file["announce-list"]
        else:
            return [[self.torrent_file["announce"]]]

    def generate_peer_id(self):
        return "-TR2940-" + str(int(time.time())) + "TR"
