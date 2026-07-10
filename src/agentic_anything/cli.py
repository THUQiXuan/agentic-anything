"""The `agentic-anything` command-line interface (alias: `aany`).

Subcommands:
  build  SOURCE     capture a website / file / folder into a pack
  chat   PACK_DIR   talk to the pack as a conversational agent
  serve  PACK...    host packs as agents over HTTP (A2A capable)
  mcp    PACK...    expose packs as a read-only stdio MCP server
  mcp-config PACK... print Codex or Claude Code MCP configuration
  skill  PACK_DIR   generate skills/SKILL.md for a pack (LLM or --no-llm)
  clify  PACK_DIR   generate a zero-dependency site CLI for a pack
  pack   SOURCE     one-shot: build + skill + clify
  query  PACK_DIR Q keyword search over a pack
  page   PACK_DIR ID  print one page (md or json)
  apis   PACK_DIR   show the discovered API surface
  info   PACK_DIR   pack summary

Every data-producing command supports --json. Exit codes: 0 ok, 1 error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import BuildConfig, LLMConfig
from .ingest import (
    IngestError,
    build_pack_from_cli_tool,
    build_pack_from_source,
    build_pack_from_url_asset,
    classify_url,
    detect_source_kind,
)
from .packer import build_pack
from .query import PackNotFound, PackReader, search_pack
from .sitecli import generate_site_cli
from .skills import generate_skill
from .util import site_slug_from_url, slugify, with_default_scheme


def _print_json(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _build_config_from_args(args) -> BuildConfig:
    return BuildConfig(
        max_pages=args.max_pages,
        same_origin_only=not args.allow_cross_origin,
        respect_robots=not args.ignore_robots,
        timeout=args.timeout,
        render=args.render or args.screenshots,
        screenshots=args.screenshots,
        include_html=not args.no_html,
        probe_well_known=not args.no_probe,
        extra_seeds=args.seed or [],
    )


def _llm_config_from_args(args) -> LLMConfig:
    return LLMConfig.from_env(
        model=getattr(args, "model", None),
        base_url=getattr(args, "base_url", None),
    )


def _add_build_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("url", metavar="source",
                        help="what to agentify: a website URL; a video/repo/arXiv/"
                             "PDF/feed URL; a local file (.pdf .docx .pptx .xlsx "
                             ".epub .md .txt .csv .json .ipynb .sqlite .eml .srt "
                             ".mp4 .zip ...); a folder or repo; or cli:<tool> for "
                             "installed software")
    parser.add_argument("-o", "--output", default=None,
                        help="pack directory (default: packs/<site-slug>)")
    parser.add_argument("--site-id", default=None, help="override the site id/slug")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--render", action="store_true",
                        help="render pages with Chromium (requires the [render] extra)")
    parser.add_argument("--screenshots", action="store_true",
                        help="save full-page screenshots (implies --render)")
    parser.add_argument("--no-html", action="store_true", help="do not keep captured HTML")
    parser.add_argument("--allow-cross-origin", action="store_true",
                        help="follow links to other origins (default: same-origin only)")
    parser.add_argument("--ignore-robots", action="store_true",
                        help="do not check robots.txt (use responsibly)")
    parser.add_argument("--no-probe", action="store_true",
                        help="skip sitemap/openapi/.well-known probes")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--seed", action="append", default=None,
                        help="extra seed URL (repeatable)")


def _add_llm_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=None,
                        help="chat model id (default: env AGENTIC_MODEL or google/gemini-3.5-flash)")
    parser.add_argument("--base-url", default=None,
                        help="OpenAI-compatible base URL (default: env AGENTIC_BASE_URL or OpenRouter)")
    parser.add_argument("--no-llm", action="store_true",
                        help="deterministic generation without any API calls")
    parser.add_argument("--language", choices=["en", "zh", "both"], default="en",
                        help="skill language (default: en)")


def _resolve_output(args) -> Path:
    if args.output:
        return Path(args.output)
    if args.url.startswith("cli:"):
        slug = args.site_id or slugify(args.url[4:], 60) or "tool"
        return Path("packs") / slug
    if args.url.lower().startswith("arxiv:"):
        slug = args.site_id or ("arxiv-" + slugify(args.url[6:], 40))
        return Path("packs") / slug
    if detect_source_kind(args.url) != "web":
        path = Path(args.url).expanduser()
        slug = args.site_id or slugify(path.stem if path.is_file() else path.name, 60)
    else:
        url = with_default_scheme(args.url)
        if classify_url(url) != "crawl":
            import hashlib

            stem = slugify(Path(url.split("?")[0]).stem, 40)
            tail = hashlib.sha1(url.encode()).hexdigest()[:6]
            slug = args.site_id or f"{stem or site_slug_from_url(url)}-{tail}"
        else:
            slug = args.site_id or site_slug_from_url(url)
    return Path("packs") / slug


def _run_build(args) -> tuple[int, dict]:
    out = _resolve_output(args)

    # installed software: build cli:<tool>
    if args.url.startswith("cli:"):
        result = build_pack_from_cli_tool(args.url[4:], out, site_id=args.site_id)
        return (0 if result.page_count > 0 else 1), result.as_json()

    # bare arXiv id: build arxiv:2401.12345
    if args.url.lower().startswith("arxiv:"):
        result = build_pack_from_url_asset(args.url, out, site_id=args.site_id)
        return (0 if result.page_count > 0 else 1), result.as_json()

    kind = detect_source_kind(args.url)
    if kind in ("file", "dir"):
        result = build_pack_from_source(args.url, out, site_id=args.site_id)
        return (0 if result.page_count > 0 else 1), result.as_json()

    # web URL: crawl, or a URL asset (video / repo / arXiv / file / feed)
    url = with_default_scheme(args.url)
    if classify_url(url) != "crawl":
        result = build_pack_from_url_asset(url, out, site_id=args.site_id)
        return (0 if result.page_count > 0 else 1), result.as_json()

    config = _build_config_from_args(args)

    def progress(page) -> None:
        if not args.json:
            print(f"  captured {page.page_id}  ({page.final_url})", file=sys.stderr)

    result = build_pack(args.url, out, config=config, site_id=args.site_id, progress=progress)
    return (0 if result.page_count > 0 else 1), result.as_json()


def _run_skill(args) -> dict:
    llm_config = _llm_config_from_args(args)
    use_llm = not args.no_llm
    if use_llm and not llm_config.available:
        print(
            "warning: no OPENROUTER_API_KEY / AGENTIC_API_KEY set; "
            "falling back to deterministic skill generation (--no-llm).",
            file=sys.stderr,
        )
        use_llm = False
    path = generate_skill(args.pack_dir, llm_config=llm_config, use_llm=use_llm,
                          language=args.language)
    return {"skill_path": str(path), "llm_used": use_llm,
            "model": llm_config.model if use_llm else None}


def cmd_build(args) -> int:
    rc, payload = _run_build(args)
    if args.json:
        _print_json(payload)
    else:
        print(f"pack: {payload['pack_dir']}")
        print(f"pages captured: {payload['page_count']}   frontier: {payload['frontier_count']}   "
              f"api surface entries: {payload['api_count']}")
        for warning in payload["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
    return rc


def cmd_skill(args) -> int:
    payload = _run_skill(args)
    if args.json:
        _print_json(payload)
    else:
        print(f"skill written: {payload['skill_path']}")
    return 0


def cmd_clify(args) -> int:
    path = generate_site_cli(args.pack_dir)
    if args.json:
        _print_json({"cli_path": str(path)})
    else:
        print(f"site CLI written: {path}")
        print(f"try: python {path} pages")
    return 0


def cmd_pack(args) -> int:
    rc, build_payload = _run_build(args)
    if rc != 0:
        if args.json:
            _print_json({"build": build_payload, "skill": None, "cli": None})
        else:
            for warning in build_payload["warnings"]:
                print(f"warning: {warning}", file=sys.stderr)
        return rc
    out = _resolve_output(args)
    args.pack_dir = str(out)
    skill_payload = _run_skill(args)
    cli_path = generate_site_cli(args.pack_dir)
    if args.json:
        _print_json({"build": build_payload, "skill": skill_payload,
                     "cli": {"cli_path": str(cli_path)}})
    else:
        print(f"pack: {build_payload['pack_dir']}")
        print(f"pages captured: {build_payload['page_count']}   "
              f"frontier: {build_payload['frontier_count']}   "
              f"api surface entries: {build_payload['api_count']}")
        print(f"skill written: {skill_payload['skill_path']}")
        print(f"site CLI written: {cli_path}")
        print(f"\ndone. explore the pack:\n  agentic-anything info {out}\n"
              f"  cat {out}/skills/SKILL.md")
    return 0


def cmd_query(args) -> int:
    results = search_pack(args.pack_dir, args.query, top=args.top, method=args.method)
    if args.json:
        _print_json(results)
    else:
        if not results:
            print("(no matches)")
        for r in results:
            print(f"{r['score']:>7}  {r['page_id']:<36} {r['title']}")
            for ev in r["evidence"][:3]:
                print(f"         - [{ev['kind']}] {ev['text'][:110]}")
    return 0


def cmd_page(args) -> int:
    reader = PackReader(args.pack_dir)
    if args.format == "json" or args.json:
        _print_json(reader.page(args.page_id))
    else:
        print(reader.page_markdown(args.page_id), end="")
    return 0


def cmd_apis(args) -> int:
    reader = PackReader(args.pack_dir)
    apis = reader.apis
    if args.json:
        _print_json(apis)
    else:
        total = 0
        for key in ("forms", "endpoints", "observed_network", "openapi", "feeds",
                    "well_known", "sitemaps"):
            items = apis.get(key, [])
            total += len(items)
            for item in items:
                label = item.get("url") or item.get("action_url", "")
                method = item.get("method", "")
                print(f"[{key}] {method} {label}".replace("  ", " "))
        if total == 0:
            print("(no API surface discovered)")
    return 0


def cmd_info(args) -> int:
    reader = PackReader(args.pack_dir)
    info = reader.info()
    if args.json:
        _print_json(info)
    else:
        for key, value in info.items():
            print(f"{key}: {value}")
    return 0


def cmd_chat(args) -> int:
    from .chat import HttpPeer, ResourceAgent, run_chat_repl

    llm_config = _llm_config_from_args(args)
    if not llm_config.available:
        print(
            "error: chat requires an API key. Set OPENROUTER_API_KEY (or "
            "AGENTIC_API_KEY), and optionally AGENTIC_MODEL / AGENTIC_BASE_URL.",
            file=sys.stderr,
        )
        return 1
    peers = {}
    for spec in args.peer or []:
        peer_id, _, url = spec.partition("=")
        if not url:
            print(f"error: --peer expects id=http://host:port, got '{spec}'", file=sys.stderr)
            return 1
        peers[peer_id] = HttpPeer(peer_id, url, description=f"remote agent at {url}")
    agent = ResourceAgent(args.pack_dir, llm_config, top_k=args.top_k, peers=peers)

    if args.ask:
        reply = agent.ask(args.ask)
        if args.json:
            _print_json({"agent": agent.agent_id, **reply.as_json()})
        else:
            print(reply.answer)
            if reply.citations:
                print(f"\ncitations: {', '.join(reply.citations)}", file=sys.stderr)
        return 0
    return run_chat_repl(agent)


def cmd_serve(args) -> int:
    from .server import AgentServer

    llm_config = _llm_config_from_args(args)
    if not llm_config.available:
        print(
            "error: serve requires an API key. Set OPENROUTER_API_KEY (or "
            "AGENTIC_API_KEY), and optionally AGENTIC_MODEL / AGENTIC_BASE_URL.",
            file=sys.stderr,
        )
        return 1
    try:
        server = AgentServer(
            args.pack_dirs,
            llm_config,
            host=args.host,
            port=args.port,
            enable_a2a=args.enable_a2a,
            top_k=args.top_k,
        )
    except PackNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"agent server on {server.base_url}")
    for agent_id, agent in server.agents.items():
        print(f"  - {agent_id} ({agent.resource_type}: {agent.name})")
    print(f"try:  curl {server.base_url}/agents")
    print(f'      curl -X POST {server.base_url}/agents/{next(iter(server.agents))}/ask '
          f'-d \'{{"question": "..."}}\'')
    if args.enable_a2a and len(server.agents) > 1:
        print("agent-to-agent: enabled (every agent can @ask its co-hosted peers)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nstopped")
    return 0


def cmd_mcp(args) -> int:
    from .mcp import run_stdio_server

    return run_stdio_server(args.pack_dirs)


def cmd_mcp_config(args) -> int:
    from .mcp import claude_config, codex_config

    if args.client == "codex":
        print(codex_config(args.pack_dirs, server_name=args.server_name), end="")
    else:
        _print_json(claude_config(args.pack_dirs, server_name=args.server_name))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentic-anything",
        description="Turn any resource into an evidence-preserving agent interface.",
    )
    parser.add_argument("--version", action="version", version=f"agentic-anything {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="capture a website / file / folder into a pack")
    _add_build_options(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("chat", help="talk to a pack as a conversational agent")
    p.add_argument("pack_dir")
    p.add_argument("--ask", default=None, help="one-shot question (default: interactive REPL)")
    p.add_argument("--model", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--top-k", type=int, default=6, help="retrieved units per question")
    p.add_argument("--peer", action="append", default=None, metavar="ID=URL",
                   help="peer agent server, e.g. books=http://127.0.0.1:8373 (repeatable)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("serve", help="host packs as chatable agents over HTTP")
    p.add_argument("pack_dirs", nargs="+", metavar="PACK_DIR")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8373)
    p.add_argument("--enable-a2a", action="store_true",
                   help="let co-hosted agents consult each other")
    p.add_argument("--model", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--top-k", type=int, default=6)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("mcp", help="expose packs as a read-only stdio MCP server")
    p.add_argument("pack_dirs", nargs="+", metavar="PACK_DIR")
    p.set_defaults(func=cmd_mcp)

    p = sub.add_parser("mcp-config", help="print MCP configuration for an agent runtime")
    p.add_argument("pack_dirs", nargs="+", metavar="PACK_DIR")
    p.add_argument("--client", choices=["codex", "claude"], default="codex")
    p.add_argument("--server-name", default="agentic_anything")
    p.set_defaults(func=cmd_mcp_config)

    p = sub.add_parser("skill", help="generate skills/SKILL.md for a pack")
    p.add_argument("pack_dir")
    _add_llm_options(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_skill)

    p = sub.add_parser("clify", help="generate a site-specific CLI for a pack")
    p.add_argument("pack_dir")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_clify)

    p = sub.add_parser("pack", help="one-shot: build + skill + clify")
    _add_build_options(p)
    _add_llm_options(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("query", help="keyword search over a pack")
    p.add_argument("pack_dir")
    p.add_argument("query")
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--method", choices=["hybrid", "legacy"], default="hybrid")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("page", help="print one captured page")
    p.add_argument("pack_dir")
    p.add_argument("page_id")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--json", action="store_true", help="same as --format json")
    p.set_defaults(func=cmd_page)

    p = sub.add_parser("apis", help="show the discovered API surface")
    p.add_argument("pack_dir")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_apis)

    p = sub.add_parser("info", help="pack summary")
    p.add_argument("pack_dir")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_info)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except PackNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
