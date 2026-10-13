# 默认技术路线 v0.1

## 当前与建议

当前已经实现 `frontend/` 和 `backend/`：原生 HTML／CSS／JavaScript + FastAPI + SQLite。没有真实采集器、真实模型摘要或定时任务。

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
| GET `/api/content` | channel、kind、country、city、q、cursor 筛选 |
| GET `/api/events` | 当地日期区间、地区、活动类型筛选 |
| GET `/api/today` | 精选、开幕／上映、即将结束，限制圈内动态比例 |
| GET `/api/bookmarks` | 收藏与状态 |
| POST／PATCH／DELETE `/api/bookmarks` | 添加、改状态、移除收藏 |
| GET／PUT `/api/preferences` | 个人设置 |
| GET `/api/export` | 个人收藏和设置的可移植 JSON |

已实现 content、events、bookmarks、preferences、export，以及 `/api/health`、`/api/dataset`、`POST /api/import`。`/api/today` 尚未实现，精选使用前端 core.js；API 尚无分页。正式版本修改设置、采集与导出等接口需按实际部署限制访问，目前只监听本机。

小规模个人服务的异步路由执行短 SQLite 查询，避免当前受限环境中的后台线程唤醒问题。采集／模型调用将独立于请求路径；未来大规模数据操作应迁移到独立任务进程或异步数据层。

## 模型接口

下一阶段定义 `summarize(record) -> {summary_zh, suggested_tags, provider, model, generated_at}`。

提供一个无需账号的 NoOp 适配器和可配置的真实供应商适配器；模型供应商、模型名称、请求地址和密钥由环境配置，不写死在业务逻辑。支持结构化结果校验、超时、重试上限和每日处理预算。

给模型的原文视为资料，不作为系统指令。摘要的外部 URL 与关键日期必须回溯已有资料；模型输出不得直接覆盖已核实活动日期。处理失败保留原文链接和 pending 状态。

编写代码所用 AI 与应用内用于摘要的模型是两套独立能力。更换建设者不要求更换应用模型；关闭模型也应能阅读原始资讯。

## 配置与运行

个人设置初值来自 `config/preferences.json`；正式用户状态写本地数据目录或数据库。候选源来自 `config/sources.json`，未核实默认不启用。

T001 已提供依赖锁定与启动命令，仍待浏览器与 TCP 监听验收。T004 将提供手动采集命令。定时器由 T008 完成，在那之前不得写“每天自动更新”。数据目录、数据库、API 密钥与个人导出不进入 Git。
