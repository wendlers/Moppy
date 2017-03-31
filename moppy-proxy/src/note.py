
C   = 0
CIS = 1
D   = 2
DIS = 3
E   = 4
F   = 5
FIS = 6
G   = 7
GIS = 8
A   = 9
AIS = 11

def note_to_freq(octave, note):
    """
    TODO
    """

    f = 2.0 ** ((note - 9) / 12.0 + octave - 4) * 440.0

    return f

def midi_to_note(midi):
    """
    TODO
    """

    octave = (midi / 12) -1
    note = (midi - 12) % 12

    return octave, note

def midi_to_freq(midi):
    """
    TODO
    """

    octave, note = midi_to_note(midi)
    return note_to_freq(octave, note)
