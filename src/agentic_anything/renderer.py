"""Optional Playwright rendering: JS execution, screenshots, network sniffing.

Playwright is an optional dependency (``pip install agentic-anything[render]``
plus ``python -m playwright install chromium``). Import is lazy so the core
package works without it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RenderResult:
    final_url: str
    html: str
    status: int = 200
    title: str = ""
    screenshot: bytes | None = None
    network_log: list[dict] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.html) and 200 <= self.status < 400


class Renderer:
    """Holds one headless Chromium instance for the whole crawl."""

    def __init__(self, timeout_ms: int = 20000, render_wait_ms: int = 1200) -> None:
        self.timeout_ms = timeout_ms
        self.render_wait_ms = render_wait_ms
        self._playwright = None
        self._browser = None

    def __enter__(self) -> "Renderer":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on extras
            raise RuntimeError(
                "Rendered capture requires Playwright. Install with:\n"
                "  pip install 'agentic-anything[render]'\n"
                "  python -m playwright install chromium"
            ) from exc
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        return self

    def __exit__(self, *exc_info) -> None:
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass

    def render(self, url: str, screenshot: bool = False, sniff: bool = True) -> RenderResult:
        assert self._browser is not None, "Renderer must be used as a context manager"
        context = None
        network_log: list[dict] = []
        try:
            context = self._browser.new_context(viewport={"width": 1366, "height": 900})
            page = context.new_page()

            if sniff:
                def on_response(response) -> None:
                    try:
                        request = response.request
                        if request.resource_type in ("xhr", "fetch") or "json" in (
                            response.headers.get("content-type", "")
                        ):
                            network_log.append(
                                {
                                    "url": request.url,
                                    "method": request.method,
                                    "status": response.status,
                                    "resource_type": request.resource_type,
                                    "response_content_type": response.headers.get("content-type", ""),
                                }
                            )
                    except Exception:
                        pass

                page.on("response", on_response)

            response = page.goto(url, timeout=self.timeout_ms, wait_until="load")
            status = response.status if response is not None else 200
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            if self.render_wait_ms > 0:
                page.wait_for_timeout(self.render_wait_ms)

            shot: bytes | None = None
            if screenshot and 200 <= status < 400:
                try:
                    shot = page.screenshot(full_page=True, type="png")
                except Exception:
                    shot = None

            return RenderResult(
                final_url=page.url,
                html=page.content(),
                status=status,
                title=page.title(),
                screenshot=shot,
                network_log=network_log,
            )
        except Exception as exc:
            return RenderResult(final_url=url, html="", error=f"{type(exc).__name__}: {exc}")
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
