#!/usr/bin/env python3
"""Find the current terracotta "M" plate patch, then repair it by cloning the
best-matching clean patch of the same surface from elsewhere in the photo.

Why a search instead of a hand-picked donor: picking by eye put the donor past
the edge of the van on the first try and cloned a kayak into the bumper. Scoring
candidates by how well their SURROUNDINGS match the surroundings of the plate
picks a donor that is on the same surface, in the same light, automatically.

Usage: replate.py IN.jpg OUT.jpg CX CY   (CX,CY = a point inside the M patch)
"""
import subprocess, sys, os

#   replate.py IN OUT CX CY              — find the terracotta "M" and repair it
#   replate.py IN OUT X1 Y1 X2 Y2        — repair an explicit rectangle
# The rect form is for working from the ORIGINAL library file, where the real
# plate is smaller than the old "M" patch and sits entirely on the bumper. The
# "M" overhung the edge of the van on four photos, and a single rectangular
# donor cannot match bodywork and ground at once — that is what dragged a wheel
# and gravel onto the bumper on the first pass.
IN, OUT = sys.argv[1], sys.argv[2]
EXPLICIT = len(sys.argv) > 6
if EXPLICIT:
    RX1, RY1, RX2, RY2 = (int(v) for v in sys.argv[3:7])
    CX, CY = (RX1 + RX2) // 2, (RY1 + RY2) // 2
else:
    CX, CY = int(sys.argv[3]), int(sys.argv[4])

W, H = map(int, subprocess.run(
    ["magick", "identify", "-format", "%w %h", IN],
    capture_output=True, text=True).stdout.split())
raw = subprocess.run(["magick", IN, "-depth", "8", "rgb:-"],
                     capture_output=True).stdout


def px(x, y):
    i = (y * W + x) * 3
    return raw[i], raw[i + 1], raw[i + 2]


# --- 1. Find the flat terracotta patch by flood-ish bbox growth from (CX,CY) ---
r0, g0, b0 = px(CX, CY)


def is_terracotta(x, y):
    """The flat brand fill, #B5643A, as JPEG left it."""
    r, g, b = px(x, y)
    return abs(r - 181) < 34 and abs(g - 100) < 34 and abs(b - 53) < 40


def is_patch(x, y):
    """Patch pixels are the flat brand terracotta, or the white letter inside."""
    r, g, b = px(x, y)
    white = r > 235 and g > 230 and b > 220
    return is_terracotta(x, y) or white


# grow a bbox outward while rows/cols still contain patch pixels
x1 = x2 = CX
y1 = y2 = CY
for _ in range(0 if EXPLICIT else 400):
    grew = False
    if x1 > 0 and any(is_patch(x1 - 1, y) for y in range(y1, y2 + 1)):
        x1 -= 1; grew = True
    if x2 < W - 1 and any(is_patch(x2 + 1, y) for y in range(y1, y2 + 1)):
        x2 += 1; grew = True
    if y1 > 0 and any(is_patch(x, y1 - 1) for x in range(x1, x2 + 1)):
        y1 -= 1; grew = True
    if y2 < H - 1 and any(is_patch(x, y2 + 1) for x in range(x1, x2 + 1)):
        y2 += 1; grew = True
    if not grew:
        break

if EXPLICIT:
    x1, y1, x2, y2 = RX1, RY1, RX2, RY2
PAD = 3                      # cover the anti-aliased edge of the old patch
x1, y1 = max(0, x1 - PAD), max(0, y1 - PAD)
x2, y2 = min(W - 1, x2 + PAD), min(H - 1, y2 + PAD)
pw, ph = x2 - x1 + 1, y2 - y1 + 1
print(f"patch found: {pw}x{ph}+{x1}+{y1}")

# --- 2. Ring of real pixels around the patch, used to score donors ----------
RING = 7
ring = []
for y in range(max(0, y1 - RING), min(H, y2 + RING + 1)):
    for x in range(max(0, x1 - RING), min(W, x2 + RING + 1)):
        if x1 <= x <= x2 and y1 <= y <= y2:
            continue                      # inside the patch: not real pixels
        ring.append((x - x1, y - y1, *px(x, y)))

