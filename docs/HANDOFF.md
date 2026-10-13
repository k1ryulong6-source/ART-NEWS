# 当前交接记录 · v0.4

更新时间：2026-10-13 UTC。建设者：Codex。

## 仓库与授权

仓库：https://github.com/k1ryulong6-source/ART-NEWS 。用户明确选择公开仓库，保留公开设置与原来的初始化提交。此前 v0.3 的 GitHub 检查与刷新已验证成功。本轮 v0.4 本地 22 个来源两轮全部成功，第二轮 inserted=0，339 条资料／45 项活动；最新 GitHub 结果将在本次推送后补录。

API 密钥、密码、SMTP 配置、个人数据库与收藏不进入 Git。data/live.json 和 frontend/data.js 只有公开来源元数据及处理次数账本。

## 实际完成

- 今日／探索／日历／收藏／设置；频道、地区、城市、搜索、圈内动态开关与配额。
- 内容／活动详情、关注对象排序、收藏状态、JSON 导出恢复、ICS 日历导出。
- SQLite 存储，真实／示例分离，旧库迁移、首次公开快照恢复。
- 22 个真实来源；339 条资讯与资料、45 项活动（日本 28、英国 8、印度 3、南非 6）。
- 全球默认、18 国／城市／语言筛选、日本专题；标题多地区提及与媒体发布地分离，未知地点不猜测。
- 已保存来源核实档案 data/source-research.json、覆盖缺口 docs/COVERAGE.md；质量脚本检查重复、日期、器材与活动引用。
- 旧资料标记并保留在探索；今日排除 30 天外新闻及无日期证据的资料。MAP 周一闭馆／周二免费说明已核对。
- 今日兼顾频道与来源；城市优先为可选；活动倒计时、站内与邮件过滤按各活动当地日期。
- URL 去重，内容变化识别，稳定活动 ID，日期变更保持收藏引用。
- 来源开关、手动异步更新、跨进程刷新锁、读取失败日志与最后成功时间。
- 可替换 NoOp／OpenAI-compatible 摘要接口、输出校验、缓存和跨 CI 的每日请求上限。
- 12 小时后台调度、收藏活动开始／闭展提醒、已读标记、可选 SMTP 投递。
- 静态版、单文件版、本地服务、可选个人访问密码、Docker／Compose 部署配置。
- GitHub CI、定时公开快照更新、任务和 PR 模板。

## 已实际验证

- 22 项 Python 与 11 项 JavaScript 检查通过。
- Uvicorn 实际监听与 HTTP 请求通过。
- 22 个来源两轮真实读取成功；重复采集插入数为 0。
- Chromium 桌面 1440px／手机 390px 五个页面无横向溢出、无脚本错误。
- 浏览器筛选、收藏刷新保存、状态修改、JSON 下载／上传、ICS 下载、来源开关、提醒入口与手动更新完成。
- v0.4 浏览器：法语 20 条、葡语 44 条、旧资料标签、班加罗尔展览与票价／闭馆说明、开普敦闭展状态；五个页面无溢出与脚本错误。
- 单文件静态版在 390px 验证全球默认、切换伦敦优先、阅读时区、设置／收藏刷新保持、JSON 导出和五页布局。
- 本环境浏览器禁止 file URL；单文件没有外部资源引用，一般浏览器可直接打开。
- v0.2 时 Docker 镜像成功构建；首次发现 COPY 目录权限导致非 root 用户不可读，已添加只读权限修复。修复后容器 HTTP 200，成功返回 160 条真实资讯与 28 项活动。

## 尚需配置／持续扩充

- SUMMARY_API_KEY 尚未配置。真实外部模型调用未启用；结构化日期摘要与中文来源摘录可读，其他新闻保持原标题。
- SMTP 未配置。没有实际发送邮件；站内提醒已实现，模拟发送与去重已测试。
- 网站公开静态／私人托管方式的问题待用户答复。不能把仓库网址称作已部署网站。
- 仍需补日本外的逐片上映／影展、摄影征集、更多官方场馆及非英语艺术源，按 T018；18 国菜单不代表均已接入官方活动源。

## 运行与检查

python3 scripts/build_static.py：生成 dist。
python3 -m backend：本地服务，默认 http://127.0.0.1:8000。
python3 -m backend.jobs：完整刷新。
python3 -m backend.jobs --schedule --interval-hours 12：后台更新。
python3 scripts/export_snapshot.py：仅导出公开资讯。
python3 scripts/import_snapshot.py：首次恢复公开快照，并恢复当天处理预算。

检查：python3 scripts/audit_data.py --output data/quality.json --strict；python3 scripts/check_project.py；python3 -m unittest discover -s tests -v；node tests/core.test.js；node --check frontend/app.js。

## 下一位 AI

先读 AGENTS.md、本文件、DECISIONS.md、tasks.json；查看实际 Git 状态与 Actions 结果。现有页面与采集链路不需要重写。按 T013／T014 处理用户选择启用的外部服务，按 T015 完成选定托管，按 T018 扩充全球非英语来源和官方展期。

模型密钥只放运行环境／GitHub Secrets；不要让用户把密钥提交到公开仓库。日期／票价不由模型改写。每次交付更新任务、交接、决策和实际检查结果。


## GitHub 验证与领取入口

- CI：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38378046262
- 实际自动刷新：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38378052566
- 摘要配置：https://github.com/k1ryulong6-source/ART-NEWS/issues/1
- 托管选择：https://github.com/k1ryulong6-source/ART-NEWS/issues/2
- 已完成全球更新：https://github.com/k1ryulong6-source/ART-NEWS/issues/3
- 已完成全球来源补全：https://github.com/k1ryulong6-source/ART-NEWS/issues/4

公开网站的 Pages 工作流已准备，但仅 workflow_dispatch，不随 push 自动发布，也尚未触发；等待用户选择公开网站后再配置 Pages 并验证网址。
