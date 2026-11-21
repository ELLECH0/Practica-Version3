# -*- coding: utf-8 -*-
"""Генератор SVG-иллюстраций каталога (без внешних зависимостей)."""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "img")
os.makedirs(OUT, exist_ok=True)

GREEN = "#2f6b4f"
DARK = "#1d4a35"
SOFT = "#cfe0d4"
ORANGE = "#c2703d"
BLUE = "#3f7fb3"
INK = "#16211b"


def wrap(body, bg1="#eef3ea", bg2="#e2ead9"):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240" '
        'width="320" height="240" role="img">\n'
        f'  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/>'
        "</linearGradient></defs>\n"
        '  <rect width="320" height="240" rx="0" fill="url(#bg)"/>\n'
        '  <ellipse cx="160" cy="203" rx="112" ry="13" fill="#000" opacity=".07"/>\n'
        f"{body}\n</svg>\n"
    )


def wheel(cx, cy, r):
    return (
        f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{DARK}" stroke-width="7"/>\n'
        f'  <circle cx="{cx}" cy="{cy}" r="{max(r // 4, 3)}" fill="{DARK}"/>\n'
    )


BIKE = (
    wheel(86, 152, 43)
    + wheel(234, 152, 43)
    + f'  <g stroke="{GREEN}" stroke-width="8" stroke-linecap="round" fill="none">\n'
    '    <path d="M86 152 L141 92 L162 152 L86 152"/>\n'
    '    <path d="M162 152 L214 96"/>\n'
    '    <path d="M141 92 L214 96"/>\n'
    '    <path d="M214 96 L234 152"/>\n'
    "  </g>\n"
    f'  <path d="M126 84 h30" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>\n'
    f'  <path d="M202 82 l30 12" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>\n'
    f'  <circle cx="162" cy="152" r="9" fill="none" stroke="{INK}" stroke-width="5"/>\n'
)

SCOOTER = (
    wheel(92, 176, 22)
    + wheel(226, 176, 22)
    + f'  <rect x="86" y="152" width="104" height="14" rx="7" fill="{INK}"/>\n'
    f'  <path d="M186 152 L206 78" stroke="{GREEN}" stroke-width="11" stroke-linecap="round"/>\n'
    f'  <path d="M182 74 l42 10" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>\n'
    f'  <path d="M186 152 L104 152" stroke="{SOFT}" stroke-width="4"/>\n'
    f'  <path d="M120 152 L196 118" stroke="{GREEN}" stroke-width="8" stroke-linecap="round"/>\n'
    f'  <rect x="196" y="112" width="34" height="9" rx="4.5" fill="{ORANGE}"/>\n'
)

SNOWBOARD = (
    '  <g transform="rotate(-14 160 120)">\n'
    f'    <rect x="58" y="96" width="204" height="50" rx="25" fill="{GREEN}"/>\n'
    f'    <rect x="74" y="106" width="172" height="30" rx="15" fill="{DARK}" opacity=".55"/>\n'
    f'    <rect x="112" y="98" width="26" height="46" rx="8" fill="{INK}"/>\n'
    f'    <rect x="186" y="98" width="26" height="46" rx="8" fill="{INK}"/>\n'
    f'    <path d="M70 121 h180" stroke="{SOFT}" stroke-width="3" opacity=".8"/>\n'
    "  </g>\n"
)

TENT = (
    f'  <path d="M160 62 L262 184 H58 Z" fill="{GREEN}"/>\n'
    f'  <path d="M160 62 L196 184 H124 Z" fill="{DARK}"/>\n'
    f'  <path d="M160 62 L160 184" stroke="{SOFT}" stroke-width="3" opacity=".7"/>\n'
    f'  <path d="M132 184 L160 110 L188 184" fill="{INK}" opacity=".55"/>\n'
    f'  <path d="M160 62 L52 184" stroke="{INK}" stroke-width="4" opacity=".25"/>\n'
    f'  <path d="M160 62 L268 184" stroke="{INK}" stroke-width="4" opacity=".25"/>\n'
    f'  <rect x="50" y="182" width="220" height="7" rx="3.5" fill="{INK}" opacity=".18"/>\n'
)

