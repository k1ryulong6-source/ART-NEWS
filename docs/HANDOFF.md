# 当前交接记录 · v0.17

更新时间：2026-10-14 JST。建设者：Codex。

最新要求：重要性与时效优先，用户取消第二轮模型校对，最新要求按性价比选择足够完成全文翻译的模型，当前按用户费用反馈默认GPT-5.6（gpt-5.6-sol），不默认Luna或自动升级较贵模型，不另配API。新稿直接AI翻译＋程序段落/数字/来源检查，不能称校译；旧32校译保留。当前44已翻译（直接12＋旧校译32，6篇公开部分），49原生中文，442待译，2正文缺失。当前537资料／198活动／26来源，T028仍doing。T029增加四级及依据、每批旧稿份额和真实快模型译稿；每日任务原日程保持。

## 仓库与授权

仓库：https://github.com/k1ryulong6-source/ART-NEWS 。用户保留公开仓库，并已明确授权公开网页。v0.5 新增四个官方来源，434 条资料／158 项活动；真实重复采集新来源 inserted=0。源级历史保留；本轮 GitHub 刷新 24 源成功，Asian Movie Pulse 与 BFI 返回 HTTP 403，分别保留原 8 条资料与 101 场次及最后成功时间，没有绕过限制。

API 密钥、密码、SMTP 配置、个人数据库与收藏不进入 Git。data/live.json 和 frontend/data.js 包含公开来源元数据、已采集正文、机器译文及处理次数账本。

## 实际完成（早期功能清单；最新计数与界面以页首及末尾验收记录为准）

- 今日／探索／日历／收藏／设置；频道、地区、城市、搜索、圈内动态开关与配额。
- 内容／活动详情、关注对象排序、收藏状态、JSON 导出恢复、ICS 日历导出。
- SQLite 存储，真实／示例分离，旧库迁移、首次公开快照恢复。
- 26 个真实来源；434 条资讯与资料、158 项活动（日本 28、英国 109、印度 3、南非 6、法国 4、韩国 4、全球征集 4）。
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

- 33 项 Python 与 14 项 JavaScript 检查通过。
- Uvicorn 实际监听与 HTTP 请求通过。
- 本轮新增四个官方来源两轮真实读取成功；重复采集 inserted=0。原 22 源本地验证见 v0.4 记录；GitHub 的 Asian Movie Pulse 403 不隐瞒。
- Chromium 桌面 1440px／手机 390px 五个页面无横向溢出、无脚本错误。
- 浏览器筛选、收藏刷新保存、状态修改、JSON 下载／上传、ICS 下载、来源开关、提醒入口与手动更新完成。
- v0.4 浏览器：法语 20 条、葡语 44 条、旧资料标签、班加罗尔展览与票价／闭馆说明、开普敦闭展状态；五个页面无溢出与脚本错误。
- v0.5 桌面／手机浏览器：摄影征集 4 项、学生组时刻冲突、报名入口、101 场伦敦放映、法国上映与首尔展期；收藏与 UTC ICS 下载验证通过。
- 单文件静态版在 390px 验证全球默认、切换伦敦优先、阅读时区、设置／收藏刷新保持、JSON 导出和五页布局。
- 本环境浏览器禁止 file URL；单文件的脚本与样式内联，可直接打开；v0.6 来源图片是外链，需要联网，离线有明确占位。
- v0.2 时 Docker 镜像成功构建；首次发现 COPY 目录权限导致非 root 用户不可读，已添加只读权限修复。修复后容器 HTTP 200，成功返回 160 条真实资讯与 28 项活动。

## 尚需配置／持续扩充

- SUMMARY_API_KEY 尚未配置。真实外部模型调用未启用；结构化日期摘要与来源摘录可读；v0.6 公共机器翻译已实际启用，独立于生成式摘要。
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

- CI：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407746912
- 实际自动刷新：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407982361
- 摘要配置：https://github.com/k1ryulong6-source/ART-NEWS/issues/1
- 托管选择：https://github.com/k1ryulong6-source/ART-NEWS/issues/2
- 已完成全球更新：https://github.com/k1ryulong6-source/ART-NEWS/issues/3
- 已完成全球来源补全：https://github.com/k1ryulong6-source/ART-NEWS/issues/4

