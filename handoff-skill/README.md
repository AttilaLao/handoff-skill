# Handoff Skill

> A [Codex](https://codex.ai) Skill that auto-generates project handoff documents when switching between conversations.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-blue.svg)](https://codex.ai)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)]()

## Why this exists

Every time you switch to a new Codex conversation, you lose context. The new conversation doesn't know what you changed, what services are running, what credentials are configured, or what mistakes to avoid. This skill fixes that by **automatically generating a complete handoff document** in one step.

No more manually writing交接文档. No more forgetting to mention that one critical config. No more "didn't check the knowledge base before touching infrastructure" accidents.

## Features

- **Auto-detects everything** -- project name, tech stack (2-level subdir scan), services (docker-compose, launchd, brew), git state, deploy scripts, SSH keys
- **Knowledge base integration** -- queries `memory_search` for past architecture decisions and accident records before generating, writes back new findings via `memory_add` after
- **Two output files** -- `AGENTS_HANDOFF.md` (compact, incremental updates) + `HANDOFF_YYYY-MM-DD_description.md` (detailed, one per session)
- **Safety rules** -- credentials show "configured/not configured" only, SSH key paths never exposed, infrastructure red lines marked with warning format
- **Multi-project** -- works in any project directory, each project gets its own `AGENTS_HANDOFF.md`
- **Triggered by natural language** -- just say "写无缝衔接" or "handoff" in any conversation

## Quick start

### Install

```bash
# Clone the repo
git clone https://github.com/AttilaLao/handoff-skill.git

# Copy into your Codex skills directory
cp -r handoff-skill/handoff-skill ~/.codex/skills/
```

### Use

In any Codex conversation, working in any project directory, just say:

> 写无缝衔接

Or equivalently:

> 写交接 / handoff / 交接文档 / 换聊天

The skill will automatically:

1. Detect your project identity and tech stack
2. Scan for services (docker-compose, launchd, brew, deploy.sh)
3. Check git status and recent changes
4. Query the knowledge base for past decisions and accidents
5. Generate `AGENTS_HANDOFF.md` + `HANDOFF_YYYY-MM-DD_xxx.md`
6. Write key findings back to the knowledge base

## How it works

```
Trigger: "写无缝衔接"
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Step 0: Project identity (cwd, package.json, etc.) │
│  Step 1: Environment probe (4 detectors in parallel)│
│  Step 2: Knowledge base query (memory_search)       │
│  Step 3: Generate two documents                     │
│  Step 4: Knowledge base writeback (memory_add)      │
│  Step 5: Show results                               │
└─────────────────────────────────────────────────────┘
        │
        ▼
   AGENTS_HANDOFF.md          HANDOFF_2026-08-29_xxx.md
   (compact, incremental)     (detailed, per session)
```

## Output example

`AGENTS_HANDOFF.md` (the compact version, first thing a new conversation reads):

```markdown
# ToToo 社媒管理中台 — 无缝衔接（2026-08-29 更新）

> 新对话第一句：**请先阅读本文件全部内容。**
> 工作目录：`/Users/mac/Documents/ChatGPT/搭建社媒管理系统`

## 当前服务状态
| 服务 | 地址 | 状态 | 说明 |
|------|------|------|------|
| FastAPI | :8000 | running | 主后端 |
| Dashboard | :3002 | running | Next.js 前端 |
| PostgreSQL | :5432 | running | docker-compose |

## 关键配置提醒
- ⚠️ 禁止: 不要直接 docker rm 数据库容器
- ⚠️ 禁止: 不要在 VPS 上运行 docker-compose down

## 部署/恢复命令
# scp -r tooto-social/ root@121.41.212.118:/root/
# ssh root@121.41.212.118 'cd /root/totoo-social && bash deploy.sh'
```

## Detectors

| Detector | What it finds | Output |
|----------|--------------|--------|
| `project.py` | Project name, path, tech stack, frameworks | JSON |
| `services.py` | docker-compose services, launchd plists, brew services, deploy.sh, SSH keys | JSON |
| `git.py` | Branch, recent commits, changed files, date range, dirty state | JSON |
| `knowledge.py` | Knowledge base query list, fallback local docs | JSON |

All detectors are standalone Python scripts that output JSON. You can run them independently:

```bash
python3 detectors/project.py /path/to/your/project
python3 detectors/services.py /path/to/your/project
python3 detectors/git.py /path/to/your/project
python3 detectors/knowledge.py search "your-project" /path/to/your/project
```

## File structure

```
handoff-skill/
├── SKILL.md                  # Skill instructions (loaded by Codex)
├── README.md                 # This file
├── LICENSE                   # MIT
├── agents/
│   └── openai.yaml           # UI metadata (display name, tags, version)
├── templates/
│   ├── handoff.md.tmpl       # Template for AGENTS_HANDOFF.md
│   └── detail.md.tmpl        # Template for detailed daily file
└── detectors/
    ├── project.py            # Project identity & tech stack detector
    ├── services.py           # Service architecture detector
    ├── git.py                # Git state detector
    └── knowledge.py          # Knowledge base query/writeback wrapper
```

## Requirements

- [Codex](https://codex.ai) desktop app (for skill activation)
- Python 3.10+
- Git (optional, but recommended)
- Optional: `memory_search` / `memory_add` MCP tools (falls back to local docs if unavailable)

## Trigger words

| Language | Triggers |
|----------|----------|
| Chinese | 写无缝衔接, 写交接, 换聊天, 无缝衔接, 交接文档, 写交接文档 |
| English | handoff |
| Explicit | `$handoff-skill` |

## Safety

This skill follows strict safety rules:

- Credentials are never shown in plaintext -- only "configured / not configured"
- SSH private key paths are never exposed
- Infrastructure red lines are marked with `⚠️ 禁止:` format
- Knowledge base writeback never includes credential values

## License

MIT -- see [LICENSE](LICENSE)

## Contributing

Found a bug or want to improve a detector? PRs welcome.

1. Fork the repo
2. Create a branch: `git checkout -b fix/improve-detector`
3. Make your changes
4. Run the validator: `python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py handoff-skill/`
5. Submit a PR

## Author

[AttilaLao](https://github.com/AttilaLao)
