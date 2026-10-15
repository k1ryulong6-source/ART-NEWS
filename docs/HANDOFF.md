> T061已验收（2026-10-15）：3e940d5已上线，CI38696435261/Pages38696435200 success；132Python+27JS、stdlib构建/项目检查。生产1440/390px主头条与三栏ID精确匹配后台/队列，旧10月8日/9月24日占位稿退出；新头条为Sandra Hüller/Rose访谈、Gary Waddell讣告、Tammy Nguyen威尼斯双年展、野生动物摄影奖，均已有有效Gemini中文全文（34/12/15/47块），公开原文hash/中原文块数及原文/Babel验证通过，无额外重译。正常主头条72h、缺新最多7天，所有栏目不回灌7天外旧库；每2h减1分、重要性/紧急度及既定降权/来源平衡，发布时间未知仅明确2天内活动后备，不以抓取时间伪造新鲜度/随机凑版。Claude视觉不改。已保留并发采集新增5条，最新900资讯/661待AI/841输入；API新批38696435355仍pending、旧批38696221501 active，未称已完成。T028继续doing；API独立接续、免费500/日不变、禁止会话翻译工作者。

> T061（2026-10-15）：修正头版选稿，视觉/文章排版不改。重要新闻直接参与；主头条优先72小时内，缺新最多回退7天，栏目也不从7天外旧库填充。重要性高24/中8，P0加12/P1加6/P3减12，每2小时减1分，非日本普通展览原惩罚保留；后续同源减6促进媒体平衡。未知发布时间仅在没有同栏近期报道且有明确2天内活动时后备，不用抓取/翻译时间伪造新鲜度。兴趣筛选留在原selectToday辅助功能，不再截断公共头条。无随机轮换，历史/日历全部保留。Python/JS选稿与API头条优先ID同步，待生产验收。

> T060已验收：f0f0107，CI38695109390/Pages38695109367 success；127Python+27JS、stdlib构建及项目检查通过。/reports/operations.json生产核对通过，明确180AI=115API+65其他AI、656待AI、215/500请求及503等待/验证失败/覆盖缺口，观察不足24h；API有效单元保留及小时备用已部署，只GitHub后台API，无会话翻译。当前自动批38694943268独立执行，遵守503原退避，不把执行中的本批算产量。T028仍doing。用户头条问题已定位并列T061 todo：主头条先兴趣候选再重要性且无时效衰减/驻留限制，摄影栏目后备池会回灌旧库；主头条10月8日、摄影首篇9月24日。本轮未改选稿或Claude视觉，下一步修正并保持前后端/翻译头条ID一致。

> T060进行中（2026-10-15）：仅GitHub免费API；上一批38690039638已实际发布7篇后遇503，等待至07:08UTC，累计Gemini115篇/180AI全文、656有正文待AI/10缺正文。修复同请求单段失败丢弃其他合格单元，保留缓存只重试失败字段；数字提示增强但程序标准不放松；每小时UTC45备用，500/日免费及原节流保持。新增/reports/operations.json、本地/api/operations及bootstrap.automation.operations，分开API/旧AI/机翻/失败/配额/来源缺口和真实未满24h观察；尚待远端发布验证。

> T059已验收（2026-10-15）：77bfaec已上线，CI38690039734/Pages38690039775/38690067708 success；42篇生产JSON原文hash/块数及已有中文模型/块数均与清理结果一致，桌面1440/手机390头条/原文/巴别塔回归通过。只后台Gemini免费API，不再调用会话翻译模型；旧每日会话翻译任务已暂停。API38690039638当前执行中，不把尚未发布的本批计作产量；上批38685372309真实11篇，累计108篇Gemini。已发布173AI=141直接+32旧校译，49原生中文正文，663待AI（207有有效机翻），10缺正文，895资讯。T028仍doing，API独立接续；不要恢复会话5.6分工或称全量已清空。

> T059清理实绩：42篇178块8946字符已处理，保留9AI/14机翻及7匹配旧pack，无模型翻译调用；GitHub38689796131仅28成功/14 Artnet403，工作区公开请求补齐14（data/article-cleanup-supplement.json），不能把GitHub绿色等同全部成功。严格审计0错误、全量pack模拟0新导入/0invalid；不改变895资讯/173AI身份。最新主链只后台免费API，会话任务已暂停，禁止5.6分工；config/translation.json旧会话字段不再执行，保留原JSON以免API断点指纹无谓失效。最终公开发布/API实绩待补。

> T059进行中（2026-10-15）：用户澄清只运行后台免费API，禁止会话模型翻译；旧每日ChatGPT翻译任务已暂停，不恢复5.6/Luna分工。6名5.6工作者实际触及usage limit；21篇有效新稿已分两批提交，另2篇后台API先完成未重复导入、1篇数字不合格留待API。T028仍doing。后端结构化去除订阅/广告/相关文章组件，现存正文清理仅允许逐块完全一致的纯删除子序列并映射已有译文，模型/人工身份保持；未知差异保留旧稿，不调用模型检查。真实运行与数量待验收补证。

> T057当前（2026-10-15 JST）：按用户精确命名建立「一种关注」来源单元，ID=a-kind-of-attention。首批人工精选Artishock、ArtThrob、TAKE on Art、ZUM、ART AFRICA，已有真实RSS采集记录；不是新增5个RSS，总数仍39启用/30 RSS。config/attention-units.json记录推荐理由/专长/关注范围。独立约10%新正文保护名额在现有20%发现预算内，头条/重大消息先行，空缺回流，另给其他发现源留位；500免费请求上限不改。公开/reports/attention-units.json及/reports/attention-units/a-kind-of-attention.json、本地/api/attention-units对应接口、bootstrap.coverage.attention_units均已实现，Claude负责前端设计。113Python+26JS、纯stdlib构建/项目检查通过；真实库存干选60名额中16个单元来源，未发网络/模型请求。构建单元5媒体/68资料/37正文，低频发布时间与抓取时间、故障和缓存分别呈现，不冒称全译。已上线b7285c0：CI38670550982/Pages38670550944 success；公开索引和单元JSON一致，名称精确、5来源success、68资料/37正文/3有效AI全文，实际字段核对通过。生产1440/390px头条排序/原文/巴别塔回归无脚本错误或溢出。T057 done；这里只实现后端单元/抓取保护名额与展示接口，页面呈现由Claude接续，不冒称前端已出现新栏目。

> T056已验收（2026-10-15 JST）：领域地区创作关注×独立媒体权重/国际渠道已上线，最终规则f9670c0；CI38668140741/Pages38668140811 success，107Python+26JS。实际采集38667702336 success：11新RSS全部成功，149首次补库＋4既有源新增，库存887/198活动，启用39源=30 RSS+9官方。29 RSS的504条范围内列表全入库，AMP仍失败/BFI官方故障不隐瞒；全球完整率unknown。149新稿56有正文、93待后续正文预算轮转，勿冒称全量全文完成；T028欠账仍doing。生产报告39独立媒体分数/14项重点国家领域来源缺口已验证，1440/390px头条排序/原文/巴别塔正常，另新ARTnews JAPAN正文实测可读。监测队列误报修复55c5aa8，实际issues=[]。采集已自动启动AI38668063512，407de60有真实新检查点；不要中断、重复译或覆盖它，费用500/日免费保护不改。权重是人工编辑初值，不能当全球客观流量占比或艺术家国籍判断；来源矩阵只是明确分配，不是各国覆盖证明。

> T056最新（2026-10-15 JST）：用户要求按电影/艺术/摄影分别给地区创作关注等级，并独立给每源国际影响/本地专业/新作者发现权重。日本艺术/摄影为重点，未列国家默认发现；强国际媒体的报道不受总部地区创作等级限制，薄弱本地媒体地区通过跨地区渠道补位，逐国缺口明确。所有RSS每轮读取，先地区再媒体轮转；有限新正文预算约20%发现、约30%国际媒体，头条/重大消息先行且不受地区压低。新增11个实际RSS与逐源公开正文探测均成功：ART iT/ARTnews JAPAN、ArtAsiaPacific、Canvas、Artishock、ZUM、Blind、ArtThrob、TAKE、Africanah、Lenscratch；配置39启用源（30 RSS+9官方），149条首次列表候选，不冒称是当天新增。Africanah/TAKE等低频源的旧日期保留，失效/跨领域/多年未更候选不启用。102Python+26JS、构建/项目检查已通过，50fe0bf已推送，CI38667640980/Pages38667640817 success；生产/reports/regional-coverage.json已验证39源/14项缺口，1440/390px主头条排序、原文切换和巴别塔入口通过，无脚本错误/溢出。真实刷新38667702336已派发，等待旧AI/机翻数据写锁后执行。发现health把新配置引起的pending取消误报translation:failed，已加旧实际运行识别及4项测试（真实失败仍报警）；55c5aa8已推送，CI38667920489与实际监测38667920369 success，真实API确认running/healthy而不误报被替代的队列失败。又补单篇已知报道涉及地优先于媒体总部、未知不推断的分配测试，107Python通过；采集最终证据待补。不要覆盖自动批次新译文；不改Claude视觉/原文ID/API500免费上限。