网站：https://k1ryulong6-source.github.io/ART-NEWS/

首次公开部署成功：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38389258730。公开 URL 返回 HTTP 200；在线 Chromium 1440px／390px 五页无溢出和脚本错误，摄影时刻冲突、报名入口、101 场放映、地区筛选、收藏和 UTC ICS 下载通过。GitHub 每 12 小时自动刷新，刷新完成后自动重新发布。

T018 本轮资料任务：https://github.com/k1ryulong6-source/ART-NEWS/issues/5 。

## T019 · 同域名离线缓存冲突

用户确认网址显示 Selah；已复现根应用 Service Worker 拦截 `/ART-NEWS/`。全新浏览器验收漏掉已安装其他 PWA 的情形。用户已明确授权修改 Selah；私有源码 23d9830 修复根导航回退，发布 e8b1592，部署成功：https://github.com/k1ryulong6-source/k1ryulong6-source.github.io/actions/runs/38393132033。同一保留旧 Worker 的生产浏览器升级前复现、更新后正确打开映间，存储标记保留，390px／1440px 五页通过，根站仍离线可打开。已验收 T019；当前浏览器旧 Worker 如未升级，点击页面“更新 Selah”再打开资讯。详见 PAGES_TROUBLESHOOTING.md。

## T020 · 原文摘录、译文与配图

已完成采集、页面、公开发布和在线验收。当前 434 条资料／158 活动，306 张来源配图、299 条原文摘录、384 个机器翻译标题、249 个机器翻译摘录（另 50 条中文）。实际公共翻译 633 次请求，0 失败；重复翻译 0 新请求。图片只保存来源 URL，不镜像报道图片。原文摘录最多 280 字符加省略号／55 单词；短摘录、机器译文与全文入口明确区分。

31 Python／13 JS 检查通过；静态版与本地服务 1440px／390px 五页、真正加载来源图片、中文标题／译文、原文文本对照、全文链接、故障图回退、中文搜索通过。原有 101 场放映、4 征集、时刻冲突和 UTC ICS 再验通过。翻译不改事件日期、票价或收藏；预算与缓存跨快照恢复。

公开机器翻译配置为 TRANSLATION_PROVIDER=google-public，可关闭；每日最多 1000 请求，固定 3 个线程。端点可能变动／受限，失败不冒称已翻译，缓存保留。生成式 AI 摘要 T013 仍待账号；不应因已有公共译文而声称已启用付费模型。后续不要恢复只有标题的旧快照或用原始 1200 字符处理摘录作为公开全文。

T020 GitHub 检查 44 项通过：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407746912；实际自动刷新：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407982361；刷新后发布：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38398252913。GitHub 本轮新增 23 条日本上映资料摘录与译文，翻译 0 失败；保留 306 张图，当前 322 原文摘录、384 翻译标题、272 翻译摘录。两项补读页面失败保留此前内容；Asian Movie Pulse／BFI 403 仍如实记录。实际公开 URL 1440px／390px 源图真正加载、译文与原文、全文入口、失败图回退及五页通过。

## T021 · 站内原文，全部来源保留

用户明确要求原文在本站直接阅读，并补充所有来源保留、不能筛掉别的。已实现专门原文页，点击标题进入默认原文视图、中文摘要切换、活动信息、返回、收藏与直达路由。全部 434 个内容 ID、26 个来源及全部来源启用状态经逐项比较保持。当前响应头检查：211 页未禁止嵌入、223 页明确限制；限制不导致删除、禁用或筛掉记录。网络未确认的页仍可由用户浏览器尝试；明确限制的页保留摘录和地址，提示原因而不伪称全文成功。

原文窗口直接请求来源网站，本站不获取／镜像／代理文章正文，也不修改来源 frame-ancestors／X-Frame-Options。嵌入窗口限制来源脚本改变本站顶层地址；原文收藏不重新创建窗口。BFI 原文地址保留 context_id，稳定规范 ID 不改；8 个 RapaduraCast Patreon 原始链接保留且核实附加域名，不绕过订阅。每次刷新检查最多 20 页，过七天复核；不能将检查未禁止误称全部实际全文成功。

