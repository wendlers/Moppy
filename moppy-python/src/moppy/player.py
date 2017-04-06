import argparse
import operator
import curses
import mido
import os


class NullPort(mido.ports.BaseOutput):

    def _send(self, message):
        pass

    def reset(self):
        pass


class MoppySysfsPort(mido.ports.BaseOutput):

    def _write_sysfs(self, msg, target="freq"):

        with open("/sys/kernel/moppy/" + target, "w") as f:
            f.write(msg)

    def _send(self, message):

        if message.type == 'note_on':

            msg = "%d, %d" % (message.channel, message.note)
            self._write_sysfs(msg, "note")

        elif message.type == 'note_off':
            msg = "%d, %d" % (message.channel, 0)

            # print(msg)
            self._write_sysfs(msg)

        else:
            print("** unsupported message type: %s" % message.type)

    def reset(self):

        self._write_sysfs("reset", "ctrl")


class Player:

    def __init__(self, port, filename, ch_max=4, ch_filter=None,
                 ch_optimize=True, octave_optimize=True, update_hook=None):

        self.port = port
        self.filename = filename

        if ch_filter is None:
            self.ch_filter = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        else:
            self.ch_filter = ch_filter

        self.ch_max = ch_max
        self.ch_optimize = ch_optimize
        self.octave_optimize = octave_optimize

        self.update_hook = update_hook
        self.playing = False

    def play(self, midi=None, info=None):

        self.port.reset()

        if midi is None:
            midi = mido.MidiFile(self.filename)

        if info is None:
            info = self.analyze(midi)

        ch_map = {}

        if self.ch_optimize:

            most_used_channels = sorted(info["channels"].items(), key=operator.itemgetter(1),
                                        reverse=True)

            mapped_ch = 0

            for ch, _ in most_used_channels:
                if ch in self.ch_filter:

                    ch_map[ch] = mapped_ch
                    mapped_ch += 1

                    if mapped_ch == self.ch_max:
                        break
        else:

            for ch in self.ch_filter:
                ch_map[ch] = ch

        self.playing = True

        for msg in midi.play():

            if not self.playing:
                break

            if msg.type in ['note_on', 'note_off'] and msg.channel in ch_map:

                if self.octave_optimize:
                    msg = self.constraint_octave(msg)

                msg.channel = ch_map[msg.channel]

                octave = msg.note // 12 - 1

                if self.update_hook is not None:
                    if msg.type == 'note_on':
                        self.update_hook(msg.channel, octave, msg.note % 12)
                    else:
                        self.update_hook(msg.channel, octave, 12)

                self.port.send(msg)

        self.port.reset()

    @staticmethod
    def analyze(midi):

        stats = {
            "channels": {},
            "octaves": {},
        }

        for msg in midi:

            if not msg.is_meta and msg.type == 'note_on':

                if msg.channel in stats["channels"]:
                    stats["channels"][msg.channel] += 1
                else:
                    stats["channels"][msg.channel] = 1

                octave = int(msg.note / 12) - 1

                if octave in stats["octaves"]:
                    stats["octaves"][octave] += 1
                else:
                    stats["octaves"][octave] = 1

                    # print(msg)

        return stats

    @staticmethod
    def constraint_octave(msg):

        octave = msg.note // 12 - 1

        if octave < 2:
            msg.note += (2 - octave) * 12
        elif octave > 5:
            msg.note -= (octave - 5) * 12

        return msg

    def stop(self):
        self.playing = False