> T055最终（2026-10-15 JST）：用户认为固定留50次会浪费每日不滚存额度，并要求工作流实际执行。最终每日保护上限500，与用户账号RPD500对齐；RPM15/TPM250000，仍每15秒最多1请求、每批40请求/480秒、免费模式且不自动付费。历史requests/tokens/预留全部保留，429继续退避。下方450是本轮临时设置，100是更早试跑；均被本条取代。最终配置ded64bb已推送，CI38666287639/Pages38666287642均success。自动批38665966593自01:32:31 UTC已实际生成；4ff47c3持久化4请求及3篇栏目头条的译文单元，本地100→104/剩36预留；主头条一次ai_paragraph_not_translated仍待重试，不能算4篇全部完成。当前批checkout初版450，但每批40不受差异影响；后续批从main取最终500。T055配置/启动验收done；本批最终产量和发布仍须查看任务结束后的真实报告，不中断它。覆盖实数见COVERAGE.md新首段（19 RSS＋9官方页，18 RSS355条已入库、1失败、全球比例未知）。

> T055最新（2026-10-15 JST）：用户提供账号RPM4/15、TPM9.9k/250k、RPD98/500。原100/太平洋日是网站自设限制，不是Google免费总量；现改450/日保护上限，预留50次余量。保持free-project-only、paid_activation=false、15秒间隔、40请求/480秒批次及头条全文先译，不清空现有用量或预留。下方100为历史；当天无需等午夜重置即可使用剩余额度，最终执行取决于自动任务排队和真实提供方限制。验证/发布证据待补。

> T054最新（2026-10-15 JST）：以后先译公共首页主头条，再译电影／艺术／摄影各栏首篇的全文；已完成有效AI稿跳过，之后按重要性／时效与旧稿份额交错，缺正文／失败退避不变。Gemini、离线兜底、ChatGPT队列共用translation_batch；不是只译标题，不提高100请求/太平洋日上限或启用付费。前端原选稿提取为CultureCore.frontpageRows，backend/frontpage.py按默认公共偏好镜像；不改Claude视觉，未来改选稿需同步两端与精确ID顺序测试。94Python＋26JS、静态构建、项目和严格资料审计通过（0错误，2来源失败保留）；已上线697da4a：CI38663178104/Pages38663178008均success；生产mujianrest.work桌面1440/手机390的主头条与三栏首篇ID精确匹配，原文切换/巴别塔入口无错误。T054 done；既有自动批次不被中断，新代码从后续批次选稿时执行，未加开生成请求。下方API产量为历史记录，请以最新状态文件为准。

> T038最新实际接通（2026-10-15 JST）：key有效；2.5实际404拒绝新用户（即使ListModels可见），已按Google建议改3.5 Flash-Lite官方免费档，MINIMAL thinking，不开付费。验证38612425164真实2请求成功1篇4102字符全文/另1格式失败；Pages38612903303 success，公开1440/390中文全文默认/原文/真实模型/巴别塔原文+中文参考验证通过。动态严格JSON及失败响应token记账已补，91Python+26JS通过。自动批38612766700正在运行并持久化接受断点；T038继续doing直到该独立批次结束及最终发布验收，T028全量欠账仍doing。24小时复盘已从首篇成功03:07:54 JST算至10月16日同一时间，基线已更新；不要重复要key、恢复2.5、沿用旧月费估算或覆盖Claude界面。
>
> 覆盖评估：28来源为12电影/11艺术/11摄影（跨频道重叠），18英语/3日语；成功对照18份RSS的359条全部入库，只属于这批列表，另1核对失败/9官方页范围未核实；全球重要资讯覆盖率unknown，不能用28来源或RSS100%宣称无遗漏。具体缺口见COVERAGE.md。来源扩展必须实际核验，非日本普通展览仍低优先级。

> T038接入实际阻塞（2026-10-15 JST）：用户已配置GEMINI_API_KEY，不要再重复要求添加密钥。首轮38605781397的真实请求返回ai_http_404，0篇Gemini译文，源状态data/ai-translation-status.json为configuration_error；下一步需安全核查账号可用模型/API版本并修复，保持免费项目/不启用付费。已收到配置与域名成功均不代表AI试运行成功；24小时复盘必须报告真实0产量及此错误，机翻兜底单独计数。

> T049已完成（2026-10-15 JST）：https://mujianrest.work/ 已上线并强制HTTPS，根域/www证书approved，旧GitHub URL与文章hash自动跳转；PR#12合并10c6782，CI38610234915/Pages38610235002 success。Babel7976620兼容已发布；生产1440/390英日原文/词典/导入/笔记marks刷新/旧链接通过，689篇API。早先“等待DNS/Pages”记录为历史，详见CUSTOM_DOMAIN.md末尾。原免费API试运行计费政策和T038/T028未完成状态保持，不能用域名成功冒称AI调用成功。

> T049最新：Porkbun五条DNS已正确，Babel7976620 Pages38609603860已success；主站迁移PR#12 CI已通过。Pages cname写入403，等待主人在ART-NEWS/settings/pages保存mujianrest.work后合并PR/验证HTTPS。

> 2026-10-15 JST当前T049：用户已在Porkbun购买mujianrest.work，授权迁移幕间休息；巴别塔地址保持。迁移代码和验证见CUSTOM_DOMAIN.md，需先发布接收端双接口，再确认DNS/Pages后合并生产者迁移。未就绪不能冒称新域已上线；不覆盖Claude主题或自动采集新数据。

> 当前工作（2026-10-14，T038）：用户分工为Claude做前端/文章排版，Codex做后端/API/自动运行/重要新闻覆盖。免费或低价语境AI API为主，机翻仅临时兜底，覆盖之前“不另配API”的选择。Gemini 2.5 Flash-Lite接入代码已准备，真实调用须GEMINI_API_KEY；本次GitHub Secrets管理API为403，需仓库主人一次性设置。费用尚未授权，不自动开启付费。详细当前流程见AUTONOMOUS_WORKFLOW.md，当前API证据见FREE_TRANSLATION_APIS.md。不要根据下方历史日志恢复iframe、旧只读标题或旧型号/不接API规则。

> 2026-10-15 JST补充：用户确认已配置GEMINI_API_KEY，要求先按免费额度观察24小时，再决定是否付费及预算；没有付费授权。手动验证38605781397已排队，当前不能把密钥配置等同于实际AI完成。data/ai-free-trial-baseline.json保存本次起点（44既有AI全文、596有正文待AI、695总资讯及采集计数），24小时后按实际API全文、临时机翻、入库/首次补库、待译增减、限流/失败与真实tokens分别复盘。一次性复盘任务已创建；实际调用与发布证据另行追加。

# 当前交接记录 · v0.17

更新时间：2026-10-14 JST。建设者：Codex。

最新要求：重要性与时效优先，用户取消第二轮模型校对，最新要求按性价比选择足够完成全文翻译的模型，当前按用户费用反馈默认GPT-5.6（gpt-5.6-sol），不默认Luna或自动升级较贵模型，不另配API。新稿直接AI翻译＋程序段落/数字/来源检查，不能称校译；旧32校译保留。当前44已翻译（直接12＋旧校译32，6篇公开部分），49原生中文，442待译，2正文缺失。当前537资料／198活动／26来源，T028仍doing。T029增加四级及依据、每批旧稿份额和真实快模型译稿；每日任务原日程保持。

## 仓库与授权

仓库：https://github.com/k1ryulong6-source/ART-NEWS 。用户保留公开仓库，并已明确授权公开网页。v0.5 新增四个官方来源，434 条资料／158 项活动；真实重复采集新来源 inserted=0。源级历史保留；本轮 GitHub 刷新 24 源成功，Asian Movie Pulse 与 BFI 返回 HTTP 403，分别保留原 8 条资料与 101 场次及最后成功时间，没有绕过限制。

API 密钥、密码、SMTP 配置、个人数据库与收藏不进入 Git。data/live.json 和 frontend/data.js 包含公开来源元数据、已采集正文、机器译文及处理次数账本。

## 实际完成（早期功能清单；最新计数与界面以页首及末尾验收记录为准）

