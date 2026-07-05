"""The generated site CLI must work as a standalone zero-dependency script."""

import json
import shutil
import subprocess
import sys

import pytest

from agentic_anything.sitecli import generate_site_cli


@pytest.fixture(scope="module")
def cli_pack(built_pack, tmp_path_factory):
    dest = tmp_path_factory.mktemp("clipack") / "demo"
    shutil.copytree(built_pack, dest)
    script = generate_site_cli(dest)
    return dest, script


def _run(script, *args):
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, timeout=60,
    )
    return proc


def test_script_created(cli_pack):
    _, script = cli_pack
    assert script.name == "demo_cli.py"
    assert (script.parent / "README.md").exists()


def test_info(cli_pack):
    _, script = cli_pack
    proc = _run(script, "--json", "info")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["site_id"] == "demo"
    assert data["page_count"] >= 5


def test_pages_and_page(cli_pack):
    _, script = cli_pack
    proc = _run(script, "--json", "pages")
    pages = json.loads(proc.stdout)
    assert any(p["page_id"] == "pricing" for p in pages)

    proc = _run(script, "page", "pricing")
    assert proc.returncode == 0
    assert "$79/month" in proc.stdout

    proc = _run(script, "page", "pricing", "--format", "json")
    manifest = json.loads(proc.stdout)
    assert manifest["page_id"] == "pricing"

    proc = _run(script, "page", "missing__page")
    assert proc.returncode == 1
    assert "not found" in proc.stderr


def test_search(cli_pack):
    _, script = cli_pack
    proc = _run(script, "--json", "search", "team", "plan")
    results = json.loads(proc.stdout)
    assert results and results[0]["page_id"] == "pricing"


def test_apis_and_forms(cli_pack):
    _, script = cli_pack
    proc = _run(script, "apis")
    assert proc.returncode == 0
    assert "/api/" in proc.stdout

    proc = _run(script, "--json", "forms")
    forms = json.loads(proc.stdout)
    assert forms and any(f["method"] == "POST" for f in forms)


def test_form_curl(cli_pack):
    _, script = cli_pack
    forms = json.loads(_run(script, "forms", "--json").stdout)
    post_idx = next(i for i, f in enumerate(forms) if f["method"] == "POST")
    get_idx = next(i for i, f in enumerate(forms) if f["method"] == "GET")

    proc = _run(script, "form-curl", str(post_idx))
    assert proc.returncode == 0
    assert proc.stdout.startswith("curl -X POST")
    assert "-d 'full_name=" in proc.stdout

    # GET forms must submit as query parameters, not a request body
    proc = _run(script, "form-curl", str(get_idx))
    assert proc.returncode == 0
    assert proc.stdout.startswith("curl -G")
    assert "--data-urlencode 'q=" in proc.stdout
    assert "-X GET" not in proc.stdout

    proc = _run(script, "form-curl", "99")
    assert proc.returncode == 1


def test_json_flag_after_subcommand(cli_pack):
    _, script = cli_pack
    proc = _run(script, "info", "--json")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["site_id"] == "demo"


def test_missing_pack_file_gives_clean_error(cli_pack, tmp_path):
    _, script = cli_pack
    import shutil
    broken = tmp_path / "broken" / "cli"
    broken.mkdir(parents=True)
    lone = broken / script.name
    shutil.copy(script, lone)
    proc = _run(lone, "pages")
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr
    assert "pack file missing" in proc.stderr


def test_fetch_same_origin(cli_pack):
    _, script = cli_pack
    proc = _run(script, "--json", "fetch", "/api/quotes")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["body"]["quote"] == "Ship widgets, not excuses."


def test_fetch_cross_origin_refused(cli_pack):
    _, script = cli_pack
    proc = _run(script, "fetch", "https://example.org/other")
    assert proc.returncode == 1
    assert "same-origin" in proc.stderr
