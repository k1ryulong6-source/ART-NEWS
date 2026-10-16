"""幕間先生 (Mr. Intermission): the promo's original host, drawn as SVG.

A 1950s educational-cartoon presenter — slicked black hair, suit, bow tie, pocket square
and a 日 badge — designed for this site (not based on any existing mascot). Drawn black
and white after the Fallout-style cartoon reference, with cel shading (light from the
upper left), a heavier outer contour and finer inner lines.

`host(pose, badge)` returns an SVG group in a 400×520 box; poses: wave, thumbs, point,
surprised, plain. The parts the film animates carry classes: h-head (turns about the
neck), h-eyes (blinks), h-arm (the gesturing arm, about the shoulder) and three mouths
m0 (closed), m1 (smile, the resting face) and m2 (open) for lip sync.
"""
# Black-and-white palette; BADGE is the one place the brand red may stay.
INK, SKIN, SKIN_SH, HAIR, SHINE = "#141414", "#f4f1e8", "#cdc7b8", "#141414", "#7a7873"
SUIT, SUIT_SH, LAPEL, SHIRT, SHIRT_SH = "#8c8a84", "#6a6863", "#4f4d49", "#f4f1e8", "#d3cdbf"
CHEEK, TONGUE = "#d8d2c4", "#6e6b65"
TEAL = SUIT                      # kept for callers of the earlier palette
BADGE = "#d1361f"
O = f'stroke="{INK}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"'     # outer contour
I = f'stroke="{INK}" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"'   # inner lines


def shape(d: str, fill: str, shade: str = "", shade_fill: str = "", line: str = O) -> str:
    """A filled shape, its shadow, then its outline on top."""
    out = f'<path d="{d}" fill="{fill}"/>'
    if shade:
        out += f'<path d="{shade}" fill="{shade_fill}"/>'
    return out + f'<path d="{d}" fill="none" {line}/>'


def arm(points: str, colour: str = SUIT) -> str:
    return (f'<path d="{points}" fill="none" stroke="{INK}" stroke-width="47" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{points}" fill="none" stroke="{colour}" stroke-width="33" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{points}" fill="none" stroke="{SUIT_SH}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" transform="translate(7 5)" opacity=".85"/>')


def cuff(x: float, y: float, angle: float) -> str:
    return (f'<g transform="translate({x} {y}) rotate({angle})"><rect x="-21" y="-9" width="42" height="18" rx="6" fill="{SHIRT}" {I}/>'
            f'<path d="M-15 5 H15" fill="none" stroke="{SHIRT_SH}" stroke-width="5" stroke-linecap="round"/></g>')


def fist_thumb(x: float, y: float, flip: bool = False) -> str:
    s = -1 if flip else 1
    return (f'<g transform="translate({x} {y}) scale({s} 1)">'
            f'<rect x="-14" y="-54" width="21" height="48" rx="10" fill="{SKIN}" {O}/>'
            f'<path d="M-2 -46 Q3 -38 1 -12" fill="none" stroke="{SKIN_SH}" stroke-width="5" stroke-linecap="round"/>'
            f'<rect x="-25" y="-14" width="52" height="46" rx="17" fill="{SKIN}" {O}/>'
            f'<path d="M10 -8 Q22 6 18 26 L24 24 Q28 4 16 -10 Z" fill="{SKIN_SH}"/>'
            f'<path d="M-23 4 H18 M-23 17 H18" fill="none" {I}/></g>')


def open_hand(x: float, y: float, angle: float = 0) -> str:
    fingers = "".join(f'<rect x="{-30 + 15 * i}" y="-46" width="14" height="42" rx="7" fill="{SKIN}" {I} transform="rotate({-12 + 8 * i} {-23 + 15 * i} -4)"/>' for i in range(4))
    return (f'<g transform="translate({x} {y}) rotate({angle})">{fingers}'
            f'<rect x="-34" y="-14" width="66" height="46" rx="20" fill="{SKIN}"/>'
            f'<path d="M14 -10 Q30 4 26 28 L32 22 Q34 0 20 -12 Z" fill="{SKIN_SH}"/>'
            f'<rect x="-34" y="-14" width="66" height="46" rx="20" fill="none" {O}/>'
            f'<path d="M-6 8 Q2 16 12 10" fill="none" stroke="{SKIN_SH}" stroke-width="4" stroke-linecap="round"/>'
            f'<rect x="-62" y="-2" width="34" height="16" rx="8" fill="{SKIN}" {I} transform="rotate(28 -28 6)"/></g>')


