import threading
import argparse
import logging
import argparse
import time
import mido
import os

from moppy import player, version, sudo
from flask import Flask, render_template, jsonify
from flask import redirect, url_for, request, flash
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'mid'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class PlayerThread(threading.Thread):

    def __init__(self, base_path, midi_file):
        threading.Thread.__init__(self)

        self.logger = logging.getLogger('playert')

        self.midi_file = midi_file
        self.base_path = base_path

        if os.path.isdir('/sys/kernel/moppy'):
            port = player.MoppySysfsPort()
            self.logger.info("Using sysfs port for output")
        else:
            port = player.NullPort()
            self.logger.info("Using null port for output")

        # TODO: read max. channels from kernel module via sysfs
        self.player = player.Player(port, ch_max=8)

        self.time = None
        self.length = None

    def run(self):

        midi = mido.MidiFile(os.path.join(self.base_path, self.midi_file))
        info = self.player.analyze(midi)

        # no percussion
        self.player.ch_filter = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10,
                                 11, 12, 13, 14, 15]

        # mirror if possible
        if len(set(info["channels"].keys()).intersection(
                self.player.ch_filter)) <= (self.player.ch_max // 2):
            self.player.ch_mirror = True
            self.player.ch_max = self.player.ch_max // 2
            self.logger.info("Enabled channel mirroring")

        self.length = midi.length
        self.time = time.time()

        self.player.play(midi, info)


class FlaskApp:

    def __init__(self, home_dir=None, port=8088):

        self.logger = logging.getLogger('webapp')

        self.port = port
        self.player_thread = None

        if home_dir is None:
            home_dir = os.getenv("HOME")

        self.base_path = os.path.join(os.path.join(home_dir,
                                                   ".moppy"))

        self.logger.info('Base dir is: %s' % self.base_path)

        self.midi_base_path = os.path.join(self.base_path, "songs")

        if not os.path.isdir(self.midi_base_path):
            if not os.path.isdir(self.base_path):
                os.mkdir(self.base_path)
            os.mkdir(self.midi_base_path)

        self.app = Flask(__name__)
        self.app.secret_key = '09d8sfoiP(7spfd8uj3%23'

        self.app.add_url_rule("/", view_func=self.root,
                              methods=['GET', 'POST'])
        self.app.add_url_rule("/play/<file>", view_func=self.play)
        self.app.add_url_rule("/delete/<file>", view_func=self.delete)
        self.app.add_url_rule("/stop", view_func=self.stop)
        self.app.add_url_rule("/status", view_func=self.status)

    def run(self):

        self.app.run(host='0.0.0.0', port=self.port, threaded=True,
                     debug=False)

    def root(self):

        if request.method == 'POST':

            if 'file' not in request.files:
                flash('No file was submitted')
                self.logger.warning('No file was submitted')
            else:
                file = request.files['file']

                if file.filename == '':
                    flash('No file was selected')
                    self.logger.warning('No file was selected')
                elif file:
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(self.midi_base_path, filename))
                    else:
                        flash('Invalid file type')
                        self.logger.warning('Invalid file type: %s' %
                                         file.filename)

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

        self.logger.info('Now playing: %s' % file)

        return s

    def delete(self, file):

        fqn = os.path.join(self.midi_base_path, file)

        if os.path.isfile(fqn):
            os.unlink(fqn)

        self.logger.info("Deleted: %s" % file)

        return redirect(url_for('root'))

    def stop(self):
        if self.player_thread is None or not self.player_thread.is_alive():
            s = "Player already stopped"
        else:
            self.player_thread.player.playing = False
            self.player_thread.join()
            s = "Player stopped"
            self.logger.info('Stopped playing')

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


def main():

    parser = argparse.ArgumentParser(description='MoppyServer %s' %
                                     version.FULL)

    parser.add_argument("--logfile", help="write log to file",
                        default=None)

    parser.add_argument("--loglevel",
                        help="loglevel (CRITICAL, ERROR, WARNING, INFO," +
                        " DEBUG)", default="INFO")

    parser.add_argument("--user", help="run as user",
                        default=None)

    args = parser.parse_args()

    if args.logfile is not None:
        logging.basicConfig(format='%(asctime)-15s %(name)-10s %(message)s',
                            filename=os.path.expanduser(args.logfile),
                            level=args.loglevel)
    else:
        logging.basicConfig(format='%(asctime)-15s %(name)-10s %(message)s',
                            level=args.loglevel)

    logging.info('MoppyServer %s' % version.FULL)

    home_dir = None

    if args.user is not None:
        logging.info('Running as user: %s' % args.user)
        sudo.drop_privileges(args.user)

        # FIXME we don't know if this is the user home dir
        home_dir = '/home/' + args.user

    app = FlaskApp(home_dir=home_dir)
    app.run()


if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
