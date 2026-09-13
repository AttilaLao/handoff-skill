---
name: handoff-skill
description: Generate handoff documents when switching between Codex threads for the same project. Activates on 写无缝衔接, 写交接, handoff, and similar triggers.
---

# Handoff Skill — 无缝衔接

触发后自动感知项目环境，生成 `AGENTS_HANDOFF.md` 和详细日期文件，确保新对话能无缝接手。

## 最常见的三个错误（每次执行前默念）

1. **只生成了一个文件** — 必须生成 AGENTS_HANDOFF.md 和 HANDOFF_日期_简述.md 两个文件
2. **没查知识库** — 即使自认为了解项目，也必须用 memory_search 查事故和禁止操作
3. **开发工作流规则是空占位符** — 必须从探测器的 dev_hints 和 restart_hints 字段取具体值填入
4. **文件生成在错误目录** — AGENTS_HANDOFF.md 必须生成在实际项目根目录（有 package.json 的那个），不是 cwd。新对话可能在上级目录启动，找不到文件。

## 触发词

"写无缝衔接" / "写交接" / "换聊天" / "无缝衔接" / "handoff" / "交接文档" / "写交接文档" / `$handoff-skill`

## 核心流程（7 步，必须全部执行）

### 第 0 步：确定项目根目录和身份

**不要盲信 cwd。** cwd 可能是项目的上级目录。按以下逻辑确定实际项目根目录：

1. 检查 cwd 是否有 package.json / pyproject.toml / Cargo.toml / go.mod / Dockerfile
2. 如果 cwd 没有这些文件，检查一级子目录里哪个有（如 `cwd/fashion-site/package.json`）
3. 找到后，**项目根目录 = 该子目录**，不是 cwd
4. 如果 cwd 和子目录都有，优先用 cwd
5. 如果都没找到，项目根目录 = cwd

**后续所有步骤都基于项目根目录，不是 cwd。** AGENTS_HANDOFF.md 生成在项目根目录下。

项目名按优先级推断：package.json name → pyproject.toml name → Cargo.toml name → go.mod → 目录名。
如果项目根目录是 cwd 的子目录，在生成文档的「新对话接手步骤」中写明 `cd {子目录名}` 作为第一步。

### 第 1 步：项目环境探测（并行，不询问用户）

运行 4 个探测器：

```bash
python3 detectors/project.py $CWD    # 项目名、技术栈、dev_hints
python3 detectors/git.py $CWD        # git log、改动文件、日期范围
python3 detectors/services.py $CWD   # 服务列表、deploy.sh、SSH 密钥、restart_hints
python3 detectors/knowledge.py search {项目名} $CWD  # 查询列表 + fallback 文档
```

同时在**项目根目录**（不是 cwd）检查 `AGENTS_HANDOFF.md` 是否已存在（决定增量更新还是全新创建）。如果项目根目录是 cwd 的子目录，探测器参数用项目根目录路径。

### 第 2 步：知识库查询（不能跳过）

即使你觉得自己已经知道项目上下文，也必须执行。知识库里可能有你不知道的事故记录。

1. 从 `knowledge.py search` 输出拿到查询列表
2. 用 `memory_search` 逐条查询（脚本不能调 MCP，必须你来）
3. 额外查 `memory_search("{项目名} 事故")` 和 `memory_search("{项目名} 禁止")`
4. 查到的事故用 `⚠️ 禁止: {操作}` 格式写入关键配置提醒段落
5. MCP 不可用时 fallback 到 knowledge.py 返回的 fallback_sources 本地文档

### 第 3 步：生成文档（必须产出两个文件，缺一不可）

**文件一：`AGENTS_HANDOFF.md`** — 精简版，用 `templates/handoff.md.tmpl`。已存在则增量更新。
- 必须包含模板中的所有段落，不能省略
- 「开发期间必须记住的规则」：从 project.py 的 `dev_hints` 取热更新状态，从 services.py 的 `restart_hints` 取重启命令
- 「新对话接手步骤」：给出具体 curl 健康检查命令和启动命令
- 「当前服务状态」表格：列出探测器发现的所有服务（含 PostgreSQL、Redis 等基础设施），不明的标 unknown
- 技术栈到重启命令的映射参考 [references/workflow-rules.md](references/workflow-rules.md)

**文件二：`HANDOFF_{YYYY-MM-DD}_{简述}.md`** — 详细版，用 `templates/detail.md.tmpl`，每次新建不复写。
- 必须包含完整代码片段（git diff 修改前后对比）、复现命令、踩坑记录

### 第 4 步：知识库回写

用 `memory_add` 回写架构变更、事故记录、重要决策。标签 `["交接", "{项目名}"]`，不写凭据值。
MCP 不可用则跳过。但如果 MCP 可用而你跳过了第 2 步，这是错误 — 必须回去执行第 2 步。

### 第 5 步：验证完整性（强制，不能跳过）

逐项检查，**任何一项不满足都必须回到第 3 步补全：**

- [ ] AGENTS_HANDOFF.md 已生成在**项目根目录**（有 package.json 的目录，不是 cwd）
- [ ] HANDOFF_{YYYY-MM-DD}_{简述}.md 已生成（第二个文件，不能省略）
- [ ] 「开发期间必须记住的规则」有具体的重启命令（不是占位符 {xxx}）
- [ ] 「新对话接手步骤」有 curl 健康检查命令
- [ ] 「当前服务状态」表格包含探测器发现的所有服务
- [ ] 「关键配置提醒」包含事故记录（如有），用 `⚠️ 禁止:` 标注

### 第 6 步：展示结果

列出生成的两个文件路径和关键摘要。

## 安全规则

1. 凭据只显示"已配置/未配置"
2. 不输出 SSH 私钥路径
3. 禁止操作用 `⚠️ 禁止:` 标注
4. 知识库回写不含密钥

## 边界情况

- 项目无 git → 跳过 git 探测
- MCP 不可用 → fallback 读文档，不回写
- 多子项目 → 以 cwd 为准

## 资源文件

- `templates/handoff.md.tmpl` — AGENTS_HANDOFF.md 模板
- `templates/detail.md.tmpl` — 详细日期文件模板
- `references/workflow-rules.md` — 技术栈到重启命令映射参考
- `detectors/project.py` — 项目身份和技术栈探测
- `detectors/services.py` — 服务架构探测
- `detectors/git.py` — Git 状态探测
- `detectors/knowledge.py` — 知识库查询/回写封装
