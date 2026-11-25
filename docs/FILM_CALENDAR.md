# 日历的排期和来源

公开站 `/#calendar` 先选地区，再选活动。默认东京和电影。东京视图也收录日本全国院线上映日。流媒体汇总所有收录地区。适用地区以出处为准。

- 已有资讯库提供映画.com 日本上映和一部分流媒体日期、Diaphana 法国上映、BFI 影展、各场馆的海外展览及 World Photography Organisation 征集。展览目录提供日本展览的开闭展并链接站内正文，带「不感兴趣」的展览只在个人专区列出。
- 东京放映补充 Eurospace、Theatre Image Forum、新文芸坐和 Cinema Vera Shibuya 的逐场排片。日历使用官网公布的当地日期与时间，有官方购票链接时同时显示。
- 流媒体补充 Apple TV Press 电影数据、Disney+／Hulu 月排期、Criterion Channel 月度片单和 About Netflix 新闻稿。首次上映、现有电影进入片库与片单上线都以出处公布的日期精度列出。Netflix Tudum 另行显示自动采集受限状态。

同一展览关联到统一展览 ID。其余排期以规范化标题、日期、场馆与放映时刻比对。流媒体区分平台和已知适用地区。重复项保留来源，异时、异地、异地区或不同平台各自列出。月历标记明确的放映、开幕、闭展和截止日。仅公布月份的片单在本月分页中显示。

`config/film-calendar.json` 配置官方来源。`python scripts/collect_film_calendar.py` 更新 `data/film-calendar.json`，只读取源站公开数据。GitHub Actions 在东京 07:35、17:35 调度，随后发布资料与来源状态。采集失败时保留上次成功的记录。`/film-calendar.json` 可核对各来源的最近读取及逐条出处。
