import client.bencoder as bencoder

def parse_info(info):
    info_dict = {}
    info_dict["piece_length"] = info[b"piece length"]
    info_dict["name"] = info[b"name"].decode()
    info_dict["md5sum"] = info[b"md5sum"].decode() if b"md5sum" in info else None
    info_dict["files"] = []
    if b"files" in info:
        for file in info[b"files"]:
            file_dict = {}
            file_dict["length"] = file[b"length"]
            file_dict["path"] = [path.decode() for path in file[b"path"]]
            file_dict["md5sum"] = file[b"md5sum"].decode() if b"md5sum" in file else None
            info_dict["files"].append(file_dict)
    else:
        info_dict["length"] = info[b"length"]
    return info_dict

def parse_torrent(torrent_data):
    torrent_dict = {}
    torrent_dict["announce"] = torrent_data[b"announce"].decode()
    torrent_dict["announce-list"] = [[a.decode() for a in announce] for announce in torrent_data[b"announce-list"]]
    torrent_dict["creation date"] = torrent_data[b"creation date"]
    torrent_dict["created by"] = torrent_data[b"created by"].decode()
    torrent_dict["comment"] = torrent_data[b"comment"].decode()
    torrent_dict["info"] = parse_info(torrent_data[b"info"])
    return torrent_dict

def parse_torrent_file(torrent_file_path):
    with open(torrent_file_path, 'rb') as f:
        torrent_data = bencoder.decode(f.read())
        return parse_torrent(torrent_data)