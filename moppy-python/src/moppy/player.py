import argparse
import operator
import curses
import mido
import os


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

    def __init__(self, port, filename, ch_max=4, ch_filter=None, update_hook=None):

        self.port = port
        self.filename = filename

        if ch_filter is None:
            self.ch_filter = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]
        else:
            self.ch_filter = ch_filter

        self.ch_max = ch_max
        self.update_hook = update_hook
        self.playing = False

    def play(self, midi=None, info=None):

        self.port.reset()

        if midi is None:
            midi = mido.MidiFile(self.filename)

        if info is None:
            info = self.analyze(midi)

        most_used_channels = sorted(info["channels"].items(), key=operator.itemgetter(1), reverse=True)

        ch_map = {}

        mappend_ch = 0

        for ch, _ in most_used_channels:
            if ch in self.ch_filter:

                ch_map[ch] = mappend_ch
                mappend_ch += 1

                if mappend_ch == self.ch_max:
                    break

        self.playing = True

        for msg in midi.play():

            if not self.playing:
                break

            if msg.type in ['note_on', 'note_off'] and msg.channel in ch_map:

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

    def analyze(self, midi):

        stats = {
            "channels": {},
            "octaves": {},
        }

        '''
        print("")
        print("Results for: %s" % midi.filename)
        print("             length: %d:%d" % (midi.length // 60, midi.length - (midi.length // 60) * 60))
        print("          midi type: %d" % midi.type)
        print("   number of tracks: %d" % len(midi.tracks))
        print(" number of channels: %d" % (len(stats["channels"])))
        print("      channels used: %s" % ([x for x in stats["channels"].keys()]))
        print("  notes in channels: %s" % stats["channels"])
        print("  number of octaves: %d" % (len(stats["octaves"])))
        print("       octaves used: %s" % ([x for x in stats["octaves"].keys()]))
        '''

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

    def constraint_octave(self, msg):

        octave = msg.note // 12 - 1

        if octave < 2:
            msg.note += (2 - octave) * 12
        elif octave > 5:
            msg.note -= (octave - 5) * 12

        return msg

    def stop(self):
        self.playing = False


class VisualPlayer(Player):

    def __init__(self, port, filename, ch_max=4, ch_filter=None):

        Player.__init__(self, port, filename, ch_max, ch_filter, self.set_note)

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

        self.handl_keys()

    def update_file_info(self):

        self.win_info.addstr( 2, 3, "File           : %s" % self.file_info[0])
        self.win_info.addstr( 3, 3, "Length         : %d:%d" % self.file_info[1])
        self.win_info.addstr( 4, 3, "Type           : %d" % self.file_info[2])
        self.win_info.addstr( 5, 3, "Tracks         : %d" % self.file_info[3])
        self.win_info.addstr( 6, 3, "Channels       : %d" % self.file_info[4])
        self.win_info.addstr( 7, 3, "Channels used  : %s" % self.file_info[5])
        self.win_info.addstr( 8, 3, "Octaves        : %d" % self.file_info[6])
        self.win_info.addstr( 9, 3, "Octaves used   : %s" % self.file_info[7])
        self.win_info.addstr(10, 3, "Notes in chan. : %s" % self.file_info[8])
        self.win_info.refresh()

    def handl_keys(self):

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

    parser.add_argument("--file", default="moppy.midi",
                        help="MIdi file to play")

    parser.add_argument("--port", default="midi",
                        help="Port to use")

    parser.add_argument("--maxch", default=4, type=int,
                        help="Maximum number of channels")

    parser.add_argument("--optimized", default=False, action="store_true",
                        help="Use optimizing player")

    args = parser.parse_args()

    if args.port == "midi":
        port_names = mido.get_output_names()
        port = mido.open_output(port_names[1])
    else:
        port = MoppySysfsPort()

    '''
    if args.optimized:
        do_play = play_optimized
    else:
        do_play = play
    '''

    vp = VisualPlayer(port, args.file, args.maxch)
    vp.play()


if __name__ == '__main__':

    try:
        main()
    except Exception as e:
        print(e)
