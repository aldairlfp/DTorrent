import sys
import os

from PyQt5.QtGui import QIcon, QStandardItemModel
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QTreeWidgetItem,
)
from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi
from client.resources_rc import *

from client.parser_torrent import parse_torrent_file


class TorrentClientApp(QMainWindow):
    def __init__(self):
        super(TorrentClientApp, self).__init__()
        loadUi(
            "client/ui_designs/main_page.ui",
            self,
        )

        self.actionLoad_torrent.triggered.connect(self.open_file_dialog_to_add_torrent)

        headers = ["#", "Name", "Size"]
        self.tableProgress.setColumnCount(3)
        self.tableProgress.setRowCount(1)
        self.tableProgress.setHorizontalHeaderLabels(headers)

    def open_file_dialog_to_add_torrent(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Torrent File",
            "",
            "Torrent Files (*.torrent)",
            options=options,
        )
        torrent_data = parse_torrent_file(file_path)
        if file_path:
            self.add_torrent_window = AddTorrentWindow(torrent_data)
            self.add_torrent_window.comboPathDir.addItem(os.path.dirname(file_path))
            self.add_torrent_window.show()


class AddTorrentWindow(QMainWindow):
    def __init__(self, torrent_data) -> None:
        super(AddTorrentWindow, self).__init__()
        loadUi("client/ui_designs/add_torrent.ui", self)

        # Connect the button to the function to open file dialog
        self.buttonPathDir.clicked.connect(self.open_file_dialog_to_change_path)

        self.treeTorrentFile.setHeaderLabels(["Name", "Type", "Size"])
        self.treeTorrentFile.header().resizeSection(0, 200)
        self.show_torrent_data(torrent_data)
        self.lineNameTorrent.setText(torrent_data["info"]["name"])

    def open_file_dialog_to_change_path(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.comboPathDir.addItem(folder_path)
            self.comboPathDir.setCurrentText(folder_path)

    def show_torrent_data(self, torrent_data):
        # Add root node
        self.treeTorrentFile.clear()
        root_item = QTreeWidgetItem(self.treeTorrentFile)
        root_item.setText(0, torrent_data["info"]["name"])
        root_item.setCheckState(0, Qt.Checked)
        root_item.setFlags(root_item.flags() | Qt.ItemFlag.ItemIsTristate)

        if "files" in torrent_data["info"]:
            files = torrent_data["info"]["files"]
            parent_paths = [[]]
            items = [root_item]
            for file_info in files:
                file_name = file_info["path"][-1]
                file_size = file_info["length"]
                if file_size >= 1024 * 1024:
                    file_size = f"{file_size/(1024*1024):.2f} MB"
                elif file_size >= 1024:
                    file_size = f"{file_size/1024:.2f} KB"
                else:
                    file_size = f"{file_size} B"
                file_type = file_info["path"][-1].split(".")[-1]

                # Find the common parent folder
                count_index = 0
                while count_index < len(file_info["path"]):
                    if (
                        count_index >= len(parent_paths[-1])
                        or file_info["path"][count_index]
                        != parent_paths[-1][count_index]
                    ):
                        break
                    count_index += 1

                # Remove the nodes that are not common
                for i in range(len(parent_paths[-1]) - 1, count_index - 1, -1):
                    parent_paths.pop()
                    items.pop()

                # Add the new nodes
                directory = file_info["path"][:-1]
                for i in range(count_index, len(directory)):
                    parent_paths.append(directory)
                    item = QTreeWidgetItem(items[-1])
                    item.setText(0, directory[i])
                    item.setCheckState(0, Qt.Checked)
                    item.setIcon(0, QIcon("client/ui_designs/icons/folder.png"))
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsTristate)
                    items.append(item)

                # Add the file node
                item = QTreeWidgetItem(items[-1])
                item.setText(0, file_name)
                item.setText(1, file_type)
                item.setText(2, file_size)
                item.setCheckState(0, Qt.Checked)
                item.setIcon(0, QIcon("client/ui_designs/icons/file.png"))

        else:
            file_name = torrent_data["info"]["name"]
            file_size = torrent_data["info"]["length"]
            if file_size >= 1024 * 1024:
                file_size = f"{file_size/(1024*1024):.2f} MB"
            elif file_size >= 1024:
                file_size = f"{file_size/1024:.2f} KB"
            else:
                file_size = f"{file_size} B"
            file_type = file_name.split(".")[-1]
            item = QTreeWidgetItem(root_item)
            item.setText(0, file_name)
            item.setText(1, file_type)
            item.setText(2, file_size)

    def addFilePathWithCheckBox(self, filepath):
        parts = filepath.split(os.path.sep)
        parent_item = self.treeTorrentFile.invisibleRootItem()
        for part in parts[:-1]:
            child_item = self.treeTorrentFile.findChild(QTreeWidgetItem, [part])
            if not child_item:
                child_item = QTreeWidgetItem(parent_item, [part])
            parent_item = child_item
        item = QTreeWidgetItem(parent_item, [parts[-1]])
        item.setCheckState(0, Qt.Checked)
        item.setData(0, Qt.UserRole, filepath)


def main():
    app = QApplication(sys.argv)
    window = TorrentClientApp()
    window.show()
    return app.exec_()
