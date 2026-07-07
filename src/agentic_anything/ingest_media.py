"""Media ingestion: local audio/video files and online videos.

Local files (mp4/mkv/webm/mp3/wav/...):
  1. a sidecar subtitle file next to the video (same stem, .srt/.vtt) wins;
  2. otherwise embedded subtitles are extracted with ``ffmpeg``;
  3. otherwise the audio is transcribed with ``whisper`` (or
     ``faster-whisper``'s CLI) when installed;
  4. otherwise a clear error explains what to install.

Online videos (YouTube/Bilibili/Vimeo/... URLs) use ``yt-dlp`` to fetch
manual or automatic subtitles without downloading the video. The metadata
(title/uploader/duration/description) becomes an extra unit.

External tools are invoked with timeouts and never with shell=True.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .util import slugify, truncate_text

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".aac"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

VIDEO_HOSTS = (
    "youtube.com", "youtu.be", "bilibili.com", "b23.tv", "vimeo.com",
    "dailymotion.com", "twitch.tv", "nicovideo.jp",
)

_TOOL_TIMEOUT = 600


class MediaError(ValueError):
    pass


def _run(cmd: list[str], timeout: int = _TOOL_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False
    )


def _tool(name: str) -> str | None:
    return shutil.which(name)


def is_video_url(url: str) -> bool:
    bare = url.split("?")[0].split("#")[0]
    host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", bare).split("/")[0])
    host = host.split(":")[0].lower()  # strip an explicit port
    if any(host == h or host.endswith("." + h) for h in VIDEO_HOSTS):
        return True
    return bare.lower().endswith(tuple(MEDIA_EXTENSIONS))


# ------------------------------------------------------------ local files --

def ingest_local_media(path: Path) -> list:
    """Local audio/video file → transcript units (+ a metadata unit)."""
    from .ingest import _ingest_subtitles

    units = []
    meta_unit = _probe_metadata(path)
    if meta_unit is not None:
        units.append(meta_unit)

    subtitle = _find_transcript(path)
    units.extend(_ingest_subtitles(subtitle))
    for unit in units:
        unit.source_path = str(path)
    return units


def _find_transcript(path: Path) -> Path:
    # 1. sidecar subtitle
    for ext in (".srt", ".vtt"):
        sidecar = path.with_suffix(ext)
        if sidecar.exists():
            return sidecar
    workdir = Path(tempfile.mkdtemp(prefix="aany_media_"))

    # 2. embedded subtitles via ffmpeg
    if _tool("ffmpeg"):
        out = workdir / "embedded.srt"
        proc = _run(["ffmpeg", "-nostdin", "-y", "-i", str(path),
                     "-map", "0:s:0", "-f", "srt", str(out)], timeout=300)
        if proc.returncode == 0 and out.exists() and out.stat().st_size > 0:
            return out

    # 3. speech-to-text via whisper
    whisper = _tool("whisper") or _tool("faster-whisper")
    if whisper:
        proc = _run([whisper, str(path), "--output_format", "srt",
                     "--output_dir", str(workdir)], timeout=_TOOL_TIMEOUT)
        candidates = sorted(workdir.glob("*.srt"))
        if proc.returncode == 0 and candidates:
            return candidates[0]

    hints = []
    if not _tool("ffmpeg"):
        hints.append("ffmpeg (extracts embedded subtitles)")
    if not (_tool("whisper") or _tool("faster-whisper")):
        hints.append("openai-whisper (`pip install openai-whisper`, transcribes speech)")
    raise MediaError(
        f"no transcript available for {path.name}: no sidecar .srt/.vtt, "
        f"no embedded subtitles, no transcriber. Install: {', '.join(hints) or 'n/a'} "
        "— or place a subtitle file next to the media file."
    )


def _probe_metadata(path: Path):
    from .ingest import Unit

    if not _tool("ffprobe"):
        return None
    proc = _run(["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", str(path)], timeout=60)
    if proc.returncode != 0:
        return None
    try:
        info = json.loads(proc.stdout)
    except ValueError:
        return None
    fmt = info.get("format", {})
    lines = [f"file: {path.name}"]
    if fmt.get("duration"):
        seconds = float(fmt["duration"])
        lines.append(f"duration: {int(seconds // 60)}m{int(seconds % 60):02d}s")
    for stream in info.get("streams", []):
        kind = stream.get("codec_type")
        codec = stream.get("codec_name", "?")
        if kind == "video":
            lines.append(f"video: {codec} {stream.get('width')}x{stream.get('height')}")
        elif kind == "audio":
            lines.append(f"audio: {codec} {stream.get('sample_rate')}Hz")
        elif kind == "subtitle":
            lines.append(f"embedded subtitles: {codec} "
                         f"({stream.get('tags', {}).get('language', '?')})")
    return Unit(
        unit_id=f"{slugify(path.stem, 40)}__000__media-info",
        title=f"Media info: {path.name}",
        kind="metadata",
        content=[{"kind": "p", "text": ln} for ln in lines],
        source_path=str(path),
        locator="metadata",
    )


# ------------------------------------------------------------ remote URLs --

def _ytdlp_base_cmd() -> list[str]:
    """yt-dlp with a JS runtime fallback: YouTube extraction needs one, and
    only deno is enabled by default — pass node explicitly if that's what
    the machine has."""
    cmd = ["yt-dlp", "--no-playlist"]
    if not _tool("deno") and _tool("node"):
        cmd += ["--js-runtimes", "node"]
    return cmd


def ingest_remote_video(url: str) -> tuple[str, list]:
    """Online video URL → (title, units) via yt-dlp subtitles + metadata."""
    from .ingest import Unit, _ingest_subtitles

    if not _tool("yt-dlp"):
        raise MediaError(
            "online-video ingestion requires yt-dlp: pip install yt-dlp"
        )
    workdir = Path(tempfile.mkdtemp(prefix="aany_video_"))

    meta_proc = _run([*_ytdlp_base_cmd(), "--dump-json",
                      "--skip-download", url], timeout=180)
    if meta_proc.returncode != 0:
        raise MediaError(
            f"yt-dlp could not read the video: {truncate_text(meta_proc.stderr, 400)}"
        )
    try:
        meta = json.loads(meta_proc.stdout.splitlines()[0])
    except (ValueError, IndexError) as exc:
        raise MediaError("yt-dlp returned unparseable metadata") from exc

    title = meta.get("title") or url
    base = slugify(title, 50) or "video"

    sub_proc = _run([
        *_ytdlp_base_cmd(), "--skip-download",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", "en.*,zh.*,und,-live_chat",
        "--convert-subs", "srt",
        "-o", str(workdir / "media"),
        url,
    ], timeout=300)

    subtitle_files = sorted(
        p for p in workdir.glob("media*")
        if p.suffix.lower() in (".srt", ".vtt")
    )

    units: list = []
    info_lines = [f"title: {title}", f"url: {url}"]
    if meta.get("uploader"):
        info_lines.append(f"uploader: {meta['uploader']}")
    if meta.get("duration"):
        seconds = int(meta["duration"])
        info_lines.append(f"duration: {seconds // 60}m{seconds % 60:02d}s")
    if meta.get("upload_date"):
        info_lines.append(f"upload date: {meta['upload_date']}")
    if meta.get("view_count") is not None:
        info_lines.append(f"views: {meta['view_count']}")
    description = (meta.get("description") or "").strip()
    content = [{"kind": "p", "text": ln} for ln in info_lines]
    if description:
        content.append({"kind": "heading", "level": 2, "text": "Description"})
        content += [{"kind": "p", "text": truncate_text(p, 2000)}
                    for p in re.split(r"\n\s*\n", description) if p.strip()]
    units.append(Unit(
        unit_id=f"{base}__000__video-info",
        title=f"Video: {title}",
        kind="metadata",
        content=content,
        source_path=url,
        locator="metadata",
    ))

    if subtitle_files:
        transcript_units = _ingest_subtitles(subtitle_files[0])
        for unit in transcript_units:
            unit.source_path = url
        units.extend(transcript_units)
    else:
        units[0].content.append({
            "kind": "p",
            "text": "(no subtitles available for this video — transcript "
                    f"missing; yt-dlp said: {truncate_text(sub_proc.stderr, 200)})",
        })
    return title, units
