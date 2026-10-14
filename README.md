# ART-NEWS · 映间 / Culture Desk

面向公众、供查询与阅览的艺术、电影、摄影新闻资讯平台，以世界文化新闻为主，日本上映与展览保留专题，加入少量圈内动态，排除器材评测。不同 AI 可以在同一仓库接力建设。

仓库：https://github.com/k1ryulong6-source/ART-NEWS 。根据用户选择保持公开；本地数据库、收藏、密码和 API 密钥不入库。

**在线访问：[映间资讯平台](https://k1ryulong6-source.github.io/ART-NEWS/)**

同域名旧 PWA 的导航缓存冲突已修复并上线。若浏览器仍显示「Selah」，在该页点击“更新 Selah”，再打开上述完整资讯地址；无需删除浏览器数据。详见 [Pages 排查记录](docs/PAGES_TROUBLESHOOTING.md)。

## 当前版本 v0.15

**重要性、时效与快模型直接翻译**：用户取消二次模型校对，并选择本会话快模型分工、不另配API。新闻标紧急／优先／普通／资料，重要程度与明确日期时效分别记录；重大新消息、临近上映／展期／截止先翻译，每批保留8条旧稿份额。自动初判可在资料页查看原因，支持按级别筛选；不代表消息真伪或艺术价值。

已实际用gpt-6-luna完成12篇直接全文翻译，不增加第二轮模型调用，只做程序结构／数字／来源检查。当前44篇已翻译（旧校译32＋直接翻译12，6篇仅公开部分），49篇原生中文，440篇待译，2条正文缺失；全量目标仍未完成。每日任务同步新策略和优先顺序，实际模型来源保留，不能假称每次任务都能选择子模型。 最新费用偏好：以足够完成全文翻译的性价比选择模型，当前默认GPT-5.6；不把Luna默认当便宜型号，无可靠费用依据不自动升级。每日量和覆盖范围见docs/OPERATING_METRICS.md。

[覆盖与翻译进度](https://k1ryulong6-source.github.io/ART-NEWS/#coverage)继续显示逐源对照、地区和官方抽查缺口。525条资料／198活动／26来源保持，公开采集每2小时。[Claude UI／美术交接](docs/CLAUDE_UI_HANDOFF.md)继续适用，保留分级、直译身份、全量队列及来源。

已实现今日、探索、日历、收藏和设置；筛选／搜索、圈内动态开关、详情、关注排序；SQLite 持久保存；JSON 导出／恢复、ICS 日历导出；真实采集、去重、来源开关、手动更新、更新状态、站内提醒；可替换摘要接口与可选邮件提醒。

2026-10-13 实际接入 26 个来源，收录 462 条公开资讯与资料、163 项活动（日本 31、英国 109、印度 3、南非 6、法国 6、韩国 4、全球征集 4）。data/live.json 是标明时间的公开资讯与正文快照；虚构示例单独保存于 data/demo.json，页面可切换，二者不混用。

新增 Variety Film、Artnet News、Hyperallergic、British Journal of Photography、L’Œil de la Photographie、Cinéfilos（西语）和 Tate Modern；保留原有七个来源。v0.4 新增 ART AFRICA、Cinema com Rapadura、Cine PREMIERE、Trois Couleurs、Fisheye、Asian Movie Pulse 及 MAP、Zeitz MOCAA 官方展期。默认全球阅读，提供 18 个国家、城市、原文语言筛选与日本专题快捷入口。媒体所在地与报道涉及地区分开保存；原标题提及的地区标为“涉及”，没有证据时显示“地点未说明”，不猜测活动地点。

今日精选兼顾来源、频道与发布时间；全球模式不按东京／中国加分。用户也可切换城市优先。阅读时区用于显示更新时间；活动倒计时和提醒始终按活动自身时区计算。Tate 只读取明确完整展期，不从单独闭展日期推算开幕，不把会员免费写成一般票价免费。上映类型区分院线与流媒体；未明确的票价、休馆日和预约保持待确认。

新增法国发行商 Diaphana、BFI 伦敦电影节、World Photography Organisation 和 MMCA 首尔馆。影展支持场次时刻、场馆、票价范围及售罄提示，摄影征集支持截止时刻、资格、费用条件与官方报名入口。

旧资料保留在探索与收藏，并标记“旧资料”；今日只用近期新闻及明确日期的进行中／近期活动，不以抓取日补造发布日期。MAP 的周二免费和周一闭馆取自馆方访问说明。资料覆盖与剩余缺口见 docs/COVERAGE.md，来源核实档案见 data/source-research.json；每次自动刷新会生成 data/quality.json。

## 立即体验静态版

```sh
python3 scripts/build_static.py
```

现代浏览器打开 dist/culture-desk-preview.html，或把 dist/ 作为静态站点。全部界面资源与已采集正文内嵌，无远程字体依赖；来源图片通过外链加载。静态版保存到当前浏览器，换设备前导出备份；来源开关只影响当前浏览器显示。静态版本身不后台采集，需要仓库的定时工作流或本地服务更新快照。

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

手动刷新或后台每 2 小时刷新：

```sh
python3 -m backend.jobs
python3 -m backend.jobs --schedule --interval-hours 12
```

页面的“更新”按钮会异步采集并刷新；失败来源保留旧内容，显示最近成功时间。停用来源后不再调度。不同进程共享刷新锁，避免并行重复任务。

## 模型与邮件配置

默认 SUMMARY_PROVIDER=noop，不调用任何付费模型，原标题与日期仍可读。中文官方日期摘要由已有结构化信息生成。公共机器翻译默认启用，独立于生成式 AI 摘要，无需账号密钥。

启用任意 OpenAI-compatible 服务时，在环境或 GitHub Secrets／Variables 配置：

- SUMMARY_PROVIDER=openai-compatible
- SUMMARY_BASE_URL：服务的 v1 请求根地址
- SUMMARY_MODEL：该服务可用的模型名
- SUMMARY_API_KEY：密钥，仅放环境或 Secrets
- SUMMARY_DAILY_LIMIT：每日请求上限，默认 20

数据内容是资料，不作为模型指令。模型结果经过校验，不修改活动日期／票价。缓存基于输入内容；超时、限额或输出错误保留原始内容。预算账本随公开快照迁移，避免 CI 每次启动重置同一天的上限。

邮件需要 SMTP_HOST／PORT／FROM／TO，以及可选 USER／PASSWORD。未配置时只有站内提醒。仅提醒收藏且未看过的真实活动；撤销收藏、标为看过或活动已经结束后不会发送邮件。当前未配置生成式摘要账号与邮件服务；公共机器翻译已实际启用。生成式摘要／邮件接口已用模拟响应验证。

## GitHub 协作与自动运行

.github/workflows/checks.yml 在 push／PR 执行检查并提供静态构建下载。

.github/workflows/refresh.yml 设置每2小时更新公开快照，也可手动触发。只保存公开元数据与处理次数账本，不保存个人收藏或凭据。GitHub 调度可能延迟；可在 Actions 查看实际执行结果。

任务编号、负责人、依赖、验收条件在 tasks.json。领取任务前读取 AGENTS.md 和 docs/HANDOFF.md。用分支与 Pull Request 提交；每次完成或额度接近用尽时更新交接记录。GitHub 不会自动转移各 AI 的账号或额度。

## 维护用本地服务（可选）

```sh
docker compose up -d --build
```

app 与 updater 共用持久数据卷；默认只绑定本机 8000。部署到远程私人服务时可设置 CULTURE_DESK_PASSWORD，用户名 owner，并由 HTTPS 网关提供访问。同一受保护服务的多个浏览器共享 SQLite 状态；静态版各浏览器状态独立。

Docker 与托管细节见 docs/OPERATIONS.md。用户已选择其他人均可访问的公开资讯页。网站已公开上线：[https://k1ryulong6-source.github.io/ART-NEWS/](https://k1ryulong6-source.github.io/ART-NEWS/)，HTTP 200 与桌面／手机交互验收通过。pages.yml 在前端／公开快照变更和定时刷新完成后自动部署。各读者收藏保存在各自浏览器。

## 检查

```sh
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_project.py
python3 scripts/audit_data.py --output data/quality.json --strict
python3 -m unittest discover -s tests -v
node tests/core.test.js
node --check frontend/app.js
```

33 项 Python 与 14 项 JavaScript 检查通过。桌面 1440px 与手机 390px 五个页面无横向溢出；实际浏览器检查了筛选、收藏刷新、状态设置、JSON 下载／上传、ICS 下载、来源开关、提醒与手动刷新。静态版与服务版分别检查。

## 文件入口

- frontend/：无前端依赖的阅读界面与逻辑。
- backend/：API、数据仓库、来源适配器、摘要、调度与邮件。
- config/sources.json：核实状态与接入方法。
- schema.sql：数据库初始结构，启动时兼容旧库迁移。
- scripts/：检查、静态构建、公开快照导入／导出。
- docs/HANDOFF.md：最新真实进度与下一项操作。
- docs/DECISIONS.md：用户要求和设计选择。
- docs/NEXT_AI_PROMPT.md：可转交给其他 AI 的提示词。

可继续扩充亚洲、拉美、非洲等地区的文化来源、更多官方场馆展期和关注名单；覆盖范围不代表已经收录所有国家／场馆。全文和报道图片不会被默认镜像。

## 阅读、翻译与配图 v0.6

本轮 462 条资料中有 311 张来源配图、327 条原文短摘录。391 条外文标题及 277 条外文摘录实际完成公共机器翻译，另 50 条中文资料无需翻译。详情显示中文摘要／译文、原标题、原文摘录、阅读全文与翻译全文入口。全文在来源网站阅读，不把短摘录称为全文。图片由来源地址加载，注明来源，失败时显示明确占位；没有真实配图时使用标注的原创示意，不冒充原作。

TRANSLATION_PROVIDER=google-public（disabled 可关闭）；TRANSLATION_DAILY_LIMIT=1000 是公共翻译请求数上限，READING_PAGE_LIMIT=20 控制每次补读缺失公开摘要／图片。翻译缓存使用标题、短摘录、语言与服务输入哈希，来源改变时失效；账本随公开快照恢复，重复处理无新增请求。仅向翻译服务发送公开标题和短摘录，不发送收藏、偏好、媒体或凭据。此公共端点不是付费官方 API，访问失败保留现有译文与原文，后续可替换服务。

单文件版的脚本／样式与文字快照可离线使用，来源图片需要网络，离线时回退到明确占位。

## 原文与每日ChatGPT校译 v0.10

#reader/ID保留本站原文和“中文校译”视图。未完成校译不删原文或来源，旧Google机翻不默认显示。

每日任务读取小文件队列与 docs/DAILY_TRANSLATION.md，按重要性和时效使用可用快模型直接翻译全文，不安排第二轮模型校对；译稿写data/translations并记录实际模型。GitHub发布桥接核对原标题、正文hash、块数、数字与直译/旧校译身份，再入库并重新发布。陈旧／未通过稿不覆盖原文。公开定时状态与真实发布证据见 docs/DAILY_TRANSLATION_STATUS.md，API密钥不是这一路线的必需配置。

EDITORIAL_PROVIDER=chatgpt-task为当前默认。OpenAI-compatible API模式仅为可选替代，配置与凭据仍来自用户环境；不会在直接ChatGPT任务中暗中调用。

最新展览偏好：明确非日本普通展览降低排序，日本和重大展览按原规则，未知地区不按语言推断；全部资料/原文/日历保持。免费API选项与官方额度见docs/FREE_TRANSLATION_APIS.md，本轮仅咨询，未启用外部API。

界面已改为旧报纸风格：报头、纸底、衬线分栏，四主导航与折叠筛选；资讯18条分页并搜索全部库存。其他AI的修改入口是frontend/theme.css和frontend/ui.js（CultureUI v1），完整契约见[UI_CUSTOMIZATION](docs/UI_CUSTOMIZATION.md)，Claude交接见docs/CLAUDE_UI_HANDOFF.md。

当前报版已重新排成头条/次条/简讯三栏，报头与查询工具紧凑，重复介绍隐藏，开发与处理说明按需展开。公共新闻查询/阅览为主，收藏/偏好为辅助。后端重复记录合并UPDATE、统计分组、浏览器去冗余正文，实测与兼容约定见[BACKEND_OPTIMIZATION](docs/BACKEND_OPTIMIZATION.md)。
