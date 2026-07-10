# Changelog

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
