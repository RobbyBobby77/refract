#!/usr/bin/env python3
"""Generate the Mission Center Glass app icon (branding/icon.svg).

The shape is an Apple-style continuous-corner squircle (a superellipse);
the mark is a frosted glass panel carrying a live activity line in the app's
device colours. Only gradients and plain strokes are used, no SVG filters,
so Qt's SVG renderer (what Plasma uses for icons) draws it exactly like a
browser does.

    python3 branding/make_icon.py        # writes branding/icon.svg
"""

from __future__ import annotations

import math
from pathlib import Path

SIZE = 1024
CENTER = SIZE / 2


def squircle(half: float, n: float = 5.0, cx: float = CENTER, cy: float = CENTER, steps: int = 240) -> str:
    """Superellipse |x|^n + |y|^n = half^n as an SVG path."""
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        x = cx + half * math.copysign(abs(c) ** (2 / n), c)
        y = cy + half * math.copysign(abs(s) ** (2 / n), s)
        pts.append(f"{x:.1f} {y:.1f}")
    return "M" + " L".join(pts) + " Z"


def smooth_line(values: list[float], x0: float, x1: float, y_top: float, y_bottom: float) -> tuple[str, tuple[float, float]]:
    """Monotone cubic through the samples (same curve style as the app's graphs)."""
    n = len(values)
    dx = (x1 - x0) / (n - 1)
    ys = [y_bottom - v * (y_bottom - y_top) for v in values]
    slopes = [(ys[i + 1] - ys[i]) / dx for i in range(n - 1)]
    m = [slopes[0]] + [0.0 if slopes[i - 1] * slopes[i] <= 0 else (slopes[i - 1] + slopes[i]) / 2
                       for i in range(1, n - 1)] + [slopes[-1]]
    d = f"M{x0:.1f} {ys[0]:.1f}"
    for i in range(n - 1):
        xa, xb = x0 + i * dx, x0 + (i + 1) * dx
        d += (f" C{xa + dx / 3:.1f} {ys[i] + m[i] * dx / 3:.1f}"
              f" {xb - dx / 3:.1f} {ys[i + 1] - m[i + 1] * dx / 3:.1f} {xb:.1f} {ys[i + 1]:.1f}")
    return d, (x1, ys[-1])


def build() -> str:
    body = squircle(448)
    shadow = squircle(446, cy=CENTER + 14)

    # glass panel geometry
    px, py, pw, ph, pr = 172, 236, 680, 552, 104
    # activity line inside the panel
    samples = [0.14, 0.24, 0.18, 0.44, 0.32, 0.72, 0.56, 0.86]
    line, (ex, ey) = smooth_line(samples, px + 58, px + pw - 70, py + 92, py + ph - 88)
    area = f"{line} L{px + pw - 70:.1f} {py + ph - 60:.1f} L{px + 58:.1f} {py + ph - 60:.1f} Z"
    grid = "".join(
        f'<line x1="{px + 40}" y1="{py + ph * f:.0f}" x2="{px + pw - 40}" y2="{py + ph * f:.0f}" '
        f'stroke="#FFFFFF" stroke-opacity="0.07" stroke-width="4" stroke-linecap="round"/>'
        for f in (0.30, 0.52, 0.74))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}">
  <title>Mission Center Glass</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2B3163"/>
      <stop offset="0.5" stop-color="#161A38"/>
      <stop offset="1" stop-color="#0A0B1A"/>
    </linearGradient>
    <radialGradient id="glowBlue" cx="0.18" cy="0.98" r="0.62">
      <stop offset="0" stop-color="#0A84FF" stop-opacity="0.60"/>
      <stop offset="1" stop-color="#0A84FF" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowPink" cx="0.92" cy="0.90" r="0.58">
      <stop offset="0" stop-color="#FF375F" stop-opacity="0.45"/>
      <stop offset="1" stop-color="#FF375F" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowViolet" cx="0.55" cy="1.05" r="0.55">
      <stop offset="0" stop-color="#BF5AF2" stop-opacity="0.45"/>
      <stop offset="1" stop-color="#BF5AF2" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.14"/>
      <stop offset="0.35" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.50"/>
      <stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.08"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.22"/>
    </linearGradient>
    <radialGradient id="shadow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0.86" stop-color="#000000" stop-opacity="0.28"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="panelFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.14"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.04"/>
    </linearGradient>
    <linearGradient id="panelRim" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.85"/>
      <stop offset="0.45" stop-color="#FFFFFF" stop-opacity="0.12"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0.40"/>
    </linearGradient>
    <linearGradient id="line" x1="{px}" y1="0" x2="{px + pw}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#46A3FF"/>
      <stop offset="0.40" stop-color="#8C7BFF"/>
      <stop offset="0.72" stop-color="#D56AF6"/>
      <stop offset="1" stop-color="#FF5A82"/>
    </linearGradient>
    <linearGradient id="area" x1="0" y1="{py + 90}" x2="0" y2="{py + ph - 40}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#A37BFF" stop-opacity="0.42"/>
      <stop offset="0.75" stop-color="#A37BFF" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <!-- soft contact shadow -->
  <path d="{shadow}" fill="url(#shadow)" transform="translate(512 526) scale(1.035) translate(-512 -526)"/>

  <!-- body: deep night gradient lit from below in the device colours -->
  <path d="{body}" fill="url(#bg)"/>
  <path d="{body}" fill="url(#glowBlue)"/>
  <path d="{body}" fill="url(#glowViolet)"/>
  <path d="{body}" fill="url(#glowPink)"/>
  <path d="{body}" fill="url(#sheen)"/>
  <path d="{body}" fill="none" stroke="url(#rim)" stroke-width="5"/>

  <!-- the glass panel -->
  <rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="{pr}" fill="url(#panelFill)"/>
  <rect x="{px + 2.5}" y="{py + 2.5}" width="{pw - 5}" height="{ph - 5}" rx="{pr - 2.5}" fill="none" stroke="url(#panelRim)" stroke-width="5"/>
  <path d="M{px + pr * 0.55} {py + 22} H{px + pw - pr * 0.55}" stroke="#FFFFFF" stroke-opacity="0.22" stroke-width="5" stroke-linecap="round"/>
  {grid}

  <!-- live activity line -->
  <path d="{area}" fill="url(#area)"/>
  <path d="{line}" fill="none" stroke="url(#line)" stroke-opacity="0.16" stroke-width="72" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="{line}" fill="none" stroke="url(#line)" stroke-opacity="0.28" stroke-width="48" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="{line}" fill="none" stroke="url(#line)" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="40" fill="#FF5A82" fill-opacity="0.30"/>
  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="24" fill="#FFFFFF"/>
  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="24" fill="none" stroke="#FF5A82" stroke-width="8"/>
</svg>
'''


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "icon.svg"
    out.write_text(build())
    print("wrote", out)