- 今日／探索／日历／收藏／设置；频道、地区、城市、搜索、圈内动态开关与配额。
- 内容／活动详情、关注对象排序、收藏状态、JSON 导出恢复、ICS 日历导出。
- SQLite 存储，真实／示例分离，旧库迁移、首次公开快照恢复。
- 26 个真实来源；434 条资讯与资料、158 项活动（日本 28、英国 109、印度 3、南非 6、法国 4、韩国 4、全球征集 4）。
- 新增 101 场伦敦影展放映、4 个全球摄影征集、4 个法国上映、4 个韩国展期；准确时刻、报名、资格、费用及冲突提示。
- 全球默认、18 国／城市／语言筛选、日本专题；标题多地区提及与媒体发布地分离，未知地点不猜测。
- 已保存来源核实档案 data/source-research.json、覆盖缺口 docs/COVERAGE.md；质量脚本检查重复、日期、器材与活动引用。
- 旧资料标记并保留在探索；今日排除 30 天外新闻及无日期证据的资料。MAP 周一闭馆／周二免费说明已核对。
- 今日兼顾频道与来源；城市优先为可选；活动倒计时、站内与邮件过滤按各活动当地日期。
- URL 去重，内容变化识别，稳定活动 ID，日期变更保持收藏引用。
- 来源开关、手动异步更新、跨进程刷新锁、读取失败日志与最后成功时间。
- 可替换 NoOp／OpenAI-compatible 摘要接口、输出校验、缓存和跨 CI 的每日请求上限。
- 12 小时后台调度、收藏活动开始／闭展提醒、已读标记、可选 SMTP 投递。
- 静态版、单文件版、本地服务、可选个人访问密码、Docker／Compose 部署配置。
- GitHub CI、定时公开快照更新、任务和 PR 模板。

## 已实际验证

- 33 项 Python 与 14 项 JavaScript 检查通过。
- Uvicorn 实际监听与 HTTP 请求通过。
- 本轮新增四个官方来源两轮真实读取成功；重复采集 inserted=0。原 22 源本地验证见 v0.4 记录；GitHub 的 Asian Movie Pulse 403 不隐瞒。
- Chromium 桌面 1440px／手机 390px 五个页面无横向溢出、无脚本错误。
- 浏览器筛选、收藏刷新保存、状态修改、JSON 下载／上传、ICS 下载、来源开关、提醒入口与手动更新完成。
- v0.4 浏览器：法语 20 条、葡语 44 条、旧资料标签、班加罗尔展览与票价／闭馆说明、开普敦闭展状态；五个页面无溢出与脚本错误。
- v0.5 桌面／手机浏览器：摄影征集 4 项、学生组时刻冲突、报名入口、101 场伦敦放映、法国上映与首尔展期；收藏与 UTC ICS 下载验证通过。
- 单文件静态版在 390px 验证全球默认、切换伦敦优先、阅读时区、设置／收藏刷新保持、JSON 导出和五页布局。
- 本环境浏览器禁止 file URL；单文件的脚本与样式内联，可直接打开；v0.6 来源图片是外链，需要联网，离线有明确占位。
- v0.2 时 Docker 镜像成功构建；首次发现 COPY 目录权限导致非 root 用户不可读，已添加只读权限修复。修复后容器 HTTP 200，成功返回 160 条真实资讯与 28 项活动。

## 尚需配置／持续扩充

- SUMMARY_API_KEY 尚未配置。真实外部模型调用未启用；结构化日期摘要与来源摘录可读；v0.6 公共机器翻译已实际启用，独立于生成式摘要。
- SMTP 未配置。没有实际发送邮件；站内提醒已实现，模拟发送与去重已测试。
- 来源访问限制：Asian Movie Pulse 与 BFI 在 GitHub 返回 HTTP 403，旧资料与来源状态保留，后续按来源状态复核。
- T018 本轮已补法国上映、伦敦影展、摄影征集与韩国展期；仍是持续覆盖，不能声称所有地区、所有电影或场馆已收齐。

## 运行与检查

python3 scripts/build_static.py：生成 dist。
python3 -m backend：本地服务，默认 http://127.0.0.1:8000。
python3 -m backend.jobs：完整刷新。
python3 -m backend.jobs --schedule --interval-hours 12：后台更新。
python3 scripts/export_snapshot.py：仅导出公开资讯。
python3 scripts/import_snapshot.py：首次恢复公开快照，并恢复当天处理预算。

检查：python3 scripts/audit_data.py --output data/quality.json --strict；python3 scripts/check_project.py；python3 -m unittest discover -s tests -v；node tests/core.test.js；node --check frontend/app.js。

## 下一位 AI

先读 AGENTS.md、本文件、DECISIONS.md、tasks.json；查看实际 Git 状态与 Actions 结果。现有页面与采集链路不需要重写。按 T013／T014 处理用户选择启用的外部服务，T015／T018 已验收；继续按 COVERAGE 扩充全球非英语来源和官方展期。

模型密钥只放运行环境／GitHub Secrets；不要让用户把密钥提交到公开仓库。日期／票价不由模型改写。每次交付更新任务、交接、决策和实际检查结果。


## GitHub 验证与领取入口

- CI：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407746912
- 实际自动刷新：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407982361
- 摘要配置：https://github.com/k1ryulong6-source/ART-NEWS/issues/1
- 托管选择：https://github.com/k1ryulong6-source/ART-NEWS/issues/2
- 已完成全球更新：https://github.com/k1ryulong6-source/ART-NEWS/issues/3
- 已完成全球来源补全：https://github.com/k1ryulong6-source/ART-NEWS/issues/4

网站：https://k1ryulong6-source.github.io/ART-NEWS/

首次公开部署成功：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38389258730。公开 URL 返回 HTTP 200；在线 Chromium 1440px／390px 五页无溢出和脚本错误，摄影时刻冲突、报名入口、101 场放映、地区筛选、收藏和 UTC ICS 下载通过。GitHub 每 12 小时自动刷新，刷新完成后自动重新发布。

T018 本轮资料任务：https://github.com/k1ryulong6-source/ART-NEWS/issues/5 。

## T019 · 同域名离线缓存冲突

用户确认网址显示 Selah；已复现根应用 Service Worker 拦截 `/ART-NEWS/`。全新浏览器验收漏掉已安装其他 PWA 的情形。用户已明确授权修改 Selah；私有源码 23d9830 修复根导航回退，发布 e8b1592，部署成功：https://github.com/k1ryulong6-source/k1ryulong6-source.github.io/actions/runs/38393132033。同一保留旧 Worker 的生产浏览器升级前复现、更新后正确打开映间，存储标记保留，390px／1440px 五页通过，根站仍离线可打开。已验收 T019；当前浏览器旧 Worker 如未升级，点击页面“更新 Selah”再打开资讯。详见 PAGES_TROUBLESHOOTING.md。

## T020 · 原文摘录、译文与配图

已完成采集、页面、公开发布和在线验收。当前 434 条资料／158 活动，306 张来源配图、299 条原文摘录、384 个机器翻译标题、249 个机器翻译摘录（另 50 条中文）。实际公共翻译 633 次请求，0 失败；重复翻译 0 新请求。图片只保存来源 URL，不镜像报道图片。原文摘录最多 280 字符加省略号／55 单词；短摘录、机器译文与全文入口明确区分。

31 Python／13 JS 检查通过；静态版与本地服务 1440px／390px 五页、真正加载来源图片、中文标题／译文、原文文本对照、全文链接、故障图回退、中文搜索通过。原有 101 场放映、4 征集、时刻冲突和 UTC ICS 再验通过。翻译不改事件日期、票价或收藏；预算与缓存跨快照恢复。

公开机器翻译配置为 TRANSLATION_PROVIDER=google-public，可关闭；每日最多 1000 请求，固定 3 个线程。端点可能变动／受限，失败不冒称已翻译，缓存保留。生成式 AI 摘要 T013 仍待账号；不应因已有公共译文而声称已启用付费模型。后续不要恢复只有标题的旧快照或用原始 1200 字符处理摘录作为公开全文。

T020 GitHub 检查 44 项通过：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407746912；实际自动刷新：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407982361；刷新后发布：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38398252913。GitHub 本轮新增 23 条日本上映资料摘录与译文，翻译 0 失败；保留 306 张图，当前 322 原文摘录、384 翻译标题、272 翻译摘录。两项补读页面失败保留此前内容；Asian Movie Pulse／BFI 403 仍如实记录。实际公开 URL 1440px／390px 源图真正加载、译文与原文、全文入口、失败图回退及五页通过。

## T021 · 站内原文，全部来源保留

用户明确要求原文在本站直接阅读，并补充所有来源保留、不能筛掉别的。已实现专门原文页，点击标题进入默认原文视图、中文摘要切换、活动信息、返回、收藏与直达路由。全部 434 个内容 ID、26 个来源及全部来源启用状态经逐项比较保持。当前响应头检查：211 页未禁止嵌入、223 页明确限制；限制不导致删除、禁用或筛掉记录。网络未确认的页仍可由用户浏览器尝试；明确限制的页保留摘录和地址，提示原因而不伪称全文成功。

原文窗口直接请求来源网站，本站不获取／镜像／代理文章正文，也不修改来源 frame-ancestors／X-Frame-Options。嵌入窗口限制来源脚本改变本站顶层地址；原文收藏不重新创建窗口。BFI 原文地址保留 context_id，稳定规范 ID 不改；8 个 RapaduraCast Patreon 原始链接保留且核实附加域名，不绕过订阅。每次刷新检查最多 20 页，过七天复核；不能将检查未禁止误称全部实际全文成功。

33 Python／14 JS 检查通过。实际 Chromium 1440px／390px 在本站读取 IMA 原网页，原文内容存在且留在本站；Film Stage、ART AFRICA、Cinéfilos 英／西文页面也实际可读。收藏保持窗口且刷新持久、原文直达链接刷新、中文切换、受限页面不删资料、探索全部 434 记录验证通过。已完成公开发布与实际在线原页验收。

