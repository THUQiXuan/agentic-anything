# Teaser cut list — “dragons, machines, and a breaking world”

## Task

A creator has a footage folder: three open films with subtitles but no script. Assemble a short teaser (under 45 seconds) on the theme 'dragons, machines, and a breaking world'. Find the exact spoken moments, then emit a frame-accurate cut list with per-clip attribution and executable ffmpeg commands against the films' official releases. Every timecode must come from a read transcript unit.

## Edit decision list (16.686s total, budget 45s)

| # | Film | Source cue (transcript) | Padded cut (±0.75s) | Line | Evidence | Length |
|---|---|---|---|---|---|---|
| 1 | Elephants Dream (2006) | `[00:03:10.010 → 00:03:14.396]` | `00:03:09.260 → 00:03:15.146` | “Listen… Listen to the sounds of the machine.” | [F1] | 5.886s |
| 2 | Sintel (2010) | `[00:02:23.400 → 00:02:25.000]` | `00:02:22.650 → 00:02:25.750` | “A dragon.” | [F2] | 3.1s |
| 3 | Sintel (2010) | `[00:07:37.800 → 00:07:40.500]` | `00:07:37.050 → 00:07:41.250` | “These are dragon lands, Sintel.” | [F3] | 4.2s |
| 4 | Tears of Steel (2012) | `[00:06:01.000 → 00:06:03.000]` | `00:06:00.250 → 00:06:03.750` | “But that's no reason to destroy the world.” | [F4] | 3.5s |

Every “source cue” above is quoted verbatim from a transcript unit that this
run read through MCP; the padded cut is pure arithmetic on that cue.

## Cut commands (against the official releases)

```bash
ffmpeg -ss 00:03:09.260 -to 00:03:15.146 -i "https://archive.org/download/ElephantsDream/ed_1024_512kb.mp4" -c:v libx264 -c:a aac -movflags +faststart clip_01.mp4
ffmpeg -ss 00:02:22.650 -to 00:02:25.750 -i "https://download.blender.org/durian/movies/Sintel.2010.1080p.mkv" -c:v libx264 -c:a aac -movflags +faststart clip_02.mp4
ffmpeg -ss 00:07:37.050 -to 00:07:41.250 -i "https://download.blender.org/durian/movies/Sintel.2010.1080p.mkv" -c:v libx264 -c:a aac -movflags +faststart clip_03.mp4
ffmpeg -ss 00:06:00.250 -to 00:06:03.750 -i "https://media.xiph.org/tearsofsteel/tears_of_steel_1080p.webm" -c:v libx264 -c:a aac -movflags +faststart clip_04.mp4

cat > teaser_concat.txt <<'LIST'
file 'clip_01.mp4'
file 'clip_02.mp4'
file 'clip_03.mp4'
file 'clip_04.mp4'
LIST
ffmpeg -f concat -safe 0 -i teaser_concat.txt -c copy teaser.mp4
```

Re-encoding (`libx264`) keeps the cuts frame-accurate; `-c copy` on the final
concat is lossless. Timecodes are authored against the official full-length
releases listed below — a differently trimmed encode may shift them.

## Alternate / b-roll (scouted, not in the main sequence)

| Film | Source cue | Padded cut | Line | Evidence |
|---|---|---|---|---|
| Tears of Steel (2012) | `[00:00:30.800 → 00:00:34.000]` | `00:00:30.050 → 00:00:34.750` | “Why don't you just admit that you're freaked out by my robot hand?” | [F5] |

## Attribution (required by the licenses)

- **Elephants Dream (2006)** — CC-BY 2.5 — © copyright 2006, Blender Foundation / Netherlands Media Art Institute | orange.blender.org
  media: https://archive.org/download/ElephantsDream/ed_1024_512kb.mp4
- **Sintel (2010)** — CC-BY 3.0 — © copyright Blender Foundation | durian.blender.org
  media: https://download.blender.org/durian/movies/Sintel.2010.1080p.mkv
- **Tears of Steel (2012)** — CC-BY 3.0 — (CC) Blender Foundation | mango.blender.org
  media: https://media.xiph.org/tearsofsteel/tears_of_steel_1080p.webm

## Citations

[F1] `footage-library/elephants-dream-en-srt__elephants-dream-en__001__00-00-15` — `elephants_dream_en.srt · 00:00:15–00:03:14` — sha256 `3538c39866ce3ddb823813809395bd15e69e04ce252cd321aaa9be4779810c28`
[F2] `footage-library/sintel-en-srt__sintel-en__001__00-01-47` — `sintel_en.srt · 00:01:47–00:04:28` — sha256 `58eca9968c1ab3534b6e7b6abc54deb3919cd528207605ad10f14f5fc0fdc0f0`
[F3] `footage-library/sintel-en-srt__sintel-en__002__00-05-04` — `sintel_en.srt · 00:05:04–00:07:44` — sha256 `f72121b65476a6963033f61465fc62e08d32ca17d5a89799d029a4567cd4cc93`
[F4] `footage-library/tears-of-steel-en-srt__tears-of-steel-en__002__00-03-23` — `tears_of_steel_en.srt · 00:03:23–00:06:25` — sha256 `a9f9c6ff2d04c720e6687b8d49a3dadc89cb02f2fc215dcfa805a6bc25e1e135`
[F5] `footage-library/tears-of-steel-en-srt__tears-of-steel-en__001__00-00-23` — `tears_of_steel_en.srt · 00:00:23–00:03:23` — sha256 `55392d6ac98f89c07a71f9c7a4f3eb17de7a394d862c208abd26b5abf720c69e`
