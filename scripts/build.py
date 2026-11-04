#!/usr/bin/env python3
"""Builds themes/ember-dusk.json and previews/*.svg from the palettes below.

Every foreground color is nudged until it meets a minimum WCAG contrast ratio
against the editor background, and the added/deleted/modified colors are tuned
until they stay distinguishable under protanopia, deuteranopia and tritanopia.

    python3 scripts/build.py
"""
import colorsys
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cvd import worst  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Minimum contrast against the editor background (WCAG AA is 4.5, AAA is 7).
# A variant can raise these with "min_code" / "min_muted".
MIN_CODE = 4.5      # every syntax token, comments included
MIN_MUTED = 4.5     # muted UI text
MIN_SOFT = 3.0      # line numbers, placeholders (non-essential text)

# Minimum CIELAB distance between paired status colors, under normal vision
# and every simulated color vision deficiency.
MIN_CVD_DISTANCE = 20

DARK_ACCENTS = {
    "orange": "#f5813f", "amber": "#f2b04a", "gold": "#e3c27e",
    "green": "#a9c46c", "teal": "#8ec5b0", "blue": "#82b4c9",
    "rose": "#e08aa0", "red": "#e8695a", "plum": "#c49bd1",
}

VARIANTS = [
    {
        "name": "Ember Dusk", "appearance": "dark",
        "bg": "#1c1917", "bg_dim": "#171412", "surface": "#201c1a",
        "elevated": "#282321", "element": "#2c2623", "hover": "#352e2a",
        "active": "#40372f", "border": "#302926", "border_var": "#272220",
        "fg": "#ede4dc", "muted": "#ab9c90", "comment": "#8f8075",
        "subtle": "#6f625a", "accents": DARK_ACCENTS,
    },
    {
        "name": "Ember Dusk Deep", "appearance": "dark",
        "bg": "#110e0d", "bg_dim": "#0c0a09", "surface": "#161211",
        "elevated": "#1e1917", "element": "#221c1a", "hover": "#2b2420",
        "active": "#362d28", "border": "#251f1c", "border_var": "#1c1715",
        "fg": "#f2eae3", "muted": "#a8998d", "comment": "#857669",
        "subtle": "#62564f", "accents": DARK_ACCENTS,
    },
    {
        "name": "Ember Dusk Soft", "appearance": "dark",
        "bg": "#272220", "bg_dim": "#211d1b", "surface": "#2b2523",
        "elevated": "#332c29", "element": "#372f2c", "hover": "#403733",
        "active": "#4b403b", "border": "#3b332f", "border_var": "#322b28",
        "fg": "#ddd2c7", "muted": "#ab9c90", "comment": "#998a7e",
        "subtle": "#7c6e65",
        "accents": {
            "orange": "#e8915c", "amber": "#e3b265", "gold": "#d8bf8c",
            "green": "#a8bd7d", "teal": "#94bfae", "blue": "#8fb4c4",
            "rose": "#d895a6", "red": "#dd7a6c", "plum": "#bfa2c9",
        },
    },
    {
        "name": "Ember Dusk High Contrast", "appearance": "dark",
        "min_code": 7.0, "min_muted": 7.0,
        "bg": "#0f0c0b", "bg_dim": "#080606", "surface": "#141110",
        "elevated": "#1c1816", "element": "#221d1a", "hover": "#2e2622",
        "active": "#3b312c", "border": "#4a3f39", "border_var": "#362e2a",
        "fg": "#fbf6f1", "muted": "#cbbcb0", "comment": "#b5a598",
        "subtle": "#8f8075", "accents": DARK_ACCENTS,
    },
    {
        "name": "Ember Dawn", "appearance": "light",
        "bg": "#faf5ee", "bg_dim": "#f1eae1", "surface": "#f5efe7",
        "elevated": "#fffcf8", "element": "#ece4da", "hover": "#e6ddd2",
        "active": "#ddd2c5", "border": "#e2d8cc", "border_var": "#ebe3d9",
        "fg": "#3a2f2a", "muted": "#6e5f55", "comment": "#7d6d62",
        "subtle": "#a6978b",
        "accents": {
            "orange": "#c2510f", "amber": "#a5660a", "gold": "#8a6914",
            "green": "#4d7a1f", "teal": "#1f7a68", "blue": "#2a6a8a",
            "rose": "#b03a63", "red": "#b8322a", "plum": "#7f4a99",
        },
    },
]


