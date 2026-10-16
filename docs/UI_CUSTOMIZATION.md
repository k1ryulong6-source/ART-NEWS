# UI 修改接口 v1 · 公共新闻报版

仓库：https://github.com/k1ryulong6-source/ART-NEWS

网站：https://k1ryulong6-source.github.io/ART-NEWS/

这是原生HTML/CSS/JS＋Python FastAPI，不需要React、额外模型API或在线编辑器。其他AI从最新main创建分支，通过GitHub工具或本地checkout改代码并提交PR；仓库链接可供阅读，直接写入仍取决于该AI客户端的GitHub授权。

## 三个视觉入口

| 文件 | 修改内容 |
| --- | --- |
| `frontend/theme.css` | 主视觉入口。纸色、墨色、衬线字体、字号、宽度、间距、响应式；末尾加载覆盖基础样式。 |
| `frontend/ui.js` | 展示组件接口`window.CultureUI`，版本1；改标题、卡片、头条、分页的HTML。支持CommonJS，便于独立测试。 |
| `frontend/index.html` | 报头、导航容器、搜索、页脚和资源加载顺序。 |

`frontend/styles.css`为现有基础行为/布局样式。`frontend/app.js`管理状态、渲染页面和事件；新增组件或改交互时在此接入。`frontend/core.js`处理筛选、优先级、时间、安全转义和导入等公共逻辑。`frontend/data.js`与`dist/`是生成文件，不手改。

主题变量：`--canvas`、`--paper`、`--white`、`--ink`、`--muted`、`--line`、`--accent`、`--green`、`--serif`、`--display`、`--sans`、`--paper-width`、`--paper-gutter`、`--headline-size`、`--article-size`、`--reader-measure`（阅读页正文宽度）。改变颜色与字号不用改采集或数据库。内容图片只在卡片/头条采用报纸滤色，阅读正文原图保持正常颜色；占位图必须注明原创示意。

## CultureUI v1

加载顺序：data.js → core.js → ui.js → app.js。app创建：

```js
const ui = CultureUI.create({
  C: CultureCore,
  artwork, saveButton, findBookmark,
  sourceName, publicationLabel, priorityBadge
});
```

返回组件（兼容v1并新增`frontpage(rows, agendaHTML)`）：`heading(title, subtitle)`（副标题默认不展示）、`meta(row)`、`card(row, showStatus=false)`、`feature(row)`、`pagination(total, page, size)`，返回HTML字符串。`row`为现有content数据，保持稳定ID和原文身份。纯展示组件不修改数据、不调用API、不读写localStorage。文本使用`C.escape()`；URL采用`C.readerRoute()`或core已有安全URL工具。注入的artwork/saveButton/priorityBadge返回可信项目HTML，其余字符串须转义。

提供者：`artwork(row,large=false)`渲染来源图或示意图；`saveButton('content',id)`渲染独立收藏按钮；`findBookmark('content',id)`提供当前收藏或空；`sourceName(row)`、`publicationLabel(row)`提供展示文本；`priorityBadge(row)`提供优先级标记。组件不通过媒体总部猜举办地，不把标题译完算作全文译完。

稳定展示标记：`data-ui="masthead"`、`news-card`、`lead-story`、`pagination`。可以改这些组件内部布局和CSS，但须保留下面的行为契约。

## 交互契约

- 标题、摘要和图片为同一`#reader/ID`链接；收藏按钮为链接的兄弟元素，不能嵌套在链接内。支持键盘与新标签打开。
- 主页面容器`#main`；搜索`#search`；导航`#navigation`；偏好入口`#coordinate-button`；提醒`#inbox-button`；日期`#edition-date`；页脚说明`#edition-note`；弹窗`#detail-dialog`/`#detail-body`/`#close-detail`；消息`#toast`。
- 导航按钮`data-view`使用today/explore/calendar/bookmarks/settings/coverage。路由键不随中文标签改变；“剪报”仍是bookmarks。
- 折叠筛选`#advanced-filters`；保留country-filter/city-filter/language-filter/priority-filter/event-type-filter/buzz-filter及原事件绑定。全球/日本用`data-scope`；频道`data-channel`；种类`data-kind`。
- 分页默认18条。`data-list-page`按钮与`#article-page`跳页选择器；筛选/搜索时回第一页。搜索查全部库存，不只当前页；所有记录通过分页可达。页面状态在当前会话中保存，不改变收藏格式。
- 收藏保留`data-save-type`/`data-save-id`，状态保留`data-bookmark-status`。浏览器存储键`culture-desk-v1`、schema版本1保持。
- 阅读页保留中文/原文/资料三个tab、深链接、原标题及保存正文；未译明确待译、公开部分与缺正文如实标注。
- 保留日历/活动当地时区、来源开关、JSON与ICS导出、覆盖进度、非日本普通展览降级和重大例外。全部来源/原文/ID不能为精简UI删掉。

