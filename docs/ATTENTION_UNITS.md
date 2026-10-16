# 一种关注

用户指定的正式名称为「一种关注」，稳定ID为a-kind-of-attention。它是人工维护的地区媒体关注单元：把目光投向本站日常资讯较少触及的国家与地区，以及长期深耕这些地区的专业艺术与摄影媒体。名称不可自行改为“宝藏媒体”等其他标题。

首批为Artishock（智利与拉美）、ArtThrob（南非创作现场）、TAKE on Art（印度与南亚）、ZUM（巴西/拉美与跨地区摄影）、ART AFRICA（非洲与全球南方）。均复用已经启用、真实采集成功的RSS及稳定source_id；建立单元不虚增来源总数。媒体并非只报道出版方所在国，关注范围不等于单篇发生地或艺术家国籍。

维护入口是config/attention-units.json。每个成员填写source_id、focus_label、focus_countries、why、specialties、selected_at、reviewed_at。来源URL、语种和三项媒体权重继续由sources.json维护，避免两份配置相互漂移。推荐理由为编辑判断，不是客观国家艺术排名或读者份额；新增成员先核实实际RSS/内容与访问结果。

## 采集与预算

全部来源仍进入现有约2小时RSS刷新。单元从现有约20%发现预算内保留约10%的新正文名额，头条/重大消息先行；预算不是增加10%，更不是每批必须生成额外API请求。单元有候选时按地区/媒体权重轮转；空缺返还其他来源，其他发现渠道也保留位置，旧稿复查份额保持。

成员被暂停时不占保护份额，关注单元仍保留该来源的历史资料和暂停状态。读取失败保留最后成功时间与缓存文章，不能隐藏故障；低频媒体的真实最后发布日期与最近成功抓取时间分别展示。现有译文复用，全文仍执行头条优先/重要性与时效/旧稿规则；500请求/太平洋日免费上限不变，不增加二轮校对或启用付费。

## 给Claude与其他AI的展示接口

- 公开索引：/reports/attention-units.json。
- 本单元：/reports/attention-units/a-kind-of-attention.json。
- 本地API：/api/attention-units和/api/attention-units/a-kind-of-attention。
- 前端已有bootstrap.coverage.attention_units，单元数据在units数组中。

包含正式名称、描述、成员和推荐理由、领域标签、来源独立权重、RSS/主页、真实采集/列表核对状态、最后成功抓取时间、最新发布日期、库存/正文/AI译文数量，以及每个来源最近5篇报道的稳定ID与阅读路径。has_body只代表已有保存正文；article_status仍可能是partial。AI计数要求完整有效正文/中文标题，不能把只译标题或机翻计为AI全文完成。

Claude负责前端呈现；本次提供数据单元及接口，没有修改报纸布局。建议使用来源名、关注范围、推荐理由与最近报道，详细状态可折叠。保留现有CultureCore.readerRoute(id)、中文/原文切换、图片出处、收藏和巴别塔入口。不要将relative reader_path解析为reports子目录，应由稳定ID生成站内路由，或拼到站点根地址。

添加/暂停单元由配置维护，id只接受小写字母、数字和连字符；移除/暂停后构建清理旧单元JSON。成员引用必须存在、单元内不得重复，启用单元预留份额之和不得超出现有发现份额。提交前执行相关测试、check_project.py和build_static.py。