# --- color helpers ---------------------------------------------------------

def rgb(h):
    h = h.lstrip("#")[:6]
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def hexc(c):
    return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02x}" for v in c)


def luminance(h):
    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def ensure(color, bg, ratio):
    """Shift lightness away from bg until the contrast ratio is met."""
    h, l, s = colorsys.rgb_to_hls(*rgb(color))
    step = 0.005 if luminance(bg) < 0.5 else -0.005
    while contrast(hexc(colorsys.hls_to_rgb(h, l, s)), bg) < ratio and 0 <= l <= 1:
        l += step
    return hexc(colorsys.hls_to_rgb(h, max(0, min(1, l)), s))


def mix(a, b, t):
    return hexc(tuple(x + (y - x) * t for x, y in zip(rgb(a), rgb(b))))


def alpha(h, a):
    return h[:7] + f"{round(a * 255):02x}"


def shift(color, dh=0.0, dl=0.0):
    h, l, s = colorsys.rgb_to_hls(*rgb(color))
    return hexc(colorsys.hls_to_rgb((h + dh) % 1, max(0, min(1, l + dl)), s))


def tune_status(a, bg, min_code):
    """Pick added/deleted colors that never collapse under color blindness.

    Added drifts from green toward teal and deleted from red toward crimson,
    with a lightness split, using the smallest change that keeps added vs
    deleted vs modified at least MIN_CVD_DISTANCE apart for every simulation.
    """
    best = None
    for dh_ok in range(0, 61, 5):            # green -> teal, degrees
        for dh_bad in range(0, 21, 5):        # red -> crimson, degrees
            for dl in (0, 0.04, 0.08, 0.12, 0.16):  # added lighter, deleted darker
                sign = 1 if luminance(bg) < 0.5 else -1
                ok = ensure(shift(a["green"], dh_ok / 360, sign * dl), bg, min_code)
                bad = ensure(shift(a["red"], -dh_bad / 360, -sign * dl), bg, min_code)
                score = min(worst(ok, bad)[0], worst(ok, a["amber"])[0], worst(bad, a["amber"])[0])
                cost = dh_ok + 2 * dh_bad + 200 * dl
                if score >= MIN_CVD_DISTANCE and (best is None or cost < best[0]):
                    best = (cost, ok, bad)
    if best is None:
        raise SystemExit("No color-blind-safe added/deleted pair found; adjust the palette.")
    return best[1], best[2]


# --- theme -----------------------------------------------------------------

