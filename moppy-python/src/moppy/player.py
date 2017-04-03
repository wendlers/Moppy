import argparse
import operator
import colorama
import mido

colorama.init()


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

    return stats


def constraint_octave(msg):

    octave = msg.note // 12 - 1

    if octave < 2:
        msg.note += (2 - octave) * 12
    elif octave > 5:
        msg.note -= (octave - 5) * 12

    return msg


def play(port, filename, max_ch, ch_filter=None):

    print("")
    print("** non-optimized player ")
    print("")

    if ch_filter is None:
        ch_filter = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    midi = mido.MidiFile(filename)

    analyze(midi)

    stats = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]

    print("")
    print(("c/o  | " + "%02d " * 16) % tuple(range(16)))
    print("-" * 55)

    port.reset()

    try:

        for msg in midi.play():

            if msg.type in ['note_on', 'note_off'] and msg.channel in ch_filter and msg.channel < max_ch:

                octave = msg.note // 12 - 1

                # print(msg.channel, octave)
                if msg.type == 'note_off':
                    stats[octave][msg.channel] = 0xff
                else:
                    stats[octave][msg.channel] = msg.note

                for o, chan_stat in enumerate(stats):

                    disp = "%02d   | %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X" % \
                           (tuple([o]) +  tuple(chan_stat))

                    print(disp.replace(" 00", " __").replace("FF", "--"))

                print(colorama.Cursor.UP(len(stats) + 1) + colorama.Cursor.BACK())

                port.send(msg)

    except KeyboardInterrupt:
        pass

    port.reset()

    print(colorama.Cursor.DOWN(len(stats) + 1))


def play_optimized(port, filename, max_ch, ch_filter=None):

    print("")
    print("** optimized player ")
    print("")

    if ch_filter is None:
        ch_filter = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]

    midi = mido.MidiFile(filename)

    info = analyze(midi)

    most_used_channels = sorted(info["channels"].items(), key=operator.itemgetter(1), reverse=True)

    ch_map = {}

    mappend_ch = 0

    for ch, _ in most_used_channels:
        if ch in ch_filter:

            ch_map[ch] = mappend_ch
            mappend_ch += 1

            if mappend_ch == max_ch:
                break

    stats = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]

    print("")
    print(("c/o  | " + "%02d " * 16) % tuple(range(16)))
    print("-" * 79)

    port.reset()

    try:

        for msg in midi.play():

            if msg.type in ['note_on', 'note_off'] and msg.channel in ch_map:

                msg = constraint_octave(msg)
                msg.channel = ch_map[msg.channel]

                octave = msg.note // 12 - 1

                # print(msg.channel, octave)
                if msg.type == 'note_off':
                    stats[octave][msg.channel] = 0xff
                else:
                    stats[octave][msg.channel] = msg.note

                for o, chan_stat in enumerate(stats):

                    disp = "%02d   | %03d %03d %03d %03d %03d %03d %03d %03d %03d %03d %03d %03d %03d %03d %03d %03d" % \
                           (tuple([o]) + tuple(chan_stat))

                    print(disp.replace(" 000", " ___").replace("255", colorama.Fore.GREEN + ".|." + colorama.Fore.RESET))

                print(colorama.Cursor.UP(len(stats) + 1) + colorama.Cursor.BACK())

                port.send(msg)

    except KeyboardInterrupt:
        pass

    port.reset()

    print(colorama.Cursor.DOWN(len(stats) + 1))


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

    if args.optimized:
        do_play = play_optimized
    else:
        do_play = play

    do_play(port, args.file, args.maxch)


if __name__ == '__main__':

    try:
        main()
    except Exception as e:
        print(e)
