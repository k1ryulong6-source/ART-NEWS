# ART-NEWS · 映间 / Culture Desk

个人电影、艺术、摄影资讯平台，覆盖日本上映与展览，加入少量圈内动态，排除器材评测。不同 AI 可以在同一仓库接力建设。

仓库：https://github.com/k1ryulong6-source/ART-NEWS 。根据用户选择保持公开；本地数据库、收藏、密码和 API 密钥不入库。

## 当前版本 v0.2

已实现今日、探索、日历、收藏和设置；筛选／搜索、圈内动态开关、详情、关注排序；SQLite 持久保存；JSON 导出／恢复、ICS 日历导出；真实采集、去重、来源开关、手动更新、更新状态、站内提醒；可替换摘要接口与可选邮件提醒。

2026-10-13 实际接入 7 个来源，收录 160 条公开资讯与 28 项日本活动。data/live.json 是标明时间的公开元数据快照；虚构示例单独保存于 data/demo.json，页面可切换，二者不混用。

来源：映画.com 上映安排、东京都写真美术馆官方展期、IMA、The Film Stage、ARTnews、Aperture、Artforum 中文网。国际新闻的活动地区未知时显示“国际”，不猜测地点。上映类型区分院线与流媒体；未明确的票价、休馆日和预约保持待确认。

## 立即体验静态版

```sh
python3 scripts/build_static.py
```

现代浏览器打开 dist/culture-desk-preview.html，或把 dist/ 作为静态站点。全部界面资源内嵌，无远程字体／图片依赖。静态版保存到当前浏览器，换设备前导出备份；来源开关只影响当前浏览器显示。静态版本身不后台采集，需要仓库的定时工作流或本地服务更新快照。

本工作区的浏览器禁止 file URL，因此单文件通过本地 HTTP 服务完成操作检查。一般本地浏览器可直接打开；受限制时执行 python3 -m http.server 8002 --directory dist，访问 http://127.0.0.1:8002/culture-desk-preview.html。

## 本地服务版

Python 3.10+：

```sh
python3 -m venv .venv
```

激活虚拟环境，然后：

```sh
python3 -m pip install -r requirements.txt
python3 scripts/build_static.py
python3 -m backend
```

打开 http://127.0.0.1:8000。首次启动恢复公开快照，收藏和偏好保存在 runtime/culture-desk.db。已有数据库不会被快照覆盖。CULTURE_DESK_DB 可改变路径，CULTURE_DESK_PORT 可改变端口。

手动刷新或后台每 12 小时刷新：

```sh
python3 -m backend.jobs
python3 -m backend.jobs --schedule --interval-hours 12
```

页面的“更新”按钮会异步采集并刷新；失败来源保留旧内容，显示最近成功时间。停用来源后不再调度。不同进程共享刷新锁，避免并行重复任务。

## 模型与邮件配置

默认 SUMMARY_PROVIDER=noop，不调用任何付费模型，原标题与日期仍可读。中文官方日期摘要由已有结构化信息生成；外文新闻未翻译时明确提示待整理。

启用任意 OpenAI-compatible 服务时，在环境或 GitHub Secrets／Variables 配置：

- SUMMARY_PROVIDER=openai-compatible
- SUMMARY_BASE_URL：服务的 v1 请求根地址
- SUMMARY_MODEL：该服务可用的模型名
- SUMMARY_API_KEY：密钥，仅放环境或 Secrets
- SUMMARY_DAILY_LIMIT：每日请求上限，默认 20

数据内容是资料，不作为模型指令。模型结果经过校验，不修改活动日期／票价。缓存基于输入内容；超时、限额或输出错误保留原始内容。预算账本随公开快照迁移，避免 CI 每次启动重置同一天的上限。

邮件需要 SMTP_HOST／PORT／FROM／TO，以及可选 USER／PASSWORD。未配置时只有站内提醒。仅提醒收藏且未看过的真实活动；撤销收藏、标为看过或活动已经结束后不会发送邮件。当前未配置模型账号与邮件服务，实际外部调用尚未启用；代码接口已用模拟响应验证。

## GitHub 协作与自动运行

.github/workflows/checks.yml 在 push／PR 执行检查并提供静态构建下载。

.github/workflows/refresh.yml 每天 UTC 01:15、13:15 更新公开快照，也可手动触发。只保存公开元数据与处理次数账本，不保存个人收藏或凭据。GitHub 调度可能延迟；可在 Actions 查看实际执行结果。

任务编号、负责人、依赖、验收条件在 tasks.json。领取任务前读取 AGENTS.md 和 docs/HANDOFF.md。用分支与 Pull Request 提交；每次完成或额度接近用尽时更新交接记录。GitHub 不会自动转移各 AI 的账号或额度。

## 私人服务部署

```sh
docker compose up -d --build
```

app 与 updater 共用持久数据卷；默认只绑定本机 8000。部署到远程私人服务时可设置 CULTURE_DESK_PASSWORD，用户名 owner，并由 HTTPS 网关提供访问。同一受保护服务的多个浏览器共享 SQLite 状态；静态版各浏览器状态独立。

Docker 与托管细节见 docs/OPERATIONS.md。网站公开／私人访问方式仍按用户选择处理，不把仓库公开等同于网站已经发布。pages.yml 是尚未触发的公开静态托管准备，用户选定公开网页后再开启。

## 检查

```sh
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_project.py
python3 -m unittest discover -s tests -v
node tests/core.test.js
node --check frontend/app.js
```

14 项 Python 与 7 项 JavaScript 检查通过。桌面 1440px 与手机 390px 五个页面无横向溢出；实际浏览器检查了筛选、收藏刷新、状态设置、JSON 下载／上传、ICS 下载、来源开关、提醒与手动刷新。静态版与服务版分别检查。

## 文件入口

- frontend/：无前端依赖的阅读界面与逻辑。
- backend/：API、数据仓库、来源适配器、摘要、调度与邮件。
- config/sources.json：核实状态与接入方法。
- schema.sql：数据库初始结构，启动时兼容旧库迁移。
- scripts/：检查、静态构建、公开快照导入／导出。
- docs/HANDOFF.md：最新真实进度与下一项操作。
- docs/DECISIONS.md：用户要求和设计选择。
- docs/NEXT_AI_PROMPT.md：可转交给其他 AI 的提示词。

可继续扩充中国上映、其他城市的展览来源和关注名单；覆盖范围不代表已经收录所有国家／场馆。全文和报道图片不会被默认镜像。
