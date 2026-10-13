# 文化信息台 · Culture Desk

GitHub 仓库：ART-NEWS。保留用户创建的仓库，用于持续建设本项目。

一个供个人使用的电影、艺术、摄影资讯汇总项目，重点覆盖中文阅读、日本上映情报和日本展览，支持不同 AI 接续建设。

## 当前交付 · v0.1

第一版代码已实现：今日、探索、日历、收藏、设置；频道／国家／城市／关键词筛选；圈内动态开关；活动与报道详情；收藏状态；偏好与 JSON 导出／导入。所有资讯仍为虚构示例，真实资讯模式为空。

提供两种运行方式：浏览器本地存储的静态版；FastAPI + SQLite 的本地服务版。逻辑、数据库与 ASGI 接口检查已通过，浏览器视觉验收因当前环境限制尚未完成。真实采集、模型摘要、定时任务和在线部署仍待实现。

- 已确认：不要器材评测；加入少量八卦／圈内动态；其他 AI 可以参与或接力建设。
- 建议默认：手机优先网页、东京为日本默认城市、圈内动态约占每日精选 10%。默认值均可调整。
- 无需模型账号或 API 密钥即可检查当前基础包。

## 交给下一个 AI

让它打开 `AGENTS.md`，随后按 `docs/HANDOFF.md` 的顺序读取文件。当前先处理 `T011` 浏览器验收并解除 `T001` 的验证阻塞；之后接入真实来源，见 `tasks.json`。

如果换了工具或工作区，请上传本项目整个压缩包／目录，或者放进你自己的 Git 仓库。AI 的历史聊天和账户额度不会自动共享；项目文件负责传递上下文。

可直接复制的交接提示词在 `docs/NEXT_AI_PROMPT.md`。先读最新 HANDOFF，避免重复建设已有页面。

## 立即体验

先生成静态版：

```sh
python3 scripts/build_static.py
```

用现代浏览器直接打开 `dist/culture-desk-preview.html` 即可，不需要安装依赖或配置 API 密钥。它是完整内嵌资源的单文件演示。`dist/index.html` 是分文件静态版。收藏保存在当前浏览器；换设备前在设置中导出备份。

## 本地服务版

Python 3.10+：

```sh
python3 -m venv .venv
```

激活虚拟环境（macOS／Linux：`source .venv/bin/activate`；Windows：`.venv\Scripts\activate`），然后：

```sh
python3 -m pip install -r requirements.txt
python3 scripts/build_static.py
python3 -m backend
```

打开 `http://127.0.0.1:8000`。页面发现本地 API 后自动使用 SQLite 保存；没有 API 时使用浏览器存储。两种保存位置相互独立，可用导出／导入迁移。

数据库默认 `runtime/culture-desk.db`，可通过 `CULTURE_DESK_DB` 改路径；`CULTURE_DESK_PORT` 可改端口。服务默认仅监听本机。此命令已提供，当前受限工作区没有完成 TCP 服务监听验证；ASGI 接口在进程内已验证。

## 本地检查

需要 Python 3.10+，仅使用标准库：

```sh
python3 scripts/check_project.py
```

检查任务依赖、来源状态、示例数据、SQL 初始化以及日本／中国上映日期的分别存储。检查数据库在内存中建立，不写入实际内容库。

应用检查（开发检查额外需要 `requirements-dev.txt` 中的 httpx，以及 Node 18+）：

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
node tests/core.test.js
```

5 项 Python 检查覆盖持久保存、导出恢复、幂等／原子导入、验证规则和真实 ASGI HTTP 请求；6 项 JavaScript 检查覆盖过滤、圈内动态比例、当地日期、闭展、恢复校验和内容转义。完整浏览器端交互与布局仍待验收。

## 目录

| 文件 | 用途 |
| --- | --- |
| `AGENTS.md` | 所有建设者的工作规则 |
| `docs/PRODUCT.md` | 用户范围、页面、内容和验收标准 |
| `docs/ARCHITECTURE.md` | 默认技术路线、采集流程和模型接口 |
| `docs/SOURCES.md` | 来源接入与内容编辑规则 |
| `docs/DECISIONS.md` | 已确认需求与可调整决策 |
| `docs/HANDOFF.md` | 当前真实进度、下一步、验证记录 |
| `docs/NEXT_AI_PROMPT.md` | 发给其他 AI 的接力提示词 |
| `tasks.json` | 可领取、有依赖和验收条件的任务 |
| `schema.sql` | 可执行的 SQLite 数据结构 |
| `config/preferences.json` | 个人兴趣及默认展示参数 |
| `config/sources.json` | 待核实的候选来源，不包含未经核实的 RSS 地址 |
| `data/demo.json` | 显式标为示例的开发数据 |
| `scripts/check_project.py` | 基础包一致性检查 |
| `frontend/` | 无外部前端依赖的阅读界面与筛选逻辑 |
| `backend/` | FastAPI 接口与 SQLite 仓库 |
| `tests/` | 数据、ASGI 接口和前端业务逻辑检查 |
| `scripts/build_static.py` | 静态版与单文件演示构建 |
| `docs/OPERATIONS.md` | 运行、备份、恢复和当前限制 |

## 建设顺序

当前页面与本地数据工具已写好。先完成浏览器验收，再接入一个已核实来源；之后添加可替换模型摘要、自动去重和定时更新。任务验收未完成时保持 blocked／todo，不把写好代码等同于已经全部验收。

本目录可以独立使用 Git 管理；无需绑定特定 AI、平台或云服务。
