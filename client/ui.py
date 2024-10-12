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
    QInputDialog,
    QMessageBox,
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
from create_torrent2 import create_torrent

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
        self.client: bittorrent_client = bittorrent_client()

    def _exit_threads(self):
        self.peers_manager.is_active = False
        os._exit(0)

    def open_file_dialog_to_create_torrent(self):
        # Open the folder selection dialog
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Any File",
            "",
            "All Files (*);;Torrent Files (*.torrent);;RAR Files (*.rar)",
            options=options,
        )

        if file_path:
            # Si se seleccionó un archivo, abrir el diálogo para ingresar la lista de anuncios
            self.get_announce_list(file_path)

    def get_announce_list(self, file_name):
        # Diálogo para ingresar la lista de anuncios
        announce_list, ok = QInputDialog.getText(
            self, "Lista de Anuncios", "Ingrese la URL del tracker:"
        )

        if ok and announce_list:
            # Aquí puedes manejar la creación del torrent usando el archivo y la lista de anuncios
            QMessageBox.information(
                self,
                "Información",
                f"Archivo seleccionado: {file_name}\nLista de Anuncios: {announce_list}",
            )
            create_torrent(file_name,[announce_list])
            torrent_path = os.path.abspath(file_name) + '.torrent'
            self.client.set_torrent(torrent_path, 'seed')
            self.client.set_seeding(file_name)
            self.client.init_upload(len(self.client.seeding) - 1)

    def open_file_dialog_to_add_torrent(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Torrent File",
            "",
            "Torrent Files (*.torrent)",
            options=options,
        )
        self.client.set_torrent(file_path)
        self.client.set_dowloading('.\\downloads')
        self.client.init_download(len(self.client.downloading) - 1)


def main():
    app = QApplication(sys.argv)
    window = TorrentClientApp()
    window.show()
    return app.exec_()