33 Python／14 JS 检查通过。实际 Chromium 1440px／390px 在本站读取 IMA 原网页，原文内容存在且留在本站；Film Stage、ART AFRICA、Cinéfilos 英／西文页面也实际可读。收藏保持窗口且刷新持久、原文直达链接刷新、中文切换、受限页面不删资料、探索全部 434 记录验证通过。已完成公开发布与实际在线原页验收。

T021 最新公开验证：原有 434 IDs 全保留，并合并自动刷新，当前 441 条资料／160 活动、26 来源。213 页响应头未阻止嵌入，228 页由来源限制；不将前者数量冒称所有页实际全文通过。47 项 CI 成功：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407746912。实际刷新：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407982361；原页检查新增 2 available／5 blocked，资料不删。刷新后部署成功：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38408100107。真实公开 URL 的 1440px／390px 原页、收藏不重建窗口、刷新、中文切换、受限内容保留、全部 441 探索记录，以及 Film Stage／ART AFRICA／Cinéfilos 原页再次通过。


## T022 · v0.8 来源正文直接阅读

用户明确拒绝嵌入，要求抓取保存原文。新增 backend/articles.py：来源特定选择器＋Trafilatura，安全重定向域名与结构化内容块。本站转义排版，不执行原站 HTML，不使用 iframe。保存段落、图片／图注、链接、作者、原始出处与时间；source ID/content ID/events 和 enabled 状态都与上一版完全一致。

本次批量对全部 441 条实际 GET。427 collected、13 partial（ARTnews 订阅标记的公开部分）、1 no_body（Artforum 2023 科尔比·张伯伦谈乔什·克莱恩，页面只返回标题作者）。50 条 Artforum 中包含杂志目录，目录保持自身页面内容，不补造整本杂志。BFI 的 78 个报道页各有不同正文 hash，对应 109 项场次／英国活动；MMCA 4 个展览介绍各自独立。

正文翻译240次实际调用，10条完成、1条部分，未完成块保持原文。累计当日翻译请求931次，账本随快照保存。每轮新增正文60条，翻译120次，失败两天重试，已采集七天复核；共享默认每天1000次上限。翻译停用／失败不会阻止原文阅读。

本地验收：python scripts/check_project.py；python -m unittest discover -s tests -v（39项）；node tests/core.test.js（15项）；node --check frontend/app.js；严格资料审计0错误、1个已有摄影征集时刻冲突提醒。Chromium 1440／390px 实测 Variety、ARTnews、IMA、ART AFRICA、BFI、MMCA、Artforum 的存储正文显示，全部 iframe 数为0；阻断来源网络仍可读保存的正文；中文全文、收藏不重建正文、刷新深链保存、缺正文记录保留、441条探索可见均通过。

所有公开部署与实际线上验证已通过。不要在未验证时声称全部来源／全部文章均有完整正文或全文译文。


T022 自动更新与新增资料：GitHub refresh 38428321826 成功，新增21条资讯与3项活动，441条旧ID和已保存的440条正文全部保持。新增正文16 collected、3 partial，2条Artnet在GitHub返回403；同一公开原文地址在当前正常采集环境补读成功（4218／9042字符），没有切换隐藏端点、剥除响应规则或解除登录。最新快照462条、163活动：445 collected、16 partial、1 no_body。正文翻译完成11条，累计当日共享调用1000次，已停止新请求，下一预算日继续。

实际发布验收：CI 38428245662（39 Python＋15 JS）通过；首轮公开部署38428245750通过；自动更新后部署38428538871通过。公开网址在1440／390px重复验证七个来源的保存正文、iframe=0、原站网络阻断仍可读、译文、收藏、刷新、探索462条、全部26来源保持，均通过。最终两条Artnet补读后快照发布与实际线上核验也已完成。


T022 最终完成：代码538ec99，自动快照c9f764c，补读快照7b36281。最终CI [38428982448](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38428982448) 与部署 [38428982544](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38428982544) 成功；自动更新 [38428321826](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38428321826) 成功。直接读取已发布 data.js 核对462条、26来源、445 collected／16 partial／1 no_body，两个Artnet补读正文都存在。公开手机／桌面重新验收全部通过，原文不依赖来源网页请求，iframe=0，无页面脚本错误。

