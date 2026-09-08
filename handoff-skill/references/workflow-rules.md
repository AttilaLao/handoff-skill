# 开发工作流规则参考

本文档是技术栈到重启命令的映射参考。当探测器的 `dev_hints` 或 `restart_hints` 字段没有覆盖到时，从此表查找。

## 后端代码改动

| 技术栈 | 改代码后 | 原因 |
|--------|---------|------|
| Python (FastAPI/Flask/Django) | 必须重启服务进程 | uvicorn/gunicorn 不会自动热更新 |
| Node.js (Express/Fastify) | 用 nodemon/tsx watch 则自动，否则手动重启 | 取决于启动方式 |
| Go | 需重新编译 + 重启 | 编译型语言 |
| Rust | 需 cargo build + 重启 | 编译型语言 |

## 前端代码改动

| 技术栈 | 改代码后 | 原因 |
|--------|---------|------|
| Next.js dev mode | 保存即生效 | HMR 热更新 |
| Vite dev | 保存即生效 | HMR 热更新 |
| 生产构建 | 需 npm run build + 部署 | 静态文件需重新生成 |

## 服务重启命令

| 服务管理方式 | 重启命令 |
|-------------|---------|
| launchd | `launchctl unload/load ~/Library/LaunchAgents/{plist}` |
| docker-compose | `docker-compose restart {service}` |
| docker run | `docker stop/rm/run {container}` |
| systemd | `systemctl restart {service}` |
| pm2 | `pm2 restart {app}` |

## 线上部署路径标注

- 前端 → 构建命令 + 部署命令（wrangler pages deploy / vercel deploy / scp + nginx）
- 后端 → 代码同步方式（scp / git push / docker build）+ 重启方式
- 如有 deploy.sh → 读取并提取关键命令
