> T063双接口（2026-10-15）：支持两个独立Gemini项目并行。原密钥GEMINI_API_KEY保留；第二个密钥在仓库Actions Secrets新增GEMINI_API_KEY_SECONDARY。同项目多密钥不增加额度，代码只能拦截完全相同的密钥。每路保护500/太平洋日、40请求/480秒/15秒间隔，未配第二路仍单路运行，未授权付费。

> T062调度优化（2026-10-15）：备用API改每半小时UTC05/35分；采集后触发保持。每批40请求/480秒、15秒间隔、免费500/太平洋日及503/429退避不变，GitHub定时可能延迟。离线4分钟兜底与API分开统计，不能把机翻完成1篇当作全链产量。

> T060（2026-10-15）：API按单元程序检查并保存合格结果；同次返回有坏段时，合格段不会丢失，失败段按原退避接续（完整文章语境不变），整篇组装检查也尽量只退回失败字段，不增加模型校对。新增numeric_literals提示保留字面数字，检查标准不放宽。备用Actions改每小时UTC45分，免费500/太平洋日、批40/480秒及15秒间隔不变；503/429的全局等待仍生效。

只读实况 /reports/operations.json（本地/api/operations；bootstrap.automation.operations）按发布时快照生成：API/历史会话/旧校译/原生中文/待AI/临时机翻/缺正文分别计数，部分公开正文另列；AI服务等待与Actions执行状态分开，失败与核心来源/地区缺口保留，账本请求/预留/token未知部分不当完整账单。观察未满24小时明确false，来源首次补库不当日均新闻量。报告本身不调用模型，也不是新的ChatGPT定时任务。

> 2026-10-15最新：只允许GitHub后台免费API翻译，禁止启动ChatGPT会话翻译/工作者。旧每日ChatGPT翻译任务已暂停。Actions在用户ChatGPT额度耗尽/离线时仍独立采集→Gemini→临时机翻→保存→发布；API自己的免费额度不足则保存断点和退避，不启用付费或会话替代。正文清理在抓取前按DOM组件执行；一次性旧稿清理工作流cleanup.yml接受纯删除并保留已有译文，完成后接续后台AI。

> T056地区/媒体双轴：config/editorial-regions.json定义领域地区关注等级与来源建设目标；sources.json的editorial_focus记录目标地区及独立international/local_specialist/discovery媒体权重。所有启用RSS仍每轮读取，按地区轮转后在地区内加权，正文优先头条/重大消息，再给发现渠道约20%、国际媒体约30%的新正文预算（紧急消息占满时让位），旧稿复查份额保留。报告位于/reports/regional-coverage.json；来源分配不是逐篇地点或作者国籍。39源配置须以实际采集成功和最新审计确认，完整率仍unknown。

> T055最终（2026-10-15）：用户要求不固定闲置50次，最终上限500/太平洋日，与用户AI Studio的RPD500对齐；每日余量不累计。下方450为临时方案。已用计数/预留不清零，15秒间隔、40请求/480秒批次及免费模式保持；若账号共享用量导致提前429，仍按提供方限流退避。

> T055最新配额（2026-10-15）：用户AI Studio显示RPM4/15、TPM9.9k/250k、RPD98/500。网站每日保护上限从100改450，给Google的500/日留余量；保留现有当天累计/预留，按剩余量申请批次。不启用付费，不更改15秒间隔、40请求/480秒批次。账号值可能变化，也可能被同项目其他调用共享；429仍自动退避。

> T054（2026-10-15）：Gemini、临时机翻和会话队列统一优先公共默认首页主头条及电影／艺术／摄影栏首篇全文，已完成或冷却中的文章按原规则跳过。头条块之后才交错其他重要／及时新闻和旧稿；不会只优先标题或加开额度。backend/priority.py产出headline_order/slot，translation_batch统一选批；frontend/core.js的frontpageRows与backend/frontpage.py由精确顺序测试约束。公共偏好来自config/preferences.json。

# 后台自动采集、AI翻译与发布

网站：https://mujianrest.work/

最新分工：Codex负责后端/API/自动运行/重要新闻覆盖，Claude负责前端/文章排版。**AI全文直译为主，离线机翻仅临时兜底**，不依赖每日打开ChatGPT。

| 阶段 | 执行 | 证据 |
| --- | --- | --- |
| 采集 | refresh.yml，每2小时UTC15分附近 | 原文/图片/出处、逐源成功失败、实际新增量 |
| 核对 | 每次采集后遍历配置列表并检查重要新闻 | 多专栏缺条/部分故障/核心来源停滞/重要稿待译 |
| AI | autotranslate.yml，采集结束触发；每半小时UTC05/35分备用 | 全文语境直译、断点/配额/退避/真实模型与tokens |
| 临时兜底 | 同一任务AI之后执行离线M2M100 | 机翻身份明确，不冒称AI，不覆盖AI |
| 发布 | pages.yml，采集/翻译结束触发 | 最新安全快照，AI/机翻/待译原文分别标注 |
| 监测 | automation-health.yml，每6小时及任务完成 | 实际Actions链接/最近成功/AI配置与等待状态 |