运行与待补：按 docs/OPERATIONS.md 安装依赖并运行；正文采集与翻译已进入定时流程。唯一未取得正文为 Artforum https://www.artforum.com.cn/print/202304/14499，原站仅提供标题和作者。16条ARTnews只保留公开部分；11条非中文正文已完成机器译文，其余待每日共享账本重置后分段继续。当前请求账本达到1000次上限，不扩大额度、不丢弃原文。更多地区来源与官方日期缺口继续见 COVERAGE，未配置的生成式摘要／SMTP并不阻止正文阅读。


## T023 · v0.9 全文语境AI校译

用户明确选择AI全文语境翻译并校对。新增editorial.py、术语表、draft/review两请求、段落与数字校验、approved状态、并发hash保护及独立editorial_usage账本。前端只显示已reviewed校译，旧Google译文与标题退出默认展示；默认全部来源仍在，新增“AI校译”主动入口。原文／已收录活动与所有ID保持。

本次会话实际为4篇西／日／英／法原文制作中文稿并逐段对照：Cinéfilos《边境》、IMA铃木崇“もののをかし”展、ART AFRICA的Brandon Gercara展、Fisheye的Julie Peiffer报道。保留暂译说明、原名、原文数字、图像、时间和票价；不得称人工译者审核。provider=session-ai:context-review-v1，非外部模型调用，APIusage未虚增。

本地检查：44 Python＋16 JS=60项通过，项目检查／严格审计0错误通过。真实Chromium1440／390px：4稿原文/校译切换、译名说明、AI来源标注、旧机翻不显示、主动筛选4稿后返回全部462条、全部26来源保持，均通过，无横向溢出与页面错误。当前运行环境无EDITORIAL_API_KEY；GitHub密钥列表GET返回403，不能读取或新设模型密钥。用户服务名称问题已提出，可继续无凭据的建设，但自动API校译必须等配置。

自动校译配置与真实模型端到端验证是剩余工作：管理员在仓库Actions secrets添加EDITORIAL_API_KEY，按账户选BASE_URL/MODEL/REVIEW_MODEL，详见OPERATIONS。当前只测试了模拟模型契约和真实会话样稿，不声称外部API实际执行。公开发布验收已完成，模型API配置单独留为T024。


T023实际发布证据：代码c570808；[CI38433869071](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38433869071) 60项检查通过；[部署38433869177](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38433869177) 成功；公开站1440／390px实测4份校译、说明、来源标注、旧Google隐藏及全部来源保持通过。

真实GitHub更新 [38434030648](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38434030648) 继续正常采集原文，新增12条至474条，所有旧ID和4份校译保留。translations明确not_configured、reviewed=0、reason=EDITORIAL_API_KEY_missing；没有回退Google、没有付费API调用、editorial_usage为空。自动再发布 [38434258959](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38434258959) 已成功。自动校译模型配置与真实请求留为T024 blocked，不掩盖缺口。


最终公开474条版本在1440／390px再次通过4稿原文/校译切换、AI来源说明、旧机翻隐藏、主动筛选后返回全部、原文保持验收。T023已完成软件与实际样稿；T024为明确的凭据依赖阻塞。管理员配置MODEL/BASE_URL/REVIEW_MODEL及EDITORIAL_API_KEY后，运行一次Refresh并核查真实模型结果再报告启用。不要要求用户重新确认公开访问或AI校译方式。


## T025 · 每日ChatGPT直接校译路线建设中

用户要求每天由ChatGPT直接代译，转为定时任务＋已连接GitHub，不要求配置额外网站模型API。GitHub get_repo真实只读成功，push权限确认；automations.peek无重复任务。准备data/translation-input逐篇完整源块、data/translation-queue.json（跨频道／来源与旧稿份额）、docs/DAILY_TRANSLATION.md和data/translations译稿格式。新增import_packs源hash／标题／段落／数字／校对检查，模型不可用也能独立导入。

新增Publish daily AI translations工作流，分享文化资料写锁，验证后提交快照并自动Pages；refresh也导入既有译稿、重新生成队列。幂等导入避免重复覆盖；陈旧译稿不覆盖新原文，无源码／密码输入要求。当前任务还待实际提交发布、每日任务创建与验证，勿伪称已经每天运行。


