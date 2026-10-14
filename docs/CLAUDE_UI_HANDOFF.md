# Claude 与其他AI的界面接力

仓库：https://github.com/k1ryulong6-source/ART-NEWS

网站：https://k1ryulong6-source.github.io/ART-NEWS/

用户要求面向公众的艺术新闻查询/阅览平台，重做真正报版并隐藏介绍。当前实现：紧凑报头、三栏竖线、头条/次条/简讯与正文排印；四个主导航“头版/资讯/日历/剪报”，偏好在页眉；频道与日本专题直接可见，其他筛选折叠；资讯18条分页，全库存搜索。中文默认、原文切换、收藏、日历和收录进度保留。

先读AGENTS.md、docs/HANDOFF.md、docs/PRODUCT.md、docs/DECISIONS.md和tasks.json。详细可修改接口见[UI_CUSTOMIZATION.md](UI_CUSTOMIZATION.md)。优先修改theme.css主题变量和ui.js展示组件；index.html控制报头与容器，app.js负责状态/事件，core.js保留数据与安全逻辑。CultureUI v1包含heading/meta/card/feature/pagination，其他AI无需改后端即可改视觉。

本项目是原生HTML/CSS/JS＋Python FastAPI/SQLite，不是React/Vite。data.js和dist为生成文件，不能手改。新增资产同步静态构建与本地API白名单。保留GitHub Pages的/ART-NEWS/路径和单文件预览；不要让视觉依赖模型密钥。

保留全部来源、稳定ID、保存原文、图片出处和消息状态；所有旧/新外文仍需翻译，T028未全量完成保持doing。用户取消二轮模型校对，最新按足够完成翻译的性价比选型号，当前按费用反馈默认GPT-5.6，不另配API；新稿称AI翻译，旧已校译身份保持。标题译文不代表正文完成，不能展示旧逐句机翻或外文冒充中文。未知信息不补造。

非日本普通展览降低排序，日本/重大/未知地点维持原规则；不因此删资讯或日历。覆盖页显示真实有限来源和缺口，不称全球100%。公开采集每2小时，每日会话翻译任务与全量分页保持。

浏览器收藏继续使用culture-desk-v1版本1。标题/摘要/图片指向同篇阅读；收藏按钮独立。18条分页仍覆盖全量，筛选/搜索回到第一页。CSS颜色或组件布局变更不能破坏这些契约。

代码验证和手机/平板/桌面验收命令见UI_CUSTOMIZATION.md。桌面与手机截图见images/newspaper-desktop.png与images/newspaper-mobile.png。从最新main创建分支，通过PR接续；无需问已明确风格，但更改数据或功能另建任务。单给链接不自动授予写权限；Claude Code可在已授权checkout工作，网页会话需GitHub连接，只有只读工具时交付可应用补丁，不声称已发布。

## 当前分工与文章排版接口 · 2026-10-14

用户明确让Claude负责前端设计与文章排版，Codex负责后端/API/自动更新/重要新闻覆盖。请基于最新main建前端分支，用PR合并；后台每2小时自动写data，避免提交旧快照或重写工作流、供应商配置及配额账本。

- 完整档案在data/live.json；浏览器以window.CULTURE_BOOTSTRAP.live读取压缩后的全量。不要假定article_text一定传到浏览器，原文用CultureCore.sourceText(row)，正文块用CultureCore.articleBlocks(row, translated)。
- 块type包括paragraph、heading、quote、list_item、image；文字text，图片url/alt/caption/credit；图片和来源信息保留。AI正文存editorial_blocks_json，临时机翻存article_translation_json，两者不能混成同一已译口径。
- CultureCore.editorialReady判断有效AI全文，machineReady判断有效临时机翻；默认AI→有效机翻→保存原文，无正文显示采集状态。原文开关必须可用，部分公开稿不能冒称订阅全文。原标题、原文语言、译文真实身份清楚但不要塞冗长技术介绍。
- CultureUI v1保持，theme.css负责主题，ui.js负责卡片/头版/pagination，app.js负责阅读与状态。图/标题/摘要都打开同篇#reader/ID，收藏独立；全文搜索、全部分页与culture-desk-v1收藏保持。
- boot.coverage.important_news为重要新闻观察：missing_important_items/core_source_problems/fresh_important_items/awaiting_AI_count；boot.coverage.collection_metrics记录真实日新增并单列first_source_run_records。名单漏条为零不等于全球无遗漏。
- boot.automation.ai与translation分别为AI和临时机翻状态；health记录实际Actions。AI needs_configuration不能显示为已开启，quota_wait/daily_limit为保存进度后等待，不是永久失败；本轮尚未真实调用API。
- 文章排版至少验证长英文/日文原文、AI中文、机器中文、图片说明、公开部分、缺正文、1440/768/390px无溢出、键盘链接和刷新收藏。

