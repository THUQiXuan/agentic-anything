"""HTTP fetching with redirect tracking, retries, and robots.txt support.

Stdlib-only (urllib) so the core install has zero dependencies.
"""

from __future__ import annotations

import gzip
import io
import re
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from .config import USER_AGENT

_META_CHARSET_RE = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([a-zA-Z0-9_\-]+)""", re.IGNORECASE
)


def encode_url_for_fetch(url: str) -> str:
    """Make an IRI safe for urllib: percent-encode path/query, IDNA the host.

    Hrefs like ``/café`` or ``/日本語`` are legal in HTML but crash
    http.client if passed through verbatim.
    """
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        try:
            host.encode("ascii")
        except UnicodeEncodeError:
            host = host.encode("idna").decode("ascii")
        netloc = host
        if parts.port:
            netloc = f"{netloc}:{parts.port}"
        if parts.username:
            cred = quote(parts.username, safe="")
            if parts.password:
                cred += ":" + quote(parts.password, safe="")
            netloc = f"{cred}@{netloc}"
        path = quote(parts.path, safe="/%:@&=+$,;~*!()'")
        query = quote(parts.query, safe="=&%:@+$,;~*!()'/?")
        return urlunsplit((parts.scheme, netloc, path, query, ""))
    except Exception:
        return url


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    content_type: str
    body: bytes
    charset: str = ""
    redirect_chain: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and 200 <= self.status < 300

    @property
    def is_html(self) -> bool:
        return "html" in self.content_type

    def text(self, limit: int | None = None) -> str:
        data = self.body if limit is None else self.body[:limit]
        # 1. charset from Content-Type; 2. <meta charset> sniff; 3. UTF-8.
        for encoding in (self.charset, _sniff_meta_charset(data), "utf-8"):
            if not encoding:
                continue
            try:
                return data.decode(encoding, errors="strict" if encoding != "utf-8" else "replace")
            except (LookupError, UnicodeDecodeError):
                continue
        return data.decode("utf-8", errors="replace")


def _sniff_meta_charset(data: bytes) -> str:
    match = _META_CHARSET_RE.search(data[:4096])
    return match.group(1).decode("ascii", errors="ignore") if match else ""


def _parse_content_type(raw: str) -> tuple[str, str]:
    """'text/html; charset=GBK' -> ('text/html', 'gbk')"""
    if not raw:
        return "", ""
    parts = raw.split(";")
    media_type = parts[0].strip().lower()
    charset = ""
    for param in parts[1:]:
        if "=" in param:
            key, _, value = param.partition("=")
            if key.strip().lower() == "charset":
                charset = value.strip().strip("\"'").lower()
    return media_type, charset


class _RedirectRecorder(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        self.chain: list[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, timeout: float = 20.0, max_bytes: int = 8_000_000, retries: int = 2) -> FetchResult:
    """GET a URL, following redirects and recording the chain."""
    last_error = ""
    fetch_url = encode_url_for_fetch(url)
    for attempt in range(retries + 1):
        recorder = _RedirectRecorder()
        opener = urllib.request.build_opener(recorder)
        req = urllib.request.Request(
            fetch_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip",
            },
        )
        try:
            with opener.open(req, timeout=timeout) as resp:
                body = resp.read(max_bytes + 1)
                truncated = len(body) > max_bytes
                if truncated:
                    body = body[:max_bytes]
                if resp.headers.get("Content-Encoding", "") == "gzip":
                    try:
                        body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(max_bytes)
                    except EOFError:
                        # Truncated gzip stream: salvage what decompresses.
                        import zlib

                        try:
                            decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)
                            body = decomp.decompress(body, max_bytes)
                        except zlib.error:
                            pass
                    except OSError:
                        pass
                media_type, charset = _parse_content_type(resp.headers.get("Content-Type") or "")
                return FetchResult(
                    url=url,
                    final_url=resp.geturl(),
                    status=resp.status,
                    content_type=media_type,
                    charset=charset,
                    body=body,
                    redirect_chain=recorder.chain,
                )
        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = exc.read(65536)
            except Exception:
                pass
            media_type, charset = _parse_content_type(
                (exc.headers.get("Content-Type") or "") if exc.headers else ""
            )
            return FetchResult(
                url=url,
                final_url=exc.url or url,
                status=exc.code,
                content_type=media_type,
                charset=charset,
                body=body,
                redirect_chain=recorder.chain,
            )
        except Exception as exc:  # URLError, timeout, ConnectionReset, ...
            last_error = f"{type(exc).__name__}: {exc}"
    return FetchResult(url=url, final_url=url, status=0, content_type="", body=b"", error=last_error)


class RobotsGate:
    """Cached robots.txt checks per origin. Fail-open on fetch errors."""

    def __init__(self, enabled: bool = True, timeout: float = 10.0) -> None:
        self.enabled = enabled
        self.timeout = timeout
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def allowed(self, url: str) -> bool:
        if not self.enabled:
            return True
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._parsers:
            parser = urllib.robotparser.RobotFileParser()
            result = fetch(urljoin(origin, "/robots.txt"), timeout=self.timeout, retries=0)
            if result.ok and result.body:
                try:
                    parser.parse(result.text().splitlines())
                    self._parsers[origin] = parser
                except Exception:
                    self._parsers[origin] = None
            else:
                self._parsers[origin] = None
        parser = self._parsers[origin]
        if parser is None:
            return True
        try:
            if not parser.can_fetch(USER_AGENT, url):
                return False
            # URL normalization strips trailing slashes, but 'Disallow: /x/'
            # only matches the slashed form — check that variant too.
            path = urlsplit(url).path
            if path and not path.endswith("/"):
                return parser.can_fetch(USER_AGENT, url + "/")
            return True
        except Exception:
            return True