GitHub尽力调度，可能排队和延迟，不承诺精确到点。采集/译稿导入/翻译共用数据写锁，checkout最新main；监测独立锁且不触发Pages，避免循环。覆盖页读取最新公开健康记录，workflow成功不等于AI已配置或产出。

## AI主路线

Gemini 3.5 Flash-Lite免费项目优先（旧2.5实际拒绝新用户），一次性Secrets设置、官方价格和账号边界见[FREE_TRANSLATION_APIS.md](FREE_TRANSLATION_APIS.md)。无密钥时needs_configuration/0篇，不生成伪API数据；费用未授权，付费关闭。

backend/ai_translation.py调用原生REST，无额外SDK，key只在header。整篇原文单元/术语表始终在上下文；长稿限制每次输出并保存断点，不永久跳过。顺序拼回全部段落，图片/出处/版权信息保持；仅程序块数/数字/源hash检查，不作第二轮模型校对。入库editorial_status=translated、review_model=null，优先记录返回modelVersion。

最多40生成请求/480秒/批、500请求/太平洋日，15秒间隔，账号实际配额可能更低。每批推理前把最多40请求的预留写入Git ledger并推送，正常结束释放未使用部分；硬中断留下保守预留至当天结束，不会在新runner清空重花配额。每个生成请求前本地记账，收到响应后记已知真实tokens，即使输出格式/完整性检查失败也记账；unknown_usage_requests区分无法取得usage的失败请求，不能拿可见tokens冒称完整账单。429/服务错误全局退避，日额度次日接续，不自动付费；损坏配额账本失败关闭，不能清空继续调用。data/ai-translation-progress保存通过单元，GitHub每分钟推送一次接受进度，临时DB中已完成副本也留完整断点以免中断后重调模型；硬中断最多可能丢最近未推送的一分钟，配额预留仍在。完整检查后才发布；源hash/原标题/摘录/术语规则变更使旧断点失效。

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

## 双项目自动调度与配置

1. 原GEMINI_API_KEY不改。到 https://github.com/k1ryulong6-source/ART-NEWS/settings/secrets/actions/new 新建Name=GEMINI_API_KEY_SECONDARY，Secret填写另一个独立项目的Gemini密钥；不要放聊天/代码/前端，保持免费项目。
2. 部署本代码后，下一次autotranslate.yml会自动识别；也可在Actions → Automatic full-text translation → Run workflow启动。无需每天操作。
3. 两个线程按同一全量优先队列交错分配互斥ID；头条/重大/时效与旧稿份额保持。每路最多40请求/480秒并行执行，不能保证篇数翻倍。一路503/429/日额度不足，另一路继续；下一批健康接口可接续等待接口未完成的文章。文章检查失败保留原退避，不换接口无限重试。
4. 主账本data/ai-translation-ledger.json原样保留；第二路data/ai-translation-ledger-secondary.json单独计数/预留/退避，均在推理前提交。API调用不持Git锁，写断点/数据库及分钟级Git保存共用短锁；已有效稿不重复，原文变更保护保持。
5. data/ai-translation-status.json是合计报告，projects分别记录primary/secondary实际请求与完成量；data/ai-translation-projects保存每路最后实际结果。/reports/operations.json的api.projects、quota.projects、quota.combined为Claude可用接口；旧quota顶层字段仍只指primary，legacy_fields_project明确说明，不能把它当两路总量。未配置第二路不加总它的500额度；未知用量不会当零。
6. 当前key是否真正属于独立项目、实际免费额度多少需在各自AI Studio核实；配置存在与真实生成成功分开。程序不开户/付费/开计费，按服务端429继续退避。

T063用户追加授权：第二密钥已配置，要求本次重置前充分使用免费额度翻译。config.ai-translation.drain_until_quota_day=2026-10-15，实际配额日匹配、有待译且本批真正消耗请求且该路完成/到达批次上限/仅文章检查部分失败、该路日额度仍剩时才自动dispatch下一批；有采集等待则让路，由采集接续翻译。503/429仍退避，零请求/全量完成/日上限不循环；配额日过后自动恢复半小时常规计划，不永久提前耗光后续每日额度。实际生成、剩余量和预计篇数需由远端成功证据核实，不保证Google服务异常时耗尽。

## T069 · 临时服务错误恢复（2026-10-16）

503/500/502/504及临时网络错误按每个项目的持久连续失败次数，约1/2/4/8/16/30分钟递增并加0–15秒抖动（总上限30分钟）；Google Retry-After更长则照守，支持秒数与HTTP-date。成功HTTP响应后才复位连续服务错误，即使响应的译文未过程序检查；文章检查失败仍按原头条30分钟/普通6小时处理，不混为服务故障。

批内最多2次短故障重试，需要还有请求/日额度/足够时间预算；等待仍计入480秒窗口，并留出HTTP120秒超时预算。每一次重试都先消耗原请求预留，40/批及500/项目/太平洋日保持。持续错误退出保存断点，由原半小时计划接续；不保证Google服务异常时仍能耗尽额度。旧已记录等待保留，不猜测旧Retry-After来源、不清零或绕过现存限流。

/reports/operations.json的api新增service_retry_policy、inline_service_retries、service_failures；projects逐路给service_retry（连续次数、delay_seconds/server_retry_seconds/retry_after），区分已恢复/仍在等待与已发表译稿，不以Actions绿色表示服务已恢复。
