# 免费翻译API选项 · 2026-10-14核对

用户询问免费API，本轮仅核对官方额度和用途，没有开户、提交密钥、启用API、切换翻译路线或自动付费。此前不另配API的选择仍保持。用户当前偏好是足够完成语境全文翻译且费用合适，不再要求第二轮模型校对。

| 服务 | 官方页面当前额度 | 对本项目的用途与边界 |
| --- | --- | --- |
| Gemini 2.5 Flash-Lite | 标准Free Tier输入/输出为Free of charge；限频、日配额和实际可用性按型号与账号 | 通用AI，可输入整篇语境和术语表，最接近当前翻译方式。免费档不保证能清空全部欠账或每天完成所有新增；部分账号地区可能不支持。 |
| Azure AI Translator F0 | 每月200万字符：标准翻译与自定义翻译训练额度合计 | 专用翻译服务，额度较大；与通用AI按整篇语境翻译不是同一种流程。 |
| DeepL API Free | 每月50万字符 | 专用翻译服务，确认是API Free而不是网页试用套餐；注册资格及文档限制另核验。 |
| Google Cloud Translation | NMT标准文本翻译每月前50万字符免费，以每月10美元credit体现 | 此额度不能套用于页面上的LLM Adaptive Translation价格。需Cloud项目/API密钥或服务账号，超额度有收费，不能把账单预算提醒当硬性停止。 |

官方证据：

- Gemini：https://ai.google.dev/gemini-api/docs/pricing 。已读gemini-2.5-flash-lite段，标准免费输入/输出，不把收费档每百万token单价误作免费配额。
- Azure：https://azure.microsoft.com/en-us/pricing/details/translator/ 。已读F0 Free标准翻译200万字符/月。
- DeepL：https://support.deepl.com/hc/en-us/articles/360021200939-DeepL-API-Free 。已读“up to 500,000 characters per month for free”；usage-limits中的50万字符文件大小限制不是月额度证据。
- Google：https://cloud.google.com/products/translate/pricing 。已读NMT前50万字符/月与10美元credit，LLM Adaptive段另收费。

若用户以后选择接入：先根据地区/账号可用性选实际免费档，服务端或GitHub Secrets保存密钥，设置可计量的请求上限、429退避与用完停止；禁止浏览器暴露密钥、默认开收费回退或跨档升级。需完整块、源hash及数字检查，按真实提供方/型号/模式标译文，不把专用翻译冒称已校译。现有原文和译稿缓存保留，不为换提供方重复翻译有效稿。
