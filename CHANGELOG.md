# Changelog

## 0.4.1 — 2026-07-11

- Restore **Agentic Anything** as the project and system identity: the core
  promise remains any resource → agent-native representation → resource agent.
- Add the preferred `agentify` one-shot command while retaining `pack` as a
  backward-compatible alias.
- Generate `agent-interface.json` and `AGENT.md` so humans and agent hosts can
  discover chat, MCP, HTTP/OpenAI/A2A, offline query/read, SKILL, and
  resource-CLI entry points without learning the pack layout first.
- Reframe the English and Chinese documentation around heterogeneous ingestion
  and practical resource-agent interfaces; keep MCP and Unicode BM25F as
  modules of the larger system.
- Expand the offline suite to 170 tests.

## 0.4.1 — 2026-07-11（中文）

- 固定 **Agentic Anything** 为项目与系统名称，主线保持“任何资源 → Agent
  原生表示 → 资源 Agent”；
- 新增首选的一站式 `agentify` 命令，原 `pack` 保留为向后兼容别名；
- 生成 `agent-interface.json` 与 `AGENT.md`，让人类和 Agent host 无需先理解
  pack 布局即可发现 chat、MCP、HTTP/OpenAI/A2A、离线 query/read、SKILL
  与资源 CLI；
- 中英文文档重新围绕异构资源摄入和实用资源 Agent 接口组织，MCP 与
  Unicode BM25F 明确作为完整系统中的模块；
- 离线测试增至 170 个。

## 0.4.0 — 2026-07-10

- Expose one or more resource packs through a dependency-free, read-only stdio
  MCP server with tools, resources, and prompts.
- Generate ready-to-review Codex and Claude Code MCP configurations with
  `mcp-config`.
- Replace ASCII-only query matching with structure-aware BM25F, Unicode word
  analysis, and precision-oriented CJK bigrams/short phrases.
- Stop injecting arbitrary first units when retrieval has no match.
- Add public BEIR evaluation, a frozen multilingual heterogeneous diagnostic,
  and installed-host MCP smoke checks.
- Expand the offline suite to 168 tests and document the empirical failure that
  led to removing multi-character CJK unigrams.

## 0.4.0 — 2026-07-10（中文）

- 新增零依赖、只读的 stdio MCP 服务，以 tools、resources、prompts 暴露一个或多个资源包；
- `mcp-config` 可生成 Codex 与 Claude Code 配置；
- 将 ASCII-only 检索升级为结构感知 BM25F、Unicode word 与高精度 CJK 双字/短语特征；
- 无匹配证据时不再注入任意开头单元；
- 新增 BEIR、冻结多语言异构诊断和真实 host MCP smoke check；
- 离线测试增至 168 个，并如实记录 CJK 单字误检及其修复。
