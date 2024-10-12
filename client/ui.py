import json
import sys
import os
import hashlib
import threading
import time
import urllib
import requests
import random
import os
import socket

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QTreeWidgetItem,
    QTableWidgetItem,
    QStyledItemDelegate,
    QStyleOptionProgressBar,
    QApplication,
    QStyle,
)
from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi
from client.resources_rc import *
from bcoding import bdecode, bencode

from client.client import bittorrent_client

MAX_PEERS_TRY_CONNECT = 30
MAX_PEERS_CONNECTED = 8


class TorrentClientApp(QMainWindow):
    def __init__(self):
        super(TorrentClientApp, self).__init__()
        loadUi(
            "client/ui_designs/main_page.ui",
            self,
        )

        self.actionLoad_torrent.triggered.connect(self.open_file_dialog_to_add_torrent)
        self.actionCreate_torrent.triggered.connect(
            self.open_file_dialog_to_create_torrent
        )

        headers = ["#", "Name", "Size", "Progress"]
        self.tableProgress.setColumnCount(4)
        self.tableProgress.setRowCount(0)
        self.tableProgress.setHorizontalHeaderLabels(headers)

        self.percentage_completed = -1
        self.last_log_line = ""

        self.server_address = socket.gethostbyname(socket.gethostname())

    def _exit_threads(self):
        self.peers_manager.is_active = False
        os._exit(0)

    def open_file_dialog_to_create_torrent(self):
        # Open the folder selection dialog
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Torrent File",
            "",
            "Torrent Files (*.torrent)",
            options=options,
        )
        
        # if file_path:  # Check if a folder was selected
            # self.create_torrent(
            #     self.server_address,
            #     folder_path,
            #     [f"http://{self.server_address}:8000"],
            #     folder_name,
            # )
            
    def open_file_dialog_to_add_torrent(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Torrent File",
            "",
            "Torrent Files (*.torrent)",
            options=options,
        )
        self.client: bittorrent_client = bittorrent_client(file_path)
        
def main():
    app = QApplication(sys.argv)
    window = TorrentClientApp()
    window.show()
    return app.exec_()
