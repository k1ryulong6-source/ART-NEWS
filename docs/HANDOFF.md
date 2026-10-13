# 当前交接记录 · v0.5

更新时间：2026-10-13 UTC。建设者：Codex。

## 仓库与授权

仓库：https://github.com/k1ryulong6-source/ART-NEWS 。用户保留公开仓库，并已明确授权公开网页。v0.5 新增四个官方来源，432 条资料／158 项活动；真实重复采集新来源 inserted=0。源级历史保留；本轮 GitHub 刷新 24 源成功，Asian Movie Pulse 与 BFI 返回 HTTP 403，分别保留原 8 条资料与 101 场次及最后成功时间，没有绕过限制。

API 密钥、密码、SMTP 配置、个人数据库与收藏不进入 Git。data/live.json 和 frontend/data.js 只有公开来源元数据及处理次数账本。

## 实际完成

- 今日／探索／日历／收藏／设置；频道、地区、城市、搜索、圈内动态开关与配额。
- 内容／活动详情、关注对象排序、收藏状态、JSON 导出恢复、ICS 日历导出。
- SQLite 存储，真实／示例分离，旧库迁移、首次公开快照恢复。
- 26 个真实来源；432 条资讯与资料、158 项活动（日本 28、英国 109、印度 3、南非 6、法国 4、韩国 4、全球征集 4）。
- 新增 101 场伦敦影展放映、4 个全球摄影征集、4 个法国上映、4 个韩国展期；准确时刻、报名、资格、费用及冲突提示。
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

- 27 项 Python 与 12 项 JavaScript 检查通过。
- Uvicorn 实际监听与 HTTP 请求通过。
- 本轮新增四个官方来源两轮真实读取成功；重复采集 inserted=0。原 22 源本地验证见 v0.4 记录；GitHub 的 Asian Movie Pulse 403 不隐瞒。
- Chromium 桌面 1440px／手机 390px 五个页面无横向溢出、无脚本错误。
- 浏览器筛选、收藏刷新保存、状态修改、JSON 下载／上传、ICS 下载、来源开关、提醒入口与手动更新完成。
- v0.4 浏览器：法语 20 条、葡语 44 条、旧资料标签、班加罗尔展览与票价／闭馆说明、开普敦闭展状态；五个页面无溢出与脚本错误。
- v0.5 桌面／手机浏览器：摄影征集 4 项、学生组时刻冲突、报名入口、101 场伦敦放映、法国上映与首尔展期；收藏与 UTC ICS 下载验证通过。
- 单文件静态版在 390px 验证全球默认、切换伦敦优先、阅读时区、设置／收藏刷新保持、JSON 导出和五页布局。
- 本环境浏览器禁止 file URL；单文件没有外部资源引用，一般浏览器可直接打开。
- v0.2 时 Docker 镜像成功构建；首次发现 COPY 目录权限导致非 root 用户不可读，已添加只读权限修复。修复后容器 HTTP 200，成功返回 160 条真实资讯与 28 项活动。

## 尚需配置／持续扩充

- SUMMARY_API_KEY 尚未配置。真实外部模型调用未启用；结构化日期摘要与中文来源摘录可读，其他新闻保持原标题。
- SMTP 未配置。没有实际发送邮件；站内提醒已实现，模拟发送与去重已测试。
- 来源访问限制：Asian Movie Pulse 与 BFI 在 GitHub 返回 HTTP 403，旧资料与来源状态保留，后续按来源状态复核。
- T018 本轮已补法国上映、伦敦影展、摄影征集与韩国展期；仍是持续覆盖，不能声称所有地区、所有电影或场馆已收齐。

## 运行与检查

python3 scripts/build_static.py：生成 dist。
python3 -m backend：本地服务，默认 http://127.0.0.1:8000。
python3 -m backend.jobs：完整刷新。
python3 -m backend.jobs --schedule --interval-hours 12：后台更新。
python3 scripts/export_snapshot.py：仅导出公开资讯。
python3 scripts/import_snapshot.py：首次恢复公开快照，并恢复当天处理预算。

检查：python3 scripts/audit_data.py --output data/quality.json --strict；python3 scripts/check_project.py；python3 -m unittest discover -s tests -v；node tests/core.test.js；node --check frontend/app.js。

## 下一位 AI

先读 AGENTS.md、本文件、DECISIONS.md、tasks.json；查看实际 Git 状态与 Actions 结果。现有页面与采集链路不需要重写。按 T013／T014 处理用户选择启用的外部服务，T015／T018 已验收；继续按 COVERAGE 扩充全球非英语来源和官方展期。

模型密钥只放运行环境／GitHub Secrets；不要让用户把密钥提交到公开仓库。日期／票价不由模型改写。每次交付更新任务、交接、决策和实际检查结果。


## GitHub 验证与领取入口

- CI：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38389258753
- 实际自动刷新：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38389285444
- 摘要配置：https://github.com/k1ryulong6-source/ART-NEWS/issues/1
- 托管选择：https://github.com/k1ryulong6-source/ART-NEWS/issues/2
- 已完成全球更新：https://github.com/k1ryulong6-source/ART-NEWS/issues/3
- 已完成全球来源补全：https://github.com/k1ryulong6-source/ART-NEWS/issues/4

网站：https://k1ryulong6-source.github.io/ART-NEWS/

首次公开部署成功：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38389258730。公开 URL 返回 HTTP 200；在线 Chromium 1440px／390px 五页无溢出和脚本错误，摄影时刻冲突、报名入口、101 场放映、地区筛选、收藏和 UTC ICS 下载通过。GitHub 每 12 小时自动刷新，刷新完成后自动重新发布。

T018 本轮资料任务：https://github.com/k1ryulong6-source/ART-NEWS/issues/5 。

## T019 · 同域名离线缓存冲突

用户确认网址显示 Selah；已复现根应用 Service Worker 拦截 `/ART-NEWS/`。全新浏览器验收漏掉已安装其他 PWA 的情形。永久修复涉及另一个项目 Selah，补丁和针对性 Node／Chromium 回归已完成，等待跨项目修改与重新发布授权。临时无痕可访问，不等于永久修复。详见 PAGES_TROUBLESHOOTING.md。