def pointing(x: float, y: float) -> str:
    return (f'<g transform="translate({x} {y})">'
            f'<rect x="14" y="-21" width="54" height="18" rx="9" fill="{SKIN}" {I}/>'
            f'<rect x="-26" y="-22" width="48" height="44" rx="16" fill="{SKIN}"/>'
            f'<path d="M-24 10 Q-2 22 20 10 L20 18 Q-2 26 -24 18 Z" fill="{SKIN_SH}"/>'
            f'<rect x="-26" y="-22" width="48" height="44" rx="16" fill="none" {O}/>'
            f'<path d="M-20 4 H14 M-20 14 H12" fill="none" {I}/></g>')


def mouths(expression: str) -> str:
    """m0 closed, m1 the resting smile, m2 open — the film switches them with the voice."""
    if expression == "surprised":
        return (f'<g class="mouth m0"><ellipse cx="200" cy="244" rx="12" ry="13" fill="{INK}" {I}/></g>'
                f'<g class="mouth m1"><ellipse cx="200" cy="242" rx="17" ry="21" fill="{INK}" {I}/><path d="M188 254 Q200 246 212 254 Q200 262 188 254 Z" fill="{TONGUE}"/></g>'
                f'<g class="mouth m2"><ellipse cx="200" cy="244" rx="20" ry="27" fill="{INK}" {I}/><path d="M186 260 Q200 250 214 260 Q200 270 186 260 Z" fill="{TONGUE}"/></g>')
    corners = (f'<path d="M154 222 Q150 229 157 233 M246 222 Q250 229 243 233" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>')
    closed = f'<path d="M160 228 Q200 262 240 228" fill="none" stroke="{INK}" stroke-width="6.5" stroke-linecap="round"/>{corners}'
    smile = (f'<path d="M160 226 Q200 278 240 226 Q200 240 160 226 Z" fill="{INK}" {I}/>'
             f'<path d="M168 230 Q200 242 232 230 L229 239 Q200 251 171 239 Z" fill="#fff"/>'
             f'<path d="M182 258 Q200 250 218 258 Q200 266 182 258 Z" fill="{TONGUE}"/>{corners}')
    talk = (f'<path d="M162 226 Q200 300 238 226 Q200 238 162 226 Z" fill="{INK}" {I}/>'
            f'<path d="M168 230 Q200 241 232 230 L230 238 Q200 249 170 238 Z" fill="#fff"/>'
            f'<path d="M178 272 Q200 256 222 272 Q200 286 178 272 Z" fill="{TONGUE}"/>{corners}')
    return f'<g class="mouth m0">{closed}</g><g class="mouth m1">{smile}</g><g class="mouth m2">{talk}</g>'


