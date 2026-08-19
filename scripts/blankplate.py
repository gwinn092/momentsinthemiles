#!/usr/bin/env python3
"""Blank out a licence plate: keep the plate, lose the characters.

Jesse's call, 2026-08-12, reaffirmed 2026-08-19, and it is what car photography
does — a blank plate still reads as a real object, so the eye passes over it.
The alternatives were both worse: a branded sticker looked amateur, and erasing
the plate into the bumper left a soft smear that was obvious at hero size. That
smear is exactly what shipped in b314a52 and what this rewrite replaces.

WHAT CHANGED, 2026-08-19
------------------------
The first version painted an opaque rectangle over the whole plate, rim and all.
That only works for a plate photographed square-on. Most of these photos are
three-quarter views where the plate is a foreshortened parallelogram — often
nearer square than 2:1 — and an axis-aligned rectangle laid over one reads as a
sticker, which was the original complaint.

So the region is now an INSET: a box safely INSIDE the plate, never its edges.
The plate's own border, corners, perspective, shadow and specular highlight are
real pixels that survive untouched; only the characters are covered. The fill is
feathered into them, so there is no seam to find. Being inset also makes the
coordinates forgiving — a few pixels of error stays inside the plate instead of
spilling onto the bumper.

Work from the ORIGINAL photo in the library, never from a version already
sanitised: the fill colour is sampled from the region's own bright pixels, and
sampling a previous smear just launders the smear.

A plate shot from three-quarters on is a tilted parallelogram, and an
axis-aligned box inside one either misses the corners or spills onto the grille.
Pass four corners instead and the fill follows the plate.

Usage: blankplate.py IN OUT X1 Y1 X2 Y2 [FEATHER]                  (box)
       blankplate.py IN OUT X1,Y1 X2,Y2 X3,Y3 X4,Y4 [FEATHER]      (quad)
       Coordinates describe a region INSIDE the plate, never its edges.
       FEATHER = blur radius for the mask edge, default 3.
"""
import subprocess, sys

IN, OUT = sys.argv[1], sys.argv[2]
rest = sys.argv[3:]
QUAD = None
if "," in rest[0]:
    QUAD = [tuple(int(v) for v in p.split(",")) for p in rest[:4]]
    FEATHER = float(rest[4]) if len(rest) > 4 else 3.0
    X1 = min(p[0] for p in QUAD); X2 = max(p[0] for p in QUAD)
    Y1 = min(p[1] for p in QUAD); Y2 = max(p[1] for p in QUAD)
else:
    X1, Y1, X2, Y2 = (int(v) for v in rest[:4])
    FEATHER = float(rest[4]) if len(rest) > 4 else 3.0
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

# A plate is lit slightly unevenly; ~5% top-to-bottom reads as real, flat does not.
hx = lambda m: "#%02X%02X%02X" % tuple(int(round(min(255, max(0, c * m)))) for c in face)
hex_top, hex_bot = hx(1.05), hx(0.95)
shape = ("polygon " + " ".join(f"{x},{y}" for x, y in QUAD)) if QUAD \
        else f"rectangle {X1},{Y1} {X2},{Y2}"
print(f"plate face {hx(1.0)}  {'quad' if QUAD else 'box'} {w}x{h} at {X1},{Y1}  feather {FEATHER}")

# The fill, and a mask whose blurred edge lets the real plate show through at the
# boundary. Composited with -composite over a mask so the seam never lands on an
# edge the eye is already tracking.
subprocess.run([
    "magick", IN,
    "(", "-size", f"{w}x{h}", f"gradient:{hex_top}-{hex_bot}",
         "-attenuate", "0.22", "+noise", "Gaussian", "-blur", "0x0.5",
    ")", "-geometry", f"+{X1}+{Y1}",
    "(", "-size", f"{W}x{H}", "xc:black",
         "-fill", "white", "-draw", shape,
         "-blur", f"0x{FEATHER}",
    ")",
    "-compose", "over", "-composite",
    "-quality", "95", OUT], check=True)
print("wrote", OUT)
