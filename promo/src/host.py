"""幕間先生 (Mr. Intermission): the promo's original host, drawn as SVG.

A 1950s educational-cartoon presenter — slicked black hair, teal suit, red bow tie and a
red 日 badge — designed for this site (not based on any existing mascot). `host(pose)`
returns an SVG group in a 400×520 box; poses: wave, thumbs, point, surprised, plain.
"""
INK, SKIN, HAIR, SHINE = "#1e2a3a", "#f3c79b", "#1e2a3a", "#5d7390"
TEAL, LAPEL, SHIRT, RED, CHEEK = "#2f9c95", "#1d6f6a", "#f6eedb", "#d1361f", "#f0a07a"
O = f'stroke="{INK}" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"'


def arm(points: str, colour: str = TEAL) -> str:
    return (f'<path d="{points}" fill="none" stroke="{INK}" stroke-width="46" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{points}" fill="none" stroke="{colour}" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>')


def fist_thumb(x: float, y: float, flip: bool = False) -> str:
    s = -1 if flip else 1
    return (f'<g transform="translate({x} {y}) scale({s} 1)">'
            f'<rect x="-24" y="-14" width="50" height="44" rx="16" fill="{SKIN}" {O}/>'
            f'<rect x="-14" y="-52" width="20" height="46" rx="10" fill="{SKIN}" {O}/>'
            f'<path d="M-22 4 H20 M-22 16 H20" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/></g>')


def open_hand(x: float, y: float, angle: float = 0) -> str:
    fingers = "".join(f'<rect x="{-30 + 15 * i}" y="-44" width="14" height="40" rx="7" fill="{SKIN}" {O} transform="rotate({-12 + 8 * i} {-23 + 15 * i} -4)"/>' for i in range(4))
    return (f'<g transform="translate({x} {y}) rotate({angle})">{fingers}'
            f'<rect x="-34" y="-14" width="66" height="46" rx="20" fill="{SKIN}" {O}/>'
            f'<rect x="-62" y="-2" width="34" height="16" rx="8" fill="{SKIN}" {O} transform="rotate(28 -28 6)"/></g>')


def pointing(x: float, y: float) -> str:
    return (f'<g transform="translate({x} {y})">'
            f'<rect x="-26" y="-22" width="48" height="44" rx="16" fill="{SKIN}" {O}/>'
            f'<rect x="14" y="-20" width="52" height="18" rx="9" fill="{SKIN}" {O}/>'
            f'<path d="M-20 8 H14 M-20 18 H12" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/></g>')


def face(expression: str) -> str:
    head = (f'<ellipse cx="126" cy="196" rx="17" ry="24" fill="{SKIN}" {O}/><ellipse cx="274" cy="196" rx="17" ry="24" fill="{SKIN}" {O}/>'
            f'<path d="M132 150 C132 92 268 92 268 150 L268 204 C268 268 236 302 200 302 C164 302 132 268 132 204 Z" fill="{SKIN}" {O}/>')
    hair = (f'<path d="M128 182 C114 104 166 56 226 60 C276 64 298 104 284 156 C280 138 270 124 256 116 L178 112 C156 120 140 140 134 182 Z" fill="{HAIR}" {O}/>'
            f'<path d="M178 112 C200 92 244 92 270 112" fill="none" stroke="{HAIR}" stroke-width="10"/>'
            f'<path d="M176 112 L172 80" fill="none" stroke="{SHINE}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M196 104 Q232 76 266 96 M204 90 Q236 70 262 84" fill="none" stroke="{SHINE}" stroke-width="5" stroke-linecap="round"/>')
    brows = (f'<path d="M156 152 Q172 140 188 148" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>'
             f'<path d="M212 148 Q228 140 244 152" fill="none" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>')
    nose = f'<path d="M200 186 Q210 204 198 210" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
    cheeks = f'<ellipse cx="160" cy="220" rx="14" ry="8" fill="{CHEEK}" opacity=".6"/><ellipse cx="240" cy="220" rx="14" ry="8" fill="{CHEEK}" opacity=".6"/>'
    eye_l = f'<ellipse cx="174" cy="176" rx="9" ry="13" fill="{INK}"/><circle cx="177" cy="171" r="3" fill="#fff"/>'
    eye_r = f'<ellipse cx="226" cy="176" rx="9" ry="13" fill="{INK}"/><circle cx="229" cy="171" r="3" fill="#fff"/>'
    grin = (f'<path d="M160 226 Q200 276 240 226 Q200 240 160 226 Z" fill="#7a1f12" {O}/>'
            f'<path d="M168 230 Q200 242 232 230 L229 238 Q200 250 171 238 Z" fill="#fff"/>'
            f'<path d="M156 222 Q152 228 158 232 M244 222 Q248 228 242 232" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>')
    if expression == "wink":
        eye_r = f'<path d="M214 180 Q226 168 238 180" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
        brows = brows.replace("M212 148 Q228 140 244 152", "M212 156 Q228 150 244 158")
    if expression == "surprised":
        eye_l = f'<ellipse cx="174" cy="174" rx="12" ry="17" fill="#fff" {O}/><circle cx="174" cy="176" r="6" fill="{INK}"/>'
        eye_r = f'<ellipse cx="226" cy="174" rx="12" ry="17" fill="#fff" {O}/><circle cx="226" cy="176" r="6" fill="{INK}"/>'
        brows = brows.replace("M156 152 Q172 140 188 148", "M154 140 Q172 126 190 136").replace("M212 148 Q228 140 244 152", "M210 136 Q228 126 246 140")
        grin = f'<ellipse cx="200" cy="240" rx="18" ry="22" fill="#7a1f12" {O}/>'
    return head + hair + brows + eye_l + eye_r + nose + cheeks + grin


