import math

import hashlib
import time
import logging
import os

from bcoding import bencode, bdecode


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

    def load_from_path(self, path):
        with open(path, "rb") as file:
            contents = bdecode(file.read())

        self.torrent_file = contents
        self.piece_length = self.torrent_file["info"]["piece length"]
        self.pieces = self.torrent_file["info"]["files"]
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
                path_file = os.path.join(root, *file["path"])

                self.file_names.append({"path": path_file, "length": file["length"]})
                self.total_length += file["length"]

        else:
            self.file_names.append(
                {"path": root, "length": self.torrent_file["info"]["length"]}
            )
            self.total_length = self.torrent_file["info"]["length"]

    def select_files(self, selected_files):
        self.selected_files = selected_files
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
                "piece length": 2**14,
                "files": [],
            },
        }

        folder = len(folder_path) - len(os.path.basename(folder_path))
        base_name = len(os.path.basename(folder_path))
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root[base_name + 1:], file)
                file_info = {
                    "length": os.path.getsize(os.path.join(root, file)),
                    "path": file_path.split("\\"),
                }
                self.torrent_file["info"]["files"] += [file_info]

        with open(f"torrents/{name}.torrent", "wb") as file:
            file.write(bencode(self.torrent_file))

        return self.torrent_file

    def get_trakers(self):
        if "announce-list" in self.torrent_file:
            return self.torrent_file["announce-list"]
        else:
            return [[self.torrent_file["announce"]]]

    def generate_peer_id(self):
        return "-TR2940-" + str(int(time.time())) + "TR"
