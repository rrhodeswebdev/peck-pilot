"""Machining Strategy: turn top-face holes into ordered drilling Operations. Every rule constant lives here."""
import math
from dataclasses import dataclass

# 6061 aluminum, HSS drills.
SURFACE_SPEED = 75.0  # m/min
FEED_PER_REV = 0.02  # x diameter, mm/rev
FEED_PER_REV_RANGE = (0.05, 0.25)  # mm/rev
MAX_RPM = 10_000
DRILL_SIZES = [d / 2 for d in range(2, 27)]  # 1.0 to 13.0 mm in 0.5 mm steps
DRILL_TOLERANCE = 0.05  # mm
SPOT_DRILL_DIAMETER = 6.0  # 90° spot drill
SPOT_DEPTH_MAX = 1.0  # mm; never deeper than D/2, so the spot is never wider than the hole
PECK_THRESHOLD = 3.0  # G83 when depth > 3 x D
PECK_DEPTH = 1.0  # x D
DRILL_POINT = 0.3  # x D: tip length of a 118° drill point
BREAKTHROUGH = 1.0  # mm the full diameter clears the bottom of a through hole
R_PLANE = 2.0  # mm above the hole entry
BLIND_WARNING = "flat bottom needs end mill or flat-bottom drill; cone left"


@dataclass(frozen=True)
class Tool:
    number: int
    kind: str  # "spot drill" | "drill"
    diameter: float


@dataclass
class Operation:
    tool: Tool
    feature: int  # index into the Machining Features list
    cycle: str  # "G81" | "G83"
    x: float
    y: float
    r_plane: float
    z: float  # final tip depth, absolute
    peck: float  # G83 Q, mm; None for G81
    rpm: int
    feed: float  # mm/min
    warning: str = None


def _speeds(diameter):
    rpm = min(MAX_RPM, round(1000 * SURFACE_SPEED / (math.pi * diameter)))
    fpr = min(max(FEED_PER_REV * diameter, FEED_PER_REV_RANGE[0]), FEED_PER_REV_RANGE[1])
    return rpm, round(rpm * fpr, 1)


def _drill_for(diameter):
    if diameter > DRILL_SIZES[-1] + DRILL_TOLERANCE:
        return None, "too large to drill"
    best = min(DRILL_SIZES, key=lambda d: abs(d - diameter))
    if abs(best - diameter) > DRILL_TOLERANCE + 1e-9:
        return None, "no drill within tolerance"
    return best, None


def plan(features):
    """Operations for every top-face hole, in machining order. Holes that can't be drilled get their reason set."""
    holes = []
    for i, f in enumerate(features):
        if f.hole is None or f.reason:
            continue
        size, reason = _drill_for(f.hole.diameter)
        if reason:
            f.reason = reason
        else:
            holes.append((i, f.hole, size))
    if not holes:
        return []

    holes.sort(key=lambda h: (h[1].x, h[1].y))
    # shortcut: holes run in X-then-Y order with no travel optimization; add nearest-neighbour if cycle time matters.
    tools = [Tool(1, "spot drill", SPOT_DRILL_DIAMETER)]
    tools += [Tool(n, "drill", d) for n, d in enumerate(sorted({h[2] for h in holes}), start=2)]
    ops = []

    rpm, feed = _speeds(SPOT_DRILL_DIAMETER)
    for i, hole, size in holes:
        ops.append(Operation(tools[0], i, "G81", hole.x, hole.y, hole.top_z + R_PLANE,
                             hole.top_z - min(SPOT_DEPTH_MAX, size / 2), None, rpm, feed))

    for tool in tools[1:]:
        rpm, feed = _speeds(tool.diameter)
        for i, hole, size in holes:
            if size != tool.diameter:
                continue
            peck = hole.depth > PECK_THRESHOLD * size
            if hole.through:
                z, warning = hole.bottom_z - BREAKTHROUGH - DRILL_POINT * size, None
            else:
                z, warning = hole.bottom_z, BLIND_WARNING  # tip stops at the floor: never cut outside the Part
            ops.append(Operation(tool, i, "G83" if peck else "G81", hole.x, hole.y, hole.top_z + R_PLANE, z,
                                 PECK_DEPTH * size if peck else None, rpm, feed, warning))
    return ops
