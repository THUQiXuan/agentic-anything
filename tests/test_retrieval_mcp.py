from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agentic_anything.ingest import build_pack_from_source
from agentic_anything.mcp import ResourceMCPServer, claude_config, codex_config
from agentic_anything.query import PackReader, search_pack
from agentic_anything.retrieval import analyze


@pytest.fixture()
def chinese_pack(tmp_path):
    source = tmp_path / "handbook_zh.md"
    source.write_text(
        """# 产品手册

## 退款政策

客户必须在购买后的十四天内申请退款，并提供订单编号。

## 安全部署

生产环境需要启用双因素认证，并每三十天轮换访问令牌。

## 故障恢复

错误代码 E42 表示缓存已经过期，需要重新构建索引。
""",
        encoding="utf-8",
    )
    pack = tmp_path / "pack"
    build_pack_from_source(str(source), pack, site_id="产品手册")
    return pack


def _request(request_id, method, params=None):
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    return payload


def test_unicode_analyzer_keeps_latin_and_cjk_features():
    tokens = analyze("退款 Policy E42")
    assert "g:退款" in tokens
    assert "w:policy" in tokens
    assert "w:e42" in tokens


def test_chinese_query_no_longer_falls_back(chinese_pack):
    assert search_pack(chinese_pack, "退款期限", method="legacy") == []
    results = search_pack(chinese_pack, "退款期限")
    assert results
    assert "退款政策" in results[0]["title"]
    assert any("十四天" in item["text"] for item in results[0]["evidence"])
    assert results[0]["retrieval_method"] == "bm25f-unicode"


def test_hybrid_search_handles_code_like_terms(chinese_pack):
    results = search_pack(chinese_pack, "E42 缓存")
    assert results
    assert "故障恢复" in results[0]["title"]


def test_mcp_initialize_tools_search_and_resource_read(chinese_pack):
    server = ResourceMCPServer([chinese_pack])
    initialized = server.handle(_request(1, "initialize", {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    }))
    assert initialized["result"]["protocolVersion"] == "2025-06-18"
    assert initialized["result"]["capabilities"]["tools"] == {"listChanged": False}
    assert "untrusted data" in initialized["result"]["instructions"]

    tools = server.handle(_request(2, "tools/list"))["result"]["tools"]
    assert {tool["name"] for tool in tools} == {
        "resource_info", "search_resource", "read_unit"
    }
    assert all(tool["annotations"]["readOnlyHint"] for tool in tools)

    searched = server.handle(_request(3, "tools/call", {
        "name": "search_resource",
        "arguments": {"query": "退款期限", "top_k": 2},
    }))["result"]
    assert searched["isError"] is False
    hit = searched["structuredContent"]["hits"][0]
    assert hit["resource_id"] == "产品手册"
    assert hit["unit_id"]

    resources = server.handle(_request(4, "resources/list"))["result"]["resources"]
    unit_resource = next(item for item in resources if item["mimeType"] == "text/markdown")
    read = server.handle(_request(5, "resources/read", {"uri": unit_resource["uri"]}))
    assert read["result"]["contents"][0]["mimeType"] == "text/markdown"


def test_mcp_tool_errors_are_structured(chinese_pack):
    server = ResourceMCPServer([chinese_pack])
    response = server.handle(_request(1, "tools/call", {
        "name": "read_unit", "arguments": {"unit_id": "missing"}
    }))
    assert response["result"]["isError"] is True
    assert "unknown unit_id" in response["result"]["content"][0]["text"]


def test_mcp_stdio_is_newline_delimited_json_only(chinese_pack):
    env = os.environ.copy()
    src = str(Path(__file__).resolve().parents[1] / "src")
    # The suite is normally run with PYTHONPATH=src. Preserve it explicitly
    # for subprocess-based protocol coverage.
    env["PYTHONPATH"] = os.environ.get("PYTHONPATH", src)
    messages = [
        _request(1, "initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "stdio-test", "version": "1"},
        }),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        _request(2, "ping"),
        _request(3, "tools/list"),
    ]
    proc = subprocess.run(
        [sys.executable, "-m", "agentic_anything", "mcp", str(chinese_pack)],
        input="".join(json.dumps(item, ensure_ascii=False) + "\n" for item in messages),
        text=True,
        capture_output=True,
        timeout=20,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert len(lines) == 3  # notification produces no response
    decoded = [json.loads(line) for line in lines]
    assert [item["id"] for item in decoded] == [1, 2, 3]
    assert proc.stderr == ""


def test_runtime_config_generators_use_stdio_and_absolute_paths(chinese_pack):
    codex = codex_config([chinese_pack])
    assert "[mcp_servers.agentic_anything]" in codex
    assert 'command = "agentic-anything"' in codex
    assert str(chinese_pack.resolve()) in codex

    claude = claude_config([chinese_pack])
    entry = claude["mcpServers"]["agentic-anything"]
    assert entry["type"] == "stdio"
    assert entry["args"][0] == "mcp"
    assert entry["args"][1] == str(chinese_pack.resolve())
