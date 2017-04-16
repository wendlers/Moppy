import threading
import time
import mido
import os

from moppy import player
from flask import Flask, render_template, jsonify, redirect, url_for, request, flash
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'mid'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        self.base_path = base_path

        # TODO: read max. channels from kernel module via sysfs
        self.player = player.Player(DebugPort(), ch_max=8)

        self.time = None
        self.length = None

    def run(self):

        midi = mido.MidiFile(os.path.join(self.base_path, self.midi_file))
        info = self.player.analyze(midi)

        # no percussion
        self.player.ch_filter = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]

        # mirror if possible
        if len(set(info["channels"].keys()).intersection(self.player.ch_filter)) <= (self.player.ch_max // 2):
            self.player.ch_mirror = True
            # print("using channel mirror")

        self.length = midi.length
        self.time = time.time()

        self.player.play(midi, info)


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
        self.app.secret_key = '09d8sfoiP(7spfd8uj3%23'

        self.app.add_url_rule("/", view_func=self.root, methods=['GET', 'POST'])
        self.app.add_url_rule("/play/<file>", view_func=self.play)
        self.app.add_url_rule("/delete/<file>", view_func=self.delete)
        self.app.add_url_rule("/stop", view_func=self.stop)
        self.app.add_url_rule("/status", view_func=self.status)

    def run(self):

        self.app.run(host='0.0.0.0', port=self.port, threaded=True, debug=True)

    def root(self):

        if request.method == 'POST':

            if 'file' not in request.files:
                flash('No file was submitted')
            else:
                file = request.files['file']

                if file.filename == '':
                    flash('No file was selected')
                elif file:
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(self.midi_base_path, filename))
                    else:
                        flash("Invalid file type")

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
            "length": 0,
            "time": 0,
            "mirror": False
        }

        if self.player_thread is not None:
            s["playing"] = self.player_thread.player.playing
            if self.player_thread.player.playing:
                s["file"] = self.player_thread.midi_file
                s["time"] = int(time.time() - self.player_thread.time)
                s["length"] = int(self.player_thread.length)
                s["mirror"] = self.player_thread.player.ch_mirror

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