def build(v):
    bg, dark = v["bg"], v["appearance"] == "dark"
    min_code = v.get("min_code", MIN_CODE)
    a = {k: ensure(c, bg, min_code) for k, c in v["accents"].items()}
    ok, bad = tune_status(a, bg, min_code)
    fg = ensure(v["fg"], bg, 15 if min_code > MIN_CODE else 12 if dark else 11)
    muted = ensure(v["muted"], bg, v.get("min_muted", MIN_MUTED))
    comment = ensure(v["comment"], bg, min_code)
    subtle = ensure(v["subtle"], bg, MIN_SOFT)
    disabled = mix(subtle, bg, 0.25)
    sel = 0.24 if dark else 0.18

    def status(name, color):
        return {
            name: color,
            f"{name}.background": alpha(color, 0.12 if dark else 0.10),
            f"{name}.border": alpha(color, 0.45),
        }

    style = {
        "background.appearance": "opaque",
        "accents": [a[k] for k in ("orange", "amber", "green", "teal", "blue", "plum", "rose")],

        "background": v["bg_dim"],
        "surface.background": v["surface"],
        "elevated_surface.background": v["elevated"],
        "panel.background": v["surface"],
        "drop_target.background": alpha(a["orange"], 0.12),

        "border": v["border"],
        "border.variant": v["border_var"],
        "border.focused": alpha(a["orange"], 0.6),
        "border.selected": a["orange"],
        "border.transparent": "#00000000",
        "border.disabled": mix(v["border"], bg, 0.5),
        "pane.focused_border": alpha(a["orange"], 0.6),
        "pane_group.border": v["border"],
        "panel.focused_border": a["orange"],
        "panel.indent_guide": v["border"],
        "panel.indent_guide_active": mix(v["border"], fg, 0.25),
        "panel.indent_guide_hover": mix(v["border"], fg, 0.4),

        "element.background": v["element"],
        "element.hover": v["hover"],
        "element.active": v["active"],
        "element.selected": v["active"],
        "element.disabled": mix(v["element"], bg, 0.5),
        "ghost_element.background": "#00000000",
        "ghost_element.hover": alpha(fg, 0.06),
        "ghost_element.active": alpha(fg, 0.10),
        "ghost_element.selected": alpha(a["orange"], 0.14),
        "ghost_element.disabled": "#00000000",

        "text": fg,
        "text.muted": muted,
        "text.placeholder": subtle,
        "text.disabled": disabled,
        "text.accent": a["orange"],
        "icon": mix(fg, muted, 0.35),
        "icon.muted": muted,
        "icon.placeholder": subtle,
        "icon.disabled": disabled,
        "icon.accent": a["orange"],
        "link_text.hover": a["amber"],

        "status_bar.background": v["bg_dim"],
        "title_bar.background": v["bg_dim"],
        "title_bar.inactive_background": mix(v["bg_dim"], bg, 0.5),
        "toolbar.background": bg,
        "tab_bar.background": v["bg_dim"],
        "tab.inactive_background": v["bg_dim"],
        "tab.active_background": bg,

        "scrollbar.thumb.background": alpha(fg, 0.10),
        "scrollbar.thumb.hover_background": alpha(fg, 0.20),
        "scrollbar.thumb.active_background": alpha(a["orange"], 0.45),
        "scrollbar.thumb.border": "#00000000",
        "scrollbar.track.background": "#00000000",
        "scrollbar.track.border": "#00000000",

        "editor.background": bg,
        "editor.foreground": fg,
        "editor.gutter.background": bg,
        "editor.subheader.background": v["surface"],
        "editor.active_line.background": alpha(fg, 0.04),
        "editor.highlighted_line.background": alpha(a["amber"], 0.08),
        "editor.line_number": subtle,
        "editor.active_line_number": a["amber"],
        "editor.hover_line_number": muted,
        "editor.invisible": mix(subtle, bg, 0.4),
        "editor.wrap_guide": alpha(fg, 0.05),
        "editor.active_wrap_guide": alpha(fg, 0.10),
        "editor.indent_guide": v["border"],
        "editor.indent_guide_active": mix(v["border"], fg, 0.3),
        "editor.document_highlight.read_background": alpha(a["blue"], 0.14),
        "editor.document_highlight.write_background": alpha(a["orange"], 0.20),
        "editor.document_highlight.bracket_background": alpha(a["amber"], 0.22),
        "search.match_background": alpha(a["amber"], 0.25),
        "search.active_match_background": alpha(a["orange"], 0.45),

        "terminal.background": bg,
        "terminal.foreground": fg,
        "terminal.bright_foreground": ensure(fg, bg, 14),
        "terminal.dim_foreground": muted,
        "terminal.ansi.background": bg,

        "version_control.added": ok,
        "version_control.modified": a["amber"],
        "version_control.deleted": bad,
        "version_control.word_added": alpha(ok, 0.30),
        "version_control.word_deleted": alpha(bad, 0.30),
        "version_control.conflict_marker.ours": alpha(ok, 0.18),
        "version_control.conflict_marker.theirs": alpha(a["blue"], 0.18),
    }

    for name, color in [
        ("error", bad), ("warning", a["amber"]), ("info", a["blue"]),
        ("hint", muted), ("success", ok), ("created", ok),
        ("deleted", bad), ("modified", a["amber"]), ("renamed", a["blue"]),
        ("conflict", a["gold"]), ("hidden", subtle), ("ignored", subtle),
        ("predictive", comment), ("unreachable", subtle),
    ]:
        style.update(status(name, color))

    ansi = {
        "black": v["element"] if dark else fg, "red": a["red"], "green": a["green"],
        "yellow": a["amber"], "blue": a["blue"], "magenta": a["rose"],
        "cyan": a["teal"], "white": fg if dark else v["active"],
    }
    toward = "#ffffff" if dark else "#000000"
    for k, c in ansi.items():
        style[f"terminal.ansi.{k}"] = c
        style[f"terminal.ansi.bright_{k}"] = mix(c, toward, 0.22)
        style[f"terminal.ansi.dim_{k}"] = mix(c, bg, 0.35)
    style["terminal.ansi.bright_black"] = subtle

    style["players"] = [
        {"cursor": a[k], "background": a[k], "selection": alpha(a[k], sel)}
        for k in ("orange", "blue", "green", "rose", "plum", "teal", "gold", "red")
    ]

    def s(color, **kw):
        return {"color": color, **kw}

    italic = {"font_style": "italic"}
    style["syntax"] = {
        "comment": s(comment, **italic),
        "comment.doc": s(mix(comment, a["gold"], 0.25), **italic),
        "comment.todo": s(a["amber"], font_weight=700),
        "comment.note": s(a["blue"], font_weight=700),
        "comment.warning": s(a["amber"], font_weight=700),
        "comment.error": s(a["red"], font_weight=700),

        "keyword": s(a["orange"]),
        "keyword.control": s(a["orange"]),
        "keyword.operator": s(a["orange"]),
        "keyword.import": s(a["rose"]),
        "keyword.return": s(a["orange"], **italic),
        "keyword.function": s(a["orange"]),
        "keyword.modifier": s(a["orange"]),
        "keyword.directive": s(a["plum"]),
        "keyword.exception": s(a["red"]),
        "operator": s(mix(a["orange"], fg, 0.45)),

        "punctuation": s(muted),
        "punctuation.bracket": s(mix(muted, fg, 0.35)),
        "punctuation.delimiter": s(muted),
        "punctuation.special": s(a["rose"]),
        "punctuation.list_marker": s(a["orange"]),
        "punctuation.markup": s(a["orange"]),

        "string": s(a["green"]),
        "string.doc": s(a["green"], **italic),
        "string.escape": s(a["teal"]),
        "string.regex": s(a["teal"]),
        "string.special": s(a["teal"]),
        "string.special.symbol": s(a["rose"]),
        "string.special.url": s(a["blue"]),
        "character": s(a["green"]),
        "number": s(a["rose"]),
        "boolean": s(a["rose"]),
        "constant": s(a["rose"]),
        "constant.builtin": s(a["rose"], **italic),

        "function": s(a["amber"]),
        "function.call": s(a["amber"]),
        "function.method": s(a["amber"]),
        "function.definition": s(a["amber"], font_weight=600),
        "function.builtin": s(a["amber"], **italic),
        "function.macro": s(a["plum"]),
        "function.special": s(a["plum"]),
        "constructor": s(a["gold"]),

        "type": s(a["gold"]),
        "type.builtin": s(a["gold"], **italic),
        "type.interface": s(a["gold"], **italic),
        "type.super": s(a["gold"]),
        "enum": s(a["gold"]),
        "variant": s(a["plum"]),
        "namespace": s(mix(a["gold"], fg, 0.4)),

        "variable": s(fg),
        "variable.member": s(a["blue"]),
        "variable.parameter": s(mix(a["amber"], fg, 0.6)),
        "variable.special": s(a["red"], **italic),
        "variable.builtin": s(a["red"], **italic),
        "property": s(a["blue"]),
        "field": s(a["blue"]),
        "label": s(a["teal"]),
        "attribute": s(a["plum"]),
        "decorator": s(a["plum"]),
        "preproc": s(a["plum"]),
        "embedded": s(fg),
        "primary": s(fg),

        "tag": s(a["red"]),
        "tag.doctype": s(a["plum"]),
        "selector": s(a["amber"]),
        "selector.pseudo": s(a["plum"]),

        "title": s(a["orange"], font_weight=700),
        "text.literal": s(a["green"]),
        "emphasis": s(a["rose"], **italic),
        "emphasis.strong": s(a["amber"], font_weight=700),
        "link_text": s(a["blue"]),
        "link_uri": s(a["teal"], **italic),

        "diff.plus": s(ok),
        "diff.minus": s(bad),
        "hint": s(muted, **italic),
        "predictive": s(comment, **italic),
    }
    return {"name": v["name"], "appearance": v["appearance"], "style": style}


