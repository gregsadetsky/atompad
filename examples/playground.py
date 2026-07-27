"""interactive playground: uv run python playground.py

pressure paint is always on: hit a pad (brightness = velocity), lean on it
and the color follows your pressure, blue (soft) -> red (hard), per pad.
needs pressure type = aftertouch: hold the little Setup button, tap pad 7
(one-time setting, survives replug).

keys (animations run until you press something else):
  s  states: rows solid / blink / breathe / dim
  r  rotating rainbow
  b  rgb side buttons (play/bank/preset) cycle red/green/blue/white
  0  stop + clear everything
  q  quit (leaves native mode on)

each knob stores a hue: turn it and the pad right underneath shows the color
(fades out ~1s after you stop). side buttons flash bright while held.
"""

import colorsys
import math
import select
import sys
import termios
import time
import tty

import atompad as atom

out, inp = atom.open_atom()
atom.native_mode(out, True)
time.sleep(0.05)
atom.all_pads_off(out)
print(__doc__)

hues = [0.0, 0.25, 0.5, 0.75]  # one per knob
knob_touched = [0.0] * 4       # last-change timestamps for the fade-out
held = set()
anim = None  # (name, t0)
BUTTON_CYCLE = [("red", (127, 0, 0)), ("green", (0, 127, 0)),
                ("blue", (0, 0, 127)), ("white", (127, 127, 127))]
last_phase = None


def paint(pad, value):
    """value 0-127 -> hue: 2/3 (blue) at soft down to 0 (red) at hard."""
    h = 2 / 3 * (1 - value / 127)
    r, g, b = colorsys.hsv_to_rgb(h, 1, max(value / 127, 0.1))
    atom.pad_color(out, pad, int(r * 127), int(g * 127), int(b * 127))


def tick_knob_leds():
    """top-row pad under each knob shows its hue while turning, then fades."""
    now = time.time()
    for i in range(4):
        if not knob_touched[i]:
            continue
        dt = now - knob_touched[i]
        if dt < 1.0:
            v = 1.0                      # hold while turning (debounce)
        elif dt < 1.4:
            v = 1.0 - (dt - 1.0) / 0.4   # quick fade-out
        else:
            v = 0.0
            knob_touched[i] = 0.0
        r, g, b = colorsys.hsv_to_rgb(hues[i], 1, v)
        atom.pad_color(out, 12 + i, int(r * 127), int(g * 127), int(b * 127))


def clear_all():
    atom.all_pads_off(out)
    for cc in atom.BUTTONS:
        atom.button_led(out, cc, bright=False)
    for cc in atom.RGB_BUTTONS:
        atom.button_color(out, cc, 0, 0, 0)


def set_anim(name):
    global anim, last_phase
    if anim:
        clear_all()
    anim = (name, time.time()) if name else None
    last_phase = None
    print(f"  anim: {name or 'stopped'}")


def tick_anim():
    global last_phase
    if anim is None:
        return
    name, t0 = anim
    t = time.time() - t0
    if name == "states":
        blink = 1.0 if int(t * 4) % 2 == 0 else 0.0
        breathe = 0.5 - 0.5 * math.cos(t * 3)
        for col in range(4):
            atom.pad_color(out, 12 + col, 127, 40, 0)
            atom.pad_color(out, 8 + col, int(127 * blink), int(40 * blink), 0)
            atom.pad_color(out, 4 + col, int(127 * breathe), int(40 * breathe), 0)
            atom.pad_color(out, 0 + col, 25, 8, 0)
    elif name == "rainbow":
        for i in range(16):
            r, g, b = colorsys.hsv_to_rgb((i / 16 + t / 3) % 1, 1, 1)
            atom.pad_color(out, i, int(r * 127), int(g * 127), int(b * 127))
    elif name == "buttons":
        phase = int(t / 1.5) % 4
        if phase != last_phase:
            last_phase = phase
            cname, rgb = BUTTON_CYCLE[phase]
            print("  side buttons:", cname)
            for cc in atom.RGB_BUTTONS:
                atom.button_color(out, cc, *rgb)


is_tty = sys.stdin.isatty()
old_term = termios.tcgetattr(sys.stdin) if is_tty else None
if is_tty:
    tty.setcbreak(sys.stdin)
try:
    while True:
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if key == "q" or key == "":
                break
            elif key == "s":
                set_anim("states")
            elif key == "r":
                set_anim("rainbow")
            elif key == "b":
                set_anim("buttons")
            elif key == "0":
                set_anim(None)
                clear_all()

        tick_anim()
        tick_knob_leds()

        for _ in range(30):  # drain midi between frames
            msg = inp.poll()
            if msg is None:
                break
            if msg.type in ("note_on", "note_off") and msg.note in atom.PADS:
                pad = msg.note - 36
                if msg.type == "note_on" and msg.velocity > 0:
                    held.add(pad)
                    paint(pad, msg.velocity)
                else:
                    held.discard(pad)
                    atom.pad_color(out, pad, 0, 0, 0)
            elif msg.type == "polytouch" and msg.note in atom.PADS:
                if msg.value:
                    paint(msg.note - 36, msg.value)
            elif msg.type == "aftertouch" and msg.value:
                for pad in held:  # mono fallback if poly aftertouch isn't set
                    paint(pad, msg.value)
            elif msg.type == "control_change" and msg.control in atom.KNOBS:
                i = msg.control - 14
                d = atom.knob_delta(msg.value)
                hues[i] = (hues[i] + d / 64) % 1
                knob_touched[i] = time.time()
            elif msg.type == "control_change" and msg.control in atom.BUTTONS:
                atom.button_led(out, msg.control, bright=msg.value > 0)

        time.sleep(0.03)
finally:
    if old_term is not None:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term)
    clear_all()
    print("bye (device stays in native mode)")