class VisualPlayer(Player):

    def __init__(self, port, filename, ch_max=4, ch_filter=None, ch_optimize=True, octave_optimize=True):

        Player.__init__(self, port, filename, ch_max, ch_filter, ch_optimize, octave_optimize, self.set_note)

        self.ch_last_oct = {}
        self.info_height = 15

        self.file_info = [
            "",
            (0, 0),
            0,
            0,
            0,
            "",
            0,
            "",
            ""
        ]

        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        self.stdscr.nodelay(True)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_RED)

        self.stdscr.bkgd(curses.color_pair(1))
        self.show()

    def __del__(self):

        self.hide()

    def hide(self):

        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def show(self):

        self.stdscr.refresh()

        y, x = self.stdscr.getmaxyx()

        self.max_x = x
        self.max_y = y

        if self.max_x >= 95 and self.max_y >= 35:

            self.win_info = curses.newwin(self.info_height, self.max_x, 1, 0)
            self.win_info.bkgd(curses.color_pair(1))
            self.win_info.box()
            self.win_info.refresh()

            self.win_notes = curses.newwin(self.max_y - (self.info_height + 1), self.max_x, (self.info_height + 1), 0)
            self.win_notes.bkgd(curses.color_pair(1))
            self.win_notes.box()
            self.win_notes.refresh()

            self.win_menu = curses.newwin(1, self.max_x, 0, 0)
            self.win_menu.bkgd(curses.color_pair(2))
            self.win_menu.addstr(0, 1, "F10: exit")
            self.win_menu.refresh()

            self.show_notes()
            self.update_file_info()

        else:
            self.hide()
            print("*** window too small ***")
            exit(1)

        self.stdscr.refresh()

    def show_notes(self):

        self.ch_last_oct = {}

        y = (self.max_y - self.info_height - 12) // 2
        x = (self.max_x - 88) // 2

        self.win_notes.addstr(y, x, "c/o    0    1    2    3    4    5    6    7    8    9   10   11" +
                              "   12   13   14   15  c/o", curses.color_pair(2))

        for o in range(10):
            self.win_notes.addstr(y + 1 + o, x, " %d " % o, curses.color_pair(2))

            for c in range(16):
                self.win_notes.addstr(y + 1 + o, x + 5 + c * 5, "   ", curses.color_pair(3))

            self.win_notes.addstr(y + 1 + o, x + 10 + c * 5, " %d " % o, curses.color_pair(2))

        self.win_notes.addstr(y + 11, x, "c/o    0    1    2    3    4    5    6    7    8    9   10   11" +
                              "   12   13   14   15  c/o", curses.color_pair(2))

        self.win_notes.refresh()

    def set_note(self, ch, oct, note):

        notes = [
            " C ", " C#", " D ", " D#", " E ", " F ",
            " F#", " G ", " G#", " A ", " A#", " B ",
            " * "
        ]

        y = (self.max_y - self.info_height - 12) // 2 + 1
        x = (self.max_x - 88) // 2 + 5

        if ch in self.ch_last_oct:
            self.win_notes.addstr(y + self.ch_last_oct[ch], x + 5 * ch, '   ', curses.color_pair(4))

        self.win_notes.addstr(y + oct, x + 5 * ch, notes[note], curses.color_pair(3))
        self.ch_last_oct[ch] = oct

        self.win_notes.refresh()

        self.handle_keys()

    def update_file_info(self):

        self.win_info.addstr( 2, 3, "File           : %s" % self.file_info[0])
        self.win_info.addstr( 3, 3, "Length         : %02d:%02d" % self.file_info[1])
        self.win_info.addstr( 4, 3, "Type           : %d" % self.file_info[2])
        self.win_info.addstr( 5, 3, "Tracks         : %d" % self.file_info[3])
        self.win_info.addstr( 6, 3, "Channels       : %d" % self.file_info[4])
        self.win_info.addstr( 7, 3, "Channels used  : %s" % self.file_info[5])
        self.win_info.addstr( 8, 3, "Octaves        : %d" % self.file_info[6])
        self.win_info.addstr( 9, 3, "Octaves used   : %s" % self.file_info[7])
        self.win_info.addstr(10, 3, "Notes in chan. : %s" % self.file_info[8])
        self.win_info.addstr(11, 3, "Active channels: %s" % str(self.ch_filter)[1:-1])
        self.win_info.addstr(12, 3, "Optimizations  : channels=%s, octaves=%s, nopercussion=%s" %
                             (self.ch_optimize, self.octave_optimize, 9 not in self.ch_filter))
        self.win_info.refresh()

    def handle_keys(self):

        c = self.stdscr.getch()

        if c == curses.KEY_RESIZE:
            self.show()
        elif c == curses.KEY_F10:
            self.stop()

    def play(self, midi=None, info=None):

        self.port.reset()

        if midi is None:
            midi = mido.MidiFile(self.filename)

        if info is None:
            info = self.analyze(midi)

        self.file_info = [
            os.path.basename(self.filename),
            (midi.length // 60, midi.length - (midi.length // 60) * 60),
            midi.type,
            len(midi.tracks),
            len(info["channels"]),
            str([x for x in info["channels"].keys()])[1:-1],
            len(info["octaves"]),
            str([x for x in info["octaves"].keys()])[1:-1],
            str(info["channels"])[1:-1]
        ]

        self.update_file_info()

        Player.play(self, midi, info)


def main():

    parser = argparse.ArgumentParser(description='Proxy')

    parser.add_argument("-f", "--file", default=None,
                        help="MIDI file to play")

    parser.add_argument("-p", "--port", default=None,
                        help="Port to use (sysfs or midiport)")

    parser.add_argument("-l", "--portlist", action="store_true", default=False,
                        help="List available MIDI ports")

    parser.add_argument("--chmax", default=4, type=int,
                        help="Maximum number of channels")

    parser.add_argument("--choptimize", action="store_true", default=False,
                        help="Try to optimize channel allocation")

    parser.add_argument("--nopercussions", action="store_true", default=False,
                        help="Remove percussions channel (#10)")

    parser.add_argument("--octoptimize", action="store_true", default=False,
                        help="Try to optimize octaves")

    parser.add_argument("--optimize", action="store_true", default=False,
                        help="Enable all optimizations")

    args = parser.parse_args()

    if args.portlist:
        port_names = mido.get_output_names()

        for port in port_names:
            print(port)

        exit(0)

    if args.choptimize:
        args.choptimize = True
        args.octoptimize = True
        args.nopercussions = True

    if args.port == "sysfs":
        port = MoppySysfsPort()
    elif args.port is None:
        port = NullPort()
    else:
        port = mido.open_output(args.port)

    if args.file is not None:

        if args.nopercussions:
            ch_filter = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]
        else:
            ch_filter = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

        vp = VisualPlayer(port, args.file, args.chmax, ch_filter, args.choptimize, args.octoptimize)
        vp.play()


if __name__ == '__main__':

    # main()

    try:
        main()
    except Exception as e:
        print(e)
