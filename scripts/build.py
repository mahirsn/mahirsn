"""Builds the SVG images in assets/ that the profile README shows.

GitHub strips CSS from READMEs, but an SVG shown through <img> keeps its own
styles and fonts. Each image embeds just the glyphs it uses (subset Geist),
and comes in a light and a dark version for <picture>.

    python3 scripts/build.py
"""
import base64
import io
import logging
import re
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
FONTS = {
    "sans-semibold": ROOT / "fonts/Geist-SemiBold.woff2",
    "sans": ROOT / "fonts/Geist-Regular.woff2",
    "mono": ROOT / "fonts/GeistMono-Regular.woff2",
}

# Neutral greys that sit on GitHub's own page colours, one warm accent.
THEMES = {
    "light": dict(bg="#ffffff", card="#f6f7f8", line="#e3e5e8", ink="#17191c", muted="#5d636b", accent="#e5531a"),
    "dark": dict(bg="#0d1117", card="#141a22", line="#262d37", ink="#eef1f4", muted="#9aa3ad", accent="#ff7a45"),
}

PROJECTS = [
    ("mmsimpulse", "The illogical-impulse shell on KDE, without plasmashell.", "Python"),
    ("passkey", "Your Android fingerprint as a FIDO2 security key on Linux: login, sudo, polkit and browsers.", "Rust"),
    ("mahirsn-patches", "Morphe add-on patches for YouTube: watch history kept on your own server.", "Java"),
    ("smthsModeration", "A highly customizable command executor for Minecraft moderation.", "Java"),
]

LINKS = [
    ("website", "mahirsn.net", "globe"),
    ("discord", "Discord", "discord"),
    ("instagram", "Instagram", "instagram"),
    ("youtube", "YouTube", "youtube"),
    ("reddit", "Reddit", "reddit"),
    ("gitlab", "GitLab", "gitlab"),
]

_fonts = {k: TTFont(v) for k, v in FONTS.items()}
logging.getLogger("fontTools.subset").setLevel(logging.ERROR)  # Geist's "meta" table is dropped, as intended


def font_face(name, text):
    """A @font-face rule with the font cut down to the characters in text."""
    font = TTFont(FONTS[name])
    opts = Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    sub = Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{name}';src:url(data:font/woff2;base64,{data}) format('woff2')}}"


def width(name, text, size):
    """Advance width of text in px (no kerning; close enough for wrapping)."""
    font = _fonts[name]
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    upm = font["head"].unitsPerEm
    return sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in text) * size / upm


def wrap(name, text, size, max_width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if width(name, trial, size) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def icon_path(name):
    svg = (ROOT / "scripts/icons" / f"{name}.svg").read_text()
    view = re.search(r'viewBox="([^"]+)"', svg).group(1)
    paths = re.findall(r'<path d="([^"]+)"', svg)
    return float(view.split()[2]), paths


def icon(name, x, y, size, fill):
    box, paths = icon_path(name)
    scale = size / box
    inner = "".join(f'<path d="{d}"/>' for d in paths)
    return f'<g transform="translate({x} {y}) scale({scale:.5f})" fill="{fill}">{inner}</g>'


def mark(theme):
    data = base64.b64encode((ROOT / f"scripts/mark-{theme}.png").read_bytes()).decode()
    return f"data:image/png;base64,{data}"


# Motion is one short fade on load, and none for people who ask for less.
MOTION = """
@media (prefers-reduced-motion:no-preference){
 .in{animation:in .9s cubic-bezier(.16,1,.3,1) both}
 .in2{animation:in .9s .12s cubic-bezier(.16,1,.3,1) both}
 .blink{animation:blink 1.1s steps(1) infinite}
}
@keyframes in{from{opacity:0;transform:translateY(8px)}}
@keyframes blink{50%{opacity:0}}
"""


def header(theme):
    t = THEMES[theme]
    w, h = 1200, 320
    name = "Muhammed Mahir Suna"
    line = "Linux desktop tools, Android apps and Minecraft mods."
    handle = "@mahirsn"
    css = font_face("sans-semibold", name) + font_face("sans", line) + font_face("mono", handle) + MOTION
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{name}. {line}">
<style>{css}</style>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="22" fill="{t['card']}" stroke="{t['line']}"/>
<g class="in">
 <text x="64" y="112" font-family="mono" font-size="22" fill="{t['muted']}">{handle}<tspan class="blink" fill="{t['accent']}">_</tspan></text>
 <text x="62" y="186" font-family="sans-semibold" font-size="64" letter-spacing="-2" fill="{t['ink']}">{name}</text>
 <text x="64" y="240" font-family="sans" font-size="26" fill="{t['muted']}">{escape(line)}</text>
</g>
<g class="in2">
 <circle cx="1030" cy="160" r="104" fill="none" stroke="{t['line']}" stroke-width="2"/>
 <circle cx="1030" cy="160" r="122" fill="none" stroke="{t['accent']}" stroke-width="2" stroke-dasharray="3 9" stroke-linecap="round" opacity="0.8"/>
 <image href="{mark(theme)}" x="950" y="80" width="160" height="160"/>
</g>
</svg>"""


def chip(theme, label, icon_name):
    t = THEMES[theme]
    size, pad, gap, icon_size = 17, 18, 10, 18
    w = round(pad + icon_size + gap + width("sans-semibold", label, size) + pad)
    h = 44
    css = font_face("sans-semibold", label)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">
<style>{css}</style>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{h / 2 - 0.5}" fill="{t['card']}" stroke="{t['line']}"/>
{icon(icon_name, pad, (h - icon_size) / 2, icon_size, t['ink'])}
<text x="{pad + icon_size + gap}" y="28.5" font-family="sans-semibold" font-size="{size}" fill="{t['ink']}">{escape(label)}</text>
</svg>"""


def card(theme, title, text, lang):
    t = THEMES[theme]
    w, h = 580, 210
    lines = wrap("sans", text, 19, w - 64 - 40)[:3]
    css = font_face("sans-semibold", title) + font_face("sans", " ".join(lines)) + font_face("mono", lang)
    body = "".join(
        f'<text x="32" y="{110 + i * 28}" font-family="sans" font-size="19" fill="{t["muted"]}">{escape(l)}</text>'
        for i, l in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}: {escape(text)}">
<style>{css}</style>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="18" fill="{t['card']}" stroke="{t['line']}"/>
<text x="32" y="64" font-family="sans-semibold" font-size="30" letter-spacing="-0.6" fill="{t['ink']}">{escape(title)}</text>
{icon("arrow-up-right", w - 32 - 22, 40, 22, t['muted'])}
{body}
<rect x="32" y="{h - 38}" width="10" height="10" rx="2" fill="{t['accent']}"/>
<text x="50" y="{h - 28}" font-family="mono" font-size="15" fill="{t['muted']}">{escape(lang)}</text>
</svg>"""


def main():
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        (OUT / f"header-{theme}.svg").write_text(header(theme))
        for slug, label, icon_name in LINKS:
            (OUT / f"link-{slug}-{theme}.svg").write_text(chip(theme, label, icon_name))
        for title, text, lang in PROJECTS:
            (OUT / f"project-{title}-{theme}.svg").write_text(card(theme, title, text, lang))
    print(f"wrote {len(list(OUT.glob('*.svg')))} images to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
