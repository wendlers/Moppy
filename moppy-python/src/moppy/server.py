import threading
import time
import mido
import os

from moppy import player
from flask import Flask, render_template, jsonify, redirect, url_for


class DebugPort(mido.ports.BaseOutput):

    def _send(self, message):
        # print("send: %s" % message)
        pass

    def reset(self):
        pass


class PlayerThread(threading.Thread):

    def __init__(self, base_path, midi_file):
        threading.Thread.__init__(self)

        self.midi_file = midi_file
        self.player = player.Player(DebugPort(), os.path.join(base_path, midi_file))
        self.time = None

    def run(self):

        self.time = time.time()
        self.player.play()


class FlaskApp:

    def __init__(self, port=8088):

        self.port = port
        self.player_thread = None
        self.base_path = os.path.join(os.path.join(os.getenv("HOME"), ".moppy"))
        self.midi_base_path = os.path.join(self.base_path, "songs")

        if not os.path.isdir(self.midi_base_path):
            if not os.path.isdir(self.base_path):
                os.mkdir(self.base_path)
            os.mkdir(self.midi_base_path)

        self.app = Flask(__name__)

        self.app.add_url_rule("/", view_func=self.root)
        self.app.add_url_rule("/play/<file>", view_func=self.play)
        self.app.add_url_rule("/delete/<file>", view_func=self.delete)
        self.app.add_url_rule("/stop", view_func=self.stop)
        self.app.add_url_rule("/status", view_func=self.status)
        self.app.add_url_rule("/upload", view_func=self.upload)

    def run(self):

        self.app.run(host='0.0.0.0', port=self.port, threaded=True, debug=True)

    def root(self):

        midi_files = []

        for file in os.listdir(self.midi_base_path):
            fqn = os.path.join(self.midi_base_path, file)
            if os.path.isfile(fqn) and fqn.endswith(".mid"):
                midi_files.append(file)

        return render_template('root.html', midi_files=midi_files)

    def play(self, file):

        if self.player_thread is not None and self.player_thread.is_alive():
            self.player_thread.player.playing = False
            self.player_thread.join()

        self.player_thread = PlayerThread(self.midi_base_path, file)
        self.player_thread.start()
        s = "Player started: %s" % file

        return s

    def delete(self, file):

        fqn = os.path.join(self.midi_base_path, file)

        if os.path.isfile(fqn):
            os.unlink(fqn)

        return redirect(url_for('root'))

    def stop(self):
        if self.player_thread is None or not self.player_thread.is_alive():
            s = "Player already stopped"
        else:
            self.player_thread.player.playing = False
            self.player_thread.join()
            s = "Player stopped"

        return s

    def status(self):

        s = {
            "file": None,
            "playing": False,
            "length": 120,
            "time": 0
        }

        if self.player_thread is not None:
            s["playing"] = self.player_thread.player.playing
            if self.player_thread.player.playing:
                s["file"] = self.player_thread.midi_file
                s["time"] = int(time.time() - self.player_thread.time)

        return jsonify(s)

    def upload(self):
        return "TBD"

try:

    app = FlaskApp()
    app.run()

except OSError as e:
    print(e)
    exit(1)
except Exception as e:
    print(e)
    exit(1)