# 给 Claude 的 UI 与美术改版交接

公开仓库：https://github.com/k1ryulong6-source/ART-NEWS

在线网站：https://k1ryulong6-source.github.io/ART-NEWS/

## 如何接手

把仓库链接和下面的任务说明发给 Claude，即可开始读代码与提出设计。Claude 的网页浏览／GitHub 连接是否可用，取决于你使用的客户端；单独一个链接不会自动授予推送权限。要直接提交改动，连接 Claude 的 GitHub 工具并授权此仓库，或用 Claude Code 在本地克隆仓库。仅能读网页的会话可交付补丁，再由有写权限的工具提交。

建议从最新 main 创建 claude-ui 分支，通过 PR 合并。main 有自动资讯更新和每日校译提交；提交前拉取最新代码，不强推、不用旧源码包覆盖整个仓库。各 AI 的聊天记忆与额度不共享，本文件与仓库才是交接依据。

先读 AGENTS.md、docs/HANDOFF.md、docs/PRODUCT.md、docs/DECISIONS.md、tasks.json。登记新的视觉任务，约定文件范围；T026 完成后再以实际 Git 与部署状态确认。

## 产品与改版目标

这是中文阅读为主的世界电影、艺术、摄影资讯网站，名称为“映间 / Culture Desk”。保留日本上映与展览专题，少量圈内动态，不收录器材评测。公开访问，静态版收藏保存在各浏览器。

本次请设计和实现 UI、美术、排版、配色、字形层级、导航与手机体验。可以替换原创占位插画和图标，改善卡片、日历与长文阅读；优先显示已有来源配图并保留出处。具体风格由用户与 Claude 决定，本交接不假设已确认风格。

所有标题默认中文；正文默认“中文”，阅读页可切换“原文”，同时显示原标题与本站保存的原文内容。中文标题校译与全文校译是两个独立状态，标题中文不等于正文完成。尚未全文校译的稿件必须明确显示“待校译”及原文入口，不显示旧 Google 逐句译文，不以外文段落填充中文页。原生中文稿直接显示正文。未核实作品译名注明暂译或保留原名。

## 实际结构与可改范围

这是原生 HTML/CSS/JavaScript，配 Python FastAPI 和 SQLite，不是 React/Vite 项目。

- frontend/index.html：页面容器、导航、弹窗、脚本入口。
- frontend/styles.css：全站样式、响应式与阅读排版。
- frontend/app.js：页面渲染与交互，视觉变化可在这里调整。
- frontend/favicon.svg：图标；新增美术资源须同步 scripts/build_static.py 的复制与单文件构建规则。
- frontend/core.js：日期、筛选、安全处理、译文状态、收藏导入、日历导出等公共逻辑。尽量保留行为，有功能改动时执行对应检查。
- frontend/data.js、dist/：构建产物，不手工编辑。用 python scripts/build_static.py 再生成。
- backend/、schema.sql、config/、data/、.github/workflows/：数据与自动更新链路。UI 任务不要顺带重写或删改；必要变化另建任务、解释原因。

继续支持 GitHub Pages 的 /ART-NEWS/ 路径、单文件预览与本地服务。图片外链失败时有清晰占位；不能用虚构艺术作品或虚构新闻配图冒充真实来源图片。

## 必须保留的行为

今日／探索／日历／收藏／设置、全球与日本筛选、原文语言筛选、搜索、完整校译筛选、全部资讯入口、来源开关、圈内动态比例、收藏状态、JSON 导入导出与 ICS 导出保持可用。保留 culture-desk-v1 浏览器存储键与版本，避免用户已有收藏丢失。

全部来源、稳定 content/event ID、原文 blocks、图片出处、消息状态、来源读取失败提示保持。活动用各自当地时区，未知日期／场馆／票价保持未知；新闻标题不能被当作新活动日期证据。

新闻每12小时更新；ChatGPT 每日东京时间约11:30翻译并二次对照，使用 data/translations/完整译稿与 data/headlines/标题稿。标题稿不设置 editorial_status=reviewed。不要删除这两条自动流程，也不要让新视觉依赖模型密钥。不要提交密码、实际收藏或运行数据库。

## 验证与交付

安装：python -m pip install -r requirements-dev.txt

检查：

```sh
python scripts/check_project.py
python -m unittest discover -s tests -v
node tests/core.test.js
node --check frontend/app.js
python scripts/audit_data.py --strict
python scripts/build_static.py
python -m http.server 8002 --directory dist
```

在 http://127.0.0.1:8002/ 检查1440px桌面与390px手机。至少验证五页无横向溢出，长中文标题可读，中文默认／原文切换／深链接刷新、待校译提示、图片失败、来源筛选、中文搜索、收藏刷新保留和日历导出。不要把仅做静态图或只编译通过当作功能验收。需要本地API时运行 python -m backend。

提交时提供桌面与手机截图、改动说明和实际检查结果；更新任务、HANDOFF 与必要的 DECISIONS。在PR中确认自动数据提交仍保留，合并后核对 GitHub Actions 与线上真实页面。

## 可直接发送给 Claude 的说明

> 请读取 https://github.com/k1ryulong6-source/ART-NEWS ，先看 AGENTS.md 和 docs/CLAUDE_UI_HANDOFF.md，再设计并实现这个文化资讯网站的 UI 和美术改版。重点改善视觉、排版、配图呈现、导航、日历与手机长文体验。标题和正文中文优先，阅读页可切换原文；保留采集、每日AI校译、全部来源、收藏和导出等现有功能。基于最新main建立claude-ui分支，完成实际浏览器验收并提交PR。需要我确定视觉方向时给我可比较的方案；若当前客户端没有GitHub写权限，请交付可应用的代码补丁并明确说明，别声称已发布。
