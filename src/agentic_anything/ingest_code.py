"""Code repositories and installed software as agent resources.

- ``ingest_repo_dir``      local source tree (git repo or plain code folder)
- ``ingest_github_url``    GitHub repository URL via the codeload zip export
                           (no git binary needed)
- ``ingest_cli_tool``      installed command-line software, introspected via
                           ``--help`` / ``--version`` / man page / subcommand
                           help — the classic "agentify the software" path.

Safety: CLI introspection only ever invokes the tool with help/version
arguments (never bare, never with user-controlled arguments beyond the
tool name), with timeouts and no shell.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from .util import slugify, truncate_text

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".rb", ".php", ".swift", ".scala",
    ".sh", ".bash", ".sql", ".proto", ".css", ".vue", ".lua", ".r", ".jl",
}
DOC_IN_REPO = {".md", ".rst", ".txt", ".toml", ".yaml", ".yml", ".cfg", ".ini", ".json"}
_SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache", "target",
    ".next", ".cache", "vendor", "third_party",
}
_MAX_REPO_FILES = 400
_MAX_FILE_CHARS = 20_000
_MAX_ZIP_BYTES = 100_000_000
_HELP_TIMEOUT = 15
_MAX_SUBCOMMANDS = 12

_GITHUB_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/([\w.\-]+)/([\w.\-]+?)(?:\.git)?(?:/tree/([\w.\-/%]+?))?/?$"
)


def _github_bare(url: str) -> str:
    return url.split("?")[0].split("#")[0]


class CodeError(ValueError):
    pass


def looks_like_repo(path: Path) -> bool:
    if (path / ".git").exists():
        return True
    code_files = 0
    doc_files = 0
    for p in list(path.rglob("*"))[:2000]:
        if not p.is_file():
            continue
        if p.suffix.lower() in CODE_EXTENSIONS:
            code_files += 1
        elif p.suffix.lower() in DOC_IN_REPO:
            doc_files += 1
    return code_files >= 3 and code_files >= doc_files


def is_github_repo_url(url: str) -> bool:
    return _GITHUB_RE.match(_github_bare(url)) is not None


# ------------------------------------------------------------- local repo --

def ingest_repo_dir(path: Path) -> list:
    """Source tree → tree overview + README + per-file units."""
    from .ingest import Unit, _read_text

    files: list[Path] = []
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        rel_parts = p.relative_to(path).parts
        if any(part in _SKIP_DIRS or part.startswith(".") for part in rel_parts[:-1]):
            continue
        if rel_parts[-1].startswith(".") and rel_parts[-1] not in (".env.example",):
            continue
        if p.suffix.lower() in CODE_EXTENSIONS | DOC_IN_REPO or p.name.upper().startswith(
            ("README", "LICENSE", "MAKEFILE", "DOCKERFILE")
        ):
            files.append(p)
    if not files:
        raise CodeError(f"no code or documentation files under {path}")

    truncated_repo = len(files) > _MAX_REPO_FILES
    files = files[:_MAX_REPO_FILES]

    units = []
    # 1. tree overview
    tree_lines = [str(p.relative_to(path)) for p in files]
    overview = [{"kind": "heading", "level": 2, "text": f"Repository: {path.name}"},
                {"kind": "p", "text": f"{len(files)} files"
                                      f"{' (truncated)' if truncated_repo else ''}."},
                {"kind": "pre", "text": "\n".join(tree_lines)}]
    units.append(Unit(
        unit_id="repo__000__tree",
        title=f"Repository tree: {path.name}",
        kind="code",
        content=overview,
        source_path=str(path),
        locator="tree",
    ))

    # 2. README(s) first, then everything else
    def sort_key(p: Path) -> tuple:
        return (0 if p.name.upper().startswith("README") else 1,
                len(p.relative_to(path).parts), str(p))

    for file_path in sorted(files, key=sort_key):
        rel = file_path.relative_to(path)
        try:
            text = _read_text(file_path)
        except OSError:
            continue
        if not text.strip():
            continue
        clipped = len(text) > _MAX_FILE_CHARS
        text = text[:_MAX_FILE_CHARS]
        suffix = file_path.suffix.lower()
        if suffix in (".md", ".rst", ".txt"):
            content = [{"kind": "p", "text": para.strip()}
                       for para in re.split(r"\n\s*\n", text) if para.strip()]
        else:
            entry = {"kind": "pre", "text": text}
            if suffix:
                entry["lang"] = suffix.lstrip(".")
            content = [entry]
        if clipped:
            content.append({"kind": "p", "text": f"(truncated at {_MAX_FILE_CHARS} chars)"})
        slug_parts = [slugify(part, 30) or "x" for part in rel.parts]
        units.append(Unit(
            unit_id=("file__" + "--".join(slug_parts))[:150],
            title=str(rel),
            kind="code",
            content=content,
            source_path=str(file_path),
            locator=str(rel),
        ))
    return units


# ------------------------------------------------------------ GitHub URL ---

def ingest_github_url(url: str, timeout: float = 60.0) -> tuple[str, list]:
    """GitHub repo URL → (repo_name, units) via the codeload zip export."""
    from .fetcher import fetch

    match = _GITHUB_RE.match(_github_bare(url))
    if not match:
        raise CodeError(f"not a recognizable GitHub repository URL: {url}")
    owner, repo, branch = match.group(1), match.group(2), match.group(3)
    branch = (branch or "").rstrip("/")

    # A /tree/<ref> capture may be <branch>/<subdir>; git refs cannot be
    # disambiguated without the API, so try progressively shorter prefixes.
    candidates: list[str] = []
    if branch:
        parts = branch.split("/")
        candidates = ["/".join(parts[:i]) for i in range(len(parts), 0, -1)]
    else:
        candidates = ["HEAD"]
    archive = None
    for ref in candidates:
        zip_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{ref}" \
            if ref != "HEAD" else f"https://codeload.github.com/{owner}/{repo}/zip/HEAD"
        result = fetch(zip_url, timeout=timeout, max_bytes=_MAX_ZIP_BYTES, retries=1)
        if result.ok and result.body[:2] == b"PK":
            archive = result.body
            break
    if archive is None:
        raise CodeError(
            f"could not download {owner}/{repo} from codeload.github.com "
            "(private repo, wrong branch, or network issue)"
        )
    if len(archive) >= _MAX_ZIP_BYTES:
        raise CodeError(f"repository archive exceeds {_MAX_ZIP_BYTES // 1_000_000}MB cap")

    workdir = Path(tempfile.mkdtemp(prefix="aany_repo_"))
    zip_path = workdir / "repo.zip"
    zip_path.write_bytes(archive)
    from .ingest import _safe_extract_zip

    extract_dir = workdir / "src"
    _safe_extract_zip(zip_path, extract_dir)
    roots = [p for p in extract_dir.iterdir() if p.is_dir()]
    repo_root = roots[0] if len(roots) == 1 else extract_dir
    units = ingest_repo_dir(repo_root)
    for unit in units:
        unit.source_path = url
    return f"{owner}/{repo}", units


# ------------------------------------------------------- installed tools ---

_SUBCOMMAND_LINE = re.compile(r"^\s{2,}([a-z][a-z0-9\-_]{1,24})\s{2,}\S")


def ingest_cli_tool(name: str) -> tuple[str, list]:
    """Installed CLI software → (tool_name, units) via help/man introspection.

    Only help/version/man invocations are performed — never the bare tool.
    """
    from .ingest import Unit

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+\-]{0,63}", name):
        raise CodeError(f"invalid tool name: {name!r}")
    binary = shutil.which(name)
    if binary is None:
        raise CodeError(f"'{name}' is not installed (not found on PATH)")

    def run_help(args: list[str]) -> str:
        try:
            proc = subprocess.run(
                [binary, *args], capture_output=True, text=True,
                timeout=_HELP_TIMEOUT, check=False, stdin=subprocess.DEVNULL,
            )
        except (subprocess.TimeoutExpired, OSError):
            return ""
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return output.strip()

    version = ""
    for flag in ("--version", "-V", "version"):
        version = run_help([flag])
        if version and len(version) < 2000:
            break
        version = ""

    help_text = ""
    for flag in ("--help", "-h", "help"):
        help_text = run_help([flag])
        if len(help_text) > 40:
            break
    if not help_text:
        raise CodeError(f"'{name}' produced no help output (--help/-h/help all failed)")

    units = []
    base = slugify(name, 40)
    overview = [{"kind": "heading", "level": 2, "text": f"Software: {name}"},
                {"kind": "p", "text": f"binary: {binary}"}]
    if version:
        overview.append({"kind": "p",
                         "text": "version: " + truncate_text(version.splitlines()[0], 200)})
    units.append(Unit(
        unit_id=f"{base}__000__overview",
        title=f"Software: {name}",
        kind="software",
        content=overview,
        source_path=binary,
        locator="overview",
    ))
    units.append(Unit(
        unit_id=f"{base}__001__help",
        title=f"{name} --help",
        kind="software",
        content=[{"kind": "pre", "text": truncate_text(help_text, _MAX_FILE_CHARS)}],
        source_path=binary,
        locator="--help",
    ))

    # subcommand help pages (heuristic: indented word columns in main help)
    seen: set[str] = set()
    for line in help_text.splitlines():
        match = _SUBCOMMAND_LINE.match(line)
        if not match:
            continue
        sub = match.group(1)
        if sub in seen or sub in ("help", "version") or len(seen) >= _MAX_SUBCOMMANDS:
            continue
        seen.add(sub)
        sub_help = run_help([sub, "--help"])
        if len(sub_help) < 40 or sub_help[:200] == help_text[:200]:
            continue
        units.append(Unit(
            unit_id=f"{base}__sub__{slugify(sub, 30)}",
            title=f"{name} {sub} --help",
            kind="software",
            content=[{"kind": "pre", "text": truncate_text(sub_help, _MAX_FILE_CHARS)}],
            source_path=binary,
            locator=f"subcommand {sub}",
        ))

    # man page, if available
    if shutil.which("man"):
        try:
            proc = subprocess.run(
                ["man", "-P", "cat", name], capture_output=True, text=True,
                timeout=_HELP_TIMEOUT, check=False,
            )
            man_text = re.sub(r".\x08", "", proc.stdout or "")  # strip overstrike
            if proc.returncode == 0 and len(man_text) > 200:
                units.append(Unit(
                    unit_id=f"{base}__man",
                    title=f"man {name}",
                    kind="software",
                    content=[{"kind": "pre",
                              "text": truncate_text(man_text, _MAX_FILE_CHARS * 2)}],
                    source_path=binary,
                    locator="man page",
                ))
        except (subprocess.TimeoutExpired, OSError):
            pass

    return name, units
