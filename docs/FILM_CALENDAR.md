# 日历的排期和来源

公开站 `/#calendar` 先选地区，再选活动。默认东京和电影。东京视图也收录日本全国院线上映日。流媒体汇总所有收录地区。适用地区以出处为准。

- 已有资讯库提供映画.com 日本上映和一部分流媒体日期、Diaphana 法国上映、BFI 影展、各场馆的海外展览及 World Photography Organisation 征集。展览目录提供日本展览的开闭展并链接站内正文，带「不感兴趣」的展览只在个人专区列出。
- 东京放映补充 Eurospace、Theatre Image Forum、新文芸坐和 Cinema Vera Shibuya 的逐场排片。日历使用官网公布的当地日期与时间，有官方购票链接时同时显示。
- 流媒体补充 Apple TV Press 电影数据、Disney+／Hulu 月排期、Criterion Channel 月度片单和 About Netflix 新闻稿。首次上映、现有电影进入片库与片单上线都以出处公布的日期精度列出。Netflix Tudum 另行显示自动采集受限状态。

同一展览关联到统一展览 ID。其余排期以规范化标题、日期、场馆与放映时刻比对。电影在同一天同一影院的同片场次共用一张海报，逐场显示当地时间和已有的购票入口。异地、异地区和跨平台排期各自显示。月历标记明确的放映、开幕、闭展和截止日；本月清单按天分组和分页，仅公布月份的片单列在末尾。

### 片名和海报

页面优先显示从公开豆瓣电影结果核实的中文片名，保留排期原题和相应的豆瓣入口。还没有可靠匹配时显示片方列明的原名，或排期原题。院线、影院和平台公开资料提供作品原名、制作年份与剧场海报；已确认同一作品时也能通过 Wikidata 的条目编号交叉核对豆瓣和 TMDB。电影节片单和多片联合场保留节目名。没有可用海报时以文字展示，海报地址和出处在 `/film-calendar.json` 的 `films` 中。

排期采集之后，自动读入已保存的 `data/film-metadata.json`，按片名、场馆排期出处和适用年份复用核实结果。优先核对当前和即将放映的片，给以往排期留出一部分核对名额。查到资料或重试都记录实际结果，站上保留全部活动 ID。可用 `python scripts/collect_film_calendar.py --metadata-only` 独立补资料。

`config/film-calendar.json` 配置官方来源。`python scripts/collect_film_calendar.py` 更新 `data/film-calendar.json`，只读取源站公开数据。GitHub Actions 在东京 07:35、17:35 调度，随后发布资料与来源状态。采集失败时保留上次成功的记录。`/film-calendar.json` 可核对各来源的最近读取及逐条出处。
