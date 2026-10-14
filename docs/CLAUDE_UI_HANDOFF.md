# Claude 与其他AI的界面接力

仓库：https://github.com/k1ryulong6-source/ART-NEWS

网站：https://k1ryulong6-source.github.io/ART-NEWS/

用户已确认旧报纸风格与页面精简。当前实现：泛黄纸底、黑色报头、衬线标题、分栏/细线；四个主导航“头版/资讯/日历/剪报”，偏好在页眉；频道与日本专题直接可见，其他筛选折叠；资讯18条分页，全库存搜索。中文默认、原文切换、收藏、日历和收录进度保留。

先读AGENTS.md、docs/HANDOFF.md、docs/PRODUCT.md、docs/DECISIONS.md和tasks.json。详细可修改接口见[UI_CUSTOMIZATION.md](UI_CUSTOMIZATION.md)。优先修改theme.css主题变量和ui.js展示组件；index.html控制报头与容器，app.js负责状态/事件，core.js保留数据与安全逻辑。CultureUI v1包含heading/meta/card/feature/pagination，其他AI无需改后端即可改视觉。

本项目是原生HTML/CSS/JS＋Python FastAPI/SQLite，不是React/Vite。data.js和dist为生成文件，不能手改。新增资产同步静态构建与本地API白名单。保留GitHub Pages的/ART-NEWS/路径和单文件预览；不要让视觉依赖模型密钥。

保留全部来源、稳定ID、保存原文、图片出处和消息状态；所有旧/新外文仍需翻译，T028未全量完成保持doing。用户取消二轮模型校对，最新按足够完成翻译的性价比选型号，当前按费用反馈默认GPT-5.6，不另配API；新稿称AI翻译，旧已校译身份保持。标题译文不代表正文完成，不能展示旧逐句机翻或外文冒充中文。未知信息不补造。

非日本普通展览降低排序，日本/重大/未知地点维持原规则；不因此删资讯或日历。覆盖页显示真实有限来源和缺口，不称全球100%。公开采集每2小时，每日会话翻译任务与全量分页保持。

浏览器收藏继续使用culture-desk-v1版本1。标题/摘要/图片指向同篇阅读；收藏按钮独立。18条分页仍覆盖全量，筛选/搜索回到第一页。CSS颜色或组件布局变更不能破坏这些契约。

代码验证和手机/平板/桌面验收命令见UI_CUSTOMIZATION.md。桌面与手机截图见images/newspaper-desktop.png与images/newspaper-mobile.png。从最新main创建分支，通过PR接续；无需问已明确风格，但更改数据或功能另建任务。单给链接不自动授予写权限；Claude Code可在已授权checkout工作，网页会话需GitHub连接，只有只读工具时交付可应用补丁，不声称已发布。

可直接转发：

> 请读取 https://github.com/k1ryulong6-source/ART-NEWS 的AGENTS.md、docs/CLAUDE_UI_HANDOFF.md及docs/UI_CUSTOMIZATION.md，在当前旧报纸风格上继续改界面。优先用theme.css和CultureUI v1展示组件，保留中文/原文、三处阅读链接、全部分页、收藏/日历/覆盖页和自动更新。基于最新main创建分支，完成1440/768/390px实际浏览器验证并提交PR；没有写权限则给补丁。
