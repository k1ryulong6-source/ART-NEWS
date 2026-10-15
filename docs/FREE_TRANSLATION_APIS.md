> T055最新账号额度（2026-10-15，用户AI Studio读数）：RPM4/15、TPM9.9k/250k、RPD98/500，即每分钟15请求／250000输入tokens、每日500请求上限。网站原自设100/日已调450/日，给其他调用和统计差异留余量；不是新增付费预算。保持免费项目及全部用量历史，长文拆分/重试均耗请求，不能等同每日450篇。下方旧100为历史试跑配置。

# AI翻译API选择 · 2026-10-15更新（3.5当前方案；其他价格为10月14日核对）

最新需求：AI按全文语境直译全部现存及新增外文正文，不做第二轮模型校对；离线机翻仅临时兜底。用户已明确选择Gemini免费额度，Google AI Studio可用；未授权付费，保持未绑定计费项目。

| 模型 | 标准输入/输出，每百万tokens美元 | 免费与适用性 |
| --- | --- | --- |
| Gemini 2.5 Flash-Lite | 0.10 / 0.40 | 旧方案。实际API 404明确不再向新用户开放；ListModels可见不等于可生成，新接入勿选。 |
| Gemini 3.1 Flash-Lite | 0.25 / 1.50 | 免费档可试；不因型号更新就默认升级，本轮没有翻译质量比较证据。 |
| Gemini 3.5 Flash-Lite | 0.30 / 2.50 | 当前方案。按Google实际404建议切换；官方Standard输入/输出Free of charge，实际成功生成1篇全文。未授权付费。 |
| DeepSeek-V4.1-Flash（请求名deepseek-flash） | 高峰缓存未命中0.30 / 1.20；非高峰0.15 / 0.60 | Google账号/地区不可用时的低价替代；不承诺长期免费。默认thinking须关闭，付费上限和接入待验收。 |

这是已核对服务的价格，不是所有模型的市场排名或真实调用证明。Gemini免费档资料可能用于改善产品；本项目只发送公开新闻原文，不发送个人收藏或凭据。

当前使用Gemini 3.5 Flash-Lite免费项目。旧2.5方案的月费估算不能套到3.5；3.5 Standard付费参考为每百万输入$0.30、输出（含thinking）$2.50，尚未授权付费。先观察完整24小时真实新增量、完整译文产量、请求/tokens、限流与积压，之后由用户决定是否付费及金额。早期失败请求没有完整usage，已知tokens不是完整账单。

## 免费项目一次性接入

1. 在支持地区/账号打开 https://aistudio.google.com/ 创建API key，选择**未绑定计费的Free Tier项目**。实际限频和配额在AI Studio核查，不为此步骤开启billing。
2. 打开 https://github.com/k1ryulong6-source/ART-NEWS/settings/secrets/actions/new ，Name填`GEMINI_API_KEY`，Secret粘贴key。不要发聊天、提交源码或放前端。
3. 保存后下次采集/备用调度自动执行；也可Actions → Automatic full-text translation → Run workflow即时验证。实际译文、status和Pages发布成功才算接入。

当前连接读取Secrets public-key端点返回403“Resource not accessible by integration”，不能代设置；这是仓库主人一次操作，不是每日工作。放入已绑定billing的项目key仍可能收费：程序无法凭key可靠识别计费状态，本地免费模式不保证这种key零收费。因此当前仅提供未计费项目接入，付费模式关闭。

程序最多450生成请求/太平洋日、40请求/批、480秒/批、15秒间隔，是项目上限，**不是**Google承诺配额。推理前把本批请求预留提交Git，正常结束释放未用量；硬中断保留预留至当日结束。请求前本地计数，未知usage另标，不伪称完整账单；429及服务错误保存全局退避并自动续跑。额度不足不删除待译稿，不自动升级或付费。免费档无法保证当天清空全部欠账。

## 官方依据

2026-10-15 JST：用户已确认配置密钥，最新费用选择为先观察免费项目24小时，再由用户决定是否付费及金额。未授权开启结算或自动切换付费服务。试运行起点见data/ai-free-trial-baseline.json，实际接通须核查API输出和发布，不以Secrets存在或Actions绿色代替。

- 价格：https://ai.google.dev/gemini-api/docs/pricing
- 实际配额/太平洋日重置：https://ai.google.dev/gemini-api/docs/rate-limits
- 型号：https://ai.google.dev/gemini-api/docs/models
- 生命周期：https://ai.google.dev/gemini-api/docs/deprecations
- 地区：https://ai.google.dev/gemini-api/docs/available-regions
- DeepSeek价格/高峰规则：https://api-docs.deepseek.com/quick_start/pricing
- GitHub Models于2026-07-30完全退役：https://docs.github.com/en/github-models/prototyping-with-ai-models

Azure Translator F0每月200万字符、DeepL API Free每月50万字符、Google NMT每月前50万字符是专用机翻额度，不是全文语境AI配额，已不作为主路线。


## 实际接入证据 · 2026-10-15 JST

只读模型检查38611070685成功，key有效且ListModels列出2.5；有界实际生成38611670089返回404：旧型号不再向新用户开放，Google建议gemini-3.5-flash-lite。已改3.5（官方免费Standard，MINIMAL thinking），不绑定或启用结算。

有界实际验证38612425164用2次请求，1篇完整原文4102字符译文已保存并公开，另1篇JSON格式失败保留待译。当次返回可见2301输入/1577输出tokens；包括旧404在内的历史3个失败请求usage不完整，原计数保留。已补动态严格JSON schema，失败/截断响应有usage也记账，91Python+26JS通过。后续自动批38612766700已运行并推送接受单元断点；更多产量以最新status/live/ledger为准。

公开Pages38612903303 success；https://mujianrest.work/ 的1440/390实际中文全文默认、原文切换、真实3.5模型身份与巴别塔原文/独立中文参考均通过，无接口模拟或页面脚本错误。所有原文/旧AI模型身份保留。免费观察从首篇成功2026-10-15 03:07:54 JST计，复盘已改到10月16日同一时刻。不要重复要求用户添加已有效的GEMINI_API_KEY。

手动维护：check-gemini.yml只读模型目录（0生成请求）；verify-gemini.yml最多2次生成/120秒，推理前持久配额预留，原始错误仅保留限长脱敏信息。verify完成也触发Pages，避免GITHUB_TOKEN提交不触发后续push工作流导致译文未发布。
