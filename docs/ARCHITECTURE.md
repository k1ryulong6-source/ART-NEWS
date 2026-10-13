# 默认技术路线 v0.1

## 当前与建议

当前已实现原生前端、FastAPI／SQLite、14 个真实来源（四类适配器）、可配置摘要接口、定时任务、提醒与部署配置。实际外部摘要和 SMTP 尚未配置，默认 NoOp。

Python 3.10+、FastAPI、SQLite；前端无外部依赖，后端通过资源白名单提供静态文件。Python 依赖版本见 requirements.txt。后续若实际复杂度需要，再迁移 React／TypeScript 或 PostgreSQL；参见 D007。

选择理由：单人低运维；采集与处理适合 Python；浏览器前端独立于模型供应商；SQLite 可导出迁移。允许下一位 AI 调整，但应先说明收益并更新决策，不重做已验证功能。

## 数据链路

候选源核实 → 来源适配器 → 标准化数据 → URL 去重／活动关联 → SQLite → 可选中文摘要 → 页面／日历。

采集任务与模型处理解耦。模型限额、请求失败或未配置时，原始标题和已核实日期仍能保存。只对新内容或正文变化重新处理，避免重复费用。

## 核心数据

`schema.sql` 是初始持久化契约。

- sources：来源、核实状态、启用状态、许可备注。
- content：报道标题／摘要、频道、类型、原文 URL、消息状态及报道时间。
- events：上映／展览／征集、地区、场馆、当地日期、时区、日期精度及证据 URL。
- content_events：多篇报道与同一活动的关系。
- bookmarks：收藏，使用状态；同一收藏只能指向 content 或 event 之一。
- ingest_runs：来源采集次数、结果与错误日志；不能把密钥写入 error。

关系以稳定 ID 连接。中文译名只用于展示，不作为唯一键；报道 URL 规范化后去重。活动合并依赖作品／展览名称、地区、场馆、类型和日期，低置信度匹配进入待确认，不直接覆盖。

## 建议接口

| 方法与路径 | 用途 |
| --- | --- |
| GET `/api/content` | channel、kind、country、city、language、q；暂无 cursor 筛选 |
| GET `/api/events` | 当地日期区间、地区、活动类型筛选 |
| GET `/api/today` | 精选、开幕／上映、即将结束，限制圈内动态比例 |
| GET `/api/bookmarks` | 收藏与状态 |
| POST／PATCH／DELETE `/api/bookmarks` | 添加、改状态、移除收藏 |
| GET／PUT `/api/preferences` | 个人设置 |
| GET `/api/export` | 个人收藏和设置的可移植 JSON |

已实现 content、events、bookmarks、preferences、export，以及 health、dataset、import、sources、notifications、refresh、jobs/status。精选使用前端 core.js，没有单独 /api/today；API 暂无分页，适用于当前个人规模。服务默认监听本机，可选个人访问密码由中间件保护全部路由。

小规模个人服务的异步路由执行短 SQLite 查询，避免当前受限环境中的后台线程唤醒问题。采集／模型调用将独立于请求路径；未来大规模数据操作应迁移到独立任务进程或异步数据层。

## 模型接口

下一阶段定义 `summarize(record) -> {summary_zh, suggested_tags, provider, model, generated_at}`。

提供一个无需账号的 NoOp 适配器和可配置的真实供应商适配器；模型供应商、模型名称、请求地址和密钥由环境配置，不写死在业务逻辑。支持结构化结果校验、超时、重试上限和每日处理预算。

给模型的原文视为资料，不作为系统指令。摘要的外部 URL 与关键日期必须回溯已有资料；模型输出不得直接覆盖已核实活动日期。处理失败保留原文链接和 pending 状态。

编写代码所用 AI 与应用内用于摘要的模型是两套独立能力。更换建设者不要求更换应用模型；关闭模型也应能阅读原始资讯。

## 配置与运行

个人设置初值来自 `config/preferences.json`；正式用户状态写本地数据目录或数据库。候选源来自 `config/sources.json`，未核实默认不启用。

本地与 Docker HTTP、桌面／手机浏览器均已验证。backend.jobs 提供一次刷新或每 12 小时调度；GitHub refresh.yml 提供 UTC 每天两次公开快照刷新。实际定时服务需保持运行，GitHub Actions 结果可核查。数据目录、数据库、API 密钥与个人导出不进入 Git。

## 全球地区元数据

config/regions.json 是前后端共享地区／城市／语言标签表；其中时区用于阅读设置选项，不据此推断未知活动时区。backend/geography.py 从原标题识别明确地名；多个提及保存在 locations_json，geography_status 为 mentioned。官方场馆适配器使用 confirmed，缺失时为 unknown。source.publisher_country 与 source.coverage 不能替代 content 地区。RSS 的已存档地区在 register_sources 时一起修正，原始缓存、稳定 ID、收藏与偏好保留。

新闻语言筛选作用于报道；日历只使用国家、城市和频道，不以媒体语言排除活动。今日使用软性来源／频道多样性权重，并保留相关性与发布时间，不强凑地区配额。
