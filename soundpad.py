import jack
import struct

NOTE_ON = 0x9
NOTE_OFF = 0x8

client = jack.Client('soundpad')
midi_in = client.midi_inports.register('midi_in')

@client.set_process_callback
def process(frames):
    for offset, data in midi_in.incoming_midi_events():
        if len(data) == 3:
            status, pitch, velocity = struct.unpack('3B', data)

            bank = status & 0xF
            status >>= 4

            print('status={:x} bank={:x} pitch={} velocity={}'.format(
                status, bank, pitch, velocity
            ))

with client:
    print('* Sound pad is Running. *')
    print('Hit Return to quit')
    input()
