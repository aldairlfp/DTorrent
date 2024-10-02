from client.torrent import Torrent
from bcoding import bdecode, bencode
import hashlib
import urllib
import requests
import json
import sys
import socket
import os

def create_torrent(server_addr, path, annouce_list, name):
        torrent_file = Torrent().create_torrent(path, annouce_list, name)

        raw_info_hash = bencode(torrent_file["info"])
        info_hash = hashlib.sha1(raw_info_hash).digest()

        params = {
            "info_hash": urllib.parse.quote(info_hash.hex()),
            "peer_id": Torrent().generate_peer_id(),
            "uploaded": 0,
            "downloaded": 0,
            "port": 6881,
            "left": 0,
        }
        print(torrent_file)

        response = requests.get(f"http://{server_addr}:8000", params=params)

        print(json.loads(response.content))
        
if __name__ == "__main__":
    try:
        folder_path = sys.argv[1]
        folder_name = os.path.basename(folder_path)
        create_torrent(
                socket.gethostbyname(socket.gethostname()),
                folder_path,
                [f"http://{socket.gethostbyname(socket.gethostname())}:8000"],
                folder_name,
            )
    except IndexError:
        sys.exit(0)       
        