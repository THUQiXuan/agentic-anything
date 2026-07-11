"""Skill generation: deterministic mode for real, LLM mode with a stub."""

import shutil

import agentic_anything.skills as skills_mod
from agentic_anything.config import LLMConfig
from agentic_anything.skills import build_context_document, generate_skill
from agentic_anything.query import PackReader


def _copy_pack(built_pack, tmp_path):
    dest = tmp_path / "pack"
    shutil.copytree(built_pack, dest)
    return dest


def test_deterministic_skill(built_pack, tmp_path):
    pack = _copy_pack(built_pack, tmp_path)
    path = generate_skill(pack, llm_config=None, use_llm=False)
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\nname: demo\n")
    for section in ("## Overview", "## Resource map", "## Reading the pack",
                    "## Interfaces and actions", "## Common workflows",
                    "## For AI Agents", "## Caveats"):
        assert section in content
    # grounded in actual pack data
    assert "pricing" in content
    assert "/submit" in content        # the contact form
    assert "robots" in content.lower()


def test_context_document(built_pack):
    reader = PackReader(built_pack)
    doc = build_context_document(reader)
    assert "== PAGE INDEX ==" in doc
    assert "== API SURFACE ==" in doc
    assert "pricing" in doc
    assert "FORM POST" in doc
    assert len(doc) <= 60_000


def test_llm_skill_with_stub(built_pack, tmp_path, monkeypatch):
    pack = _copy_pack(built_pack, tmp_path)
    captured = {}

    def fake_chat(messages, config, **kwargs):
        captured["system"] = messages[0]["content"]
        captured["user"] = messages[1]["content"]
        return "---\nname: demo\ndescription: stub\n---\n\n# Demo\n\n## Overview\nstub"

    monkeypatch.setattr(skills_mod, "chat", fake_chat)
    config = LLMConfig(api_key="test-key", model="test/model")
    path = generate_skill(pack, llm_config=config, use_llm=True)
    assert path.read_text(encoding="utf-8").startswith("---\nname: demo")
    # the model saw real pack data
    assert "pricing" in captured["user"]
    assert "SKILL.md" in captured["system"]


def test_llm_skill_strips_code_fence(built_pack, tmp_path, monkeypatch):
    pack = _copy_pack(built_pack, tmp_path)
    monkeypatch.setattr(
        skills_mod, "chat",
        lambda messages, config, **kw: "```markdown\n---\nname: demo\ndescription: d\n---\n\n# D\n```",
    )
    config = LLMConfig(api_key="k")
    path = generate_skill(pack, llm_config=config, use_llm=True)
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "```markdown" not in content


def test_llm_skill_bilingual(built_pack, tmp_path, monkeypatch):
    pack = _copy_pack(built_pack, tmp_path)
    calls = []

    def fake_chat(messages, config, **kwargs):
        calls.append(messages[1]["content"][:60])
        return "---\nname: demo\ndescription: d\n---\n\n# D"

    monkeypatch.setattr(skills_mod, "chat", fake_chat)
    config = LLMConfig(api_key="k")
    generate_skill(pack, llm_config=config, use_llm=True, language="both")
    assert (pack / "skills" / "SKILL.md").exists()
    assert (pack / "skills" / "SKILL_ZH.md").exists()
    assert len(calls) == 2