def body() -> str:
    return (f'<path d="M184 290 H216 V330 H184 Z" fill="{SKIN}" {O}/>'
            f'<path d="M92 520 C92 392 134 336 200 334 C266 336 308 392 308 520 Z" fill="{TEAL}" {O}/>'
            f'<path d="M200 336 L164 344 L188 420 L200 380 L212 420 L236 344 Z" fill="{SHIRT}" {O}/>'
            f'<path d="M164 344 L140 360 L180 470 L198 400 Z M236 344 L260 360 L220 470 L202 400 Z" fill="{LAPEL}" {O}/>'
            f'<path d="M200 352 L170 334 L170 370 Z M200 352 L230 334 L230 370 Z" fill="{RED}" {O}/><circle cx="200" cy="352" r="9" fill="{RED}" {O}/>'
            f'<circle cx="252" cy="410" r="20" fill="{RED}" {O}/>'
            f'<text x="252" y="418" text-anchor="middle" font-family="Promo Title, Noto Serif TC, serif" font-weight="700" font-size="22" fill="{SHIRT}">日</text>')


def host(pose: str = "plain") -> str:
    arms_back = arms_front = ""
    expression = "smile"
    if pose == "wave":
        arms_back = arm("M118 400 Q106 440 110 482")
        arms_front = arm("M290 380 Q340 330 336 250") + open_hand(336, 236, 10)
    elif pose == "thumbs":
        expression = "wink"
        arms_back = arm("M118 400 Q106 440 110 482")
        arms_front = arm("M290 380 Q344 352 342 270") + fist_thumb(342, 262)
    elif pose == "point":
        arms_back = arm("M118 400 Q106 440 110 482")
        arms_front = arm("M290 380 Q340 360 380 330") + pointing(392, 326)
    elif pose == "surprised":
        expression = "surprised"
        arms_front = arm("M290 380 Q340 330 330 260") + open_hand(330, 246, 14) + arm("M110 380 Q60 330 70 260") + open_hand(70, 246, -14)
    else:
        arms_back = arm("M118 400 Q106 440 110 482") + arm("M282 400 Q294 440 290 482")
    return f'<g class="host">{arms_back}{body()}{face(expression)}{arms_front}</g>'


if __name__ == "__main__":
    import sys
    poses = [("wave", "打招呼"), ("thumbs", "竖拇指·眨眼"), ("point", "指向"), ("surprised", "惊讶")]
    cells = "".join(f'<g transform="translate({40 + i * 470} 70)">{host(p)}<text x="200" y="590" text-anchor="middle" font-size="30" font-family="Promo Sans, sans-serif" fill="{INK}">{label}</text></g>' for i, (p, label) in enumerate(poses))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 700" width="1920" height="700"><rect width="1920" height="700" fill="#f3e9d2"/>{cells}</svg>'
    open(sys.argv[1], "w", encoding="utf-8").write(svg)