best = None
# A bumper is a curved surface lit from above, so brightness is mostly a
# function of HEIGHT. Searching far vertically found a donor 22px lower that
# carried the bumper's lit bottom edge into the shadowed plate area. Keep the
# donor in the same horizontal band and let it range widely sideways instead.
for dy in range(-10, 11, 2):
    for dx in range(-240, 241, 3):
        if abs(dx) < pw + 8 and abs(dy) < ph + 8:
            continue                      # donor would overlap the patch
        ox, oy = x1 + dx, y1 + dy
        if ox - RING < 0 or oy - RING < 0 or ox + pw + RING >= W or oy + ph + RING >= H:
            continue
        # Donor must not itself contain any of the old patch. Test the brand
        # terracotta only: is_patch() also matches white, which is the colour of
        # the letter but also of taillights, chrome and sunlit leaves — using it
        # here rejected every candidate on van-colorado-fall.
        if any(is_terracotta(ox + i, oy + j)
               for j in range(0, ph, 6) for i in range(0, pw, 6)):
            continue
        s = n = 0
        for rx, ry, r, g, b in ring:
            R, G, B = px(ox + rx, oy + ry)
            s += (R - r) ** 2 + (G - g) ** 2 + (B - b) ** 2
            n += 3
        score = (s / n) ** 0.5
        if best is None or score < best[0]:
            best = (score, dx, dy)

score, dx, dy = best
print(f"best donor: offset {dx:+d},{dy:+d}  ring RMSE {score:.1f}")

# --- 3. Tone-match the donor to the hole it is filling ----------------------
# The ring score picks the closest donor, but a few levels of residual offset
# still read as a rectangle on a flat dark surface. Measure the mean difference
# over the ring and cancel it per channel.
sum_t = [0, 0, 0]
sum_d = [0, 0, 0]
for rx, ry, r, g, b in ring:
    R, G, B = px(x1 + dx + rx, y1 + dy + ry)
    for c, (tv, dv) in enumerate(zip((r, g, b), (R, G, B))):
        sum_t[c] += tv
        sum_d[c] += dv
n = max(1, len(ring))
delta = [(sum_t[c] - sum_d[c]) / n for c in range(3)]
print(f"tone correction R{delta[0]:+.1f} G{delta[1]:+.1f} B{delta[2]:+.1f}")

Q = 65535 / 255.0
chan = []
for name, d in zip(("R", "G", "B"), delta):
    chan += ["-channel", name, "-evaluate",
             "Add" if d >= 0 else "Subtract", f"{abs(d) * Q:.0f}"]

# --- 4. Composite the donor through a feathered mask ------------------------
# The mask must be drawn LARGER than the patch and then blurred. Blurring a mask
# drawn at exactly the patch size eats into its own core, so the middle is only
# partly opaque and the old orange patch ghosts straight through it — which is
# exactly what the first attempt did. A gaussian's transition spans about 2
# sigma, so grow the rectangle by that much before blurring.
sigma = 3.5
grow = int(sigma * 2 + 1)
mx1, my1 = max(0, x1 - grow), max(0, y1 - grow)
mx2, my2 = min(W - 1, x2 + grow), min(H - 1, y2 + grow)
subprocess.run([
    "magick", IN,
    "(", "+clone", "-roll", f"{-dx:+d}{-dy:+d}", *chan, "+channel", ")",
    "(", "-size", f"{W}x{H}", "xc:black", "-fill", "white",
    "-draw", f"roundrectangle {mx1},{my1} {mx2},{my2} 4,4",
    "-blur", f"0x{sigma}", "-alpha", "off", ")",
    "-composite", "-quality", "92", OUT], check=True)
print(f"wrote {OUT}  (mask {mx2-mx1+1}x{my2-my1+1}, sigma {sigma})")
