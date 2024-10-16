import sys

from threading import Thread

# torrent file hander module for reading .torrent files
from client.torrent_file_handler import torrent_file_reader

# tracker module for making tracker request and recieving peer data
from client.tracker import torrent_tracker

# torrent module holds all the information about the torrent file
from client.torrent import *

# swarm module controls the operations over the multiple peers
from client.swarm import swarm

# share file handler module provides file I/O interface
from client.shared_file_handler import torrent_shared_file_handler

# torrent logger module for execution logging
from client.torrent_logger import *

from client.utils import *

from pathlib import Path

TORRENT_FILE_PATH = "torrent_file_path"
DOWNLOAD_DIR_PATH = "download_directory_path"
SEEDING_DIR_PATH = "seeding_directory_path"
MAX_PEERS = "max_peers"
RATE_LIMIT = "rate_limit"
AWS = "AWS"
CREATE_TORRENT = "create_torrent"

torrent_folder_path = 'client\\torrents'

"""
    Torrent client would help interacting with the tracker server and
    download the files from other peers which are participating in sharing
"""


class bittorrent_client:
    """
    initialize the BTP client with torrent file and user arguments
    reads the torrent file and creates torrent class object
    """

    def __init__(self, user_arguments=None):
        # extract the torrent file path

        # bittorrent client logger
        self.bittorrent_logger = torrent_logger(
            "bittorrent", BITTORRENT_LOG_FILE, DEBUG
        )
        self.bittorrent_logger.set_console_logging()

        # self.bittorrent_logger.log("Reading " + torrent_file_path + " file ...")

        # read metadata from the torrent torrent file

        # decide whether the user want to download or seed the torrent
        self.client_request = {
            "seeding": None,
            "downloading": None,
            "uploading rate": sys.maxsize,
            "downloading rate": sys.maxsize,
            "max peers": 4,
            "AWS": False,
        }


        self.seeding_torrents = []
        self.downloading_torrents = []

        self.seeding = []
        self.downloading = []

        self.seed_torrents_path = []
        self.download_torrents_path = []

        self.download_swarms = []
        self.seed_swarms = []

        self.try_load()

        if user_arguments:
            torrent_file_path = user_arguments[TORRENT_FILE_PATH]
            
            self.torrent_info = torrent_file_reader(torrent_file_path)
            # user wants to download the torrent file
            if user_arguments[DOWNLOAD_DIR_PATH]:
                self.client_request["downloading"] = user_arguments[DOWNLOAD_DIR_PATH]
                if user_arguments[RATE_LIMIT]:
                    self.client_request["downloading rate"] = int(
                        user_arguments[RATE_LIMIT]
                    )
            # user wants to seed the torrent file
            elif user_arguments[SEEDING_DIR_PATH]:
                self.client_request["seeding"] = user_arguments[SEEDING_DIR_PATH]
                if user_arguments[RATE_LIMIT]:
                    self.client_request["uploading rate"] = int(user_arguments[RATE_LIMIT])

            # max peer connections
            if user_arguments[MAX_PEERS]:
                self.client_request["max peers"] = int(user_arguments[MAX_PEERS])

            # AWS Cloud test
            if user_arguments[AWS]:
                self.client_request["AWS"] = True
            else:
                self.client_request["AWS"] = False

            # make torrent class instance from torrent data extracted from torrent file
            self.torrent = torrent(self.torrent_info.get_data(), self.client_request)

            self.bittorrent_logger.log(str(self.torrent))

    """
        functions helps in contacting the trackers requesting for 
        swarm information in which multiple peers are sharing file
    """

    def contact_trackers(self):
        self.bittorrent_logger.log("Connecting to Trackers ...")

        # get list of torrent tracker object from torrent file
        self.trackers_list = torrent_tracker(self.torrent)

        # get active tracker object from the list the trackers
        self.active_tracker = self.trackers_list.request_connection()

        self.bittorrent_logger.log(str(self.active_tracker))

    """
        function initilizes swarm from the active tracker connection 
        response peer data participating in file sharing
    """

    def initialize_swarm(self):
        self.bittorrent_logger.log("Initializing the swarm of peers ...")

        # get the peer data from the recieved from the tracker
        peers_data = self.active_tracker.get_peers_data()

        if self.client_request["downloading"] != None:

            # create swarm instance from the list of peers
            self.swarm = swarm(peers_data, self.torrent)

        if self.client_request["seeding"] != None:
            # no need for peers recieved from tracker
            peers_data["peers"] = []
            # create swarm instance for seeding
            self.swarm = swarm(peers_data, self.torrent)

    """
        function helps in uploading the torrent file that client has 
        downloaded completely, basically the client becomes the seeder
    """

    def set_seeding(self, path):
        self.seeding.append(path)

    def set_dowloading(self, path):
        self.downloading.append(path)

    def set_aws(self, val):
        self.client_request["AWS"] = val

    def set_download_rate(self, val):
        self.client_request["downloading rate"] = val
    
    def set_upload_rate(self, val):
        self.client_request["uploading rate"] = val

    def set_torrent(self, path, mode = 'download'):
        if mode == 'download':
            self.download_torrents_path.append(path)
            self._create_torrent(len(self.download_torrents_path) - 1)
        else:
            self.seed_torrents_path.append(path)
            self._create_torrent(len(self.seed_torrents_path) - 1, mode = 'seed')

    def modify_torrent(self, path, index, mode = 'dowload'):
        if mode == 'download':
            self.download_torrents_path[index] = path
            self._create_torrent(index)
        else:
            self.seed_torrents_path[index] = path
            self._create_torrent(index, mode)

    def _create_torrent(self, index, mode = 'download'):
        if mode == 'download':
            info = torrent_file_reader(self.download_torrents_path[index])
            
            if index < len(self.downloading_torrents):
                self.downloading_torrents[index] = torrent(info.get_data(), self.client_request)
            else:
                self.downloading_torrents.append(torrent(info.get_data(), self.client_request))
            
            self.bittorrent_logger.log(str(self.downloading_torrents[index]))
        else:
            info = torrent_file_reader(self.seed_torrents_path[index])

            if index < len(self.seeding_torrents):
                self.seeding_torrents[index] = torrent(info.get_data(), self.client_request)
            else:
                self.seeding_torrents.append(torrent(info.get_data(), self.client_request))
            
            self.bittorrent_logger.log(str(self.seeding_torrents[index]))

    def change_client_request(self, index, mode = 'download'):
        if mode == 'download':
            self.client_request["downloading"] = self.downloading[index]
            self.torrent = self.downloading_torrents[index]
        else:
            self.client_request["seeding"] = self.seeding[index]
            self.torrent = self.seeding_torrents[index]

    def seed(self):
        self.bittorrent_logger.log("Client started seeding ... ")

        # download file initialization
        upload_file_path = self.client_request["seeding"]

        # create file handler for downloading data from peers
        file_handler = torrent_shared_file_handler(upload_file_path, self.torrent)

        # add the file handler
        self.swarm.add_shared_file_handler(file_handler)

        # start seeding the file
        self.swarm.seed_file()

    """
        function helps in downloading the torrent file form swarm 
        in which peers are sharing file data
    """

    def download(self):
        # download file initialization
        download_file_path = (
            self.client_request["downloading"] + self.torrent.torrent_metadata.file_name
        )

        self.bittorrent_logger.log(
            "Initializing the file handler for peers in swarm ... "
        )

        # create file handler for downloading data from peers
        file_handler = torrent_shared_file_handler(download_file_path, self.torrent)

        # initialize file handler for downloading
        file_handler.initialize_for_download()

        # distribute file handler among all peers for reading/writing
        self.swarm.add_shared_file_handler(file_handler)

        self.bittorrent_logger.log(
            "Client started downloading (check torrent statistics) ... "
        )

        # lastly download the whole file
        self.swarm.download_file()

    """
        the event loop that either downloads / uploads a file
    """

    def event_loop(self):
        if self.client_request["downloading"] is not None:
            self.download()
        if self.client_request["seeding"] is not None:
            self.seed()

    def init_download(self):
        index = len(self.downloading) - 1
        self.change_client_request(index)
        self.client_request["seeding"] = None

        self.contact_trackers()

        self._init_swarm()
        
        Thread(target = self._download, args=(index,)).start()
        # fname = self.download_torrents_path[index].split('\\')[-1][:-8]

        # self._autorun(self.download_torrents_path[index], os.path.join(self.downloading[index], fname))

    def init_upload(self):
        index = len(self.seeding) - 1
        self.change_client_request(index, 'seed')
        self.client_request["downloading"] = None

        self.contact_trackers()

        self._init_swarm(mode='seed')

        Thread(target = self._seed, args=(index,)).start()

    def _seed(self, index):
        self.bittorrent_logger.log("Client started seeding ... ")

        upload_file_path = self.client_request["seeding"]

        file_handler = torrent_shared_file_handler(upload_file_path, self.torrent)

        self.seed_swarms[index].add_shared_file_handler(file_handler)

        self.seed_swarms[index].seed_file()

    def _download(self, index):
        download_file_path = (
            self.client_request["downloading"] + self.torrent.torrent_metadata.file_name
        )

        self.bittorrent_logger.log(
            "Initializing the file handler for peers in swarm ... "
        )

        file_handler = torrent_shared_file_handler(download_file_path, self.torrent)

        file_handler.initialize_for_download()

        self.download_swarms[index].add_shared_file_handler(file_handler)

        self.bittorrent_logger.log(
            "Client started downloading (check torrent statistics) ... "
        )

        self.download_swarms[index].download_file()

    def _init_swarm(self, mode = 'download'):
        self.bittorrent_logger.log("Initializing the swarm of peers ...")
        peers_data = self.active_tracker.get_peers_data()
        
        if mode == 'download':
            self.download_swarms.append(swarm(peers_data, self.torrent))
        else:
            peers_data["peers"] = []
            self.seed_swarms.append(swarm(peers_data, self.torrent))

    def try_load(self):
        files_path = list_files_in_directory(torrent_folder_path)

        torrents = []
        dir_path = []

        for path in files_path:
            splitted = path.split('\\')
            if splitted[-1] == 'dir.txt':
                with open(path, 'r') as file:
                    lines = file.readlines()
                    for line in lines:
                        dir_path.append(str(line))

                continue
            
            splitted = path.split('.')

            if splitted[-1] == 'torrent':
                torrents.append(path)

        if len(torrents) == len(dir_path):
            for i, path in enumerate(torrents):
                self._autorun(path, dir_path[i])

    def _autorun(self, tpath, fpath):
        dir_path = os.path.join(torrent_folder_path, 'dir.txt')

        with open(dir_path, 'w') as file:
            # new_path = ''
            # try:
            #     lines = file.readlines()
            
            #     for i, line in enumerate(lines):
            #         if i == len(lines) - 1:
            #             new_path += line
            #         else:
            #             new_path += line + '\n'
            # except:
            #     pass

            # if new_path == '':
            #     new_path = fpath
            # elif fpath not in new_path:
            #     new_path += '\n' + fpath

            file.write(fpath)

        self.set_torrent(tpath, 'seed')
        self.set_seeding(fpath)
        self.init_upload()

    
