> T054（2026-10-15）：Gemini、临时机翻和会话队列统一优先公共默认首页主头条及电影／艺术／摄影栏首篇全文，已完成或冷却中的文章按原规则跳过。头条块之后才交错其他重要／及时新闻和旧稿；不会只优先标题或加开额度。backend/priority.py产出headline_order/slot，translation_batch统一选批；frontend/core.js的frontpageRows与backend/frontpage.py由精确顺序测试约束。公共偏好来自config/preferences.json。

# 后台自动采集、AI翻译与发布

网站：https://mujianrest.work/

最新分工：Codex负责后端/API/自动运行/重要新闻覆盖，Claude负责前端/文章排版。**AI全文直译为主，离线机翻仅临时兜底**，不依赖每日打开ChatGPT。

| 阶段 | 执行 | 证据 |
| --- | --- | --- |
| 采集 | refresh.yml，每2小时UTC15分附近 | 原文/图片/出处、逐源成功失败、实际新增量 |
| 核对 | 每次采集后遍历配置列表并检查重要新闻 | 多专栏缺条/部分故障/核心来源停滞/重要稿待译 |
| AI | autotranslate.yml，采集结束触发；每4小时UTC45分备用 | 全文语境直译、断点/配额/退避/真实模型与tokens |
| 临时兜底 | 同一任务AI之后执行离线M2M100 | 机翻身份明确，不冒称AI，不覆盖AI |
| 发布 | pages.yml，采集/翻译结束触发 | 最新安全快照，AI/机翻/待译原文分别标注 |
| 监测 | automation-health.yml，每6小时及任务完成 | 实际Actions链接/最近成功/AI配置与等待状态 |

GitHub尽力调度，可能排队和延迟，不承诺精确到点。采集/译稿导入/翻译共用数据写锁，checkout最新main；监测独立锁且不触发Pages，避免循环。覆盖页读取最新公开健康记录，workflow成功不等于AI已配置或产出。

## AI主路线

Gemini 3.5 Flash-Lite免费项目优先（旧2.5实际拒绝新用户），一次性Secrets设置、官方价格和账号边界见[FREE_TRANSLATION_APIS.md](FREE_TRANSLATION_APIS.md)。无密钥时needs_configuration/0篇，不生成伪API数据；费用未授权，付费关闭。

backend/ai_translation.py调用原生REST，无额外SDK，key只在header。整篇原文单元/术语表始终在上下文；长稿限制每次输出并保存断点，不永久跳过。顺序拼回全部段落，图片/出处/版权信息保持；仅程序块数/数字/源hash检查，不作第二轮模型校对。入库editorial_status=translated、review_model=null，优先记录返回modelVersion。

最多40生成请求/480秒/批、100请求/太平洋日，15秒间隔，账号实际配额可能更低。每批推理前把最多40请求的预留写入Git ledger并推送，正常结束释放未使用部分；硬中断留下保守预留至当天结束，不会在新runner清空重花配额。每个生成请求前本地记账，收到响应后记已知真实tokens，即使输出格式/完整性检查失败也记账；unknown_usage_requests区分无法取得usage的失败请求，不能拿可见tokens冒称完整账单。429/服务错误全局退避，日额度次日接续，不自动付费；损坏配额账本失败关闭，不能清空继续调用。data/ai-translation-progress保存通过单元，GitHub每分钟推送一次接受进度，临时DB中已完成副本也留完整断点以免中断后重调模型；硬中断最多可能丢最近未推送的一分钟，配额预留仍在。完整检查后才发布；源hash/原标题/摘录/术语规则变更使旧断点失效。

重要性/明确日期时效优先，每批留旧稿份额并交错处理。有效AI稿不因换模型重译，入库再核对source hash/原标题/已有AI，避免竞态覆盖。ChatGPT定时任务仅可选补充，last_run_time=null，无实际日均。

## 临时离线机翻

MIT M2M100 418M int8经CTranslate2 CPU执行，支持100语种，不调用推理API。config/automation.json固定revision与4文件SHA256，约499MB资源缓存，校验错误失败，不执行远程模型代码。上游 https://huggingface.co/facebook/m2m100_418M ，量化副本 https://huggingface.co/gn64/M2M100_418M_CTranslate2 。

每批40篇/60,000字符/900秒，逐单元断点、6小时错误退避，AI稿不覆盖。article_translation机器字段与editorial AI字段分开，机器稿仍在AI待译队列；阅读标自动机翻。worker出错后仍审核/保存已接受工作，7日Artifacts留存。

真实GitHub批次38538667521完成24篇/59,960字符/735.72秒，3篇检查失败保留原文/断点；Pages38540275326和38540316341自动发布成功。加本地5篇累计29有效机翻；现有AI全文44。这段为历史机翻验收；最新Gemini API接通与实际产量见本文件末尾和FREE_TRANSLATION_APIS.md。

## 重要新闻与实际产能

28来源，新增Guardian电影/艺术/摄影三专栏和Deadline电影专栏，实际取得80条正文（68完整/12仅来源公开部分），原543原文/44AI/198活动全部保持。多页面单页失败不丢成功页但保留故障；核对遍历全部配置RSS，重合URL去重。正文采集先重大未取正文，再留旧稿复核份额。

config/news-watch维护17核心来源；important-news-audit记录重要漏条、核心来源故障/超过6小时不成功、48小时重要稿、缺原文/待AI数。影展/欧洲电影奖/野生动物摄影大奖/机构行业变化等信号为可解释自动初判。当前名单零重要漏条不等于世界无遗漏；未接入媒体、滚动历史、非RSS未独立核验官方页仍有盲区。

collection-metrics从声明的启用时间开始统计实际新增，按source run去重，首次来源回补另记；发布时间/fetched_at/恢复旧快照不能当入库量。连续积累后才能调整API配额和预算，不用搭建日当日均。来源403和重点独立抽查缺口保留。

## 维护接口

- GeminiTranslator.translate(document,keys)返回selected outputs与真实usage；模型更换保持断点/配额/出处/完整块契约，不开放浏览器密钥。
- ai-translation-status和auto-translation-status分别核查实际产量；automation-health核查真实Actions，不能互相冒称。
- 必须从最新main恢复新DB：CULTURE_DESK_DB=runtime/new.db python scripts/import_snapshot.py；不得导出旧DB覆盖新采集。
- Claude接口见[CLAUDE_UI_HANDOFF.md](CLAUDE_UI_HANDOFF.md)，不会要求恢复iframe、删原文或把摘要当全文。


## Gemini真实接通 · 2026-10-15 JST

用户已配置有效key。2.5 Flash-Lite实际404不再向新用户开放，按提供方建议改3.5 Flash-Lite官方Free Tier，MINIMAL thinking；保持paid_activation=false，不增加100/太平洋日、40请求/480秒每批上限。旧配置错误产生的退避仅明确修复一次，全部历史请求/tokens/未知usage和预留记录保持。

验证38612425164：1篇完整全文成功（4102原文字符），1篇格式失败留待译；两次请求已知2301输入/1577输出tokens，历史3次失败usage缺失。已补严格动态JSON schema及失败输出usage记账，91Python+26JS通过。Pages38612903303和1440/390真实线上中文全文/原文切换/模型身份/巴别塔原文与中文参考通过；自动批38612766700已独立运行，接受单元按分钟推送。首次成功后完整24小时复盘再决定付费预算，不把首篇或任务已启动当作全量已译。
