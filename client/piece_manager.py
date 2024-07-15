from client.torrent import Torrent
from client.piece import Piece
import random


class PieceManager:
    def __init__(self, torrent: Torrent):
        self.torrent: Torrent = torrent
        self.number_of_pieces = torrent.number_of_pieces
        self.pieces = self._generate_pieces()
        self.left_pieces = [piece for piece in self.pieces]
        self.downloding = []
        self.files = self._load_files()
        self.complete_pieces = 0
        self.peers = []

        for file in self.files:
            id_piece = file["idPiece"]
            self.pieces[id_piece].files.append(file)

    def _generate_pieces(self):
        pieces = []
        last_piece = self.number_of_pieces - 1

        for i in range(self.number_of_pieces):
            start = i * 20
            end = start + 20

            if i == last_piece:
                piece_length = (
                    self.torrent.total_length
                    - (self.number_of_pieces - 1) * self.torrent.piece_length
                )
                pieces.append(Piece(i, piece_length, self.torrent.pieces[start:end]))
            else:
                pieces.append(
                    Piece(i, self.torrent.piece_length, self.torrent.pieces[start:end])
                )

        return pieces
    
    def set_peers(self, peers):
        self.peers = peers

    def get_peers(self):
        return self.peers
    
    def get_random_peer(self):
        rng = random.randint(0, len(self.peers))
        return self.peers[rng]
    
    def set_download(self, piece):
        if piece in self.left_pieces:
            index = self.left_pieces.index(piece)
            self.left_pieces.pop(index)
            self.downloding.append(piece)
        else:
            print(f'Piece: {piece} is not in left pieces list.')

    def handle_downloding_error(self, piece):
        if piece in self.downloding:
            index = self.downloding.index(piece)
            self.downloding.pop(index)
            self.left_pieces.append(piece)
        else:
            print(f'Piece: {piece} is not in download list.')

    def _load_files(self):
        files = []
        piece_offset = 0
        piece_size_used = 0

        for f in self.torrent.file_names:
            current_size_file = f["length"]
            file_offset = 0

            while current_size_file > 0:
                id_piece = int(piece_offset / self.torrent.piece_length)
                piece_size = self.pieces[id_piece].piece_size - piece_size_used

                if current_size_file - piece_size < 0:
                    file = {
                        "length": current_size_file,
                        "idPiece": id_piece,
                        "fileOffset": file_offset,
                        "pieceOffset": piece_size_used,
                        "path": f["path"],
                    }
                    piece_offset += current_size_file
                    file_offset += current_size_file
                    piece_size_used += current_size_file
                    current_size_file = 0

                else:
                    current_size_file -= piece_size
                    file = {
                        "length": piece_size,
                        "idPiece": id_piece,
                        "fileOffset": file_offset,
                        "pieceOffset": piece_size_used,
                        "path": f["path"],
                    }
                    piece_offset += piece_size
                    file_offset += piece_size
                    piece_size_used = 0

                files.append(file)
        return files

    # TODO: Implement this method
    def have_all_pieces(self):
        return self.complete_pieces == self.number_of_pieces
