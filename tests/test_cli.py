"""Main CLI end-to-end (in-process via cli.main)."""

import json

import pytest

from agentic_anything.cli import main


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "agentic-anything" in capsys.readouterr().out


def test_build_and_read_commands(demo_server, tmp_path, capsys):
    out = tmp_path / "pack"
    rc = main([
        "build", f"{demo_server}/index.html", "-o", str(out),
        "--site-id", "demo", "--max-pages", "6", "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["page_count"] == 6

    rc = main(["info", str(out), "--json"])
    assert rc == 0
    info = json.loads(capsys.readouterr().out)
    assert info["site_id"] == "demo"

    rc = main(["query", str(out), "team plan price", "--json"])
    assert rc == 0
    results = json.loads(capsys.readouterr().out)
    assert results and results[0]["page_id"] == "pricing"

    rc = main(["page", str(out), "pricing"])
    assert rc == 0
    assert "$79/month" in capsys.readouterr().out

    rc = main(["apis", str(out), "--json"])
    assert rc == 0
    apis = json.loads(capsys.readouterr().out)
    assert apis["forms"]

    # deterministic skill + site cli via CLI
    rc = main(["skill", str(out), "--no-llm"])
    assert rc == 0
    capsys.readouterr()
    assert (out / "skills" / "SKILL.md").exists()

    rc = main(["clify", str(out)])
    assert rc == 0
    capsys.readouterr()
    assert (out / "cli" / "demo_cli.py").exists()


def test_skill_without_key_falls_back(built_pack, tmp_path, monkeypatch, capsys):
    import shutil

    pack = tmp_path / "p"
    shutil.copytree(built_pack, pack)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AGENTIC_API_KEY", raising=False)
    rc = main(["skill", str(pack), "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["llm_used"] is False
    assert "falling back" in captured.err
    assert (pack / "skills" / "SKILL.md").exists()


def test_pack_json_single_document(demo_server, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AGENTIC_API_KEY", raising=False)
    out = tmp_path / "onepack"
    rc = main(["pack", f"{demo_server}/index.html", "-o", str(out),
               "--site-id", "demo", "--max-pages", "3", "--json"])
    assert rc == 0
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)  # must be ONE parseable JSON document
    assert payload["build"]["page_count"] == 3
    assert payload["skill"]["llm_used"] is False
    assert payload["cli"]["cli_path"].endswith("demo_cli.py")


def test_schemeless_url_output_dir(demo_server, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    host_port = demo_server.removeprefix("http://")
    rc = main(["build", f"{host_port}/index.html", "--max-pages", "1", "--json"])
    # https:// is prepended for the slug, so the dir is host-derived, not 'site'
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "127-0-0-1" in payload["pack_dir"]
    assert not payload["pack_dir"].endswith("/site")
    assert rc in (0, 1)  # build itself may fail (https:// on a plain-http server)


def test_bad_pack_dir_error(tmp_path, capsys):
    rc = main(["info", str(tmp_path / "nothing")])
    assert rc == 1
    assert "not a site pack" in capsys.readouterr().err


def test_build_unreachable_url(tmp_path, capsys):
    rc = main([
        "build", "http://127.0.0.1:1/none", "-o", str(tmp_path / "x"),
        "--max-pages", "1", "--timeout", "2", "--no-probe", "--json",
    ])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["page_count"] == 0
    assert payload["warnings"]
