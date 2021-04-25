import glob
import queue
import struct
import sys
import threading

import jack
import soundfile as sf

NOTE_ON = 0x9
NOTE_OFF = 0x8

def extract_midi_data(data):
    status, pitch, velocity = struct.unpack('3B', data)
    bank = status & 0xF
    status >>= 4
    return status, bank, pitch, velocity

q_in = queue.Queue()
q_out = queue.Queue(maxsize=20)

client = jack.Client('soundpad')

midi_in = client.midi_inports.register('midi_in')
left = client.outports.register('left')
right = client.outports.register('right')


def play_file(bank, pitch, buffersize=20, blocksize=1024):
    try:
        path = glob.glob(f'samples/{bank}_{pitch}_*')[0]
    except IndexError:
        print(f'Sample missing: bank={bank} pitch={pitch}')
        return False
    else:
        print(f'Playing: path={path}')

    with sf.SoundFile(path) as f:
        blocks = f.blocks(blocksize=blocksize, dtype='float32',
                          always_2d=True, fill_value=0)
        for _, data in zip(range(buffersize), blocks):
            q_out.put_nowait(data)
        for data in blocks:
            q_out.put(data)


def handle_midi_input():
    while True:
        data = q_in.get()
        status, bank, pitch, velocity = extract_midi_data(data)
        print(f'Event: status={status} bank={bank} pitch={pitch} velocity={velocity}')
        if status == NOTE_ON:
            play_file(bank, pitch)


handle_midi_input = threading.Thread(target=handle_midi_input, name='midi_in', daemon=True)
handle_midi_input.start()

def print_error(*args):
    print(*args, file=sys.stderr)


def shutdown(status, reason):
    print_error('JACK shutdown!')
    print_error('status:', status)
    print_error('reason:', reason)


def stop_callback(msg=''):
    if msg:
        print_error(msg)
    for port in client.outports:
        port.get_array().fill(0)
    raise jack.CallbackExit


def process(frames):
    try:
        data = q_out.get_nowait()
    except queue.Empty:
        # print('Buffer is empty: increase buffersize?')
        pass
    else:
        # if data is None:
        #     stop_callback()  # Playback is finished
        for channel, port in zip(data.T, client.outports):
            port.get_array()[:] = channel

    for offset, data in midi_in.incoming_midi_events():
        if len(data) != 3:
            continue
        q_in.put_nowait(data)

client.set_shutdown_callback(shutdown)
client.set_process_callback(process)

with client:
    target_ports = client.get_ports(
        is_physical=True, is_input=True, is_audio=True)
    for source, target in zip(client.outports, target_ports):
        source.connect(target)

    print('* Sound pad is Running. *')
    print('Hit Return to quit')
    input()
    print('Exiting')