T025实际证据：f907c45提供桥接＋一篇真实会话校译（Steve McQueen《66–76–26》展）。47Python＋16JS检查最初通过；新增无API任务模式验证后48Python＋16JS。导入工作流38441724744成功，bot158e92e更新快照和pending队列；部署38441784624成功。未调用模型API，5份校译均实际在站可读。

GitHubApp实际读取repo和DAILY_TRANSLATION成功；通过同一连接create_file写入DAILY_TRANSLATION_STATUS.md，提交bc9e860成功，验证定时任务所需连接可读写。automations.create与update均确认success、is_enabled=true，IANA DTSTART;TZID=Asia/Tokyo:20261014T113000、FREQ=DAILY、flexible_schedule。任务id仅保存在忽略的runtime/daily-automation.json，不写公开仓库。没有提前调用run_now，因为用户要求每日重复，未要求立即触发该任务；此会话译稿验证与首次定时执行分开。

当前419条原非中文待译，新增实际稿后418，短队列36项，423份非中文原文输入保持。未来单次任务受额度／时长限制，不承诺一次完成全部；若工具连接或发布失败，保留原文／待译及已完成稿，并按真实任务结果报告。部署／网页和任务私下状态复核均已完成。


T025最终验收：a1e0114改为默认chatgpt-task模式，无EDITORIAL_API_KEY仍能正常走译稿导入；[CI38442648556](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38442648556) 64项通过；[部署38442648767](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38442648767) 成功。公开1440／390px再次验证5份校译、注释／AI身份、旧机翻隐藏、全部474条／26来源保持，无脚本错误。任务private peek确认is_enabled=true、IANA日程正确，last_run_time=null，因此不假称第一次定时任务已执行。无需继续索要API凭据；用户可在ChatGPT任务管理修改或暂停每日任务。


## T026 · 中文优先与Claude视觉交接

419份标题稿与正文校译独立保存，构建验证原标题一致与批准状态，陈旧稿不套用；所有474条资讯与163项活动已有中文标题。默认中文阅读、原标题／正文原文切换、待译正文无外文填充、原有5份完整校译、26来源与收藏保持。新标题队列加入每日任务文档；新增稿短暂待标题校译，不能承诺全部未来稿已译。

Claude改版指南提供真实原生HTML/CSS/JS结构、文件范围、必须保留的功能与工作流、分支PR协作、移动／桌面验收与可复制指令。没有联系Claude或给它授予本会话工具权限。本地50项Python＋17项JavaScript通过，严格审计0错误／1项已有时刻冲突提示。Chromium 1440／390px验证全部中文标题、5份中文正文默认与原文标题/正文切换、深链刷新、待译正文不显示外文、收藏原文DOM保持及刷新保存、中文搜索、五页无溢出和脚本错误。每日任务prompt已更新标题优先补齐要求，日程与启用状态保持；已完成GitHub部署与公开站验收，见下条。


T026最终验收：实现提交0c64d14，[CI38447900904](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38447900904)（67项）与[Pages38447900995](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38447900995)均成功。真实公开URL在1440／390px再次通过474条／163活动全部中文标题、5份校译正文中文默认、原文标题和正文切换、深链刷新、待译不掺外文、收藏保持、中文搜索与五页布局，无脚本错误。每日任务更新成功并保持enabled=true、Asia/Tokyo原日程，未声称已首次定时执行。T026完成；下一步按CLAUDE_UI_HANDOFF另开视觉任务，不覆盖自动数据提交。


## T027 · 全量队列、真实漏采证据与本轮27篇校译

以最新已发布快照独立重建runtime/full-coverage-20261014.db。本轮实测17 RSS有34条不在库存，已补采；BFI又取得17新条目和35活动。数据从474/163增至525/198，旧ID、正文与5份旧校译全部保持，新稿正文已采集。第一次本地误用旧测试库的导出未提交或发布，已从Git恢复并重建独立库；不可再用旧runtime/culture-desk.db导出本次资料。

