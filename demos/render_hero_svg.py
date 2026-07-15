#!/usr/bin/env python3
"""Render the README hero: a self-contained, looping animated SVG.

Pure SVG + CSS keyframes (no JavaScript, no external fonts/images), so the
animation plays inside GitHub's README <img> sandbox. One 32-second master
timeline; every element encodes its appearance window as keyframe
percentages, which keeps the infinite loop in sync.

    python3 demos/render_hero_svg.py   # writes assets/demo-course-agent.svg
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "demo-course-agent.svg"

W, H = 960, 400
DUR = 32.0          # master loop seconds
FADE = 0.45         # scene cross-fade seconds
LINE_H = 26
X0, Y0 = 30, 92     # content origin
FS = 15             # font size

C = {
    "bg": "#0d1117", "panel": "#161b22", "line": "#30363d",
    "text": "#e6edf3", "dim": "#8b949e", "green": "#3fb950",
    "blue": "#58a6ff", "purple": "#bc8cff", "orange": "#d29922",
    "red": "#f85149",
}
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# (start, end) visibility windows per scene
S1 = (0.6, 11.0)
S2 = (11.0, 22.0)
S3 = (22.0, 31.6)

# scene line spec: (t_rel, kind, row, segments)
#   kind: "type" (clip-reveal) | "fade"
#   segments: list of (text, color_key)
SCENE1 = [
    (0.0, "type", 0, [("$ ", "green"), ("agentic-anything agentify https://cs336.stanford.edu/spring2025/ \\", "text")]),
    (1.6, "type", 1, [("      --follow-docs 6 --follow-repos 1", "text")]),
    (3.0, "fade", 3, [("  ✓ ", "green"), ("captured course page + 7 lecture-viewer pages", "dim")]),
    (3.9, "fade", 4, [("  ✓ ", "green"), ("Lecture 3 — architecture      ", "dim"), ("(PDF → 9 page-addressable units)", "blue")]),
    (4.8, "fade", 5, [("  ✓ ", "green"), ("Lecture 4 — MoEs · Lecture 5 — GPUs · Lecture 7 · 9 · 11", "dim")]),
    (5.7, "fade", 6, [("  ✓ ", "green"), ("stanford-cs336/assignment1-basics   ", "dim"), ("(repo → 31 file units)", "blue")]),
    (6.6, "fade", 7, [("  ⚠ ", "orange"), ("4 dead handout links recorded in frontier", "orange")]),
    (7.6, "fade", 8, [("  ✓ ", "green"), ("pack ready: ", "dim"), ("SKILL.md · resource CLI · MCP · chat", "green")]),
]
SCENE2 = [
    (0.2, "type", 0, [("$ ", "green"), ("agentic-anything chat packs/cs336-course", "text")]),
    (1.4, "type", 2, [("you › ", "blue"), ("Which slides cover RoPE? Which pages should I read?", "text")]),
    (3.6, "fade", 4, [("agent › ", "green"), ("RoPE is in 2025 Lecture 3 — architecture.", "text")]),
    (4.5, "fade", 5, [("        Read pages 25–32 (variants + motivation),", "text")]),
    (5.3, "fade", 6, [("        then pages 33–40 (the math + implementation).", "text")]),
    (6.4, "pill", 8, [("2025-lecture-3-architecture · pages 25-32", "purple")]),
]
SCENE3 = [
    (0.2, "type", 0, [("you › ", "blue"), ("The handout link on the course page 404s. Where's the PDF?", "text")]),
    (2.4, "fade", 2, [("agent › ", "green"), ("The page's link is dead (recorded in the pack frontier),", "text")]),
    (3.3, "fade", 3, [("        but the repo tree lists ", "text"), ("cs336_assignment1_basics.pdf", "orange")]),
    (4.1, "fade", 4, [("        (965,629 bytes) at the repo root — it was renamed.", "text")]),
    (5.2, "pill", 6, [("frontier: attachment_fetch_failed", "purple"), ("repo tree", "purple")]),
]

_anim_css: list[str] = []
_defs: list[str] = []
_body: list[str] = []
_uid = 0


def pct(t: float) -> float:
    return max(0.0, min(100.0, round(t / DUR * 100.0, 3)))


def nid(prefix: str) -> str:
    global _uid
    _uid += 1
    return f"{prefix}{_uid}"


def window_opacity(name: str, t_in: float, t_out: float, fade: float = 0.35) -> None:
    """Keyframes: invisible → fade in at t_in → fade out at t_out."""
    k = [
        "0%{opacity:0}",
        f"{pct(t_in)}%{{opacity:0}}",
        f"{pct(min(t_in + fade, t_out))}%{{opacity:1}}",
        f"{pct(max(t_out - FADE, t_in))}%{{opacity:1}}",
        f"{pct(t_out)}%{{opacity:0}}",
        "100%{opacity:0}",
    ]
    _anim_css.append(f"@keyframes {name}{{{''.join(k)}}}")


def typing_clip(name: str, t_in: float, dur: float, chars: int) -> None:
    steps = max(chars, 4)
    k = [
        f"0%{{clip-path:inset(-4px 100% -4px 0)}}",
        f"{pct(t_in)}%{{clip-path:inset(-4px 100% -4px 0)}}",
        f"{pct(t_in + dur)}%{{clip-path:inset(-4px -2px -4px 0)}}",
        f"100%{{clip-path:inset(-4px -2px -4px 0)}}",
    ]
    _anim_css.append(f"@keyframes {name}{{{''.join(k)}}}")
    return steps


def tspans(segments) -> str:
    return "".join(
        f'<tspan fill="{C[color]}">{escape(text)}</tspan>' for text, color in segments
    )


def add_line(scene_win, t_rel, kind, row, segments) -> None:
    s0, s1 = scene_win
    t_abs = s0 + t_rel
    y = Y0 + row * LINE_H
    gid = nid("e")
    win = nid("w")
    window_opacity(win, t_abs, s1)
    text_len = sum(len(t) for t, _ in segments)

    if kind == "type":
        clip = nid("t")
        dur = min(0.055 * text_len, 2.2)
        typing_clip(clip, t_abs, dur, text_len)
        _body.append(
            f'<g style="animation:{win} {DUR}s linear infinite">'
            f'<text xml:space="preserve" x="{X0}" y="{y}" font-family="{MONO}" font-size="{FS}" '
            f'style="animation:{clip} {DUR}s steps({max(text_len, 4)}, end) infinite">'
            f"{tspans(segments)}</text></g>"
        )
    elif kind == "pill":
        x = X0 + 8 * 6
        parts = [f'<g style="animation:{win} {DUR}s linear infinite">']
        for text, color in segments:
            wpx = int(len(text) * (FS * 0.62)) + 26
            parts.append(
                f'<rect x="{x}" y="{y - 17}" rx="11" ry="11" width="{wpx}" height="24" '
                f'fill="rgba(188,140,255,0.08)" stroke="{C[color]}" stroke-opacity="0.65"/>'
                f'<text x="{x + 13}" y="{y}" font-family="{MONO}" font-size="12.5" '
                f'fill="{C[color]}">{escape(text)}</text>'
            )
            x += wpx + 12
        parts.append("</g>")
        _body.append("".join(parts))
    else:  # fade
        _body.append(
            f'<g style="animation:{win} {DUR}s linear infinite">'
            f'<text xml:space="preserve" x="{X0}" y="{y}" font-family="{MONO}" font-size="{FS}">'
            f"{tspans(segments)}</text></g>"
        )


def add_cursor(scene_win, row: int, t_in_rel: float) -> None:
    s0, s1 = scene_win
    y = Y0 + row * LINE_H
    win = nid("cw")
    window_opacity(win, s0 + t_in_rel, s1)
    _body.append(
        f'<g style="animation:{win} {DUR}s linear infinite">'
        f'<rect class="cursor" x="{X0}" y="{y - 13}" width="9" height="17" fill="{C["green"]}"/></g>'
    )


def add_banner() -> None:
    t_in = S3[0] + 6.4
    win = nid("bw")
    window_opacity(win, t_in, S3[1], fade=0.8)
    y = Y0 + 8 * LINE_H + 14
    _defs.append(
        '<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{C["blue"]}"/>'
        f'<stop offset="0.55" stop-color="{C["purple"]}"/>'
        f'<stop offset="1" stop-color="{C["green"]}"/></linearGradient>'
    )
    _body.append(
        f'<g style="animation:{win} {DUR}s linear infinite">'
        f'<text x="{W / 2}" y="{y}" text-anchor="middle" font-family="{MONO}" '
        f'font-size="16.5" fill="url(#accent)" font-weight="bold">'
        "any website · PDF · video · repo · dataset  →  an agent you can talk to</text>"
        f'<text x="{W / 2}" y="{y + 30}" text-anchor="middle" '
        f'font-family="-apple-system,Segoe UI,sans-serif" font-size="14" fill="{C["dim"]}">'
        "Agentic Anything</text></g>"
    )


def main() -> int:
    # scenes
    for spec, win in ((SCENE1, S1), (SCENE2, S2), (SCENE3, S3)):
        for t_rel, kind, row, segments in spec:
            add_line(win, t_rel, kind, row, segments)
    add_cursor(S1, 9, 8.6)
    add_cursor(S2, 9, 7.6)
    add_cursor(S3, 7, 6.0)
    add_banner()

    chrome = (
        f'<rect width="{W}" height="{H}" rx="14" fill="{C["bg"]}"/>'
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13" fill="none" stroke="{C["line"]}"/>'
        f'<rect x="1" y="1" width="{W - 2}" height="42" rx="13" fill="{C["panel"]}"/>'
        f'<rect x="1" y="30" width="{W - 2}" height="14" fill="{C["panel"]}"/>'
        f'<line x1="1" y1="44" x2="{W - 1}" y2="44" stroke="{C["line"]}"/>'
        f'<circle cx="26" cy="22" r="6.5" fill="#ff5f57"/>'
        f'<circle cx="48" cy="22" r="6.5" fill="#febc2e"/>'
        f'<circle cx="70" cy="22" r="6.5" fill="#28c840"/>'
        f'<text x="{W / 2}" y="27" text-anchor="middle" font-family="{MONO}" '
        f'font-size="13" fill="{C["dim"]}">agentic-anything — course agent in 3 steps</text>'
    )

    css = (
        ".cursor{animation:blink 1.1s steps(1) infinite}"
        "@keyframes blink{0%,49%{fill-opacity:1}50%,100%{fill-opacity:0}}"
        + "".join(_anim_css)
        + "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        'aria-label="Agentic Anything demo: agentify a course URL, then chat with it">'
        f"<defs>{''.join(_defs)}</defs>"
        f"<style>{css}</style>"
        f"{chrome}"
        f"{''.join(_body)}"
        "</svg>"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")

    # sanity checks
    import xml.etree.ElementTree as ET

    ET.fromstring(svg)
    size = OUT.stat().st_size
    assert size < 250_000, f"SVG too large: {size}"
    print(f"✓ wrote {OUT.relative_to(ROOT)} ({size:,} bytes, {DUR:.0f}s loop)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
