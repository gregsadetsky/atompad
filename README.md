# atompad

python control of the presonus atom pad controller (the original, not the SQ): rgb pad leds, per-pad pressure, endless knobs, all buttons. no daw needed.

```
pip install atompad
```

```python
import atompad

out, inp = atompad.open_atom()          # finds the port, enters native control mode
atompad.pad_color(out, 0, 127, 0, 0)    # pad 1 red
atompad.button_color(out, 109, 0, 0, 127)  # play button blue

for msg in inp:                          # decoded raw midi via mido
    if msg.type == "note_on" and msg.note in atompad.PADS:
        print("pad", msg.note - 36 + 1, "velocity", msg.velocity)
```

see `examples/` for an interactive playground (pressure painting, animations), a full input decoder, and a guided feature tour.

## what the device can do

- 16 pads: full rgb (0-127 per channel), velocity in, per-pad polyphonic aftertouch in (see below)
- 4 endless knobs with acceleration (`atompad.knob_delta` decodes the cc values)
- 20 side buttons, all send press/release; play, bank and preset +/- have rgb leds, the rest are fixed-color bright/dim
- multiple simultaneous pad presses, no banks in native control mode

## per-pad pressure (one-time device setting)

out of the box the pads send channel pressure (one value for all held pads). for true per-pad pressure: hold the small **Setup** button (pads turn into a settings menu), tap **pad 7** (row 2 = pressure type, 7 = polyphonic aftertouch), release. the setting survives power cycles.

## protocol notes (reverse-engineered, fw 3.00)

two device modes: factory midi mode (banked pads, no led control) and **native control mode** — what studio one uses, and what this lib enables. mido 0-indexed channels below:

- enter native control: `note_off ch15 note=0 vel=127`, exit with `vel=0`. persists until exit or usb replug
- pads = notes 36–51. led on/off: ch0 note_on, velocity must be exactly 127 for on (1–126 = off — there is no hardware blink/breathe/brightness; animate in software). color: ch1/2/3 note_on velocity = r/g/b
- knobs = cc 14–17, relative: value 1–63 = +n steps, 65–127 = −n
- buttons = cc on ch0 (127 down, 0 up); leds via the same cc out (127 bright, 0 dim). rgb for cc 26/27/109 via ch1/2/3
- pad pressure: channel aftertouch by default, poly aftertouch / cc22 / off selectable in hardware quick setup
- pressing the tiny setup button makes the firmware flush note-offs for all 16 pads (stuck-note prevention, harmless)

protocol sources: [kmitch95120/Reaper-ATOM-Integration](https://github.com/kmitch95120/Reaper-ATOM-Integration), [EMATech/AtomCtrl](https://github.com/EMATech/AtomCtrl), plus device testing.
