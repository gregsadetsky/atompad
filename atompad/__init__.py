"""control the presonus atom pad controller (the original, not the SQ).

protocol reverse-engineered by kmitch95120/Reaper-ATOM-Integration and
verified on firmware 3.00. everything assumes native control mode, which
open_atom() puts the device into.

channels here are 0-indexed (mido style): ch 15 = "channel 16".
"""

from typing import Any

import mido

PADS = list(range(36, 52))  # notes, pad 1..16

# side button CCs (ch 0). knobs are CC 14-17 (endless: 1..63=+n, 65..127=-n)
BUTTONS = {
    86: "setup", 85: "setloop", 31: "editor", 30: "nudge",
    29: "showhide", 27: "preset", 26: "bank", 25: "fulllevel",
    24: "noterepeat", 32: "shift",
    87: "up", 89: "down", 90: "left", 102: "right",
    103: "select", 104: "zoom", 105: "click", 107: "record",
    109: "play", 111: "stop",
}
KNOBS = {14: "knob1", 15: "knob2", 16: "knob3", 17: "knob4"}
RGB_BUTTONS = {27, 26, 109}  # preset, bank, play support full rgb


def find_port(substr: str = "ATOM") -> str:
    names = [n for n in mido.get_output_names() if substr.lower() in n.lower()]
    if not names:
        raise RuntimeError(f"no midi port matching {substr!r}: {mido.get_output_names()}")
    return names[0]


def open_atom(native: bool = True) -> "tuple[Any, Any]":
    """returns (output, input) mido ports; enters native control mode."""
    name = find_port()
    out, inp = mido.open_output(name), mido.open_input(name)
    if native:
        native_mode(out, True)
    return out, inp


def native_mode(out: Any, on: bool = True) -> None:
    """native control = full led control, no banks, everything sends events.
    persists until disabled or usb power cycle."""
    out.send(mido.Message("note_off", channel=15, note=0, velocity=127 if on else 0))


def pad_color(out: Any, pad: int, r: int, g: int, b: int) -> None:
    """pad 0-15, r/g/b 0-127. brightness = scale the rgb values.

    ch0 velocity is on/off only: tested on fw 3.00, only exactly 127 lights
    the pad (1-126 = off). blink/breathe don't exist in hardware — animate
    in software instead (the device handles 30fps updates fine)."""
    note = PADS[pad]
    out.send(mido.Message("note_on", channel=1, note=note, velocity=r))
    out.send(mido.Message("note_on", channel=2, note=note, velocity=g))
    out.send(mido.Message("note_on", channel=3, note=note, velocity=b))
    on = bool(r or g or b)
    out.send(mido.Message("note_on", channel=0, note=note, velocity=127 if on else 0))


def button_led(out: Any, cc: int, bright: bool = True) -> None:
    """all buttons: bright/dim (can't fully turn off)."""
    out.send(mido.Message("control_change", channel=0, control=cc, value=127 if bright else 0))


def button_color(out: Any, cc: int, r: int, g: int, b: int) -> None:
    """rgb only for preset(27), bank(26), play(109)."""
    out.send(mido.Message("control_change", channel=1, control=cc, value=r))
    out.send(mido.Message("control_change", channel=2, control=cc, value=g))
    out.send(mido.Message("control_change", channel=3, control=cc, value=b))
    button_led(out, cc, bool(r or g or b))


def knob_delta(value: int) -> int:
    """decode an endless-encoder cc value: 1..63 = +n steps, 65..127 = -n."""
    return value if value < 64 else 64 - value


def all_pads_off(out: Any) -> None:
    for p in range(16):
        pad_color(out, p, 0, 0, 0)
