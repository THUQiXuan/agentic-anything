<div align="center">

<img src="assets/agentic-anything-banner.png" alt="Agentic Anything" width="920">

# Agentic Anything

**把任何网站变成 Agent 原生的工具箱。**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-78%20passing-brightgreen.svg)](tests/)

[English](README.md) | [中文](README_ZH.md)

</div>

---

网站是为人眼设计的，而 Agent 值得更好的接口：用结构化数据代替像素解析，用有文档的接口代替猜测，用现成的工具代替临时爬虫。

**Agentic Anything** 把任何网站加工成三层递进的 Agent 原生产物：

```
              build                skill                clify
 任意 URL ────────────▶ Site Pack ─────────▶ SKILL.md ─────────▶ 站点 CLI
            抓取与蒸馏     结构化 JSON+MD        教 Agent 怎么用      零依赖的
                          API 面清单            这个网站（任意       站点专用
                          HTML 证据             LLM，经由            命令行工具
                          截图*                 OpenRouter）
```

1. **`build`** —— 爬取网站，把每个页面蒸馏成结构化清单（`pages/*.json`）、可直接阅读的 Markdown 视图（`pages/*.md`），以及完整的 **API 面清单**（表单、JavaScript 里发现的接口、OpenAPI 规范、feed、sitemap、真实观测到的网络请求），同时保留原始 HTML 证据，并可选生成整页**截图**供需要视觉信息的 Agent 使用。
2. **`skill`** —— 生成 `SKILL.md`，教 Agent *如何使用这个网站*：站上有什么、有哪些可用接口、具体工作流、以及诚实的注意事项。支持任何 OpenAI 兼容的 LLM（默认 OpenRouter），也提供完全确定性的 `--no-llm` 降级模式。
3. **`clify`** —— 生成一个**零依赖的站点专用 CLI**（纯 Python 标准库）：`search`、`page`、`apis`、`forms`、`form-curl`、限同源的 `fetch` —— 所有命令都支持 `--json` 输出。

最终效果：Agent 可以像读文档一样*阅读*网站、像查数据库一样*查询*网站、像用工具一样*操作*网站。

## 安装

```bash
pip install -e .                 # 核心：零运行时依赖
pip install -e '.[render]'       # + Playwright，支持 JS 渲染和截图
python -m playwright install chromium
```

需要 Python 3.10+。核心安装只用标准库。

## 快速开始

```bash
# 1. 把网站抓取成 site pack（不需要任何 API key）
agentic-anything build https://quotes.toscrape.com/ -o packs/quotes --max-pages 10

# 2. 生成 Agent 技能文档（走 OpenRouter，见下方"LLM 配置"）
export OPENROUTER_API_KEY="sk-or-..."          # 你自己的 key
agentic-anything skill packs/quotes --language both   # 同时生成中英文 SKILL

# 3. 生成站点专用 CLI
agentic-anything clify packs/quotes
python packs/quotes/cli/quotes_toscrape_com_cli.py search "Einstein miracle"

# ……或者一条命令做完全部三步：
agentic-anything pack https://quotes.toscrape.com/ -o packs/quotes
```

对 JavaScript 重的网站，打开渲染和视觉快照：

```bash
agentic-anything build https://quotes.toscrape.com/js/ -o packs/quotes-js \
    --render --screenshots
```

渲染模式还会**嗅探网络**：页面发出的每个 XHR/fetch API 调用都会被记录进 pack 的 API 面清单 —— 接口是真实观测到的，不是猜的。

## Site pack 长什么样

```
packs/quotes/
├── agent-pack.json          # 发现文档：这个 pack 里有什么
├── site.json                # 页面索引 + 爬取边界（哪些没抓、为什么没抓）
├── pages/
│   ├── index.json           # 结构化清单：内容、链接、表单、溯源信息
│   └── index.md             # 同一页面的 Markdown 视图
├── html/index.html          # 抓取的 HTML 证据
├── snapshots/index.png      # 整页截图（渲染模式，可选）
├── api/apis.json            # 表单 · JS 接口 · OpenAPI · feed · 观测到的网络请求
├── skills/SKILL.md          # 生成的 Agent 使用指南（+ SKILL_ZH.md）
└── cli/quotes_..._cli.py    # 生成的零依赖站点 CLI
```

