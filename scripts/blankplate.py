#!/usr/bin/env python3
"""Blank out a licence plate: keep the plate, lose the characters.

Jesse's call, 2026-08-12, and it is what car photography does — a blank plate
still reads as a real object, so the eye passes over it. The alternatives were
both worse: a branded sticker looked amateur, and blending the plate into the
bumper left a soft smear that was obvious at hero size.

The fill colour is taken from the plate's OWN bright pixels, so the blank plate
sits in exactly the light the real one did — bright in sun, dim when backlit —
instead of glowing white in a dark photo. A faint vertical gradient, the plate's
own darker rim and a little grain keep it from looking like pasted vector art.

Usage: blankplate.py IN OUT X1 Y1 X2 Y2
"""
import subprocess, sys

IN, OUT = sys.argv[1], sys.argv[2]
X1, Y1, X2, Y2 = (int(v) for v in sys.argv[3:7])
w, h = X2 - X1 + 1, Y2 - Y1 + 1

W, H = map(int, subprocess.run(["magick", "identify", "-format", "%w %h", IN],
                               capture_output=True, text=True).stdout.split())
raw = subprocess.run(["magick", IN, "-depth", "8", "rgb:-"], capture_output=True).stdout


def px(x, y):
    i = (y * W + x) * 3
    return raw[i], raw[i + 1], raw[i + 2]


# The plate's white: the brighter half of its own pixels. Using the plain mean
# would be dragged dark by the characters and the state graphic.
inside = []
for y in range(Y1, Y2 + 1):
    for x in range(X1, X2 + 1):
        r, g, b = px(x, y)
        inside.append((r + g + b, r, g, b))
inside.sort(reverse=True)
bright = inside[: max(1, len(inside) * 45 // 100)]
n = len(bright)
face = [sum(c[i] for c in bright) / n for i in range(1, 4)]

# Rim: the darker edge of the plate, so it still reads as a physical object.
rim = [c * 0.72 for c in face]
hex_face = "#%02X%02X%02X" % tuple(int(round(min(255, c))) for c in face)
hex_rim = "#%02X%02X%02X" % tuple(int(round(min(255, c))) for c in rim)
# A plate is lit slightly unevenly; 6% top-to-bottom reads as real, flat does not.
hex_top = "#%02X%02X%02X" % tuple(int(round(min(255, c * 1.06))) for c in face)
hex_bot = "#%02X%02X%02X" % tuple(int(round(min(255, c * 0.94))) for c in face)
print(f"plate face {hex_face}  rim {hex_rim}")

subprocess.run([
    "magick", IN,
    "(", "-size", f"{w}x{h}", f"gradient:{hex_top}-{hex_bot}",
         "-attenuate", "0.28", "+noise", "Gaussian",
         "-bordercolor", hex_rim, "-shave", "1x1", "-border", "1",
         "-blur", "0x0.4",
    ")", "-geometry", f"+{X1}+{Y1}", "-compose", "over", "-composite",
    "-quality", "92", OUT], check=True)
print("wrote", OUT)
