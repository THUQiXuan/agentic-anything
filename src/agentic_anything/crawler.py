"""Same-origin BFS crawler with a page budget and a skipped-page frontier.

Priority order (lower bucket = fetched first):
  0. the seed URL and user-supplied extra seeds
  1. links that continue the seed's path prefix (stay on-topic)
  2. other same-origin content links
  3. navigation-bar links (global nav tends to fan out)
  4. sitemap-discovered URLs

Everything discovered but not fetched is recorded in the frontier with a
skip reason, so agents can see what exists beyond the budget.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .config import BuildConfig
from .fetcher import FetchResult, RobotsGate, fetch
from .parser import PageStructure, parse_html
from .renderer import RenderResult
from .util import normalize_url, page_id_from_url, same_site, sha256_bytes

_SKIP_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".css", ".js", ".mjs", ".map",
    ".json", ".xml", ".rss", ".atom", ".txt", ".csv", ".yaml", ".yml",
    ".pdf", ".zip", ".gz", ".tar", ".dmg", ".exe",
    ".mp4", ".mp3", ".webm", ".avi", ".mov",
    ".woff", ".woff2", ".ttf", ".eot",
)


@dataclass
class CrawledPage:
    page_id: str
    url: str
    final_url: str
    status: int
    html: str
    structure: PageStructure
    discovered_via: str
    depth: int
    redirect_chain: list[str] = field(default_factory=list)
    rendered: bool = False
    screenshot: bytes | None = None
    network_log: list[dict] = field(default_factory=list)


@dataclass
class FrontierEntry:
    url: str
    candidate_page_id: str
    skip_reason: str
    discovered_via: str
    from_page_id: str = ""


@dataclass
class CrawlOutcome:
    pages: list[CrawledPage] = field(default_factory=list)
    frontier: list[FrontierEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _crawlable(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return False
    path = parts.path.lower()
    return not path.endswith(_SKIP_EXTENSIONS)


def crawl(
    seed_url: str,
    config: BuildConfig,
    renderer=None,
    sitemap_urls: list[str] | None = None,
    progress=None,
) -> CrawlOutcome:
    outcome = CrawlOutcome()
    robots = RobotsGate(enabled=config.respect_robots, timeout=min(config.timeout, 10.0))

    counter = 0  # FIFO tiebreaker within a priority bucket
    queue: list[tuple[int, int, str, str, str, int]] = []  # (bucket, n, url, via, from_page, depth)
    queued: set[str] = set()  # dedup keys (normalized URLs); originals are fetched
    fetched: dict[str, tuple[str, str]] = {}  # page_id -> (final_url, content_sha)

    def enqueue(url: str, bucket: int, via: str, from_page: str, depth: int) -> None:
        nonlocal counter
        key = normalize_url(url)
        if key in queued or not _crawlable(url):
            return
        queued.add(key)
        counter += 1
        heapq.heappush(queue, (bucket, counter, url, via, from_page, depth))

    enqueue(seed_url, 0, "seed", "", 0)
    for extra in config.extra_seeds:
        enqueue(extra, 0, "extra_seed", "", 0)
    for sm_url in (sitemap_urls or [])[:200]:
        if same_site(sm_url, seed_url):
            enqueue(sm_url, 4, "sitemap", "", 1)

    seed_path_prefix = urlsplit(seed_url).path.rstrip("/") or "/"

    while queue:
        bucket, _, url, via, from_page, depth = heapq.heappop(queue)
        candidate_id = page_id_from_url(url)

        if len(outcome.pages) >= config.max_pages:
            outcome.frontier.append(
                FrontierEntry(url, candidate_id, "page_budget_exhausted", via, from_page)
            )
            continue
        if config.same_origin_only and not same_site(url, seed_url):
            outcome.frontier.append(
                FrontierEntry(url, candidate_id, "cross_site_filtered", via, from_page)
            )
            continue
        if not robots.allowed(url):
            outcome.frontier.append(
                FrontierEntry(url, candidate_id, "robots_disallowed", via, from_page)
            )
            continue

        page, skip_reason = _capture_one(url, config, renderer)
        if page is None:
            outcome.frontier.append(FrontierEntry(url, candidate_id, skip_reason, via, from_page))
            continue
        if config.same_origin_only and not same_site(page.final_url, seed_url):
            outcome.frontier.append(
                FrontierEntry(url, candidate_id, "cross_site_redirect", via, from_page)
            )
            if via == "seed":
                outcome.notes.append(
                    f"seed redirected off-origin to {page.final_url}; nothing captured from it"
                )
            continue
        if not robots.allowed(page.final_url):  # redirect landed somewhere disallowed
            outcome.frontier.append(
                FrontierEntry(url, candidate_id, "robots_disallowed_after_redirect", via, from_page)
            )
            continue

        page.discovered_via = via
        page.depth = depth
        # Assign a unique page id. Redirect aliases and identical content
        # dedupe; genuinely different pages that slug to the same id get a
        # '~N' suffix instead of being silently dropped.
        pid = page_id_from_url(page.final_url)
        sha = sha256_bytes(page.html.encode("utf-8", errors="replace"))
        if pid in fetched:
            prev_url, prev_sha = fetched[pid]
            if prev_url == page.final_url or prev_sha == sha:
                outcome.frontier.append(
                    FrontierEntry(url, pid, "duplicate_of_captured_page", via, from_page)
                )
                continue
            n = 2
            while f"{pid}~{n}" in fetched:
                n += 1
            pid = f"{pid}~{n}"
        page.page_id = pid
        fetched[pid] = (page.final_url, sha)
        outcome.pages.append(page)
        if progress:
            progress(page)

        if page.structure.refresh_url and same_site(page.structure.refresh_url, seed_url):
            enqueue(page.structure.refresh_url, 1, "meta_refresh", page.page_id, depth + 1)

        for link in page.structure.links:
            target = link.url
            if not _crawlable(target):
                continue
            if not same_site(target, seed_url):
                if not config.same_origin_only:
                    enqueue(target, 2, "content_link", page.page_id, depth + 1)
                else:
                    # record one frontier entry per off-site target
                    key = normalize_url(target)
                    if key not in queued:
                        queued.add(key)
                        outcome.frontier.append(
                            FrontierEntry(
                                target, page_id_from_url(target),
                                "cross_site_filtered", "content_link", page.page_id,
                            )
                        )
                continue
            target_path = urlsplit(target).path
            if link.is_nav:
                enqueue(target, 3, "nav_link", page.page_id, depth + 1)
            elif target_path.startswith(seed_path_prefix) and seed_path_prefix != "/":
                enqueue(target, 1, "seed_path_link", page.page_id, depth + 1)
            else:
                enqueue(target, 2, "content_link", page.page_id, depth + 1)

    return outcome


def _capture_one(url: str, config: BuildConfig, renderer) -> tuple[CrawledPage | None, str]:
    if renderer is not None:
        render: RenderResult = renderer.render(
            url, screenshot=config.screenshots, sniff=config.sniff_network
        )
        if not render.error and render.html and render.status >= 400:
            # Real HTTP error page — do not capture it as content.
            return None, f"fetch_failed_http_{render.status}"
        if render.ok:
            structure = parse_html(render.html, render.final_url)
            return (
                CrawledPage(
                    page_id=page_id_from_url(render.final_url),
                    url=url,
                    final_url=normalize_url(render.final_url),
                    status=render.status,
                    html=render.html,
                    structure=structure,
                    discovered_via="",
                    depth=0,
                    rendered=True,
                    screenshot=render.screenshot,
                    network_log=render.network_log,
                ),
                "",
            )
        # renderer crashed or returned nothing — fall back to static fetch

    result: FetchResult = fetch(url, timeout=config.timeout)
    if not result.ok:
        return None, f"fetch_failed_http_{result.status}" if result.status else "fetch_failed"
    if not result.is_html:
        return None, "not_html"
    html = result.text()
    structure = parse_html(html, result.final_url)
    return (
        CrawledPage(
            page_id=page_id_from_url(result.final_url),
            url=url,
            final_url=normalize_url(result.final_url),
            status=result.status,
            html=html,
            structure=structure,
            discovered_via="",
            depth=0,
            redirect_chain=result.redirect_chain,
        ),
        "",
    )
