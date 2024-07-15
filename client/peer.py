import asyncio
import struct


class Peer:
    def __init__(self, host, port, file_queue):
        self.host = host
        self.port = port
        self.file_queue = file_queue

        # Denotes if peer is choking us
        self.peer_choking = True

        # Denotes if we've informed our peer we're interested
        self.am_interested = False

    async def download(self):
        reader, writer = await asyncio.open_connection(self.host, self.port)

        # Send handshake
        handshake = b"".join(
            [
                chr(19).encode(),
                b"BitTorrent protocol",
                (chr(0) * 8).encode(),
                self.file_queue.info_hash,
                self.file_queue.peer_id,
            ]
        )

        writer.write(handshake)
        await writer.drain()

        # Read and validate response
        peer_handshake = await reader.read(68)
        self.validate(peer_handshake)

        # Start exchangin messages
        buf = b""

        while True:
            resp = await reader.read(2**14)
            buf += resp

            while True:
                if len(buf) < 4:
                    break

                msg_message_length = self.get_message_length(buf)

                if msg_message_length == 0:
                    # Keep alive message
                    continue

                msg_id = struct.unpack(">b", buf[4:5])[0]
                
                # TODO: Me quede aqui
                
                