# --- preview ---------------------------------------------------------------

SAMPLE = [
    [("comment", "// Ember Dusk: warm colors, AA contrast everywhere")],
    [("keyword.import", "import"), ("punctuation", " { "), ("type", "Ember"),
     ("punctuation", " } "), ("keyword.import", "from"), ("string", " \"./fire\""),
     ("punctuation", ";")],
    [],
    [("keyword", "export"), ("keyword", " async function "),
     ("function.definition", "kindle"), ("punctuation.bracket", "("),
     ("variable.parameter", "heat"), ("punctuation", ": "), ("type.builtin", "number"),
     ("punctuation.bracket", ") {")],
    [("keyword", "  const "), ("variable", "flame"), ("operator", " = "),
     ("keyword", "new "), ("constructor", "Ember"), ("punctuation.bracket", "({ "),
     ("property", "glow"), ("punctuation", ": "), ("number", "0.82"),
     ("punctuation", ", "), ("property", "lit"), ("punctuation", ": "),
     ("boolean", "true"), ("punctuation.bracket", " });")],
    [("keyword", "  if "), ("punctuation.bracket", "("), ("variable", "heat"),
     ("operator", " > "), ("constant", "MAX_HEAT"), ("punctuation.bracket", ") "),
     ("keyword.return", "return "), ("string", "`too hot: "),
     ("string.escape", "${heat}"), ("string", "`"), ("punctuation", ";")],
    [("keyword.return", "  return await "), ("variable", "flame"),
     ("punctuation", "."), ("function.method", "spread"),
     ("punctuation.bracket", "("), ("string.regex", "/sparks?/g"),
     ("punctuation.bracket", ");")],
    [("punctuation.bracket", "}")],
]


