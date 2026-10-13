# 当前交接记录 · v0.1

更新时间：2026-10-13 UTC。建设者：Codex。

## 真实进度

已实现代码：

- frontend/：今日、探索、日历、收藏、设置；筛选／搜索、圈内动态开关、详情弹窗、收藏状态、JSON 导出／导入。
- backend/：FastAPI API、SQLite 存储、报道／活动分离、收藏与偏好持久保存、幂等且原子的导入、静态资源白名单。
- scripts/build_static.py：分文件静态版与可双击打开的单文件 HTML；同一界面能使用浏览器存储或本地后端。
- 演示有 13 条虚构资讯与 8 项虚构活动，包括中日不同上映日期、即将闭展与仅月份的征集。
- 5 项 Python 数据／ASGI HTTP 检查，6 项 JavaScript 业务逻辑检查。

尚未完成：浏览器视觉／真实点击验收、TCP 服务监听验收、真实采集、模型摘要、定时更新、外部通知和在线发布。

当前阶段：M1 代码可交付，等待浏览器验收。任务状态按严格验收保留 blocked／todo，不把代码存在视为全部验收完成。

## 读取顺序

AGENTS.md → 本文件 → PRODUCT.md／DECISIONS.md → tasks.json → 与当前任务相关的代码。不要重复生成已有页面。

## 运行

最快体验：python3 scripts/build_static.py，打开 dist/culture-desk-preview.html。

服务版：安装 requirements.txt 后运行 python3 -m backend；默认 http://127.0.0.1:8000。具体环境与备份说明见 README.md 和 OPERATIONS.md。

## 已通过检查

2026-10-13：

- python3 scripts/check_project.py：退出码 0。
- node --check frontend/core.js、node --check frontend/app.js：退出码 0。
- node tests/core.test.js：6 项通过。使用此命令可直接看到逐项结果。
- python3 -m unittest discover -s tests -v：5 项通过，包括进程内 ASGI HTTP 的首页／资源／数据接口、保存、导出、导入和错误响应。
- python3 scripts/build_static.py：静态构建完成，单文件无外部 JS／CSS 引用。

ASGI 检查不打开 TCP 端口，不能代替浏览器与外部服务验证。

## 具体阻塞

浏览器 Chromium 启动返回 setsockopt: Operation not permitted，因此没有截图，不宣称手机／桌面视觉验收通过。早先的网络权限请求未完成，RSS 端点均未核实；不能根据已知网址标记 enabled。

Sites 技能已读取，但本工作区没有找到其 site-workflow.mjs／项目 ID 助手，也无法读取该脚本资源。尚未注册 Site、未同步源码、未部署。保留可部署的 dist，等待有完整工具链的接力环境执行支持的发布流程。

## 下一步可执行动作

1. 在能打开浏览器的环境验收 OPERATIONS.md 清单，修复实际问题，更新 T001／T011 状态。
2. 验收已有筛选、SQLite、日历代码后依次完成 T002、T003、T005；不要再写一套相同页面。
3. 核实首个 RSS／API 来源，推进 T004。当前来源 config 均默认关闭。
4. 推进 T006 可替换摘要；把静态／本地演示的设置与导入能力接上真实内容，再验收 T007／T009。

## 设计调整

D007：原生前端降低依赖与交接成本，Python／SQLite 后端保留。静态版不会后台采集，两个保存位置通过 JSON 迁移。

## 接力更新模板

日期／建设者：
任务编号及状态：
实际完成行为与变更文件：
运行／检查命令与结果：
未完成／阻塞：
下一步操作：
配置变量名（不写密钥）：
Git 提交或尚未提交 diff：

意外中断时先查 doing／blocked 任务与 Git diff；重复运行检查后续接。不要把缺少浏览器权限归因于应用代码，也不要把上一条聊天描述当作验证证据。
