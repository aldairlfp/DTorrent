import hashlib
import json
import os
import time
import bencodepy
from bcoding import bencode
import urllib

import requests



def transform_length(file_size):
    if file_size >= 1024 * 1024 * 1024:
        file_size = f"{file_size/(1024*1024*1024):.2f} GB"
    elif file_size >= 1024 * 1024:
        file_size = f"{file_size/(1024*1024):.2f} MB"
    elif file_size >= 1024:
        file_size = f"{file_size/1024:.2f} KB"
    else:
        file_size = f"{file_size} B"
    return file_size


### Create Torrent from Folder ###
def create_torrent_from_folder(folder_path, output_file_name):
    if not os.path.isdir(folder_path):
        raise ValueError("The provided path is not a valid directory.")
    files = []
    total_size = 0
    # Gather all files in the directory
    for root, _, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            file_size = os.path.getsize(file_path)
            total_size += file_size
            relative_path = os.path.relpath(file_path, folder_path)
            files.append({"length": file_size, "path": [relative_path.encode()]})
    # Prepare torrent metadata
    piece_length = 524288  # Example piece length (512 KB)
    pieces = generate_piece_hashes(folder_path, piece_length)
    info_dict = {
        "name": os.path.basename(folder_path).encode(),
        "piece length": piece_length,
        "pieces": pieces,
        "files": files if len(files) > 1 else None,
        "length": total_size if len(files) == 1 else None,
    }
    # Create the full torrent dictionary
    torrent_dict = {
        "announce": "http://tracker.example.com:8080/announce",
        "info": info_dict,
    }
    # Write the .torrent file1
    with open(output_file_name, "wb") as f:
        f.write(bencodepy.encode(torrent_dict))


### Generate Piece Hashes ###
def generate_piece_hashes(folder_path, piece_length):
    sha1_hash = hashlib.sha1()
    pieces = bytearray()
    for root, _, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            with open(file_path, "rb") as f:
                while True:
                    data = f.read(piece_length)
                    if not data:
                        break
                    sha1_hash.update(data)
                    pieces.extend(sha1_hash.digest())
                    sha1_hash = hashlib.sha1()  # Reset for next piece
    return pieces


# def create_torrent(server_addr, path, annouce_list, name):
#     torrent_file = Torrent().create_torrent(path, annouce_list, name)

    # raw_info_hash = bencode(torrent_file["info"])
    # info_hash = hashlib.sha1(raw_info_hash).digest()

    # params = {
    #     "info_hash": urllib.parse.quote(info_hash.hex()),
    #     "peer_id": Torrent().generate_peer_id(),
    #     "uploaded": 0,
    #     "downloaded": 0,
    #     "port": 6881,
    #     "left": 0,
    # }

    # response = requests.get(f"http://{server_addr}:8000", params=params)

    # print(json.loads(response.content))


def create_torrent2(file_path, tracker_url):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"El archivo {file_path} no existe.")

    # Obtener tamaño del archivo
    file_size = os.path.getsize(file_path)

    # Calcular el hash SHA1 para el archivo
    def sha1_hash(file):
        hasher = hashlib.sha1()
        with open(file, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.digest()

    piece_length = 16384  # 16 KB por pieza
    pieces = b''
    
    # Dividir el archivo en piezas y calcular el hash de cada una
    with open(file_path, 'rb') as f:
        while True:
            piece = f.read(piece_length)
            if not piece:
                break
            pieces += sha1_hash(piece)

    # Crear la estructura del torrent
    torrent_data = {
        'announce': tracker_url,
        'info': {
            'name': os.path.basename(file_path),
            'length': file_size,
            'piece length': piece_length,
            'pieces': pieces,
        }
    }

    # Codificar y guardar el archivo .torrent
    torrent_file_name = f"{os.path.basename(file_path)}.torrent"
    with open(torrent_file_name, 'wb') as torrent_file:
        torrent_file.write(bencodepy.encode(torrent_data))

    print(f"Archivo .torrent creado: {torrent_file_name}")