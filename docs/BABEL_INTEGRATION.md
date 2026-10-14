# 幕间休息 × 巴别塔 · 文章联动 v1

用户已授权联动公开仓库ART-NEWS与babel；目的在巴别塔读新闻原文、查词和保存生词。无需翻译API密钥，无每日手动导出/复制，不共享个人学习数据回新闻站。巴别塔代码/接收协议： https://github.com/k1ryulong6-source/babel/blob/main/docs/INTERMISSION_IMPORT.md 。

## 一键入口与稳定接口

文章页最小新增「巴别塔阅读 ↗」入口，始终导入原文，已有中文全文另为参考，和当前中文/原文tab无关。无正文/示例不显示可用入口；原文仍在本站完整阅览。链接形如`https://k1ryulong6-source.github.io/babel/?intermission=live-ID#reading`，仅传稳定ID，不把长文或个人记录塞URL，手机、新标签和复制链接可用。

CultureCore.babelReaderUrl(row)为Claude可用的可选接口，CultureUI v1保持。data-ui=babel-import为展示入口。config/integrations.json配置目标，禁用enabled即可隐藏入口；迁移域名时同时同步接收端固定baseURL，不接受任意URL抓取参数。

backend/babel_export.article_payload/export_articles每次Pages构建从最新完整live档案生成`dist/integrations/babel/ID.json`与index.json。不是先前队列36条精选，全部已保存正文均导出；未取得正文没有伪造JSON。无需提交生成的dist到仓库，采集/翻译结束自动发布新接口。单文件离线预览的入口仍打开在线巴别塔/公开接口；首次跨项目导入需联网。

协议：protocol=intermission-article-v1、schema_version=1，id/source_hash/title/language/text/blocks/source/news_url/access/collected_at/translation_zh。原文title与text不取中文标题/摘要。blocks保留段落、标题、引用、列表与原图说明/版权人；来源公开部分access=public-partial。中文参考kind为machine/ai-direct/ai-reviewed，实际model保留，缺全文译稿则null。不得把源页面HTML或iframe导入。

本地服务同协议GET `/api/integrations/babel/ID`及`/integrations/babel/ID.json`。只按严格live-ID读取公开content字段，不导出收藏、校稿过程、密钥或用户存档。非法ID/无正文404，HTTP GET不会触发采集/模型调用。

## 巴别塔行为

原生英语/日语/西语先载对应词库与存档再打开原文，点词、生词本、选句和复习沿用现有系统。法/葡/中文可原文阅读，真实data-lang优先分派；暂无本地词典/复习明确标，已有AI可由用户主动查词，导入不自动调用AI或标搭配。日语已有词典中文释义是否齐全仍由巴别塔原词库/用户已导入日中词典决定，不新增伪中文解释。

严格保存成功后才打开。源ID+原文hash作为副本ID，相同版本复用，笔记/词汇标注不覆盖；原文变化另存新版本。保存到原Store/IndexedDB/可选云端，随巴别塔现有存档导出。成功URL带article本机副本ID，刷新先开本机副本，源站不可达也能继续读已保存原文；跨设备无副本时读取当前公开版本。

长稿不套原手动导入3万字符限制；接收限2MB JSON/100万文本字符/5000块，超限报错不截摘要。404/接口加载/存储失败均可重试，不假称成功。PWA资源已纳入manifest，修改接收脚本需运行tools/update_manifest.py，保护已有词库/课程/个人数据。

## 本轮验证

- Python导出与原文/中文身份/公开部分/隐私/长稿；JS入口及7个协议/去重/长稿/错误/链接测试。
- 1440/390px真实两个站点入口，六语种完整文本、配图、原文标题语种一致；英电影/日写真/西película实际点词，日写真实际存入词本。
- 相同稿重复只一副本，注释与marks保持；刷新不再请求源端，32,380字符长稿原样；404不造假。
- 法语在日语界面使用法语提示，不调用日语词典；源端断网仍可读本机副本；存储失败有重试且无假导入。

发布已验收：ART-NEWS b994269 CI38554022279/Pages38554022552 success，babel ab63fb4 Pages38553447792 success。真实公开1440/390六语种/词典/词本/去重/刷新/长稿/404通过，API639篇HTTP200。旧PWA缓存从20261012.1823升级到20261014.1059，个人文章保持。AI主链T038仍等待用户方便时配置Gemini免费密钥，不影响本文联动。