T021 最新公开验证：原有 434 IDs 全保留，并合并自动刷新，当前 441 条资料／160 活动、26 来源。213 页响应头未阻止嵌入，228 页由来源限制；不将前者数量冒称所有页实际全文通过。47 项 CI 成功：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407746912。实际刷新：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38407982361；原页检查新增 2 available／5 blocked，资料不删。刷新后部署成功：https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38408100107。真实公开 URL 的 1440px／390px 原页、收藏不重建窗口、刷新、中文切换、受限内容保留、全部 441 探索记录，以及 Film Stage／ART AFRICA／Cinéfilos 原页再次通过。


## T022 · v0.8 来源正文直接阅读

用户明确拒绝嵌入，要求抓取保存原文。新增 backend/articles.py：来源特定选择器＋Trafilatura，安全重定向域名与结构化内容块。本站转义排版，不执行原站 HTML，不使用 iframe。保存段落、图片／图注、链接、作者、原始出处与时间；source ID/content ID/events 和 enabled 状态都与上一版完全一致。

本次批量对全部 441 条实际 GET。427 collected、13 partial（ARTnews 订阅标记的公开部分）、1 no_body（Artforum 2023 科尔比·张伯伦谈乔什·克莱恩，页面只返回标题作者）。50 条 Artforum 中包含杂志目录，目录保持自身页面内容，不补造整本杂志。BFI 的 78 个报道页各有不同正文 hash，对应 109 项场次／英国活动；MMCA 4 个展览介绍各自独立。

正文翻译240次实际调用，10条完成、1条部分，未完成块保持原文。累计当日翻译请求931次，账本随快照保存。每轮新增正文60条，翻译120次，失败两天重试，已采集七天复核；共享默认每天1000次上限。翻译停用／失败不会阻止原文阅读。

本地验收：python scripts/check_project.py；python -m unittest discover -s tests -v（39项）；node tests/core.test.js（15项）；node --check frontend/app.js；严格资料审计0错误、1个已有摄影征集时刻冲突提醒。Chromium 1440／390px 实测 Variety、ARTnews、IMA、ART AFRICA、BFI、MMCA、Artforum 的存储正文显示，全部 iframe 数为0；阻断来源网络仍可读保存的正文；中文全文、收藏不重建正文、刷新深链保存、缺正文记录保留、441条探索可见均通过。

所有公开部署与实际线上验证已通过。不要在未验证时声称全部来源／全部文章均有完整正文或全文译文。


T022 自动更新与新增资料：GitHub refresh 38428321826 成功，新增21条资讯与3项活动，441条旧ID和已保存的440条正文全部保持。新增正文16 collected、3 partial，2条Artnet在GitHub返回403；同一公开原文地址在当前正常采集环境补读成功（4218／9042字符），没有切换隐藏端点、剥除响应规则或解除登录。最新快照462条、163活动：445 collected、16 partial、1 no_body。正文翻译完成11条，累计当日共享调用1000次，已停止新请求，下一预算日继续。

实际发布验收：CI 38428245662（39 Python＋15 JS）通过；首轮公开部署38428245750通过；自动更新后部署38428538871通过。公开网址在1440／390px重复验证七个来源的保存正文、iframe=0、原站网络阻断仍可读、译文、收藏、刷新、探索462条、全部26来源保持，均通过。最终两条Artnet补读后快照发布与实际线上核验也已完成。


T022 最终完成：代码538ec99，自动快照c9f764c，补读快照7b36281。最终CI [38428982448](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38428982448) 与部署 [38428982544](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38428982544) 成功；自动更新 [38428321826](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38428321826) 成功。直接读取已发布 data.js 核对462条、26来源、445 collected／16 partial／1 no_body，两个Artnet补读正文都存在。公开手机／桌面重新验收全部通过，原文不依赖来源网页请求，iframe=0，无页面脚本错误。

运行与待补：按 docs/OPERATIONS.md 安装依赖并运行；正文采集与翻译已进入定时流程。唯一未取得正文为 Artforum https://www.artforum.com.cn/print/202304/14499，原站仅提供标题和作者。16条ARTnews只保留公开部分；11条非中文正文已完成机器译文，其余待每日共享账本重置后分段继续。当前请求账本达到1000次上限，不扩大额度、不丢弃原文。更多地区来源与官方日期缺口继续见 COVERAGE，未配置的生成式摘要／SMTP并不阻止正文阅读。


## T023 · v0.9 全文语境AI校译

用户明确选择AI全文语境翻译并校对。新增editorial.py、术语表、draft/review两请求、段落与数字校验、approved状态、并发hash保护及独立editorial_usage账本。前端只显示已reviewed校译，旧Google译文与标题退出默认展示；默认全部来源仍在，新增“AI校译”主动入口。原文／已收录活动与所有ID保持。

本次会话实际为4篇西／日／英／法原文制作中文稿并逐段对照：Cinéfilos《边境》、IMA铃木崇“もののをかし”展、ART AFRICA的Brandon Gercara展、Fisheye的Julie Peiffer报道。保留暂译说明、原名、原文数字、图像、时间和票价；不得称人工译者审核。provider=session-ai:context-review-v1，非外部模型调用，APIusage未虚增。

本地检查：44 Python＋16 JS=60项通过，项目检查／严格审计0错误通过。真实Chromium1440／390px：4稿原文/校译切换、译名说明、AI来源标注、旧机翻不显示、主动筛选4稿后返回全部462条、全部26来源保持，均通过，无横向溢出与页面错误。当前运行环境无EDITORIAL_API_KEY；GitHub密钥列表GET返回403，不能读取或新设模型密钥。用户服务名称问题已提出，可继续无凭据的建设，但自动API校译必须等配置。

自动校译配置与真实模型端到端验证是剩余工作：管理员在仓库Actions secrets添加EDITORIAL_API_KEY，按账户选BASE_URL/MODEL/REVIEW_MODEL，详见OPERATIONS。当前只测试了模拟模型契约和真实会话样稿，不声称外部API实际执行。公开发布验收已完成，模型API配置单独留为T024。


T023实际发布证据：代码c570808；[CI38433869071](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38433869071) 60项检查通过；[部署38433869177](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38433869177) 成功；公开站1440／390px实测4份校译、说明、来源标注、旧Google隐藏及全部来源保持通过。

真实GitHub更新 [38434030648](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38434030648) 继续正常采集原文，新增12条至474条，所有旧ID和4份校译保留。translations明确not_configured、reviewed=0、reason=EDITORIAL_API_KEY_missing；没有回退Google、没有付费API调用、editorial_usage为空。自动再发布 [38434258959](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38434258959) 已成功。自动校译模型配置与真实请求留为T024 blocked，不掩盖缺口。


最终公开474条版本在1440／390px再次通过4稿原文/校译切换、AI来源说明、旧机翻隐藏、主动筛选后返回全部、原文保持验收。T023已完成软件与实际样稿；T024为明确的凭据依赖阻塞。管理员配置MODEL/BASE_URL/REVIEW_MODEL及EDITORIAL_API_KEY后，运行一次Refresh并核查真实模型结果再报告启用。不要要求用户重新确认公开访问或AI校译方式。


## T025 · 每日ChatGPT直接校译路线建设中

用户要求每天由ChatGPT直接代译，转为定时任务＋已连接GitHub，不要求配置额外网站模型API。GitHub get_repo真实只读成功，push权限确认；automations.peek无重复任务。准备data/translation-input逐篇完整源块、data/translation-queue.json（跨频道／来源与旧稿份额）、docs/DAILY_TRANSLATION.md和data/translations译稿格式。新增import_packs源hash／标题／段落／数字／校对检查，模型不可用也能独立导入。

新增Publish daily AI translations工作流，分享文化资料写锁，验证后提交快照并自动Pages；refresh也导入既有译稿、重新生成队列。幂等导入避免重复覆盖；陈旧译稿不覆盖新原文，无源码／密码输入要求。当前任务还待实际提交发布、每日任务创建与验证，勿伪称已经每天运行。


T025实际证据：f907c45提供桥接＋一篇真实会话校译（Steve McQueen《66–76–26》展）。47Python＋16JS检查最初通过；新增无API任务模式验证后48Python＋16JS。导入工作流38441724744成功，bot158e92e更新快照和pending队列；部署38441784624成功。未调用模型API，5份校译均实际在站可读。

GitHubApp实际读取repo和DAILY_TRANSLATION成功；通过同一连接create_file写入DAILY_TRANSLATION_STATUS.md，提交bc9e860成功，验证定时任务所需连接可读写。automations.create与update均确认success、is_enabled=true，IANA DTSTART;TZID=Asia/Tokyo:20261014T113000、FREQ=DAILY、flexible_schedule。任务id仅保存在忽略的runtime/daily-automation.json，不写公开仓库。没有提前调用run_now，因为用户要求每日重复，未要求立即触发该任务；此会话译稿验证与首次定时执行分开。

