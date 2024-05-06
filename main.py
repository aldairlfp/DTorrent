# import client.bencoder as bencoder

# f = open("razdacha-ne-suschestvuet.torrent", "rb")
# d = bencoder.decode(f.read())
# del d[b"info"][b"pieces"] # That's a long hash
# from pprint import pprint
# pprint(d)

import sys
import client.ui as ui

sys.exit(ui.main())