## 构建与验证

新增资源须同时改`frontend/index.html`、`scripts/build_static.py`复制/内联规则，以及`backend/app.py`安全资源白名单。本轮theme.css与ui.js已加入三处，Pages、本地API和单文件预览均包含接口。

```sh
python scripts/check_project.py
python -m unittest discover -s tests
node --test tests/core.test.js tests/ui.test.js
node --check frontend/app.js
node --check frontend/ui.js
python scripts/audit_data.py --strict
python -S scripts/build_static.py
python -m http.server 8002 --directory dist
```

浏览器验证1440、768、390px：六页与阅读无横向溢出；遍历全部分页、搜索旧稿、折叠筛选切换不意外收起、三个阅读入口、中文/原文/刷新、收藏状态持久保存。HTTP单文件`culture-desk-preview.html`没有外部CSS/JS引用并可运行；本环境浏览器禁止file协议导航，因此不冒称file协议已实际验收。未来在普通本地浏览器打开文件时另行核验。

完成后更新tasks.json/HANDOFF，提交PR并写实际验证结果。自动采集可能提交新data，提交前fetch并合并；不要强推或用旧data.js覆盖新资讯。

## T034报版与浏览器数据形态

平台定位为面向公众的艺术新闻查询/阅览。frontpage把新闻分为简讯/头条次条/焦点栏，主题改为连续报版、多栏竖线、紧凑报头；宣传/重复介绍默认不渲染，开发与处理说明默认折叠。正文中的来源促销段落仅在首页预览中跳过，完整原文/译文仍保持。

browser_snapshot只精简传输副本，data/live.json为完整档案；article_text可能省去，读取搜索正文用CultureCore.sourceText(row)，正文渲染仍用articleBlocks。弱引用缓存按原文块内容变动失效。不要恢复大段重复JSON或用摘要代替原文以“提速”。相关实测见BACKEND_OPTIMIZATION.md。


## T035 · 最新要求：报纸排印与待译原文直接刊载 · 2026-10-14

用户要求完全模仿报纸，待译正文可直接贴原文或机械翻译。本版选择本站已保存的原文，无额外API：默认阅读即完整显示已采集正文、图片和引用，标“原文·待译”与真实lang；现有中文全文优先，中文标题已有则保留，缺中文标题回退原标题。首页未译摘要/头条预览也直接用原文，避免只有待译占位。待译身份和全量翻译队列不变，缺正文与公开部分如实标注。

报头加大、四逻辑栏（头条跨两栏）、通栏标题/来源日期/双栏正文预览，阅读正文每8块组成短双栏版面，手机改为单栏，长稿不需读完整条竖栏再返回顶部。无来源配图的头条用文字排印，不以虚构艺术图填版；列表图片入口和独立收藏保持。CultureUI v1、theme.css与DOM事件接口继续开放。查阅/搜索/全部分页为公共平台主功能，不恢复个人介绍。

此次只修改展示规则，没有生成新译文、调用翻译API或改变采集/每日任务日程。T028保持doing。

## T036 · 幕间休息与字体（最新）

正式名称“幕间休息”。报头/页脚使用--display的Intermission Masthead（Ma Shan Zheng四字子集）；中文标题/正文宋体与拉丁Newsreader经--serif混排，--sans用于操作控件。字体均自托管于frontend/fonts，OFL许可和来源/重建/hash见fonts/README.md及manifest.json。不要引入第三方字体CDN或删许可证。brand现在仅四字，不能恢复“映间文化报”。移动字号用clamp；标题真实字重、无伪粗体；正文光学字号与行距独立。静态发布复制字体，本地API明确白名单，单文件预览字体内嵌。收藏键culture-desk-v1、项目路径/ID保持，改站名不迁移数据。

## T037 · 当前工作：黑体与无人值守主链

用户否定宋体，中文标题与正文改自托管Noto Sans SC黑体；书法报头、栏目和其他AI修改接口保持。采集结束触发GitHub后台离线机翻，再由工作流完成数据保存与Pages发布，不依赖当前聊天。免费模型/数字检查/断点/退避/健康记录见AUTONOMOUS_WORKFLOW.md。已有AI全文保护且优先，机器稿明确标自动机翻，与AI计数/全量精译队列分开。当前本机已实际完成5篇（约1.18万字符、129秒）；69Python＋25JS＝94检查通过，公开真实链路尚待验收。T037保持doing，T028全量AI精译仍doing。