当前419条原非中文待译，新增实际稿后418，短队列36项，423份非中文原文输入保持。未来单次任务受额度／时长限制，不承诺一次完成全部；若工具连接或发布失败，保留原文／待译及已完成稿，并按真实任务结果报告。部署／网页和任务私下状态复核均已完成。


T025最终验收：a1e0114改为默认chatgpt-task模式，无EDITORIAL_API_KEY仍能正常走译稿导入；[CI38442648556](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38442648556) 64项通过；[部署38442648767](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38442648767) 成功。公开1440／390px再次验证5份校译、注释／AI身份、旧机翻隐藏、全部474条／26来源保持，无脚本错误。任务private peek确认is_enabled=true、IANA日程正确，last_run_time=null，因此不假称第一次定时任务已执行。无需继续索要API凭据；用户可在ChatGPT任务管理修改或暂停每日任务。


## T026 · 中文优先与Claude视觉交接

419份标题稿与正文校译独立保存，构建验证原标题一致与批准状态，陈旧稿不套用；所有474条资讯与163项活动已有中文标题。默认中文阅读、原标题／正文原文切换、待译正文无外文填充、原有5份完整校译、26来源与收藏保持。新标题队列加入每日任务文档；新增稿短暂待标题校译，不能承诺全部未来稿已译。

Claude改版指南提供真实原生HTML/CSS/JS结构、文件范围、必须保留的功能与工作流、分支PR协作、移动／桌面验收与可复制指令。没有联系Claude或给它授予本会话工具权限。本地50项Python＋17项JavaScript通过，严格审计0错误／1项已有时刻冲突提示。Chromium 1440／390px验证全部中文标题、5份中文正文默认与原文标题/正文切换、深链刷新、待译正文不显示外文、收藏原文DOM保持及刷新保存、中文搜索、五页无溢出和脚本错误。每日任务prompt已更新标题优先补齐要求，日程与启用状态保持；已完成GitHub部署与公开站验收，见下条。


T026最终验收：实现提交0c64d14，[CI38447900904](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38447900904)（67项）与[Pages38447900995](https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38447900995)均成功。真实公开URL在1440／390px再次通过474条／163活动全部中文标题、5份校译正文中文默认、原文标题和正文切换、深链刷新、待译不掺外文、收藏保持、中文搜索与五页布局，无脚本错误。每日任务更新成功并保持enabled=true、Asia/Tokyo原日程，未声称已首次定时执行。T026完成；下一步按CLAUDE_UI_HANDOFF另开视觉任务，不覆盖自动数据提交。


## T027 · 全量队列、真实漏采证据与本轮27篇校译

以最新已发布快照独立重建runtime/full-coverage-20261014.db。本轮实测17 RSS有34条不在库存，已补采；BFI又取得17新条目和35活动。数据从474/163增至525/198，旧ID、正文与5份旧校译全部保持，新稿正文已采集。第一次本地误用旧测试库的导出未提交或发布，已从Git恢复并重建独立库；不可再用旧runtime/culture-desk.db导出本次资料。

本轮批次27份真实会话译稿已逐块读、译、二次对照，导入器0invalid、0stale。总32已校译，其中4为来源公开部分，49原生中文可读，442待校译，2正文未取得。全量分页15份覆盖每个待译原文，短名单不是全量。数据源、语种、是否上首页或旧稿不能成为永久排除理由；T028未全完成不能写done。

backend/coverage记录逐源原始RSS条目、排除原因、库内/缺条、范围、失败和前后列表重叠；官方配置页完整性标未知。独立官方抽查发现Bristol分展日历及美国摄影展覆盖缺口。公开#coverage提供进度、逐源证据、地区分布和判断方法，不给无分母的全球完整率。refresh改2小时并每次核对，translations继续更新全量分页；ChatGPT每日任务仅prompt加入全量遍历与持续清理，原日程保持。自然数值单位转换通过Decimal等值核对，保留日期/票价/编号。

本地54Python＋17JS=71项通过，python -S构建通过（Pages无需第三方依赖）。Chromium 1440/390px全中文标题、跨源7份正文样本中文默认与原文切换/刷新/收藏、六页布局、覆盖统计/26来源/3官方抽查/展开无溢出和脚本错误通过。公开实现8de8ce8；CI38492448896（71项）、译稿工作流38492448852和Pages38492477550全部success，真实网站1440/390px再次通过。T027完成；T028全量翻译保持doing，尚有442条待译，不宣称目标已全部完成。接续时读最新队列与data/translations匹配当前hash，避免重复，先补新增也给旧稿份额，全部可取得正文逐篇校译；不要停在样稿数量，也不要以启用任务代替实际完成。

终校将Rosé报道中的Eva Chow保留原名，避免错误套用中文人名；对应译稿与快照已更正，计数保持32/442。后续模型校译同样应优先保留存疑专名而非猜译。


## T029 · 分级与便宜模型直接翻译

两个gpt-6-luna会话工作者实际分工四篇完整全文：温哥华观众奖、马勒70周年4K／Betty Blue重映、Getty Images破产报道、香奈儿与辛迪舍曼。不安排主模型二次校对；仅规范block index与程序检查，导入0stale/invalid。新稿quality_mode=direct-ai、review.approved=false、status=not_requested，editorial_status=translated、实际draft_model记录、review_model=null。旧校译保留，无外部模型API调用。部分工作者在用户取消校对前已自校，这不冒称主模型独立校对。

backend/priority与config/translation-priority定义重要/明确活动时效/新闻新鲜度及人工override；全量分页排序，next28优先＋8旧稿，标题与活动日期不混用。探索排序、筛选、级别与依据；覆盖进度直译/旧校译分开。每日任务最新prompt无二次校对，不改日程；未来子模型可用性如实报告。可选API也支持一调用直译并跳过已有有效译文，本次用户选择不接API。

运行数据仍用runtime/full-coverage-20261014.db，勿导出旧runtime/culture-desk.db。新增模型任务不假称用户已授权外部API凭据/费用。检查与发布证据待下条补记。

T029最终批次：两个gpt-6-luna会话工作者共完成12篇，其中大都会歌剧院访谈原文28,532字符、73块，未因长稿跳过。新增8篇为当前优先级前列稿件。12份pack的标题、source hash、块序、数字程序检查全部通过，实际模型记录为gpt-6-luna (session worker)、review_model=null；未调用外部模型API，未安排二轮模型校对。当前44已完成（32旧校译＋12直接AI），49原生中文，430待译，2正文缺失，6篇已完成稿仅来源公开部分；525资料／198活动／26来源不变。77项自动检查和桌面1440／手机390浏览器验收，全部12新译稿的中文默认／原文切换／直译标识／收藏、优先级筛选、六页布局无溢出或脚本错误通过。T028仍doing。

公开实现9f5c006；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38496208635、译稿工作流 https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38496208976、Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38496208634 全部success。真实公开网站1440/390px全部12篇直译稿、中文默认/原文切换、优先级筛选、收藏/刷新、六页无溢出与脚本错误通过。 T029已验收done；T028全量翻译仍doing。下批读取最新版next与全量分页，按优先级和旧稿份额继续，不重译匹配hash的有效稿，不重启已被用户取消的二轮模型校对。

T030：用户因费用明确改用GPT-5.6。AGENTS、每日任务提示及文档、配置指定gpt-5.6-sol；不可用保留待译，不自动切换型号。历史Luna12篇真实模型出处保持，尚未冒称5.6已产生新稿。每日定时任务last_run_time=null，不能报稳定每日翻译量；最新运营计数与覆盖缺口见docs/OPERATING_METRICS.md。

用户随后授权按性价比选足够翻译的模型，取代严格型号唯一限制；目前无实时价格表，默认5.6，不猜价格或称已比较所有模型。AGENTS、配置、每日任务提示已同步。T031同时处理图片/摘要不能进入阅读页：探索、今日精选、收藏统一三个区域的语义链接，独立收藏按钮不嵌在链接中。

T030型号偏好和任务提示已实际更新并验收；T031本地1440/390三个入口、图片失败示意回退、Enter、中键新标签、独立收藏/状态、收藏摘要及布局验收通过；公开发布仍需核验。没有新增翻译调用，库存/原文不变。

公开实现c5f066d；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38497204397 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38497204425 全部success。真实公开网站Chromium 1440/390：卡片及首页精选标题/摘要/图片同篇阅读、中文默认、坏图回退点击、键盘Enter、中键新标签、独立收藏/已看过状态、收藏摘要及布局无溢出或脚本错误通过。 T031已验收done。T028仍doing，430待译；本轮没有调用任何翻译模型。

T032执行：已合并自动采集bb7bebb，当前535/198/26；44已译（32旧校译＋12直译）/49原生中文/440待译/2缺正文。23明确非日本普通展览降至P3及首页扣分；1重要奖项展例外，5日本及21未知地区维持原规则。关联展览举办地优先，多地含JP不降级，不以语种/总部猜。全量分页440及8旧稿份额保持，data/live.json和全部原文未改。每日任务prompt更新成功、启用与日程不变；免费API官方方案已核实，没有实际模型API调用。62Python＋19JS=81项通过；公开发布需后续记录。T028仍doing。

