import sys
import os

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

from client.parser_torrent import parse_torrent_file
from client.torrent import Torrent
from client.utils import transform_length


class TorrentClientApp(QMainWindow):
    def __init__(self):
        super(TorrentClientApp, self).__init__()
        loadUi(
            "client/ui_designs/main_page.ui",
            self,
        )

        self.actionLoad_torrent.triggered.connect(self.open_file_dialog_to_add_torrent)

        headers = ["#", "Name", "Size", "Progress"]
        self.tableProgress.setColumnCount(4)
        self.tableProgress.setRowCount(0)
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
        torrent = Torrent()
        torrent.load_from_path(file_path)
        if file_path:
            self.add_torrent_window = AddTorrentWindow(torrent, self)
            self.add_torrent_window.comboPathDir.addItem(os.path.dirname(file_path))
            self.add_torrent_window.show()


class AddTorrentWindow(QMainWindow):
    def __init__(self, torrent: Torrent, main_window: TorrentClientApp) -> None:
        super(AddTorrentWindow, self).__init__()
        self.main_window: TorrentClientApp = main_window
        self.torrent: Torrent = torrent
        loadUi("client/ui_designs/add_torrent.ui", self)

        # Connect the button to the function to open file dialog
        self.buttonPathDir.clicked.connect(self.open_file_dialog_to_change_path)

        self.treeTorrentFile.setHeaderLabels(["Name", "Type", "Size"])
        self.treeTorrentFile.header().resizeSection(0, 200)
        self.show_torrent_data(torrent)
        self.lineNameTorrent.setText(torrent.name)

        self.buttonOKAddTorrent.clicked.connect(self.add_torrent_to_main_window)

        self.label_5.setText(self.torrent.name)
        self.label_6.setText(self.torrent.comment)
        self.label_7.setText(transform_length(self.torrent.total_length))
        self.treeTorrentFile.clicked.connect(self.torrent_info)

    def open_file_dialog_to_change_path(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.comboPathDir.addItem(folder_path)
            self.comboPathDir.setCurrentText(folder_path)

    def add_torrent_to_main_window(self):
        row_count = self.main_window.tableProgress.rowCount()
        self.main_window.tableProgress.insertRow(row_count)
        row_count += 1

        item1 = QTableWidgetItem(str(row_count))
        item2 = QTableWidgetItem(self.lineNameTorrent.text())

        checked_elements = self.get_checked_elements()
        self.torrent.selected_files(checked_elements)
        item3 = QTableWidgetItem(transform_length(self.torrent.selected_total_length))

        delegate = ProgressDelegate(self.main_window.tableProgress)
        self.main_window.tableProgress.setItemDelegateForColumn(3, delegate)
        item4 = QTableWidgetItem()
        item4.setData(Qt.UserRole + 1000, 0)

        item1.setTextAlignment(Qt.AlignCenter)
        item2.setTextAlignment(Qt.AlignCenter)
        item3.setTextAlignment(Qt.AlignCenter)
        item4.setTextAlignment(Qt.AlignCenter)
        self.main_window.tableProgress.setItem(row_count - 1, 0, item1)
        self.main_window.tableProgress.setItem(row_count - 1, 1, item2)
        self.main_window.tableProgress.setItem(row_count - 1, 2, item3)
        self.main_window.tableProgress.setItem(row_count - 1, 3, item4)

        self.close()

    def torrent_info(self):
        checked_elements = self.get_checked_elements()
        self.torrent.selected_files(checked_elements)
        self.label_7.setText(transform_length(self.torrent.selected_total_length))

    def get_checked_elements(self):
        checked_items = []

        def recurse(parent_item, path):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                grand_children = child.childCount()
                if grand_children > 0:
                    recurse(child, f"{path}/{child.text(0)}")
                else:
                    if child.checkState(0) == Qt.Checked:
                        checked_items.append(path + "/" + child.text(0))

        recurse(self.treeTorrentFile.invisibleRootItem(), "")
        return checked_items

    def show_torrent_data(self, torrent: Torrent):
        # Add root node
        self.treeTorrentFile.clear()
        root_item = QTreeWidgetItem(self.treeTorrentFile)
        root_item.setText(0, torrent.name)
        root_item.setCheckState(0, Qt.Checked)
        root_item.setFlags(root_item.flags() | Qt.ItemFlag.ItemIsTristate)

        if len(torrent.pieces) > 0:
            files = torrent.pieces
            parent_paths = [[]]
            items = [root_item]
            for file_info in files:
                file_name = file_info["path"][-1]
                file_size = file_info["length"]
                file_size = transform_length(file_size)
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
            file_name = torrent.file_names
            file_size = torrent.total_length
            file_size = transform_length(file_size)
            file_type = file_name.split(".")[-1]
            item = QTreeWidgetItem(root_item)
            item.setText(0, file_name)
            item.setText(1, file_type)
            item.setText(2, file_size)


class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = index.data(Qt.UserRole + 1000)
        opt = QStyleOptionProgressBar()
        opt.rect = option.rect
        opt.minimum = 0
        opt.maximum = 100
        opt.progress = progress
        opt.text = "{}%".format(progress)
        opt.textVisible = True
        QApplication.style().drawControl(QStyle.CE_ProgressBar, opt, painter)


def main():
    app = QApplication(sys.argv)
    window = TorrentClientApp()
    window.show()
    return app.exec_()