本轮批次27份真实会话译稿已逐块读、译、二次对照，导入器0invalid、0stale。总32已校译，其中4为来源公开部分，49原生中文可读，442待校译，2正文未取得。全量分页15份覆盖每个待译原文，短名单不是全量。数据源、语种、是否上首页或旧稿不能成为永久排除理由；T028未全完成不能写done。

backend/coverage记录逐源原始RSS条目、排除原因、库内/缺条、范围、失败和前后列表重叠；官方配置页完整性标未知。独立官方抽查发现Bristol分展日历及美国摄影展覆盖缺口。公开#coverage提供进度、逐源证据、地区分布和判断方法，不给无分母的全球完整率。refresh改2小时并每次核对，translations继续更新全量分页；ChatGPT每日任务仅prompt加入全量遍历与持续清理，原日程保持。自然数值单位转换通过Decimal等值核对，保留日期/票价/编号。

本地54Python＋17JS=71项通过，python -S构建通过（Pages无需第三方依赖）。Chromium 1440/390px全中文标题、跨源7份正文样本中文默认与原文切换/刷新/收藏、六页布局、覆盖统计/26来源/3官方抽查/展开无溢出和脚本错误通过。公开实现8de8ce8；CI38492448896（71项）、译稿工作流38492448852和Pages38492477550全部success，真实网站1440/390px再次通过。T027完成；T028全量翻译保持doing，尚有442条待译，不宣称目标已全部完成。接续时读最新队列与data/translations匹配当前hash，避免重复，先补新增也给旧稿份额，全部可取得正文逐篇校译；不要停在样稿数量，也不要以启用任务代替实际完成。

终校将Rosé报道中的Eva Chow保留原名，避免错误套用中文人名；对应译稿与快照已更正，计数保持32/442。后续模型校译同样应优先保留存疑专名而非猜译。


## T029 · 分级与便宜模型直接翻译

两个gpt-6-luna会话工作者实际分工四篇完整全文：温哥华观众奖、马勒70周年4K／Betty Blue重映、Getty Images破产报道、香奈儿与辛迪舍曼。不安排主模型二次校对；仅规范block index与程序检查，导入0stale/invalid。新稿quality_mode=direct-ai、review.approved=false、status=not_requested，editorial_status=translated、实际draft_model记录、review_model=null。旧校译保留，无外部模型API调用。部分工作者在用户取消校对前已自校，这不冒称主模型独立校对。

backend/priority与config/translation-priority定义重要/明确活动时效/新闻新鲜度及人工override；全量分页排序，next28优先＋8旧稿，标题与活动日期不混用。探索排序、筛选、级别与依据；覆盖进度直译/旧校译分开。每日任务最新prompt无二次校对，不改日程；未来子模型可用性如实报告。可选API也支持一调用直译并跳过已有有效译文，本次用户选择不接API。

运行数据仍用runtime/full-coverage-20261014.db，勿导出旧runtime/culture-desk.db。新增模型任务不假称用户已授权外部API凭据/费用。检查与发布证据待下条补记。

T029最终批次：两个gpt-6-luna会话工作者共完成12篇，其中大都会歌剧院访谈原文28,532字符、73块，未因长稿跳过。新增8篇为当前优先级前列稿件。12份pack的标题、source hash、块序、数字程序检查全部通过，实际模型记录为gpt-6-luna (session worker)、review_model=null；未调用外部模型API，未安排二轮模型校对。当前44已完成（32旧校译＋12直接AI），49原生中文，430待译，2正文缺失，6篇已完成稿仅来源公开部分；525资料／198活动／26来源不变。77项自动检查和桌面1440／手机390浏览器验收，全部12新译稿的中文默认／原文切换／直译标识／收藏、优先级筛选、六页布局无溢出或脚本错误通过。T028仍doing。

公开实现9f5c006；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38496208635、译稿工作流 https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38496208976、Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38496208634 全部success。真实公开网站1440/390px全部12篇直译稿、中文默认/原文切换、优先级筛选、收藏/刷新、六页无溢出与脚本错误通过。 T029已验收done；T028全量翻译仍doing。下批读取最新版next与全量分页，按优先级和旧稿份额继续，不重译匹配hash的有效稿，不重启已被用户取消的二轮模型校对。