设计原则（继承自启发本项目的几个前辈项目，见[致谢](#致谢)）：

- **非视觉优先**：Agent 读 Markdown 和 JSON，不解析渲染像素。截图可用但需显式开启。
- **证据保全**：每个清单都用 SHA-256 链接回抓取的 HTML，结论可验证。
- **诚实的边界**：爬取边界记录每个被发现但*没有*抓取的 URL 及原因（预算、robots.txt、跨站、请求失败）。
- **Agent 契约式 CLI**：所有命令支持 `--json`，退出码有意义，错误走 stderr。

## CLI 参考

| 命令 | 作用 |
|---|---|
| `build URL -o DIR` | 抓取网站为 pack。选项：`--max-pages`、`--render`、`--screenshots`、`--allow-cross-origin`、`--ignore-robots`、`--no-html`、`--no-probe`、`--seed URL`、`--timeout` |
| `skill PACK` | 生成 `skills/SKILL.md`。选项：`--model`、`--base-url`、`--language en\|zh\|both`、`--no-llm` |
| `clify PACK` | 生成 `cli/<site>_cli.py` 和配套 README |
| `pack URL -o DIR` | 一站式：build + skill + clify |
| `query PACK "问题"` | 关键词搜索整个 pack，带证据片段 |
| `page PACK PAGE_ID [--format md\|json]` | 打印某个页面 |
| `apis PACK` | 展示发现的 API 面 |
| `info PACK` | pack 概要 |

所有产出数据的命令都接受 `--json`。`aany` 是 `agentic-anything` 的短别名。

## LLM 配置（OpenRouter 及任意兼容端点）

技能生成走任何 **OpenAI 兼容**的 chat 接口。默认指向 [OpenRouter](https://openrouter.ai)，一个 key 就能调用所有托管模型：

| 环境变量 | 默认值 | 含义 |
|---|---|---|
| `OPENROUTER_API_KEY` | — | API key（LLM 功能**必需**；不会写入磁盘） |
| `AGENTIC_API_KEY` | — | 备选 key 名；两者都设置时优先生效 |
| `AGENTIC_MODEL` | `google/gemini-3.5-flash` | 你的端点支持的任意模型 id |
| `AGENTIC_BASE_URL` | `https://openrouter.ai/api/v1` | 任何 OpenAI 兼容服务（OpenAI、vLLM、llama.cpp、LM Studio 等） |

```bash
export OPENROUTER_API_KEY="sk-or-..."
agentic-anything skill packs/quotes --model anthropic/claude-sonnet-4.5   # 任选模型
agentic-anything skill packs/quotes --no-llm                              # 或完全不用 LLM
```

除了 `skill`（以及 `pack` 中的 skill 步骤），其余所有功能**都不需要 API key**。

## Python API

```python
from agentic_anything import build_pack, generate_skill, generate_site_cli, search_pack
from agentic_anything.config import BuildConfig, LLMConfig

result = build_pack(
    "https://quotes.toscrape.com/",
    "packs/quotes",
    config=BuildConfig(max_pages=10, render=False),
)
generate_skill(result.pack_dir, llm_config=LLMConfig.from_env(), language="both")
generate_site_cli(result.pack_dir)

hits = search_pack(result.pack_dir, "login form fields", top=3)
```

## 测试

```bash
pip install -e '.[dev]'
python -m pytest tests -q        # 78 个测试；未装 Playwright 时渲染测试自动跳过
```

测试覆盖：HTML 解析器、爬虫策略（预算、robots.txt、同站边界、sitemap 播种）、API 发现（表单、JS 扫描、OpenAPI 探测）、pack 构建、搜索、技能生成（LLM 打桩 + 确定性模式）、生成的站点 CLI（以真实子进程运行）、LLM 客户端（对本地假服务器）。没有任何测试调用外部服务。

## 负责任地使用

- 默认遵守 robots.txt（`--ignore-robots` 仅用于你自己的网站）。
- 默认只爬同站、且有页面预算上限。
- 生成的站点 CLI 的 `fetch` 命令仅限同源 GET。
- 在为网站构建 pack、以及让 Agent 调用其接口之前，请先确认目标网站的服务条款。

## 致谢

Agentic Anything 站在这些项目的肩膀上：

- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) —— SKILL.md 契约、`--json` 全覆盖的 CLI 规范，以及"让所有软件 Agent 原生化"的理念。
- **web-anything** —— 证据保全的站点 bundle、爬取边界、非视觉页面清单。
- [AutoFigure-Edit](https://github.com/ResearAI/AutoFigure-Edit) —— 用于生成头图。

## 许可证

[MIT](LICENSE)
