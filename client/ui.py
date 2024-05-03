# import tkinter as tk
# from tkinter import filedialog
# import os
# import threading
# import client.bencoder as bencoder
# # import torrent_parser

# class BitTorrentUI:
#     def __init__(self, master):
#         self.master = master
#         master.title("BitTorrent Downloader")

#         self.label = tk.Label(master, text="Select .torrent files:")
#         self.label.pack()

#         self.browse_button = tk.Button(master, text="Browse", command=self.browse)
#         self.browse_button.pack()

#     def browse(self):
#         filenames = filedialog.askopenfilenames(initialdir=os.getcwd(), title="Select .torrent files", filetypes=(("Torrent files", "*.torrent"), ("All files", "*.*")))
#         if filenames:
#             for filename in filenames:
#                 t = threading.Thread(target=self.download_torrent, args=(filename,))
#                 t.start()

#     def download_torrent(self, torrent_file):
#         with open(torrent_file, 'rb') as f:
#             torrent_data = bencoder.decode(f.read())

#         # torrent = torrent_parser.parse_torrent(torrent_data)
#         # downloader = torrent_parser.BitTorrentDownloader(torrent)
#         torrent = torrent_data

#         self.progress_label = tk.Label(self.master, text=b"Downloading: " + torrent[b'info'][b'name'])
#         self.progress_label.pack()

#         # Change the output directory
#         output_dir = os.path.join(os.getcwd(), torrent[b'info'][b'name'].decode())
#         if not os.path.exists(output_dir):
#             os.makedirs(output_dir)

#         # downloader.start(output_dir)
#         self.progress_label.config(text="Download complete!")

# def main():
#     root = tk.Tk()
#     app = BitTorrentUI(root)
#     root.mainloop()

# if __name__ == "__main__":
#     main()

# import tkinter as tk
# from tkinter import filedialog

# class TorrentClientApp:
#     def __init__(self, master):
#         self.master = master
#         master.title("Torrent Client")

#         self.label = tk.Label(master, text="Welcome to Torrent Client")
#         self.label.pack()

#         self.select_button = tk.Button(master, text="Select Torrent File", command=self.select_torrent_file)
#         self.select_button.pack()

#         self.download_button = tk.Button(master, text="Download", command=self.download_torrent)
#         self.download_button.pack()

#         self.quit_button = tk.Button(master, text="Quit", command=master.quit)
#         self.quit_button.pack()

#     def select_torrent_file(self):
#         self.torrent_file_path = filedialog.askopenfilename(filetypes=[("Torrent Files", "*.torrent")])
#         print("Selected Torrent File:", self.torrent_file_path)

#     def download_torrent(self):
#         if hasattr(self, 'torrent_file_path'):
#             print("Downloading Torrent:", self.torrent_file_path)
#             # Add your download logic here
#         else:
#             print("Please select a torrent file first.")

# def main():
#     root = tk.Tk()
#     app = TorrentClientApp(root)
#     root.mainloop()

# if __name__ == "__main__":
#     main()

import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from client.bencoder import decode
from client.parser_torrent import parse_torrent_file

class TorrentClientApp:
    def __init__(self, master):
        self.master = master
        master.title("Torrent Client")

        self.label = tk.Label(master, text="Welcome to Torrent Client")
        self.label.pack()

        self.select_button = tk.Button(master, text="Select Torrent File", command=self.select_torrent_file)
        self.select_button.pack()

        self.file_label = tk.Label(master, text="")
        self.file_label.pack()

        self.select_file_button = tk.Button(master, text="Select File", command=self.select_file)
        self.select_file_button.pack()

        self.download_button = tk.Button(master, text="Download", command=self.download_torrent)
        self.download_button.pack()

        self.quit_button = tk.Button(master, text="Quit", command=master.quit)
        self.quit_button.pack()

    def select_torrent_file(self):
        # self.torrent_file_path = filedialog.askopenfilename(filetypes=[("Torrent Files", "*.torrent")])
        self.torrent_file_path = "razdacha-ne-suschestvuet.torrent"
        print("Selected Torrent File:", self.torrent_file_path)
        self.torrent_data = parse_torrent_file(self.torrent_file_path)
        if 'files' in self.torrent_data['info']:
            self.files = self.torrent_data['info']['files']
            self.file_label.config(text="Files available for download:")

    def select_file(self):
        self.selected_file_index = tk.simpledialog.askinteger("Select File", "Enter the index of the file you want to download:")
        if self.selected_file_index is not None:
            self.selected_file_path = '/'.join(self.files[self.selected_file_index]['path'][0])
            print("Selected File:", self.selected_file_path)
            self.show_path_tree()

    def show_path_tree(self):
        path_tree_window = tk.Toplevel(self.master)
        path_tree_window.title("File Path Tree")

        tree = ttk.Treeview(path_tree_window)
        tree.pack(expand=True, fill=tk.BOTH)

        # Add a root node
        root_node = tree.insert("", "end", text=self.selected_file_path, open=True)

        # Add child nodes
        path_parts = self.selected_file_path.split('/')
        parent = root_node
        for part in path_parts[:-1]:
            parent = tree.insert(parent, "end", text=part)

        # Highlight the last part (file name)
        tree.insert(parent, "end", text=path_parts[-1], tags="file")
        tree.tag_configure("file", foreground="blue")

    def download_torrent(self):
        if hasattr(self, 'torrent_file_path') and hasattr(self, 'selected_file_path'):
            download_path = filedialog.askdirectory(title="Select Download Location")
            print("Download Location:", download_path)
            # Add your download logic here
        else:
            print("Please select a torrent file and file to download first.")

def main():
    root = tk.Tk()
    app = TorrentClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()