def face(expression: str) -> str:
    head_d = "M132 150 C132 92 268 92 268 150 L268 204 C268 268 236 302 200 302 C164 302 132 268 132 204 Z"
    ears = (f'<ellipse cx="126" cy="196" rx="17" ry="24" fill="{SKIN}" {O}/><path d="M128 184 Q118 196 128 208" fill="none" {I}/>'
            f'<ellipse cx="274" cy="196" rx="17" ry="24" fill="{SKIN}" {O}/><path d="M272 184 Q282 196 272 208" fill="none" {I}/>'
            f'<path d="M280 178 Q292 196 280 214 L286 212 Q296 196 284 176 Z" fill="{SKIN_SH}"/>')
    head = (f'<path d="{head_d}" fill="{SKIN}"/>'
            # the shadow side of the face, and the band the hair throws on the forehead
            f'<path d="M268 160 L268 204 C268 268 236 302 200 302 C232 286 252 256 254 210 C255 186 260 170 268 160 Z" fill="{SKIN_SH}"/>'
            f'<path d="M134 176 C142 140 158 122 180 116 L256 118 C270 126 278 140 282 156 L274 166 C266 148 254 136 238 132 L186 130 C164 138 148 156 140 192 Z" fill="{SKIN_SH}"/>'
            f'<path d="M150 150 Q146 176 150 200" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".7"/>'
            f'<path d="{head_d}" fill="none" {O}/>')
    hair = (f'<path d="M128 182 C114 104 166 56 226 60 C276 64 298 104 284 156 C280 138 270 124 256 116 L178 112 C156 120 140 140 134 182 Z" fill="{HAIR}" {O}/>'
            f'<path d="M178 112 C200 92 244 92 270 112" fill="none" stroke="{HAIR}" stroke-width="10"/>'
            f'<path d="M176 112 L172 80" fill="none" stroke="{SHINE}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M196 104 Q232 76 266 96 M204 90 Q236 70 262 84" fill="none" stroke="{SHINE}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M150 104 Q160 86 178 76" fill="none" stroke="#a9a69f" stroke-width="4" stroke-linecap="round"/>')
    brows = (f'<path d="M154 152 Q172 138 190 147" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>'
             f'<path d="M210 147 Q228 138 246 152" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>')
    nose = (f'<path d="M204 196 Q214 208 202 214 Q196 210 196 206 Z" fill="{SKIN_SH}"/>'
            f'<path d="M200 184 Q212 204 198 212" fill="none" {I}/>')
    cheeks = (f'<ellipse cx="160" cy="220" rx="15" ry="8" fill="{CHEEK}"/><ellipse cx="242" cy="220" rx="13" ry="8" fill="{CHEEK}"/>'
              f'<path d="M154 218 l4 -2 M162 220 l4 -2" stroke="{SKIN}" stroke-width="2" stroke-linecap="round"/>')
    eye_l = (f'<ellipse cx="174" cy="176" rx="10" ry="14" fill="{INK}"/><circle cx="177.5" cy="170" r="3.6" fill="#fff"/><circle cx="171" cy="183" r="1.6" fill="#fff"/>'
             f'<path d="M160 164 Q174 156 188 164" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>')
    eye_r = (f'<ellipse cx="226" cy="176" rx="10" ry="14" fill="{INK}"/><circle cx="229.5" cy="170" r="3.6" fill="#fff"/><circle cx="223" cy="183" r="1.6" fill="#fff"/>'
             f'<path d="M212 164 Q226 156 240 164" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>')
    if expression == "wink":
        eye_r = (f'<path d="M212 180 Q226 166 240 180" fill="none" stroke="{INK}" stroke-width="7.5" stroke-linecap="round"/>'
                 f'<path d="M238 178 l7 -3 M236 184 l7 1" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>')
        brows = brows.replace("M210 147 Q228 138 246 152", "M210 156 Q228 150 246 160")
    if expression == "surprised":
        eye_l = f'<ellipse cx="174" cy="172" rx="13" ry="18" fill="#fff" {I}/><circle cx="174" cy="175" r="6.5" fill="{INK}"/><circle cx="176" cy="172" r="2" fill="#fff"/>'
        eye_r = f'<ellipse cx="226" cy="172" rx="13" ry="18" fill="#fff" {I}/><circle cx="226" cy="175" r="6.5" fill="{INK}"/><circle cx="228" cy="172" r="2" fill="#fff"/>'
        brows = brows.replace("M154 152 Q172 138 190 147", "M152 138 Q172 122 192 133").replace("M210 147 Q228 138 246 152", "M208 133 Q228 122 248 138")
    return (f'<g class="h-head">{ears}{head}{hair}{brows}<g class="h-eyes">{eye_l}{eye_r}</g>{nose}{cheeks}{mouths(expression)}</g>')


