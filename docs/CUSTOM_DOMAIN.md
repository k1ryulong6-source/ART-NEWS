# mujianrest.work 域名迁移 · T049

用户2026-10-15 JST确认已在Porkbun购买mujianrest.work，授权更改幕间休息域名。刊名/品牌仍为幕间休息；巴别塔仍在https://k1ryulong6-source.github.io/babel/，不迁移其IndexedDB/生词/复习记录。

## 发布地址与代码

主站：https://mujianrest.work/ 。www.mujianrest.work由GitHub Pages重定向到主域名。旧https://k1ryulong6-source.github.io/ART-NEWS/由GitHub在设置custom domain后重定向；文章仍用#reader/live-ID，hash/收藏键/采集源/正文不变。

config/integrations.json集中记录site_url、custom_domain、legacy_site_url与巴别塔地址；backend/babel_export.py生成可配置返回链接。静态构建为两种预览加入canonical和CNAME，资源继续使用相对路径，可在根域名部署。**Actions部署不能靠CNAME文件完成绑定，仍需GitHub Settings → Pages → Custom domain。** 每次自动采集/翻译后的构建继续使用该配置，不改变API密钥或计费。

巴别塔integrations/intermission.js只尝试两个固定可信地址：新域名/integrations/babel/，失败后原GitHub项目接口。DNS、证书、HTTP失败和无效JSON均可回退，不接受URL参数指定任意接口。两个地址都失败时明确报错，不生成替代原文。每次重试独立超时；已保存文章仍优先本地，原文hash不变不创建重复副本或覆盖笔记。修改接收脚本后运行python tools/update_manifest.py发布PWA缓存更新。

## Porkbun一次设置

Domain Management → mujianrest.work → DNS。根域Host留空，TTL默认即可。删除根域/www已有的停车页ALIAS、A、AAAA或CNAME冲突记录，保留MX和TXT等其他记录；不设置整站URL转发。

| Type | Host | Answer |
| --- | --- | --- |
| A | 留空 | 185.199.108.153 |
| A | 留空 | 185.199.109.153 |
| A | 留空 | 185.199.110.153 |
| A | 留空 | 185.199.111.153 |
| CNAME | www | k1ryulong6-source.github.io |

## GitHub一次绑定

https://github.com/k1ryulong6-source/ART-NEWS/settings/pages → Custom domain填写mujianrest.work并Save，等待DNS检查/证书就绪，再打开Enforce HTTPS。不要修改babel仓库或账户根站的Custom domain。若集成API返回403管理权限不足，需要仓库主人在这个页面完成一次；现有代码推送授权已经具备，无需再询问发布许可。

## 发布顺序与验收

1. 先发布巴别塔双接口兼容，旧主站继续可读。
2. 准备生产者迁移PR并通过CI；未确认DNS/Pages前不合并，避免提前发布不可达的返回地址。
3. 核查Porkbun根域四条GitHub A与www CNAME，再设置Pages主域名；旧静态网页使用相对资源可先在新根域展示。
4. 合并迁移PR，Pages成功后检查新域HTTPS/证书、资源、中文/原文、文章JSON、旧URL/hash跳转、www跳转，以及公开巴别塔真实跨域导入/查词/重复笔记/刷新。
5. DNS/证书未就绪时保留doing，不能把PR或CNAME当上线证据。

## 收藏迁移

幕间休息的localStorage按域名隔离，旧站收藏不会自动出现在新域名。改Pages域名之前在旧站页脚“阅读设置”→导出JSON，切换后在新站同处导入。后台公开新闻/译文属于仓库数据，不受浏览器域名影响。巴别塔自身地址保持，不搬其学习记录。

## 当前证据

86Python＋26新闻端JS＋8巴别塔JS＝120检查，课程检查通过；python -S静态构建和质量审计0错误。689篇原文API返回链接全部指向新域名，两个静态版本canonical及CNAME正确。1440/390模拟新根域静态资源、中文/原文和跨域导入、新接口与DNS失败旧接口回退、重复笔记保持，无脚本错误或横向溢出。这是本地验证，尚未表示新域名已经公开上线。

初次DNS查询NXDOMAIN，随后根域/www已解析到Porkbun停车页207.207.210.107/207.207.210.229，www CNAME=pixie.porkbun.com；Pages cname=null。等待用户修改DNS及Pages绑定，后续实际发布证据追加。

DNS已核实正确：根域四个185.199.108–111.153，www CNAME=k1ryulong6-source.github.io。Babel7976620已公开发布，Pages38609603860 success。迁移PR https://github.com/k1ryulong6-source/ART-NEWS/pull/12 两轮CI成功。PUT仓库Pages cname实际返回403 Resource not accessible by integration；需要主人在仓库Settings/Pages手动保存mujianrest.work，已请求此一次设置。尚未合并生产者，不冒称新站已上线。

## 公开迁移已完成 · 2026-10-15 JST

用户已保存Pages域名并开启HTTPS。API确认cname=mujianrest.work、https_enforced=true、证书approved覆盖根域和www。迁移PR#12合并10c6782，Project checks38610234915及Pages38610235002 success；巴别塔7976620 Pages38609603860 success。

公开https主站返回200；http、www和原/ART-NEWS/均跳转到https://mujianrest.work/，浏览器旧#reader/ID完整保持。公开CNAME和canonical正确；原文API689篇，英日样本JSON返回news_url指向新域，原文与保存原稿一致。Chromium1440/390真实生产链接、中文/原文、英日导入和词典、笔记/marks刷新保持、旧文章跳转，无网络模拟/脚本错误/横向溢出。T049已done。未来续费/DNS或Pages域名变化按本文件维护，用户收藏仍按上述JSON方式跨域迁移。
