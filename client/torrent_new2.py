# import math

# import hashlib
# import time
# import logging
# import os

# from bcoding import bencode, bdecode


# class Torrent(object):
#     def __init__(self):
#         self.torrent_file = {}
#         self.total_length: int = 0
#         self.piece_length: int = 0
#         self.pieces: int = 0
#         self.info_hash: str = ""
#         self.peer_id: str = ""
#         self.announce_list = ""
#         self.file_names = []
#         self.number_of_pieces: int = 0
#         self.name: str = ""
#         self.selected_files = []
#         self.selected_total_length = 0

#     def __str__(self):
#         rsult = f"peer_id: {self.peer_id}\ninfo_hash: {self.info_hash}\n"

#         return rsult

#     def load_from_path(self, path):
#         with open(path, "rb") as file:
#             contents = bdecode(file.read())

#         self.torrent_file = contents
#         self.comment = contents["comment"] if "comment" in contents else ""
#         self.piece_length = self.torrent_file["info"]["piece length"]
#         self.pieces = self.torrent_file["info"]["files"]
#         raw_info_hash = bencode(self.torrent_file["info"])
#         self.info_hash = hashlib.sha1(raw_info_hash).digest()
#         self.peer_id = self.generate_peer_id()
#         self.announce_list = self.get_trakers()
#         self.name = self.torrent_file["info"]["name"]
#         self.init_files()
#         self.number_of_pieces = math.ceil(self.total_length / self.piece_length)
#         self.selected_files = list(range(len(self.file_names)))
#         self.selected_total_length = self.total_length
#         logging.debug(self.announce_list)
#         logging.debug(self.file_names)

#         assert self.total_length > 0
#         assert len(self.file_names) > 0

#         return self

#     def init_files(self):
#         root = self.torrent_file["info"]["name"]

#         if "files" in self.torrent_file["info"]:
#             for file in self.torrent_file["info"]["files"]:
#                 path_file = file["path"]

#                 self.file_names.append({"path": path_file, "length": file["length"]})
#                 self.total_length += file["length"]

#         else:
#             self.file_names.append(
#                 {"path": root, "length": self.torrent_file["info"]["length"]}
#             )
#             self.total_length = self.torrent_file["info"]["length"]

#     def select_files(self, selected_files):
#         self.selected_files = []
#         k = 0
#         for i in range(len(self.file_names)):
#             # fn = "/".join(self.file_names[k]["path"])
#             fn = self.file_names[k]["path"]
#             if selected_files[k][1:] == fn:
#                 self.selected_files.append(k)
#                 k += 1
#         self.selected_total_length = 0
#         for file in self.selected_files:
#             self.selected_total_length += self.file_names[file]["length"]
#         self.number_of_pieces = math.ceil(
#             self.selected_total_length / self.piece_length
#         )

#     def create_torrent(self, path, announce_list, name):
#         self.torrent_file = {
#             "announce": announce_list,
#             "creation date": int(time.time()),
#             "info": {
#                 "length": 0,
#                 "name": name,
#                 "piece length": BLOCK_SIZE,
#                 "files": [],
#             },
#         }

#         # Verificar si el path es un archivo o una carpeta
#         if os.path.isfile(path):
#             self._add_file_info(path)
#         elif os.path.isdir(path):
#             self._add_folder_info(path)
#         else:
#             raise ValueError("El path proporcionado no es un archivo ni una carpeta.")

#         # Generar las piezas
#         self.torrent_file["info"]["pieces"] = self._generate_pieces_key(path)

#         # Guardar el archivo .torrent
#         output_path = f"torrents/{name}.torrent"
#         with open(output_path, "wb") as file:
#             file.write(bencode(self.torrent_file))

#         return self.torrent_file

#     def _add_file_info(self, file_path):
#         file_info = {
#             "length": os.path.getsize(file_path),
#             "path": [os.path.basename(file_path)],
#         }
#         self.torrent_file["info"]["length"] = file_info["length"]
#         self.torrent_file["info"]["files"].append(file_info)

#     def _add_folder_info(self, folder_path):
#         for root, dirs, files in os.walk(folder_path):
#             for file in files:
#                 relative_path = os.path.relpath(os.path.join(root, file), folder_path)
#                 file_info = {
#                     "length": os.path.getsize(os.path.join(root, file)),
#                     "path": (
#                         relative_path.split("\\")[1:]
#                         if "\\" in relative_path
#                         else [file]
#                     ),
#                 }
#                 self.torrent_file["info"]["files"].append(file_info)
#                 self.torrent_file["info"]["length"] += file_info["length"]

#     def _generate_pieces_key(self, path):
#         pieces = []
        
#         if os.path.isfile(path):
#             pieces += self._read_pieces_from_file(path)
#         elif os.path.isdir(path):
#             for root, dirs, files in os.walk(path):
#                 for file in files:
#                     pieces += self._read_pieces_from_file(os.path.join(root, file))

#         return b"".join(pieces)

#     def _read_pieces_from_file(self, file_path):
#         pieces = []
        
#         with open(file_path, "rb") as f:
#             while True:
#                 piece = f.read(BLOCK_SIZE)
#                 if not piece:
#                     break
#                 sha1 = hashlib.sha1()
#                 sha1.update(piece)
#                 pieces.append(sha1.digest())
                
#         return pieces

#     def get_trakers(self):
#         if "announce-list" in self.torrent_file:
#             return self.torrent_file["announce-list"]
#         else:
#             return [self.torrent_file["announce"]]

#     def generate_peer_id(self):
#         return "-TR2940-" + str(int(time.time())) + "TR"