def body(badge: str = BADGE) -> str:
    suit_d = "M92 520 C92 392 134 336 200 334 C266 336 308 392 308 520 Z"
    return (f'<path d="M184 288 H216 V332 H184 Z" fill="{SKIN}" {O}/>'
            f'<path d="M184 296 Q200 310 216 296 V314 Q200 322 184 314 Z" fill="{SKIN_SH}"/>'
            + shape(suit_d, SUIT, "M246 348 C284 368 308 418 308 520 L258 520 C266 450 262 392 246 348 Z", SUIT_SH)
            + f'<path d="M126 470 Q136 444 148 434 M276 476 Q270 450 262 440" fill="none" stroke="{SUIT_SH}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M200 336 L164 344 L188 420 L200 380 L212 420 L236 344 Z" fill="{SHIRT}" {I}/>'
            f'<path d="M200 360 L212 420 L226 372 Z" fill="{SHIRT_SH}"/>'
            f'<path d="M164 344 L140 360 L180 470 L198 400 Z M236 344 L260 360 L220 470 L202 400 Z" fill="{LAPEL}" {I}/>'
            f'<path d="M150 362 L176 446" fill="none" stroke="#6e6c67" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M118 436 L132 418 L144 424 L152 412 L160 436 Z" fill="{SHIRT}" {I}/><path d="M112 438 H166" fill="none" {I}/>'
            f'<circle cx="200" cy="488" r="6" fill="{INK}"/><circle cx="198" cy="486" r="1.8" fill="{SHINE}"/>'
            f'<path d="M200 352 L170 334 L170 370 Z M200 352 L230 334 L230 370 Z" fill="{INK}" {I}/>'
            f'<path d="M176 342 L188 350 M176 362 L188 354" fill="none" stroke="{SHINE}" stroke-width="2.5" stroke-linecap="round"/>'
            f'<circle cx="200" cy="352" r="9" fill="{INK}" {I}/>'
            f'<circle cx="252" cy="410" r="20" fill="{badge}" {I}/><circle cx="252" cy="410" r="14" fill="none" stroke="{SHINE}" stroke-width="2"/>'
            f'<text x="252" y="418" text-anchor="middle" font-family="Promo Title, Noto Serif TC, serif" font-weight="700" font-size="22" fill="{SHIRT}">日</text>')


def host(pose: str = "plain", badge: str = BADGE) -> str:
    arms_back = arms_front = ""
    expression = "smile"
    rest = arm("M118 400 Q106 440 110 482")
    if pose == "wave":
        arms_back = rest
        arms_front = arm("M290 380 Q340 330 336 262") + cuff(336, 266, 4) + open_hand(336, 236, 10)
    elif pose == "thumbs":
        expression = "wink"
        arms_back = rest
        arms_front = arm("M290 380 Q344 352 342 290") + cuff(342, 292, 2) + fist_thumb(342, 262)
    elif pose == "point":
        arms_back = rest
        arms_front = arm("M290 380 Q332 362 362 340") + cuff(364, 338, -54) + pointing(392, 326)
    elif pose == "surprised":
        expression = "surprised"
        arms_front = (arm("M290 380 Q340 330 330 276") + cuff(330, 278, 2) + open_hand(330, 246, 14)
                      + arm("M110 380 Q60 330 70 276") + cuff(70, 278, -2) + open_hand(70, 246, -14))
    else:
        arms_back = rest + arm("M282 400 Q294 440 290 482")
    return (f'<g class="host pose-{pose}">{arms_back}<g class="h-body">{body(badge)}</g>{face(expression)}'
            f'<g class="h-arm">{arms_front}</g></g>')


if __name__ == "__main__":
    import sys
    poses = [("wave", "打招呼"), ("thumbs", "竖拇指·眨眼"), ("point", "指向"), ("surprised", "惊讶")]
    cells = "".join(f'<g transform="translate({40 + i * 470} 70)">{host(p)}<text x="200" y="590" text-anchor="middle" font-size="30" font-family="Promo Sans, sans-serif" fill="{INK}">{label}</text></g>' for i, (p, label) in enumerate(poses))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 700" width="1920" height="700"><style>.mouth{{display:none}}.m1{{display:inline}}</style>'
           f'<rect width="1920" height="700" fill="#f3e9d2"/>{cells}</svg>')
    open(sys.argv[1], "w", encoding="utf-8").write(svg)
