"""guided on-device tour: uv run python demo_tour.py <step>

steps: modes | states | buttons
"""

import sys
import time

import atompad as atom

STEPS = ("modes", "states", "buttons")
if len(sys.argv) < 2 or sys.argv[1] not in STEPS:
    sys.exit(f"usage: uv run python demo_tour.py <{'|'.join(STEPS)}>")

out, inp = atom.open_atom()
step = sys.argv[1]

if step == "modes":
    print("-> sending native-control OFF: device back to factory midi mode")
    atom.native_mode(out, False)
    print("   LOOK: pads should light up stock blue (device drives its own leds,")
    print("   pressing turns them white). watching for 8s...")
    time.sleep(8)
    print("-> sending native-control ON: device becomes a slave")
    atom.native_mode(out, True)
    print("   LOOK: pads go dark. nothing lights unless software says so. 5s...")
    time.sleep(5)

elif step == "states":
    # hardware blink/breathe (velocity 1/2 on ch0) don't exist on fw 3.00 —
    # ch0 velocity is on(127)/off only. so: software animation.
    import math
    atom.native_mode(out, True)
    time.sleep(0.1)
    print("software animations, 12s: row4(top)=solid, row3=blink, row2=breathe, row1=dim")
    t0 = time.time()
    while (t := time.time() - t0) < 12:
        blink = 1.0 if int(t * 4) % 2 == 0 else 0.0
        breathe = 0.5 - 0.5 * math.cos(t * 3)
        for col in range(4):
            atom.pad_color(out, 12 + col, 127, 40, 0)
            atom.pad_color(out, 8 + col, int(127 * blink), int(40 * blink), 0)
            atom.pad_color(out, 4 + col, int(127 * breathe), int(40 * breathe), 0)
            atom.pad_color(out, 0 + col, 25, 8, 0)
        time.sleep(0.03)
    atom.all_pads_off(out)

elif step == "buttons":
    atom.native_mode(out, True)
    time.sleep(0.1)
    print("the ONLY 3 rgb side buttons: play / bank / preset+-. cycling r,g,b,white 3s each:")
    for name, rgb in [("red", (127, 0, 0)), ("green", (0, 127, 0)),
                      ("blue", (0, 0, 127)), ("white", (127, 127, 127))]:
        print("  ", name)
        for cc in atom.RGB_BUTTONS:
            atom.button_color(out, cc, *rgb)
        time.sleep(3)
    print("every OTHER side button only does bright/dim in its fixed color.")
    print("blinking them all bright<->dim 4 times, 1s each:")
    others = [cc for cc in atom.BUTTONS if cc not in atom.RGB_BUTTONS]
    for i in range(8):
        for cc in others:
            atom.button_led(out, cc, bright=(i % 2 == 0))
        time.sleep(1)
    for cc in others:
        atom.button_led(out, cc, bright=False)

print("step done.")