SLEEPING = (
    f'  <path d="M118 198c-9 0-15-7-14-16l11-96c2-20 17-31 45-31s43 11 45 31l11 96c1 9-5 16-14 16z" '
    f'fill="{ORANGE}"/>\n'
    f'  <path d="M160 55c28 0 43 11 45 31l11 96c1 9-5 16-14 16h-42z" fill="#a85e30"/>\n'
    f'  <ellipse cx="160" cy="88" rx="34" ry="26" fill="#f0d6c2"/>\n'
    f'  <ellipse cx="160" cy="88" rx="24" ry="17" fill="#e3bda3"/>\n'
    f'  <path d="M160 120 v70" stroke="#f6e9dd" stroke-width="4" stroke-dasharray="6 7"/>\n'
)

BACKPACK = (
    f'  <rect x="98" y="70" width="124" height="120" rx="34" fill="{BLUE}"/>\n'
    f'  <rect x="98" y="70" width="124" height="46" rx="30" fill="#356f9e"/>\n'
    f'  <path d="M124 74c0-20 12-30 36-30s36 10 36 30" fill="none" stroke="{INK}" stroke-width="9" '
    'stroke-linecap="round"/>\n'
    f'  <rect x="126" y="128" width="68" height="44" rx="14" fill="#356f9e"/>\n'
    f'  <path d="M160 128 v44" stroke="{SOFT}" stroke-width="3" opacity=".7"/>\n'
    f'  <path d="M108 96c-14 18-14 44-6 62" fill="none" stroke="{INK}" stroke-width="7" '
    'stroke-linecap="round" opacity=".55"/>\n'
    f'  <path d="M212 96c14 18 14 44 6 62" fill="none" stroke="{INK}" stroke-width="7" '
    'stroke-linecap="round" opacity=".55"/>\n'
)

SUP = (
    '  <g transform="rotate(-8 160 120)">\n'
    f'    <path d="M256 120c0 26-42 44-96 44s-96-18-96-44 42-44 96-44 96 18 96 44z" fill="{GREEN}"/>\n'
    f'    <path d="M64 120c0-20 40-32 96-32s96 12 96 32" fill="none" stroke="{DARK}" '
    'stroke-width="6" opacity=".5"/>\n'
    f'    <path d="M118 122 h84" stroke="{SOFT}" stroke-width="4" opacity=".7"/>\n'
    '  </g>\n'
    f'  <path d="M196 46 L236 186" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>\n'
    f'  <path d="M186 44 l28-10 10 26 -28 10z" fill="{ORANGE}"/>\n'
)

KAYAK = (
    '  <g transform="rotate(-12 160 120)">\n'
    f'    <path d="M160 40c34 22 52 52 52 80s-18 58-52 80c-34-22-52-52-52-80s18-58 52-80z" '
    f'fill="{GREEN}"/>\n'
    f'    <ellipse cx="160" cy="120" rx="26" ry="34" fill="{INK}" opacity=".7"/>\n'
    f'    <path d="M160 40 v26M160 174 v26" stroke="{SOFT}" stroke-width="4" opacity=".8"/>\n'
    "  </g>\n"
    f'  <path d="M74 190 L246 54" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>\n'
    f'  <path d="M66 182 l-12 20 22 6 12-20zM234 46 l12-20 20 14 -12 20z" fill="{ORANGE}"/>\n'
)

DRILL = (
    f'  <rect x="96" y="88" width="120" height="46" rx="16" fill="{GREEN}"/>\n'
    f'  <rect x="96" y="88" width="48" height="46" rx="16" fill="{DARK}"/>\n'
    f'  <path d="M216 111 h56" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>\n'
    f'  <path d="M236 111 l30 -7 M236 111 l30 7" stroke="{INK}" stroke-width="5"/>\n'
    f'  <path d="M132 134 l-8 62 h34 l6-62z" fill="{INK}"/>\n'
    f'  <rect x="118" y="192" width="52" height="12" rx="6" fill="{DARK}"/>\n'
    f'  <path d="M148 138 l-42 26" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>\n'
    f'  <circle cx="104" cy="166" r="11" fill="{ORANGE}"/>\n'
    f'  <rect x="164" y="100" width="26" height="8" rx="4" fill="{SOFT}"/>\n'
)

