---
name: handoff-skill
description: Generate handoff documents when switching between Codex threads for the same project. Activates on 写无缝衔接, 写交接, handoff, and similar triggers.
---

# Handoff Skill — 无缝衔接

通用的项目交接文档生成 skill。触发后自动感知项目环境，生成 `AGENTS_HANDOFF.md` 和详细日期文件，确保新对话能无缝接手。

## 触发词

用户消息中出现以下任一短语时激活:
- "写无缝衔接" / "写交接" / "换聊天" / "无缝衔接"
- "handoff" / "交接文档" / "写交接文档"
- 或通过 `$handoff-skill` 显式调用

## 核心流程

严格按以下 6 步执行，每步完成后再进入下一步。

### 第 0 步：确定项目身份

cwd 即为项目根目录。项目名按优先级从以下来源推断:
1. `package.json` → `name` 字段
2. `pyproject.toml` → `[project] name`
3. `Cargo.toml` → `[package] name`
4. `go.mod` → module 路径最后一段
5. 目录名

### 第 1 步：项目环境探测

并行执行，不询问用户。

**1a. 技术栈扫描** — 检查 `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` / `Dockerfile` / `docker-compose.yml` 等。探测器自动扫描根目录和两级子目录（适配 `project/sub-project/app/` 结构）。

**1b. 服务架构** — 读取 `docker-compose.yml`（根目录 + 子目录）提取服务和端口；扫描 `~/Library/LaunchAgents/` 下 plist 内容匹配项目路径或前缀（不只看文件名）；运行 `brew services list`；读取 `deploy.sh` 提取部署命令；检查 SSH 密钥存在性。

**1c. Git 状态** — `git log --oneline -10` + `git diff --name-only` 获取近期改动和日期范围。

**1d. 交接文档检查** — 检查 `AGENTS_HANDOFF.md` 是否存在，决定增量更新还是全新创建。

### 第 2 步：知识库查询

**2a. 获取查询列表** — 运行 `python3 detectors/knowledge.py search {项目名} $CWD`，脚本返回需要查询的关键词列表和本地 fallback 文档路径。

**2b. 逐条查询** — 拿到查询列表后，你自己用 `memory_search` 工具逐条执行查询。脚本不能直接调 MCP，这一步必须由你（LLM）完成。

**2c. 事故记录查询（强制）** — 额外执行 `memory_search("{项目名} 事故")` 和 `memory_search("{项目名} 禁止")`。如果查到事故记录：
- 提取事故教训
- 写入 `AGENTS_HANDOFF.md` 的"关键配置提醒"段落
- 用 `⚠️ 禁止: {操作}` 格式标注，确保新对话不会重蹈覆辙

**Fallback:** `memory_search` 不可用时，读取 `detectors/knowledge.py search` 返回的 `fallback_sources` 中列出的本地文档（`AGENTS.md`, `README.md`, `HANDOFF_*.md`, `deploy.sh`）。

### 第 3 步：生成文档

先运行探测器收集数据（可并行）:

```bash
python3 detectors/project.py $CWD       # 项目名、路径、技术栈
python3 detectors/git.py $CWD           # git log、改动文件、日期范围
python3 detectors/services.py $CWD      # 服务列表、deploy.sh、SSH 密钥
python3 detectors/knowledge.py search {项目名} $CWD  # 查询列表 + fallback 文档
```

然后根据探测结果 + 知识库查询结果，填充 `templates/` 下的两个模板:

- **文件一: `AGENTS_HANDOFF.md`** → 精简版，持续覆盖更新。已存在时增量更新（保留旧改动摘要追加新章节，服务/凭据/配置全量替换，待办合并去重）。第 2c 步查到的事故教训写入"关键配置提醒"段落。
- **文件二: `HANDOFF_{YYYY-MM-DD}_{简述}.md`** → 详细版，每次新建不复写。

### 第 4 步：知识库回写

运行 `python3 detectors/knowledge.py add "{标题}" "{内容}" {项目名} "{逗号分隔标签}"` 获取回写参数，然后你用 `memory_add` 工具执行写入。脚本只准备参数，实际 MCP 调用由你完成。

回写内容:
- 架构变更 → `memory_add`
- 事故记录 → `memory_add`
- 重要决策 → `memory_add`

标签统一 `["交接", "{项目名}"]`，confidence 0.8-1.0。不写入凭据值。

### 第 5 步：展示结果

列出生成的文件路径和关键摘要。

## 安全规则

1. 凭据只显示"已配置/未配置"，不显示值
2. 不输出 SSH 私钥路径
3. 禁止操作用 `⚠️ 禁止:` 格式标注
4. 知识库回写不含密钥

## 边界情况

- 项目无 git → 跳过 git 探测
- MCP 不可用 → fallback 读文档，不回写
- 多子项目 → 以 cwd 为准

## 资源文件

- `templates/handoff.md.tmpl` — AGENTS_HANDOFF.md 模板
- `templates/detail.md.tmpl` — 详细日期文件模板
- `detectors/project.py` — 项目身份和技术栈探测
- `detectors/services.py` — 服务架构探测
- `detectors/git.py` — Git 状态探测
- `detectors/knowledge.py` — 知识库查询/回写封装