公开实现a0503d4；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38503655258 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38503655263 全部success。真实公开网站Chromium 1440/390：535全量卡片、23非日本普通展览P3筛选/阅读页依据/原文、重要日本未知例外、首页推荐及覆盖说明、无溢出或脚本错误通过。 T032已验收done；T028仍doing，440待译。免费API只查官方页面，当前没有接入或调用；下一批按新的日本展览偏好与重要例外读取队列，全部旧/新原文继续。

T033旧报纸版：四主导航、偏好/覆盖页保留、更多筛选折叠、18条分页/全量搜索；源图加载占位标原创示意，读取正文原图不滤色。frontend/ui.js提供CultureUI v1（heading/meta/card/feature/pagination）；theme.css主题变量与响应式独立。index/app/构建及本地API资源同步；UI_CUSTOMIZATION与Claude交接文档重写为最新要求，data/原文/存储/任务日程不变。折叠栏在重绘时先同步open避免丢状态；skip-link hash不误回首页。62Python＋21JS=83检查通过，公开验证待记录。

公开实现ea933f5；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38512575722 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38512575751 全部success。真实公开网站Chromium1440/768/390完整遍历535条/30页、搜索/折叠筛选/三个阅读链接/中文与原文/收藏状态刷新、六页及长文无溢出或脚本错误、CultureUI v1及HTTP单文件无外部CSS/JS并可运行。 T033已验收done。修改接口已公开，主题/展示/状态/核心逻辑分层见docs/UI_CUSTOMIZATION.md，Claude接力说明指向该接口。T028仍doing，440待译，本次未调用翻译API或改日程。

T034：按公共艺术新闻查询/阅览平台定位重做报版，紧凑报头/竖线三栏/头条次条简讯，介绍隐藏与开发处理说明折叠；原文/译文/查询/分页/收藏/日历保留。CultureUI v1新增frontpage；公共浏览器包不再假定article_text必有，使用CultureCore.sourceText。原文档案data/live.json未改，536资料（最新自动新增1）、198活动、26源、44已译/49原生中文/441待译/2缺正文。T028仍doing。优化实测见BACKEND_OPTIMIZATION，65Python+23JS=88检查通过；尚需公开验收记录。

发布前已合并自动采集9a5ce82：最新537资料/198活动/26源，44已译/49原生中文/442待译/2缺正文；重新逐条核验全部537原文、译文及搜索文本等价。优化对比使用此前同一536条样本，不能把新增数据混成性能变化。

公开实现913ffb9；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38527095026 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38527094941 全部success（88检查）。真实公开网站Chromium1440/768/390：537条完整分页/全量旧稿搜索/折叠筛选/三处阅读入口/原文切换/收藏状态持久/六页长文无溢出或脚本错误；首条标题400px内、介绍不渲染、v1 frontpage接口和HTTP单文件运行通过。 T034已验收done。界面定位以公共艺术新闻检索和阅览为主，保留独立theme/UI接口；不要恢复私人介绍/黄纸卡片或冗长宣传。T028仍doing，442待译，本轮没有翻译API调用。


## T035 · 最新要求：报纸排印与待译原文直接刊载 · 2026-10-14

用户要求完全模仿报纸，待译正文可直接贴原文或机械翻译。本版选择本站已保存的原文，无额外API：默认阅读即完整显示已采集正文、图片和引用，标“原文·待译”与真实lang；现有中文全文优先，中文标题已有则保留，缺中文标题回退原标题。首页未译摘要/头条预览也直接用原文，避免只有待译占位。待译身份和全量翻译队列不变，缺正文与公开部分如实标注。

报头加大、四逻辑栏（头条跨两栏）、通栏标题/来源日期/双栏正文预览，阅读正文每8块组成短双栏版面，手机改为单栏，长稿不需读完整条竖栏再返回顶部。无来源配图的头条用文字排印，不以虚构艺术图填版；列表图片入口和独立收藏保持。CultureUI v1、theme.css与DOM事件接口继续开放。查阅/搜索/全部分页为公共平台主功能，不恢复个人介绍。

此次只修改展示规则，没有生成新译文、调用翻译API或改变采集/每日任务日程。T028保持doing。

T035本地验收：65Python＋24JS＝89项通过，python -S静态构建及数据审计0错误；Chromium1440/768/390全部537资料分页、全库搜索、三入口、收藏持久与六页无溢出/脚本错误通过。未译各语种、最长正文及公开部分样本默认逐块等于保存原文，lang与待译标记正确，缺正文保留状态；阅读双栏/手机单栏通过。每日任务prompt已实际同步原文直接刊载，启用及Asia/Tokyo日程不变。原文档案及译稿/队列未改。公开验收待下一条记录。

公开实现f433f80；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38529814910 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38529814722 均success。真实网站Chromium1440/768/390全部537条分页、全量搜索、三处阅读入口、收藏状态持久、六页与长文无溢出/脚本错误通过；未译各语种/最长正文/公开部分样本默认逐文本块精确匹配原文，真实lang、待译身份、正文缺失状态及桌面双栏/手机单栏通过。公开截图更新并保存阅读页截图。T035已验收done；T028仍doing，442待译，44已有中文译稿，无新增翻译/API调用。

T036：正式更名幕间休息。报头/标签页/描述/页脚、favicon、导入提示/API标题/邮件模板同步（未发送邮件）。使用自托管OFL字体三层：四字Ma Shan Zheng报头、Noto Serif SC宋体、Newsreader英文；来源/hash/覆盖/重建见frontend/fonts。主题--display/--serif/--sans保留AI修改入口，Pages不新增字体依赖，本地API白名单和单文件字体内嵌已同步。稳定项目路径/ID/收藏键不迁移，原文和译稿不变。每日任务prompt仅更名成功，启用与原日程保持。公开验收待追加。

T036本地验收：65Python＋24JS＝89检查通过（本地API三字库返回200），python -S静态构建与审计0错误。Chromium1440/768/390全537资料分页/查询/阅读/收藏持久及六页无溢出/脚本错误，三个Intermission字体均loaded；320px正常/阻断字体请求时均可读且无溢出。HTTP单文件内嵌三字库，loaded且无外部字体请求。站名/导出文件名/ICS日历名同步，收藏键和原始UID保持。公开验证待后续补记。

T036公开已验收done：实现d55db4d；CI https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38531313820 与Pages https://github.com/k1ryulong6-source/ART-NEWS/actions/runs/38531313853 均success。真实站点Chromium1440/768/390站名/标签页为幕间休息，三套自托管Intermission字体均loaded；全部537资料分页/查询/三阅读入口/中文和原文/收藏状态持久及六页长文无溢出/脚本错误。公开HTTP单文件字库内嵌加载成功；本地320px正常与字库失败回退均通过。实际公开截图已更新。T028仍doing，442待译/44已有中文译稿；本轮无新增译稿或外部API调用。字体职责及其他AI入口见UI_CUSTOMIZATION和frontend/fonts/README。

## T037 · 当前工作：黑体与无人值守主链

用户否定宋体，中文标题与正文改自托管Noto Sans SC黑体；书法报头、栏目和其他AI修改接口保持。采集结束触发GitHub后台离线机翻，再由工作流完成数据保存与Pages发布，不依赖当前聊天。免费模型/数字检查/断点/退避/健康记录见AUTONOMOUS_WORKFLOW.md。已有AI全文保护且优先，机器稿明确标自动机翻，与AI计数/全量精译队列分开。当前本机已实际完成5篇（约1.18万字符、129秒）；69Python＋25JS＝94检查通过，公开真实链路尚待验收。T037保持doing，T028全量AI精译仍doing。

已合并真实schedule刷新38537277827的6caf11e：543资料/198活动/26源，AI44/原生中文49/AI待译448，5份本机机翻，仅在原文hash/标题/摘录全匹配时合并，全部最新原文和AI字段、198活动逐条等价。用新完整库runtime/t037-merged.db继续，不导出旧库。实际schedule分别02:42/04:44/06:53/08:44 UTC启动，GitHub有约半小时调度延迟，不能承诺精确cron时刻。T037公开后台闭环验收仍待完成。


T038本地实现：Gemini免费项目原生REST单轮直译、完整语境分块、源绑定断点、批前Git配额预留/每分钟进度推送、未知usage区分、429/服务退避、已有AI保护。82Python＋25JS＝107检查通过，尚须公开代码CI/后台缺key状态与Pages验收；真实AI调用待一次性密钥。新增Guardian68＋Deadline电影12，623/198/28，44AI/49中文/29有效临时机翻/528待AI/2缺正文；原543所有原文/AI/198活动逐项保持。重要观察10新鲜重大稿/0当前列表重要缺条/2核心来源故障仍公开；每日实际入库记录从09:29UTC开始，80条首来源回补另计。Claude接力只改前端，不回写旧data或改变后台API。