MIXER = (
    f'  <path d="M118 96 l92 -22 c22 -5 38 10 38 30 s-16 34 -38 30 l-92 -20z" fill="{ORANGE}"/>\n'
    f'  <path d="M118 96 l92 -22 c22 -5 38 10 38 30" fill="none" stroke="#a85e30" stroke-width="5"/>\n'
    f'  <ellipse cx="118" cy="90" rx="18" ry="22" fill="#a85e30"/>\n'
    f'  <path d="M120 114 L86 190 M228 114 L258 190" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>\n'
    f'  <path d="M96 190 h180" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>\n'
    + wheel(126, 186, 18)
    + wheel(240, 186, 18)
    + f'  <path d="M150 150 l60 -10" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>\n'
    f'  <circle cx="212" cy="140" r="12" fill="{DARK}"/>\n'
)

SCAFFOLD = (
    f'  <g stroke="{GREEN}" stroke-width="10" stroke-linecap="round" fill="none">\n'
    '    <path d="M84 60 V196"/>\n'
    '    <path d="M236 60 V196"/>\n'
    '    <path d="M84 70 H236"/>\n'
    '    <path d="M84 132 H236"/>\n'
    '    <path d="M84 196 H236"/>\n'
    '  </g>\n'
    f'  <path d="M84 132 L236 70 M84 70 L236 132" stroke="{DARK}" stroke-width="6" opacity=".6"/>\n'
    f'  <rect x="70" y="120" width="180" height="14" rx="4" fill="{ORANGE}"/>\n'
    f'  <rect x="94" y="192" width="22" height="12" rx="4" fill="{INK}"/>\n'
    f'  <rect x="204" y="192" width="22" height="12" rx="4" fill="{INK}"/>\n'
    f'  <path d="M150 132 v-46" stroke="{SOFT}" stroke-width="3" stroke-dasharray="6 6"/>\n'
)

GENERATOR = (
    f'  <rect x="70" y="98" width="180" height="82" rx="14" fill="{GREEN}"/>\n'
    f'  <rect x="70" y="98" width="180" height="26" rx="13" fill="{DARK}"/>\n'
    f'  <rect x="92" y="136" width="66" height="32" rx="8" fill="{SOFT}"/>\n'
    f'  <path d="M104 152 h42" stroke="{DARK}" stroke-width="5" stroke-linecap="round"/>\n'
    f'  <circle cx="204" cy="150" r="18" fill="{INK}" opacity=".75"/>\n'
    f'  <circle cx="204" cy="150" r="7" fill="{SOFT}"/>\n'
    f'  <path d="M120 98 V70 h80" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>\n'
    + wheel(102, 186, 18)
    + wheel(218, 186, 18)
    + f'  <rect x="70" y="180" width="180" height="8" rx="4" fill="{INK}" opacity=".25"/>\n'
    f'  <path d="M236 118 l18 -14" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>\n'
)

IMAGES = {
    "bike.svg": BIKE,
    "scooter.svg": SCOOTER,
    "snowboard.svg": SNOWBOARD,
    "tent.svg": TENT,
    "sleeping.svg": SLEEPING,
    "backpack.svg": BACKPACK,
    "sup.svg": SUP,
    "kayak.svg": KAYAK,
    "drill.svg": DRILL,
    "mixer.svg": MIXER,
    "scaffold.svg": SCAFFOLD,
    "generator.svg": GENERATOR,
}

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="16" fill="#2f6b4f"/>
  <text x="32" y="42" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif"
        font-size="26" font-weight="700" fill="#d3f36b">СП</text>
</svg>
"""

for name, body in IMAGES.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(wrap(body))

with open(os.path.join(OUT, "favicon.svg"), "w", encoding="utf-8") as fh:
    fh.write(FAVICON)

print("Готово:", ", ".join(sorted(os.listdir(OUT))))
