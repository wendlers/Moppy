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
        self.app.secret_key = '09d8sfoiP(7spfd8uj3%23'

        self.app.add_url_rule("/", view_func=self.root, methods=['GET', 'POST'])
        self.app.add_url_rule("/play/<file>", view_func=self.play)
        self.app.add_url_rule("/delete/<file>", view_func=self.delete)
        self.app.add_url_rule("/stop", view_func=self.stop)
        self.app.add_url_rule("/status", view_func=self.status)
        self.app.add_url_rule("/upload", view_func=self.upload, methods=['GET', 'POST'])

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

        if request.method == 'POST':
            # check if the post request has the file part
            if 'file' not in request.files:
                flash('No file part')
                return redirect(request.url)
            file = request.files['file']
            # if user does not select file, browser also
            # submit a empty part without filename
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(self.midi_base_path, filename))
                return redirect(url_for('root'))
        return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
          <p><input type=file name=file>
             <input type=submit value=Upload>
        </form>
        '''
try:

    app = FlaskApp()
    app.run()

except OSError as e:
    print(e)
    exit(1)
except Exception as e:
    print(e)
    exit(1)