def preview(theme):
    st, syn = theme["style"], theme["style"]["syntax"]
    lh, x0, y0 = 22, 64, 56
    w, h = 760, y0 + lh * len(SAMPLE) + 24
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" rx="10" fill="{st["editor.background"]}"/>',
        f'<rect width="{w}" height="34" rx="10" fill="{st["title_bar.background"]}"/>',
        f'<rect y="24" width="{w}" height="10" fill="{st["title_bar.background"]}"/>',
        f'<text x="{w // 2}" y="22" text-anchor="middle" font-family="-apple-system,Segoe UI,sans-serif" '
        f'font-size="12" fill="{st["text.muted"]}">{theme["name"]} · kindle.ts</text>',
        f'<rect x="0" y="{y0 + lh * 3 - 15}" width="{w}" height="{lh}" fill="{st["editor.active_line.background"]}"/>',
        '<g font-family="JetBrains Mono,Menlo,Consolas,monospace" font-size="13.5" xml:space="preserve">',
    ]
    for i, line in enumerate(SAMPLE):
        y = y0 + i * lh
        num = st["editor.active_line_number"] if i == 3 else st["editor.line_number"]
        out.append(f'<text x="{x0 - 20}" y="{y}" text-anchor="end" fill="{num}">{i + 1}</text>')
        spans = "".join(
            f'<tspan fill="{syn[k]["color"]}"'
            + (' font-style="italic"' if syn[k].get("font_style") == "italic" else "")
            + (f' font-weight="{syn[k]["font_weight"]}"' if syn[k].get("font_weight") else "")
            + f'>{t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&#160;")}</tspan>'
            for k, t in line
        )
        out.append(f'<text x="{x0}" y="{y}">{spans}</text>')
    out += ["</g>", "</svg>"]
    return "\n".join(out)


def main():
    themes = [build(v) for v in VARIANTS]
    family = {
        "$schema": "https://zed.dev/schema/themes/v0.2.0.json",
        "name": "Ember Dusk",
        "author": "Divyanshu Singh",
        "themes": themes,
    }
    (ROOT / "themes" / "ember-dusk.json").write_text(json.dumps(family, indent=2) + "\n")
    (ROOT / "previews").mkdir(exist_ok=True)
    for t in themes:
        slug = t["name"].lower().replace(" ", "-")
        (ROOT / "previews" / f"{slug}.svg").write_text(preview(t) + "\n")
    print(f"Built {len(themes)} variants.")


if __name__ == "__main__":
    main()
