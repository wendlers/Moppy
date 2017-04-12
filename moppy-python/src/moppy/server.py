import threading
import time
import player
import mido
import os

from flask import Flask, render_template, jsonify


class DebugPort(mido.ports.BaseOutput):

    def _send(self, message):
        #print("send: %s" % message)
        pass

    def reset(self):
        pass

class PlayerThread(threading.Thread):

    def __init__(self, midi_file):
        threading.Thread.__init__(self)

        base_path = '/local00/sandbox/pyvenv/Moppy/moppy-desk/samplesongs'

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

        self.app = Flask(__name__)
        self.app.secret_key = '21ojfß9ssfajlök'

        self.app.add_url_rule("/", view_func=self.root)
        self.app.add_url_rule("/play/<file>", view_func=self.play)
        self.app.add_url_rule("/stop", view_func=self.stop)
        self.app.add_url_rule("/status", view_func=self.status)

    def run(self):

        self.app.run(host='0.0.0.0', port=self.port, threaded=True, debug=True)


    def root(self):

        base_path = '/local00/sandbox/pyvenv/Moppy/moppy-desk/samplesongs'

        midi_files = []

        for file in os.listdir(base_path):
            fqn = os.path.join(base_path, file)
            if os.path.isfile(fqn) and fqn.endswith(".mid"):
                midi_files.append(file)

        return render_template('root.html', midi_files=midi_files)

    def play(self, file):

        if self.player_thread is not None and self.player_thread.is_alive():
            self.player_thread.player.playing = False
            self.player_thread.join()

        self.player_thread = PlayerThread(file)
        self.player_thread.start()
        s = "Player started: %s" % file

        return s

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
try:

    app = FlaskApp()
    app.run()

except OSError as e:
    print(e)
    exit(1)
except Exception as e:
    print(e)
    exit(1)