T030：用户因费用明确改用GPT-5.6。AGENTS、每日任务提示及文档、配置指定gpt-5.6-sol；不可用保留待译，不自动切换型号。历史Luna12篇真实模型出处保持，尚未冒称5.6已产生新稿。每日定时任务last_run_time=null，不能报稳定每日翻译量；最新运营计数与覆盖缺口见docs/OPERATING_METRICS.md。

用户随后授权按性价比选足够翻译的模型，取代严格型号唯一限制；目前无实时价格表，默认5.6，不猜价格或称已比较所有模型。AGENTS、配置、每日任务提示已同步。T031同时处理图片/摘要不能进入阅读页：探索、今日精选、收藏统一三个区域的语义链接，独立收藏按钮不嵌在链接中。

T030型号偏好和任务提示已实际更新并验收；T031本地1440/390三个入口、图片失败示意回退、Enter、中键新标签、独立收藏/状态、收藏摘要及布局验收通过；公开发布仍需核验。没有新增翻译调用，库存/原文不变。

公开实现c5f066d；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38497204397 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38497204425 全部success。真实公开网站Chromium 1440/390：卡片及首页精选标题/摘要/图片同篇阅读、中文默认、坏图回退点击、键盘Enter、中键新标签、独立收藏/已看过状态、收藏摘要及布局无溢出或脚本错误通过。 T031已验收done。T028仍doing，430待译；本轮没有调用任何翻译模型。

T032执行：已合并自动采集bb7bebb，当前535/198/26；44已译（32旧校译＋12直译）/49原生中文/440待译/2缺正文。23明确非日本普通展览降至P3及首页扣分；1重要奖项展例外，5日本及21未知地区维持原规则。关联展览举办地优先，多地含JP不降级，不以语种/总部猜。全量分页440及8旧稿份额保持，data/live.json和全部原文未改。每日任务prompt更新成功、启用与日程不变；免费API官方方案已核实，没有实际模型API调用。62Python＋19JS=81项通过；公开发布需后续记录。T028仍doing。

公开实现a0503d4；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38503655258 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38503655263 全部success。真实公开网站Chromium 1440/390：535全量卡片、23非日本普通展览P3筛选/阅读页依据/原文、重要日本未知例外、首页推荐及覆盖说明、无溢出或脚本错误通过。 T032已验收done；T028仍doing，440待译。免费API只查官方页面，当前没有接入或调用；下一批按新的日本展览偏好与重要例外读取队列，全部旧/新原文继续。

T033旧报纸版：四主导航、偏好/覆盖页保留、更多筛选折叠、18条分页/全量搜索；源图加载占位标原创示意，读取正文原图不滤色。frontend/ui.js提供CultureUI v1（heading/meta/card/feature/pagination）；theme.css主题变量与响应式独立。index/app/构建及本地API资源同步；UI_CUSTOMIZATION与Claude交接文档重写为最新要求，data/原文/存储/任务日程不变。折叠栏在重绘时先同步open避免丢状态；skip-link hash不误回首页。62Python＋21JS=83检查通过，公开验证待记录。

公开实现ea933f5；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38512575722 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38512575751 全部success。真实公开网站Chromium1440/768/390完整遍历535条/30页、搜索/折叠筛选/三个阅读链接/中文与原文/收藏状态刷新、六页及长文无溢出或脚本错误、CultureUI v1及HTTP单文件无外部CSS/JS并可运行。 T033已验收done。修改接口已公开，主题/展示/状态/核心逻辑分层见docs/UI_CUSTOMIZATION.md，Claude接力说明指向该接口。T028仍doing，440待译，本次未调用翻译API或改日程。

T034：按公共艺术新闻查询/阅览平台定位重做报版，紧凑报头/竖线三栏/头条次条简讯，介绍隐藏与开发处理说明折叠；原文/译文/查询/分页/收藏/日历保留。CultureUI v1新增frontpage；公共浏览器包不再假定article_text必有，使用CultureCore.sourceText。原文档案data/live.json未改，536资料（最新自动新增1）、198活动、26源、44已译/49原生中文/441待译/2缺正文。T028仍doing。优化实测见BACKEND_OPTIMIZATION，65Python+23JS=88检查通过；尚需公开验收记录。

