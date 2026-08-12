#!/usr/bin/env python3
"""Make a licence plate read as one sitting in deep shadow.

Used where cloning the bumper over the plate fails. On van-golden-hour and
reduce-friction-van the bumper carries a strong lighting gradient across the
plate, so no translated donor matches it and the clone leaves a bright smear.

A plate is a legitimate object; the problem is only that it is legible. So keep
the object and take it down to the tone of the metal around it: blur away the
characters, then blend hard toward the mean colour of the surrounding bumper so
the panel sits in the same light as everything near it.

Usage: shadowplate.py IN OUT X1 Y1 X2 Y2
"""
import subprocess, sys

IN, OUT = sys.argv[1], sys.argv[2]
X1, Y1, X2, Y2 = (int(v) for v in sys.argv[3:7])

W, H = map(int, subprocess.run(["magick", "identify", "-format", "%w %h", IN],
                               capture_output=True, text=True).stdout.split())
raw = subprocess.run(["magick", IN, "-depth", "8", "rgb:-"], capture_output=True).stdout


def px(x, y):
    i = (y * W + x) * 3
    return raw[i], raw[i + 1], raw[i + 2]


# Mean of a ring of real bumper just outside the plate.
RING = 9
tot = [0, 0, 0]
n = 0
for y in range(max(0, Y1 - RING), min(H, Y2 + RING + 1)):
    for x in range(max(0, X1 - RING), min(W, X2 + RING + 1)):
        if X1 <= x <= X2 and Y1 <= y <= Y2:
            continue
        r, g, b = px(x, y)
        tot[0] += r; tot[1] += g; tot[2] += b; n += 1
mean = [c / max(1, n) for c in tot]
hexcol = "#%02X%02X%02X" % tuple(int(round(c)) for c in mean)
print(f"surrounding bumper mean {hexcol}")

# 82% toward that tone keeps a trace of the plate's own shading, so it still
# reads as a panel rather than a painted rectangle.
sigma = 3.0
grow = int(sigma * 2 + 1)
subprocess.run([
    "magick", IN,
    "(", "+clone", "-blur", "0x7",
         "(", "-size", f"{W}x{H}", f"xc:{hexcol}", ")",
         "-compose", "blend", "-define", "compose:args=82", "-composite",
         "-attenuate", "0.5", "+noise", "Gaussian", ")",
    "(", "-size", f"{W}x{H}", "xc:black", "-fill", "white",
         "-draw", f"roundrectangle {X1-grow},{Y1-grow} {X2+grow},{Y2+grow} 3,3",
         "-blur", f"0x{sigma}", "-alpha", "off", ")",
    "-compose", "over", "-composite", "-quality", "92", OUT], check=True)
print("wrote", OUT)