2026-10-14最新分工：Claude负责前端设计与文章排版，Codex负责后端/API/自动更新/重要新闻覆盖。语境AI API为主，离线机翻仅临时兜底；无key不冒称已启用。免费接入和真实状态见docs/AUTONOMOUS_WORKFLOW.md。此前不另配API的偏好已被最新指令覆盖，未授权费用不自动付费。

## T040 · 报纸版面 v4

theme.css已整体重写为v4：令牌在`:root`（新增`--latin`用于外文原文、`--rule`/`--rule-ink`栏线）；styles.css只保留重置与可访问性基础。CultureUI v1新增`brief(row)`（无图简讯），`card(row, showStatus, {art:false})`可关图；卡片标题/摘要、头条正文带`lang`，CSS用`:not([lang^=zh])`切换外文排印。收藏按钮改在卡片底栏（仍是链接的兄弟元素）。`artwork()`无来源图时返回空字符串，不再生成示意图；图片失败时隐藏`.card-art/.feature-art/.reader-cover/.detail-art`。报头新增`#edition-updated`；`#coordinate-button`在页脚；`.refresh-control`与`#inbox-button`仅本地API显示。

## T041 · 手机阅读

`.paper-toolbar`现为`.masthead`之后的兄弟元素（`#navigation`/`#search`等ID不变），手机端`position:sticky`；app.js滚动监听只切换`body.bar-hidden`和`.read-progress span`的scaleX，不改数据。`state.readerScroll`保存进入文章前的列表位置。手机样式集中在theme.css的“Phone”段。

## T042 · 报头（已由T043替换为细明体字标）

`.nameplate`内为`.brand`（内联SVG `<use href="#wordmark">`）、`.brand-sections`与`.edition-block`（`#edition-date`为大号日＋年月＋星期，`#edition-updated`）。尺寸只改`--wordmark-height`，红色部分是`.wordmark-light`（默认`--accent`）。重新生成字标：`python scripts/build_wordmark.py`，把输出的symbol替换进index.html。

## T043 · 标题字体、扉页与胶片边

- 字标symbol `wordmark`（横）与`wordmark-vertical`（竖）由`python scripts/build_wordmark.py`输出，字体子集由`scripts/build_title_font.py --source NotoSerifTC[wght].ttf`生成；扉页/栏目用字若要增减，先改该脚本的`CHARS`再重建。
- 扉页`#cover`：`.cover-leaf`（正反两面`.cover-front/.cover-back`）、`.cover-veil`、`.cover-film`、`.cover-title`、`.cover-note`、`.cover-turn`。翻页时长与曲线在`.cover-leaf` transition，结束移除时间在index.html脚本（1600ms）。想关闭扉页：删除`#cover`和紧随的脚本即可，其他代码不依赖它。
- 胶片边`.film-edge`与`#film-edge-print`（app.js nav()按日期写帧号）。

## T051 · 片头动画「門中見日」

- 扉页的`.cover-title`现为一个viewBox为`32 0 936 4486`的SVG：四个`<use class="cover-char" style="--i:N">`各用`#cover-char-N`裁剪出一个字，按`--i`错开逐帧闪入；`.cover-glow`椭圆是間中日的红晕；`.cover-grain`是放映灯＋颗粒层。（T053应用户要求去掉了光泽扫过。）
- 字标红色改为继承变量：`.wordmark-light{fill:var(--wordmark-light,var(--accent))}`。要单独改某处字标的红色，在该`<svg>`或其祖先上设`--wordmark-light`（选择器无法进入`<use>`影子树）。`.brand:hover`据此变墨色。
- 报头`.film-edge`走片456px（24个齿孔）后停下，`.brand .wordmark`再点亮；`html.cover-open`期间暂停，扉页移除后才播放。
- 所有时长/延迟集中在theme.css「Opening sequence」与「Masthead」两段keyframes；`prefers-reduced-motion`全部关闭。去掉片头只需删这两段CSS，扉页本身照常。
- T052：≤700px时扉页宽为黄金分割61.8%（`.cover-leaf{right:38.2%}`、`.cover-veil{left:61.8%}`），标题高`min(50vh,104vw)`；桌面与平板仍为半屏。改比例只需同时改这两个值。
