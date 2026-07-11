"""Main CLI end-to-end (in-process via cli.main)."""

import json
from pathlib import Path

import pytest

from agentic_anything.cli import main
from agentic_anything.ingest import build_pack_from_source
from agentic_anything.interface import generate_agent_interface


RESOURCES = Path(__file__).parent / "fixtures" / "resources"


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
    assert info["resource_type"] == "web"

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
    assert payload["agent"]["interface_path"].endswith("agent-interface.json")
    assert (out / "AGENT.md").exists()


def test_agentify_creates_representation_and_resource_agent(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AGENTIC_API_KEY", raising=False)
    out = tmp_path / "handbook-agent"
    rc = main([
        "agentify", str(RESOURCES / "handbook.md"), "-o", str(out),
        "--site-id", "handbook", "--no-llm", "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    manifest = json.loads((out / "agent-interface.json").read_text(encoding="utf-8"))
    discovery = json.loads((out / "agent-pack.json").read_text(encoding="utf-8"))
    assert payload["agent"]["guide_path"].endswith("AGENT.md")
    assert manifest["project"] == "Agentic Anything"
    assert manifest["kind"] == "agentic-anything-resource-agent"
    assert {"conversation", "mcp", "http_agent", "search"} <= set(manifest["interfaces"])
    assert manifest["interfaces"]["mcp"]["requires_model"] is False
    assert manifest["interfaces"]["conversation"]["requires_model"] is True
    assert manifest["agent_native_representation"]["root"] == "."
    assert manifest["interfaces"]["mcp"]["command"][-1] == "."
    assert discovery["contents"]["agent_interface"] == "agent-interface.json"
    assert "resource_agent_interface" in discovery["capabilities"]
    assert "You do not need to learn the pack's internal layout" in (
        out / "AGENT.md"
    ).read_text(encoding="utf-8")


def test_programmatic_agent_interface_contains_no_credentials(tmp_path):
    pack = tmp_path / "pack"
    build_pack_from_source(str(RESOURCES / "handbook.md"), pack, site_id="handbook")
    path = generate_agent_interface(pack)
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert "sk-or-" not in text
    assert "OPENROUTER_API_KEY" not in text
    assert payload["trust_boundary"] == {
        "captured_content_is_untrusted_data": True,
        "generated_commands_embed_credentials": False,
        "default_operations_are_read_only": True,
    }
    assert payload["agent_native_representation"]["path_resolution"] == (
        "relative_to_agent-interface.json"
    )


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
    assert "not an Agentic Anything pack" in capsys.readouterr().err


def test_build_unreachable_url(tmp_path, capsys):
    rc = main([
        "build", "http://127.0.0.1:1/none", "-o", str(tmp_path / "x"),
        "--max-pages", "1", "--timeout", "2", "--no-probe", "--json",
    ])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["page_count"] == 0
    assert payload["warnings"]
