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

from client.torrent import torrent
from client.client import bittorrent_client
from create_torrent2 import create_torrent
from client.utils import *

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

        threading.Thread(target=self.update_progress_bar, daemon=True).start()

    def update_progress_bar(self):
        while True:
            for i, torrent in enumerate(self.client.downloading_torrents):
                item = self.tableProgress.item(i, 3)
                if item:
                    item.setData(
                        Qt.UserRole + 1000, torrent.file_downloading_percentage
                    )
                self.tableProgress.update()
            time.sleep(1)

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

        if not announce_list:
            announce_list = "http://192.168.43.155:8000"
        if ok and announce_list:
            # Aquí puedes manejar la creación del torrent usando el archivo y la lista de anuncios
            QMessageBox.information(
                self,
                "Información",
                f"Archivo seleccionado: {file_name}\nLista de Anuncios: {announce_list}",
            )
            torrent_folder_path = 'client\\torrents'

            create_torrent(file_name,[announce_list], output=torrent_folder_path)
            splitted = file_name.split('/')

            torrent_path = os.path.join(torrent_folder_path, splitted[-1]) + '.torrent'
            self.client.set_torrent(torrent_path, 'seed')
            self.client.set_seeding(file_name)
            self.client.init_upload()

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
        self.client.set_dowloading("downloads/")
        self.add_torrent_to_main_window(self.client.downloading_torrents[-1])

    def add_torrent_to_main_window(self, torrent: torrent):
        row_count = self.tableProgress.rowCount()
        self.tableProgress.insertRow(row_count)
        row_count += 1

        item1 = QTableWidgetItem(str(row_count))
        item2 = QTableWidgetItem(torrent.torrent_metadata.file_name)

        # checked_elements = self.get_checked_elements()
        # torrent.select_files(checked_elements)
        item3 = QTableWidgetItem(transform_length(torrent.torrent_metadata.file_size))

        delegate = ProgressDelegate(self.tableProgress)
        self.tableProgress.setItemDelegateForColumn(3, delegate)
        item4 = QTableWidgetItem()
        item4.setData(
            Qt.UserRole + 1000, torrent.statistics.file_downloading_percentage
        )

        item1.setTextAlignment(Qt.AlignCenter)
        item2.setTextAlignment(Qt.AlignCenter)
        item3.setTextAlignment(Qt.AlignCenter)
        item4.setTextAlignment(Qt.AlignCenter)
        self.tableProgress.setItem(row_count - 1, 0, item1)
        self.tableProgress.setItem(row_count - 1, 1, item2)
        self.tableProgress.setItem(row_count - 1, 2, item3)
        self.tableProgress.setItem(row_count - 1, 3, item4)

        self.client.init_download()


class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = index.data(Qt.UserRole + 1000)
        opt = QStyleOptionProgressBar()
        opt.rect = option.rect
        opt.minimum = 0
        opt.maximum = 100
        opt.progress = int(progress)
        opt.text = "{}%".format(progress)
        opt.textVisible = True
        QApplication.style().drawControl(QStyle.CE_ProgressBar, opt, painter)


def main():
    app = QApplication(sys.argv)
    window = TorrentClientApp()
    window.show()
    return app.exec_()