T038发布验收：c030f62已push，CI38545075718通过82Python＋25JS＝107检查，Pages38545075651成功。真实公开1440/768/390全623分页、全量搜索、三阅读入口、字体、中文/原文/收藏、六页无溢出或脚本错误；公开boot核查28源/44AI/29机器/10近期重要稿/2核心来源故障/AI needs_configuration。后台38545075655真实经过配额准备和AI步骤（无key，0秒），临时机翻仍在运行，未假称AI真实产出。用户已确认能使用Google AI Studio，先接Gemini免费额度，尚待主人在Secrets添加GEMINI_API_KEY；当前连接管理403。费用不启用。收到已添加后dispatch后台并验证实际模型/完整译文/自动入库/Pages，T038仍doing，不能因代码检查通过写done。


T039实现与本地验收：静态逐文章JSON API、CultureCore.babelReaderUrl和最小文章页入口；BabelIntermission v1原文导入/持久化/语种分派/中文参考/原图与出处/重复不覆盖/更新另存。85Python＋26JS，接收端7JS＝118检查通过，三语课程40/40/30检查通过。1440/390英日西法葡中原文与图、真实英film/日写真/西película点词、日写真实际存入ja词本；笔记/marks重复与刷新保持，32,380字长稿不截断，404明确报错；法语在日语模式正确提示，源端不可达本机副本仍读，存储失败不假导入。旧巴别塔PWA shell20261012.1823→20261014.1059自动升级，个人文章marker保留。接收仓库07e0fcb及ab63fb4已push，等待公开联动总体验收；Claude主题排版不重写。原文API随最新自动刷新构建，未导出陈旧DB覆盖新数据。T038真实AI仍等主人方便时添加免费GEMINI_API_KEY，不催密钥且不影响联动。


T039公开完成：ART-NEWS b994269，CI38554022279（85Python+26JS）和Pages38554022552 success；babel ab63fb4，Pages38553447792 success。真实公开网站1440/390六语原文/原图/中文参考、原生英film日写真西película词典、日生词实际入库、重复副本/笔记marks保持/刷新、32380长文、404明确报错全部通过，无网络模拟、无脚本错误或溢出。公开JSON index HTTP200/639可读正文，当前643资料/4缺正文；缺正文不造可导入稿。旧623记录保留，已合并真实自动采集20新条和机翻推进，不导出旧DB。T039已done；以后每次build随当前完整live自动重导出。T038/T028仍需后续免费GEMINI_API_KEY真实AI输出验收和全量AI翻译，用户暂不在家，本联动不阻塞、不需额外密钥。Claude继续前端/文章排版，保留联动接口与入口。

## T040 · 报纸版面重排（Claude）· 2026-10-14

用户要求“做成报纸样式，不要AI味，不要多余的说明和按钮”。只改展示层（index.html/styles.css/theme.css/ui.js/app.js展示文案），数据、采集、翻译、存储键和路由不变。

- 报头：左耳日期星期与“艺术·电影·摄影”，中间书法站名，右耳为真实最近采集时间；粗细双栏线下接导航与检索。刷新只在本地API显示，提醒只在本地API且有未读时显示；“阅读设置”移到页脚。
- 头版：简讯（纯文字）＋日程｜头条（大标题、来源配图与图注、双栏正文）＋两条次条｜焦点；下方“更多报道”四栏，用每日精选之后按重要性排序的报道补满版面（未证实消息不补）。
- 不再绘制原创示意SVG：无来源配图时只排文字；配图加载失败时整块隐藏。图注改为图片下方“图／来源”。
- 卡片与头条的标题/摘要带lang；外文原文用Newsreader衬线，中文仍用Noto Sans SC黑体。另设仅含U+2019的撇号子集，避免中文标题里 Paris’s 出现全角撇号。
- 去掉优先级徽标、口语化提示与引导按钮（如“给好作品留个位置”“去探索 →”）；“只看AI译文”移入折叠筛选。“原文·待译”“自动机翻”标注保留为纯文字。
- 收藏在界面上称“剪报”（☆/★），存储仍为culture-desk-v1 schema 1。

验证见tasks.json T040。参考截图已更新：docs/images/newspaper-*.png。下一步：可以给“更多报道”加频道分栏标题；事件日历格内的重复“展览”字样可以改为按场馆或标题缩写显示（需另建任务，涉及展示规则）。

## T041 · 手机端阅读体验（Claude）· 2026-10-14

- 导航条`.paper-toolbar`移出`<header>`（仍紧跟报头，桌面外观不变），手机端吸顶；下滑阅读时隐藏、上滑出现；阅读页底边有2px阅读进度线（`.read-progress`）。
- 手机报头：站名一行，日期与更新时间一行；导航四项与检索框同一行，筛选行压缩。
- 从列表进入文章时记录滚动位置；文末“‹ 返回”、顶部返回和浏览器后退都回到原位置。文末重复“返回／剪报”（≤860px显示）。
- 手机列表：报道标题优先、方形小图居右（图注仍显示来源），摘要3行、左对齐（避免中英混排两端对齐的大空隙）。头条与文章图片通栏。
- 表单控件16px防iOS聚焦缩放；☆点击区44×36；页脚与提示适配安全区。
- 验证见tasks.json T041。

## T042 · 报头重新设计（Claude）· 2026-10-14

用户认为标题栏丑，允许不拘原字体与版型。新报头：左为自绘字标“幕间休息”（Noto Sans SC 900字重轮廓，间字内的“日”印红：门里亮着的光），旁边竖排“艺术／电影／摄影”，右侧是大号衬线日期数字＋年月、星期、更新时间；下接粗细双线与导航（当前栏目红色下划线）。手机隐藏竖排栏目，字标与日期同行。页脚用同一字标，favicon为黑底“间”。字标是index.html里的`<symbol id="wordmark">`，由`scripts/build_wordmark.py`生成（需可选fonttools），改字距/颜色见脚本与theme.css的`--wordmark-height`、`.wordmark-light`。不再加载Ma Shan Zheng。

## T043 · 王家卫式细繁体标题、书页扉页与胶片元素（Claude）· 2026-10-14

- 标题：用户要“王家卫那种比较瘦的繁体”。字标改为细明体繁体“幕間休息”（Noto Serif TC子集，`frontend/fonts/intermission-title-v1.woff2`，11KB，含扉页用字），間内“日”仍印红。`<title>`与元信息仍是简体“幕间休息”。
- 扉页：首页打开时左半屏是一页竖排书的扉页（竖排标题、藝術・電影・攝影、中文数字日期、外侧35mm胶片条），右半屏为压暗的头版；点击、Enter/空格/方向键、滚轮或滑动后，扉页绕书脊向右翻（传统直排书方向），纸背透出镜像标题，随后淡出。手机为整屏书页。每个浏览器会话只显示一次（sessionStorage `intermission-cover`，不动culture-desk-v1）；从#reader等深链接进入不显示；减少动态效果时只淡出。标记与小脚本在index.html，样式在theme.css“Opening page”段。
- 胶片元素：报头下沿为35mm胶片边（齿孔＋琥珀色边码，帧号随当日日期），扉页外侧为竖向胶片条。
- 新资源：字体加入`backend/app.py`本地API白名单（只加两行文件名）；静态构建与单文件预览自动复制/内联。

## T044 · 阅读页删除“资料”栏（Claude）· 2026-10-14

用户在手机上看到文章页“资料”栏（重要程度、翻译优先级依据、原始来源、关联日历活动），明确要求删除。阅读页现在只有“正文／原文”两个切换；来源与日期仍在标题上方，原文链接在文末。优先级数据和依据仍保存在数据里并继续用于排序，只是不在阅读页展示；收录页说明中“可在资料页查看依据”一句已删。

## T045 · 扉页改淡出、手机半页、光泽纸（Claude）· 2026-10-14

按反馈：去掉3D翻页（背面已删），点击/按键/滚轮/滑动后标题与文字先淡（0.4秒），纸页随后整体淡出（0.9秒，1.1秒后移除）。手机也只占左半屏（不再整屏），标题高度`min(56vh,108vw)`，胶片条收窄为24px。纸面改为光泽铜版纸：冷调亮白底、斜向高光带、书脊暗影与书口高光，见theme.css“Opening page”段`.cover-front`。

## T046 · 全站光泽纸（Claude）· 2026-10-14

用户要求整个网页改为光泽纸（与T045扉页一致）。theme.css令牌：`--paper/--canvas #f5f4f0`、`--white #fbfbf9`、`--ink #141312`、`--muted #5e5c57`、`--line #d3d1cb`；`body::before`是固定在视口、位于内容之后的斜向反光层（滚动时像光照在铜版纸上），不影响文字对比度；手机吸顶导航半透明以免切断反光。图片底色、日历选中/悬停、胶片齿孔等写死的米色已同步改冷白。

## T047 · 扉页半页重新设计（Claude）· 2026-10-14

