import requests
from client.torrent import Torrent
from bcoding import bdecode
from client.bencoder import bdecode as bdecode2
import struct
import socket

torrent = Torrent()
torrent.load_from_path("torrents/razdacha-ne-suschestvuet.torrent")
for i in range(len(torrent.announce_list)):
    try:
        answer_tracker = requests.get(
            # torrent.announce_list[i][0],
            # "http://10.2.0.2:8080",
            "http://192.168.255.229:5000",
            params={
                "info_hash": torrent.info_hash,
                "uploaded": 0,
                "downloaded": 0,
                "port": 6881,
                "left": torrent.total_length,
            },
            timeout=5,
        )
        ips = []
        list_peers = bdecode(answer_tracker.content)
        offset = 0
        for _ in range(len(list_peers["peers"]) // 6):
            ip = struct.unpack_from("!i", list_peers["peers"], offset)[0]
            ip = socket.inet_ntoa(struct.pack("!i", ip))
            offset += 4
            port = struct.unpack_from("!H", list_peers["peers"], offset)[0]
            offset += 2
            ips.append((ip, port))
        print(ips)
    except Exception as e:
        # print(e)
        pass

# answer_tracker = requests.get(
#     "http://192.168.255.229:8080",
#     params={
#         "uploaded": 0,
#         "downloaded": 0,
#         "port": 6881,
#     },
#     timeout=5,
# )