可直接转发：

> 请读取 https://github.com/k1ryulong6-source/ART-NEWS 的AGENTS.md、docs/CLAUDE_UI_HANDOFF.md和docs/UI_CUSTOMIZATION.md。你负责幕间休息的前端设计与文章排版，Codex负责后端/API/自动更新/重要新闻覆盖。以完整报纸为设计参照，基于最新main创建前端分支，保留中文/原文切换、配图、有效译文身份、图片/摘要/标题入口、全量搜索与分页、收藏、日历和覆盖状态；使用theme.css与CultureUI v1。不要改后台/API密钥/工作流或覆盖自动生成数据。完成1440/768/390px实际浏览器验收并提交PR；没有写权限则交付补丁。

T034已优化后端重复数据库写入及覆盖统计，并精简浏览器传输；完整档案/原文/译文不删。CultureUI v1新增frontpage，sourceText为可选article_text的统一读取入口。修改界面先理解UI_CUSTOMIZATION与BACKEND_OPTIMIZATION，避免恢复私人介绍页/黄纸卡片/大量重复说明。新闻检索和阅览为主，收藏与偏好为辅助。


## T035 · 最新要求：报纸排印与待译原文直接刊载 · 2026-10-14

用户要求完全模仿报纸，待译正文可直接贴原文或机械翻译。本版选择本站已保存的原文，无额外API：默认阅读即完整显示已采集正文、图片和引用，标“原文·待译”与真实lang；现有中文全文优先，中文标题已有则保留，缺中文标题回退原标题。首页未译摘要/头条预览也直接用原文，避免只有待译占位。待译身份和全量翻译队列不变，缺正文与公开部分如实标注。

报头加大、四逻辑栏（头条跨两栏）、通栏标题/来源日期/双栏正文预览，阅读正文每8块组成短双栏版面，手机改为单栏，长稿不需读完整条竖栏再返回顶部。无来源配图的头条用文字排印，不以虚构艺术图填版；列表图片入口和独立收藏保持。CultureUI v1、theme.css与DOM事件接口继续开放。查阅/搜索/全部分页为公共平台主功能，不恢复个人介绍。

此次只修改展示规则，没有生成新译文、调用翻译API或改变采集/每日任务日程。T028保持doing。

最新品牌“幕间休息”；报头/标签页/描述/页脚已统一。字体职责与自托管来源、许可见UI_CUSTOMIZATION.md和frontend/fonts/README.md，独立theme.css仍是主修改入口。不要按老截图恢复映间名称或删OFL许可，收藏存储键与新闻ID保持。

## T037 · 当前工作：黑体与无人值守主链

用户否定宋体，中文标题与正文改自托管Noto Sans SC黑体；书法报头、栏目和其他AI修改接口保持。采集结束触发GitHub后台离线机翻，再由工作流完成数据保存与Pages发布，不依赖当前聊天。免费模型/数字检查/断点/退避/健康记录见AUTONOMOUS_WORKFLOW.md。已有AI全文保护且优先，机器稿明确标自动机翻，与AI计数/全量精译队列分开。当前本机已实际完成5篇（约1.18万字符、129秒）；69Python＋25JS＝94检查通过，公开真实链路尚待验收。T037保持doing，T028全量AI精译仍doing。


T039联动入口：文章页「巴别塔阅读」一键导入原文供查词，保留CultureCore.babelReaderUrl(row)和data-ui=babel-import。可重设计按钮/位置，但必须与中文/原文显示tab无关、传原文稳定ID，无正文/示例禁用。不要把中文摘要当学习正文或恢复手动复制。跨项目协议见docs/BABEL_INTEGRATION.md，目标巴别塔接收代码已独立维护；其他视觉/排版继续由Claude负责。

## T040 · 报纸版面重排（Claude）

按用户“报纸样式、不要AI味、不要多余说明和按钮”重排：去掉原创示意图、优先级徽标、口语提示和引导按钮；简讯/头条/焦点/更多报道四区，外文原文衬线、中文黑体。细节见HANDOFF T040与UI_CUSTOMIZATION v4。

T049域名迁移：主站mujianrest.work，状态和设置见CUSTOM_DOMAIN.md。保留相对静态资源、#reader/ID和culture-desk-v1；不要把旧项目路径/域名写回返回链接。巴别塔仍在原/babel/，API新旧地址兼容；自动数据和主题设计保持。
