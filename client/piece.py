import math

from client.block import Block, BLOCK_SIZE


class Piece:
    def __init__(self, piece_index: int, piece_size: int, piece_hash: str):
        self.piece_index: int = piece_index
        self.piece_size: int = piece_size
        self.piece_hash: str = piece_hash
        self.is_full: bool = False
        self.files = []
        self.raw_data: bytes = b""
        self.number_of_blocks: int = int(math.ceil(float(piece_size) / BLOCK_SIZE))
        self.blocks: list[Block] = []

        self._init_blocks()

    def _init_blocks(self):
        self.blocks = []

        if self.number_of_blocks > 1:
            for i in range(self.number_of_blocks):
                self.blocks.append(Block())

            # Last block of last piece, the special block
            if (self.piece_size % BLOCK_SIZE) > 0:
                self.blocks[self.number_of_blocks - 1].block_size = (
                    self.piece_size % BLOCK_SIZE
                )

        else:
            self.blocks.append(Block(block_size=int(self.piece_size)))
