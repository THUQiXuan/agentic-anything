# Changelog

## 0.5.0 — 2026-07-15

- **Deep capture**: while crawling a website, `--follow-docs N` ingests linked
  documents (PDF/DOCX/PPTX/XLSX/EPUB/CSV/ipynb/SRT/…) and `--follow-repos N`
  ingests linked GitHub repositories into the *same* pack, with per-attachment
  download provenance (URL, fetched URL, SHA-256, bytes, linking page, anchor
  text). Videos are never downloaded; every document/repo/video link that is
  *not* followed now lands in the frontier with an explicit reason
  (previously several of these were silently dropped). `--follow-host` extends
  the allowed download hosts; `--follow-max-mb` caps attachment size.
- Repository trees now list files that exist beyond the text-capture boundary
  (binaries such as PDFs) with sizes, so agents can detect moved/renamed
  artifacts instead of concluding they do not exist.
- PDF units are split on a page window as well as a character budget, keeping
  citations page-addressable for slide decks (`pages 25-32` instead of one
  60-page unit).
- Subtitle units now stamp every cue inline (`[00:07:37.800 → 00:07:40.500] …`),
  which makes transcripts directly usable for moment-finding and cut lists.
- **New flagship demos** built on the above and recorded end-to-end:
  - `cs336-course`: one Stanford CS336 URL → course pack with six lecture PDF
    decks + the assignment starter repository + honestly recorded dead links;
    a 14-step deterministic run and three recorded real-model conversations
    (including the link-rot answer) ship with the pack.
  - `footage-library`: three CC-BY Blender film transcripts → a footage agent;
    a 14-step deterministic run emits a frame-accurate, license-attributed
    teaser cut list with executable ffmpeg commands.
- **Demo gallery rewritten** (GitHub Pages): before → one command → after →
  a replayed real conversation with clickable evidence, a color-coded step
  timeline for long runs, an EDL view, EN/中文 toggle — replacing the previous
  text-heavy page. All page data derives from committed recordings
  (`demos/results/gallery-data.json`) and re-verifies offline (74/74 run
  checks; every recorded citation must resolve inside its pack).
- Animated SVG hero (`assets/demo-course-agent.svg`, pure CSS, 32 s loop)
  regenerable via `demos/render_hero_svg.py`.
- Offline suite grows to 178 tests; `build`/`agentify` gain
  `attachment_count` in `--json` output.

## 0.5.0 — 2026-07-15（中文）

- **深捕获**：抓取网站时，`--follow-docs N` 将页面链接的文档
  （PDF/DOCX/PPTX/XLSX/EPUB/CSV/ipynb/SRT/…）、`--follow-repos N` 将链接的
  GitHub 仓库直接摄入**同一个** pack，并记录每个附件的下载溯源
  （URL、实际抓取 URL、SHA-256、字节数、来源页面、锚文本）。视频一律不
  下载；所有未跟进的文档/仓库/视频链接都会进入 frontier 并给出明确原因
  （旧版本会静默丢弃其中一部分）。`--follow-host` 扩展允许的下载主机，
  `--follow-max-mb` 限制单附件体积。
- 仓库树单元现在会列出文本捕获边界之外的文件（如 PDF 等二进制）及其大小，
  Agent 可以据此发现被移动/改名的文件，而不是误以为它们不存在。
- PDF 切分同时受页窗与字符预算约束，讲义 slides 的引用保持页级可寻址
  （`pages 25-32`，而非一个 60 页的大单元）。
- 字幕单元逐句内嵌时间戳（`[00:07:37.800 → 00:07:40.500] …`），转写文本
  可直接用于找镜头、出剪辑清单。
- **新旗舰 demo**（基于上述能力，全程录制）：
  - `cs336-course`：一个斯坦福 CS336 URL → 含 6 份讲义 PDF + 作业起步仓库
    + 如实记录死链的课程 pack；附 14 步确定性 run 与三段真实模型对话录制
    （包括“死链绕行”回答）。
  - `footage-library`：三部 CC-BY Blender 开源电影字幕 → 素材库 Agent；
    14 步确定性 run 输出帧级精确、带许可署名、可执行 ffmpeg 命令的
    预告片剪辑清单。
- **Demo gallery 重写**（GitHub Pages）：转化前 → 一条命令 → 转化后 →
  真实对话回放（引用可点开看证据）、长任务彩色步骤时间线、EDL 视图、
  中英文切换——取代原先的重文本页面。页面数据全部来自已提交的录制
  （`demos/results/gallery-data.json`），可离线复核（74/74 run 校验；
  每条录制引用必须能在 pack 内解析）。
- 新增动画 SVG 头图（`assets/demo-course-agent.svg`，纯 CSS，32 秒循环），
  由 `demos/render_hero_svg.py` 再生成。
- 离线测试增至 178 个；`build`/`agentify` 的 `--json` 输出新增
  `attachment_count`。

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
