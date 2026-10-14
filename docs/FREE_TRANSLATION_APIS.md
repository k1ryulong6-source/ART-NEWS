# AI翻译API选择 · 2026-10-14官方核对

最新需求：AI按全文语境直译全部现存及新增外文正文，不做第二轮模型校对；离线机翻仅临时兜底。用户已明确选择Gemini免费额度，Google AI Studio可用；未授权付费，保持未绑定计费项目。

| 模型 | 标准输入/输出，每百万tokens美元 | 免费与适用性 |
| --- | --- | --- |
| Gemini 2.5 Flash-Lite | 0.10 / 0.40 | 推荐起点；标准Free Tier输入/输出免费，未宣布停用日期。地区/账号和实际配额须验证。 |
| Gemini 3.1 Flash-Lite | 0.25 / 1.50 | 免费档可试；不因型号更新就默认升级，本轮没有翻译质量比较证据。 |
| Gemini 3.5 Flash-Lite | 0.30 / 2.50 | 免费档可试；付费高于2.5，暂不默认采用。 |
| DeepSeek-V4.1-Flash（请求名deepseek-flash） | 高峰缓存未命中0.30 / 1.20；非高峰0.15 / 0.60 | Google账号/地区不可用时的低价替代；不承诺长期免费。默认thinking须关闭，付费上限和接入待验收。 |

这是已核对服务的价格，不是所有模型的市场排名或真实调用证明。Gemini免费档资料可能用于改善产品；本项目只发送公开新闻原文，不发送个人收藏或凭据。

623条库存中外文待AI正文528篇/约215万原文字符。按30–60篇/天、约4千字符/篇粗估，Gemini 2.5 Flash-Lite基本文字费约5–15元/月，旧稿清理另需几元；JSON、长稿分块重复全文语境、重试和语言token差异会增加费用。尚无真实API账单，20元是建议起步预算，未获付费授权，也不保证足够。稳定日量需要连续记录，首次来源回补不能当日均。

## 免费项目一次性接入

1. 在支持地区/账号打开 https://aistudio.google.com/ 创建API key，选择**未绑定计费的Free Tier项目**。实际限频和配额在AI Studio核查，不为此步骤开启billing。
2. 打开 https://github.com/k1ryulong6-source/ART-NEWS/settings/secrets/actions/new ，Name填`GEMINI_API_KEY`，Secret粘贴key。不要发聊天、提交源码或放前端。
3. 保存后下次采集/备用调度自动执行；也可Actions → Automatic full-text translation → Run workflow即时验证。实际译文、status和Pages发布成功才算接入。

当前连接读取Secrets public-key端点返回403“Resource not accessible by integration”，不能代设置；这是仓库主人一次操作，不是每日工作。放入已绑定billing的项目key仍可能收费：程序无法凭key可靠识别计费状态，本地免费模式不保证这种key零收费。因此当前仅提供未计费项目接入，付费模式关闭。

程序最多100生成请求/太平洋日、40请求/批、480秒/批、15秒间隔，是项目上限，**不是**Google承诺配额。推理前把本批请求预留提交Git，正常结束释放未用量；硬中断保留预留至当日结束。请求前本地计数，未知usage另标，不伪称完整账单；429及服务错误保存全局退避并自动续跑。额度不足不删除待译稿，不自动升级或付费。免费档无法保证当天清空全部欠账。

## 官方依据

- 价格：https://ai.google.dev/gemini-api/docs/pricing
- 实际配额/太平洋日重置：https://ai.google.dev/gemini-api/docs/rate-limits
- 型号：https://ai.google.dev/gemini-api/docs/models
- 生命周期：https://ai.google.dev/gemini-api/docs/deprecations
- 地区：https://ai.google.dev/gemini-api/docs/available-regions
- DeepSeek价格/高峰规则：https://api-docs.deepseek.com/quick_start/pricing
- GitHub Models于2026-07-30完全退役：https://docs.github.com/en/github-models/prototyping-with-ai-models

Azure Translator F0每月200万字符、DeepL API Free每月50万字符、Google NMT每月前50万字符是专用机翻额度，不是全文语境AI配额，已不作为主路线。
