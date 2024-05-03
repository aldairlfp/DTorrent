import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import Image, ImageTk
from client.parser_torrent import parse_torrent_file


class TorrentClientApp:
    def __init__(self, master):
        self.master = master
        master.title("DTorrent Client")

        self.label = tk.Label(master, text="Welcome to DTorrent Client")
        self.label.pack()

        self.select_button = tk.Button(
            master, text="Select Torrent File", command=self.select_torrent_file
        )
        self.select_button.pack()

        self.file_label = tk.Label(master, text="")
        self.file_label.pack()

        self.select_file_button = tk.Button(
            master, text="Select File", command=self.show_path_tree_torrent
        )
        self.select_file_button.pack()

        self.download_button = tk.Button(
            master, text="Download", command=self.download_torrent
        )
        self.download_button.pack()

        self.quit_button = tk.Button(master, text="Quit", command=master.quit)
        self.quit_button.pack()

    def select_torrent_file(self):
        self.torrent_file_path = filedialog.askopenfilename(
            filetypes=[("Torrent Files", "*.torrent")]
        )
        print("Selected Torrent File:", self.torrent_file_path)
        self.torrent_data = parse_torrent_file(self.torrent_file_path)
        if "files" in self.torrent_data["info"]:
            self.files = self.torrent_data["info"]["files"]
            self.file_label.config(text="Files available for download:")

    def show_path_tree_torrent(self):
        path_tree_window = tk.Toplevel(self.master)
        path_tree_window.title("Torrent File Path Tree")

        tree = CheckboxTreeview(path_tree_window, columns=["Size"])
        tree.pack(expand=True, fill=tk.BOTH)

        tree.heading("#0", text="Directory structure", anchor="w")
        tree.heading("#1", text="File size", anchor="w")

        # Add a root node
        root_node = tree.insert("", "end", text=self.torrent_file_path, open=True)

        if "files" in self.torrent_data["info"]:
            parents_paths = [[]]
            parents_nodes = [root_node]
            for file_info in self.files:
                file_path = file_info["path"]
                file_size = file_info["length"]
                if file_size >= 1024 * 1024:
                    file_size = f"{file_size/(1024*1024):.2f} MB"
                elif file_size >= 1024:
                    file_size = f"{file_size/1024:.2f} KB"
                else:
                    file_size = f"{file_size} B"

                # Find the common parent folder
                count_index = 0
                while count_index < len(file_path):
                    if (
                        count_index >= len(parents_paths[-1])
                        or file_path[count_index] != parents_paths[-1][count_index]
                    ):
                        break
                    count_index += 1

                # Remove the nodes that are not common
                for i in range(len(parents_paths[-1]) - 1, count_index - 1, -1):
                    parents_nodes.pop()
                    parents_paths.pop()

                # Add the new nodes
                for i in range(count_index, len(file_path[:-1])):
                    folder_node = tree.insert(
                        parents_nodes[-1],
                        "end",
                        text=file_path[:-1][i],
                    )
                    parents_nodes.append(folder_node)
                parents_paths.append(file_path[:-1])

                # Add the file node
                tree.insert(
                    parents_nodes[-1], "end", text=file_path[-1], values=(file_size,)
                )

    def download_torrent(self):
        if hasattr(self, "torrent_file_path") and hasattr(self, "selected_file_path"):
            download_path = filedialog.askdirectory(title="Select Download Location")
            print("Download Location:", download_path)
            # Add your download logic here
        else:
            print("Please select a torrent file and file to download first.")


def set_app_icon(window):
    ico = Image.open("icon.png")
    photo = ImageTk.PhotoImage(ico)
    window.wm_iconphoto(False, photo)


def main():
    root = tk.Tk()
    root.geometry("400x150")
    set_app_icon(root)
    app = TorrentClientApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
