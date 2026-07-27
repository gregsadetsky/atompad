"""dump every event from the atom, decoded. run and mash buttons/pads/knobs.

shows simultaneous pads: held set is printed on every change.
ctrl-c to quit. --seconds N to auto-exit (for testing).
"""

import sys
import time

import atompad as atom

secs = float(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else None

out, inp = atom.open_atom()
midi_mode = "--midi-mode" in sys.argv
atom.native_mode(out, not midi_mode)
print("port:", inp.name, "| mode:", "factory midi" if midi_mode else "native control",
      "| listening... (ctrl-c to quit)")

held: set[int] = set()
t0 = time.time()
try:
    while secs is None or time.time() - t0 < secs:
        msg = inp.poll()
        if msg is None:
            time.sleep(0.001)
            continue
        ts = f"{time.time() - t0:7.3f}"
        if msg.type in ("note_on", "note_off") and msg.note in atom.PADS:
            pad = msg.note - 36
            down = msg.type == "note_on" and msg.velocity > 0
            (held.add if down else held.discard)(pad + 1)
            print(f"{ts} pad {pad + 1:2} {'down' if down else 'up  '} vel={msg.velocity:3} held={sorted(held)}")
        elif msg.type == "aftertouch":
            # channel pressure (default setting): ONE value for all held pads
            print(f"{ts} pressure={msg.value:3} held={sorted(held)}")
        elif msg.type == "polytouch" and msg.note in atom.PADS:
            # per-pad pressure! requires pressure type = aftertouch (quick setup)
            print(f"{ts} pad {msg.note - 36 + 1:2} pressure={msg.value}")
        elif msg.type == "control_change" and msg.control == 22:
            # pressure type = CC setting
            print(f"{ts} pressure(cc22)={msg.value}")
        elif msg.type == "control_change" and msg.control in atom.KNOBS:
            d = atom.knob_delta(msg.value)
            print(f"{ts} {atom.KNOBS[msg.control]} {d:+} (raw={msg.value})")
        elif msg.type == "control_change" and msg.control in atom.BUTTONS:
            state = "down" if msg.value > 0 else "up"
            print(f"{ts} button {atom.BUTTONS[msg.control]} {state}")
        else:
            print(f"{ts} ? {msg}")
except KeyboardInterrupt:
    pass