用户认可光泽纸但认为半页太丑。重做：去掉胶片条与人造高光带，标题缩到半屏高度并居中留白，左侧一列“藝術・電影・攝影”，下方红色短线＋中文数字日期（版权页式），四角印刷角线，左缘几道细线表示书页叠层，书沟处渐暗；右侧不再压灰，只有书脊阴影落在头版上。手机同样是半页，按比例缩小。样式见theme.css“Opening page”段，标记见index.html `#cover`。

## T048 · 自由设计：栏目式头版与单栏阅读（Claude，用户确认上线）· 2026-10-14

用户让Claude自由设计，只要求“不要AI味、删去无用信息”。本分支实现：
- 头版（ui.frontpage）：头条通栏（大标题＋图片7:文字5），下分電影／藝術／攝影三栏（栏名用细繁体标题字，栏内首条带图，其余标题＋两行摘要），底部“放映與展期”按电影院排片表排（日期·片名/展名·地点类型·状态，最多8条）＋“圈內”边栏。首页不再显示筛选条、不受其他页筛选影响；按频道各取5条（每日精选优先，再按重要性），圈内4条，按标题去重。
- 删去：列表逐条的“原文·待译/自动机翻”（头条与阅读页保留，规则8的标注仍在阅读处）、首页筛选条、报头更新时间（移到页脚）、阅读页“正文采集于”“来源原文为中文”、文章正文双栏（改单栏760px）。收藏星号桌面悬停出现，触屏只在剪报页显示。
- 标题字子集加入“放映與展期圈內”（scripts/build_title_font.py CHARS），字标不变。

## T050 · 自定义域名下的运行状态读取（Claude）· 2026-10-15

域名迁到mujianrest.work后，收录页“自动运行”原先只在`*.github.io`上读取raw.githubusercontent的实时健康记录，新域名会退回构建时快照。app.js改为静态站任何HTTPS主机（非本地API模式）都读取。

## T051 · 片头动画（Claude · 2026-10-14）

完成：扉页片头「門中見日」（放映灯＋颗粒、四字逐帧闪入对焦、間中日霓虹点亮与红晕、光泽扫过、翻页红光）与报头胶片走片后点亮日。只改frontend/index.html与theme.css，接口说明见UI_CUSTOMIZATION.md的T051段。验证：Playwright录屏桌面/手机逐帧、reduced-motion无动画；26项JS测试、check_project与静态构建通过。未完成：Safari/Firefox未实际验收（自定义属性离散动画在不支持的浏览器上退化为直接显示红色，不影响阅读）。

## T052 · 手机扉页黄金分割（Claude · 2026-10-14）

≤700px扉页宽61.8%，标题放大到min(50vh,104vw)；桌面/平板半屏不变。与T051片头一起经PR合并发布。验证见tasks.json T052。

## T053 · 片头去掉光泽扫过（Claude · 2026-10-15）

用户不要片头结尾斜扫的白色光带，已删除`.cover-front::after`与`cover-sheen`；灯闪、颗粒、四字闪入、日点亮、红晕、翻页红光与报头走片不变。

## T058 · 「一种关注」前端（Claude）· 2026-10-15

读取`boot.coverage.attention_units`中id=a-kind-of-attention的启用单元（Codex T057接口）。
- 按用户要求放在「资讯」里：资讯页频道行末尾的“一種關注”标签（`data-view="attention"`，细明体，选中时红色下划线），路由`#attention`（core.parseRoute已加入）；该页顶部导航高亮“资讯”，点其他频道回到资讯列表。不单独占导航项。
- 头版：在電影/藝術/攝影三栏之后、放映與展期之前插入专栏条（`ui.attentionBand`）：标题、单元描述、每家媒体的关注地区（红）、媒体名（衬线）与最新一篇（日期＋标题）。示例模式不显示。`CultureCore.frontpageRows`选稿未改。
- 单元页（`ui.attentionPage`）：只有大号细明体标题（用户要求去掉标题下的说明文字，头版专栏条同样不显示描述；selection_basis/scope_note仍在接口与ATTENTION_UNITS.md）；每家媒体一行：左为地区、名称、推荐理由、专长·语种、最近发布（读取失败时红字说明）与官网；右为最近5篇（标题按站内中文/原文规则，经readerRoute进入阅读）；“来源状态”折叠显示最近成功读取、收录/正文/AI全文数与列表核对。
- 用户要求栏目名显示为正体字「一種關注」（`ui.unitName`；数据与配置中的正式名称、ID不变）。标题细明体子集加入“一種關注”；导航用的黑体子集只含简体常用字，另建2字Noto Sans TC子集`intermission-sans-tc-v1.woff2`（種關，2.7KB，OFL随附，`scripts/build_title_font.py --source-sans-tc`），加入`--serif/--sans`字体栈；本地API白名单加两项文件名。

## T062 接续：四项验收仍 doing（2026-10-15）

用户最新要求「全部做完再叫我」。后台依旧只用已配置Gemini免费API；禁止会话翻译/第二轮校对/开启付费。新增 scripts/audit_article_quality.py（原文hash/中文结构及逐源公开段落、图注，保存data/article-quality/断点）、scripts/audit_autonomous_trial.py（真实Actions小型状态artifact，首次完整24h结束前不通过）、scripts/update_acceptance.py（四门槛及快照签名，data/acceptance.json）。前两项不是语义校译。质量检查不自动把来源改写视作污染删除；保留缓存及问题，后续正常正文重抓接续。

新增14个来源（53启用=44 RSS+9官方页面）；实际工作区RSS+公开正文样本见data/source-expansion-evidence.json。来源总数与实际runner读取结果要分开核对；有未知出版国不补猜。Fotointern按类别过滤，Matca低频发现、不冒充每日更新。Artforum旧文公开页面当前只有署名/空正文，仍列缺正文，不从隐藏数据补造。

现有24h观察截至2026-10-15 18:07:54 UTC才满24h。当前工作区下载Actions artifact被网络Forbidden，报告保留unverified，不把本地下载失败说API翻译失败；新采集流程每六小时审计将从GitHub runner核对。待译/缺正文/核心来源故障/地区矩阵缺口仍未全部解决，T028/T062不能done。原提醒6acfba93ea708191be758da0a02f1e76已改仅四项all_ready且证据匹配后通知；旧每日会话翻译6ace6f72b3dc81919301888a638a327e保持暂停。不得把条件通知已配置说成工作完成。

T062补充：已实测共享concurrency的pending取消问题，定期24h证据核对移到采集内（6h去重），独立acceptance工作流改仅手动。取消采集不再占用数据组触发翻译。质量证据匹配原文hash/原标题及提取代码+来源规则版本；发现漏段/图注或公开内容变化时，在既有正文复查名额中优先安排一次重抓，不增加API配额。新订阅墙变短不得删除过去公开取得的正文或译文；长公开图注不再静默截1000字。148 Python+27 JS及工作流YAML/项目检查通过。线上c862643的900篇/899正文与运行报告hash已核对；后续修复与真实新增来源runner采集仍待验收。

健康邮件已核实并修复：c4b955e后38703530927、38703522699及38704272234实际success；告警来自pending采集被取消后错误判failed，网站Pages38703455394成功。原文9篇线上Babel的hash/全部blocks逐一匹配，线上acceptance明确false。继续补collection-recovery用于防止延迟API定时任务挤掉采集后永久丢这一轮；保留真实失败/6h停更告警，未全项验收不得done。

真实补排验收：只取消未执行的pending采集38704887311，后台collection-recovery 38704925032实际success，在没有手工第二次dispatch的情况下自动创建38704941443并已in_progress。取消事件的翻译38704924718自动skipped，不占写锁、不发API请求。当前需等待采集实际结束后核对14个新来源/新正文/发布，不把补排成功当采集完成。旧本地artifact下载0成功时不缓存六小时“已验证”；下一采集会重试真实运行证据，断点文章数去重、另存续译事件次数。

后续真实告警38705126797来自翻译38702099095最终保存rebase冲突（acceptance.json、article-quality-report.json），不是前面的取消误判。修复push_public_update已做3个真实Git并发集成检查；失败可从runtime/public-update-evidence的accepted-public-snapshot.json恢复，必须先匹配最新原文hash/原标题，不覆盖新采集。已知派生报告重算，正文/译稿冲突不猜合并。采集和翻译后显式dispatch后续流程，取消重复workflow_run入口，辅助GITHUB_TOKEN仅新增actions:write；154 Python/27 JS、YAML和全部shell块语法检查通过。机翻临时兜底每轮4分钟，原逐单元断点与Gemini免费500/日保持。

来源实际验收：38704941443 success，1161篇，13个新增来源本轮成功，Cineuropa被GitHub runner 403（仍保留与报告，不冒称14个全成功）；242条首次来源补库不是日均新闻。快照2026-10-15T08:23:32：182有效AI（其中直接150/历史已校32）、52原生中文正文、715有原文外文待AI、212缺正文（新补库等待正文预算，非丢失212篇旧正文）。2篇旧AI因公开正文更新/补全而失效进入队列，不重译原文hash仍匹配的有效稿。各项仍doing，待新保存流程真实通过及24h/积压/剩余来源/质量门槛。