发布前已合并自动采集9a5ce82：最新537资料/198活动/26源，44已译/49原生中文/442待译/2缺正文；重新逐条核验全部537原文、译文及搜索文本等价。优化对比使用此前同一536条样本，不能把新增数据混成性能变化。

公开实现913ffb9；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38527095026 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38527094941 全部success（88检查）。真实公开网站Chromium1440/768/390：537条完整分页/全量旧稿搜索/折叠筛选/三处阅读入口/原文切换/收藏状态持久/六页长文无溢出或脚本错误；首条标题400px内、介绍不渲染、v1 frontpage接口和HTTP单文件运行通过。 T034已验收done。界面定位以公共艺术新闻检索和阅览为主，保留独立theme/UI接口；不要恢复私人介绍/黄纸卡片或冗长宣传。T028仍doing，442待译，本轮没有翻译API调用。


## T035 · 最新要求：报纸排印与待译原文直接刊载 · 2026-10-14

用户要求完全模仿报纸，待译正文可直接贴原文或机械翻译。本版选择本站已保存的原文，无额外API：默认阅读即完整显示已采集正文、图片和引用，标“原文·待译”与真实lang；现有中文全文优先，中文标题已有则保留，缺中文标题回退原标题。首页未译摘要/头条预览也直接用原文，避免只有待译占位。待译身份和全量翻译队列不变，缺正文与公开部分如实标注。

报头加大、四逻辑栏（头条跨两栏）、通栏标题/来源日期/双栏正文预览，阅读正文每8块组成短双栏版面，手机改为单栏，长稿不需读完整条竖栏再返回顶部。无来源配图的头条用文字排印，不以虚构艺术图填版；列表图片入口和独立收藏保持。CultureUI v1、theme.css与DOM事件接口继续开放。查阅/搜索/全部分页为公共平台主功能，不恢复个人介绍。

此次只修改展示规则，没有生成新译文、调用翻译API或改变采集/每日任务日程。T028保持doing。

T035本地验收：65Python＋24JS＝89项通过，python -S静态构建及数据审计0错误；Chromium1440/768/390全部537资料分页、全库搜索、三入口、收藏持久与六页无溢出/脚本错误通过。未译各语种、最长正文及公开部分样本默认逐块等于保存原文，lang与待译标记正确，缺正文保留状态；阅读双栏/手机单栏通过。每日任务prompt已实际同步原文直接刊载，启用及Asia/Tokyo日程不变。原文档案及译稿/队列未改。公开验收待下一条记录。

公开实现f433f80；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38529814910 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38529814722 均success。真实网站Chromium1440/768/390全部537条分页、全量搜索、三处阅读入口、收藏状态持久、六页与长文无溢出/脚本错误通过；未译各语种/最长正文/公开部分样本默认逐文本块精确匹配原文，真实lang、待译身份、正文缺失状态及桌面双栏/手机单栏通过。公开截图更新并保存阅读页截图。T035已验收done；T028仍doing，442待译，44已有中文译稿，无新增翻译/API调用。

T036：正式更名幕间休息。报头/标签页/描述/页脚、favicon、导入提示/API标题/邮件模板同步（未发送邮件）。使用自托管OFL字体三层：四字Ma Shan Zheng报头、Noto Serif SC宋体、Newsreader英文；来源/hash/覆盖/重建见frontend/fonts。主题--display/--serif/--sans保留AI修改入口，Pages不新增字体依赖，本地API白名单和单文件字体内嵌已同步。稳定项目路径/ID/收藏键不迁移，原文和译稿不变。每日任务prompt仅更名成功，启用与原日程保持。公开验收待追加。

T036本地验收：65Python＋24JS＝89检查通过（本地API三字库返回200），python -S静态构建与审计0错误。Chromium1440/768/390全537资料分页/查询/阅读/收藏持久及六页无溢出/脚本错误，三个Intermission字体均loaded；320px正常/阻断字体请求时均可读且无溢出。HTTP单文件内嵌三字库，loaded且无外部字体请求。站名/导出文件名/ICS日历名同步，收藏键和原始UID保持。公开验证待后续补记。
