"""Small shared helpers: slugs, page ids, JSON IO, timestamps."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slugify(text: str, max_len: int = 60) -> str:
    """Filesystem/package-safe slug: 'Quotes to Scrape' -> 'quotes-to-scrape'."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len].strip("-") or "site"


def site_slug_from_url(url: str) -> str:
    host = urlsplit(url).netloc.split("@")[-1].split(":")[0]
    host = re.sub(r"^www\.", "", host)
    return slugify(host) or "site"


def normalize_url(url: str) -> str:
    """Drop fragments and normalize the path for dedup purposes."""
    parts = urlsplit(url)
    path = parts.path or "/"
    # collapse duplicate slashes but keep the scheme's '//'
    path = re.sub(r"/{2,}", "/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def url_path_of(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return path


_PAGE_EXTENSIONS = (".html", ".htm", ".php", ".asp", ".aspx", ".jsp", ".shtml")


def page_id_from_url(url: str) -> str:
    """Stable, readable page id derived from the URL path.

    '/'              -> 'index'
    '/docs/api.html' -> 'docs__api'
    '/a?page=2'      -> 'a__q_<hash8>'  (query strings are hashed to stay short)
    """
    parts = urlsplit(url)
    path = parts.path or "/"
    path = path.strip("/")
    lower = path.lower()
    for ext in _PAGE_EXTENSIONS:
        if lower.endswith(ext):
            path = path[: -len(ext)]
            break
    if not path:
        base = "index"
    else:
        segs = [slugify(seg, 40) or "x" for seg in path.split("/")]
        base = "__".join(segs)[:120] or "index"
    if parts.query:
        qhash = hashlib.sha1(parts.query.encode("utf-8")).hexdigest()[:8]
        base = f"{base}__q_{qhash}"
    return base


def same_origin(a: str, b: str) -> bool:
    pa, pb = urlsplit(a), urlsplit(b)
    return (pa.scheme, pa.netloc.lower()) == (pb.scheme, pb.netloc.lower())


def with_default_scheme(source: str) -> str:
    """Prepend a scheme to a bare host; localhost/private hosts get http."""
    if "://" in source:
        return source
    host = source.split("/")[0].split(":")[0].lower()
    private = (host in ("localhost", "127.0.0.1", "::1", "0.0.0.0")
               or host.startswith(("192.168.", "10.", "172.16.", "172.17.",
                                   "172.18.", "172.19.", "172.2", "172.30.",
                                   "172.31.")))
    return ("http://" if private else "https://") + source


def _site_host(url: str) -> str:
    host = urlsplit(url).netloc.split("@")[-1].lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def same_site(a: str, b: str) -> bool:
    """Same host, ignoring scheme and a leading 'www.'.

    Crawl boundaries use this instead of strict origin: real sites routinely
    redirect http<->https and apex<->www, and treating those as foreign would
    silently truncate the crawl.
    """
    return _site_host(a) == _site_host(b)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def truncate_text(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
