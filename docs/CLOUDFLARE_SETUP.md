# Cloudflare托管千问接入

用途：Gemini受阻时的独立免费AI翻译备用。模型固定`@cf/qwen/qwen3-30b-a3b-fp8`；不是阿里百炼的密钥或免费额度，不需要改域名/DNS。

在Cloudflare控制台Workers AI → Use REST API，通过预设模板创建Token，同时复制Account ID。在本仓库Settings → Secrets and variables → Actions → Repository secrets添加：

| 名称 | 内容 |
| --- | --- |
| CLOUDFLARE_API_TOKEN | Workers AI API Token；也兼容官方示例的CLOUDFLARE_AUTH_TOKEN Secret别名 |
| CLOUDFLARE_ACCOUNT_ID | Cloudflare的32位十六进制Account ID；也接受同名Repository variable |

不要把Token放聊天/公开代码/前端。保留Workers Free，不启用付费或自动充值。10000 Neurons/UTC日（东京09:00重置）是官方免费分配；本仓库账本只估算自己的使用，不证明全账号剩余额度。

配置后手动执行Verify Cloudflare Qwen full-text translation。探针最多2请求/1完整正文，先提交独立请求/Neurons预留，只保存自身账本与完整断点，不写旧live快照；后续正常串行采集/翻译在import_snapshot时经源hash/全部单元/数字检查恢复合格copy，无额外模型请求。实际成功后才将config/cloudflare-translation.json的verified_enabled设true，接续原自动链；失败不得仅凭Actions绿色启用。

报告：data/cloudflare-verification-report.json；常规状态data/cloudflare-translation-status.json；公开/reports/operations.json的cloudflare.verification区分已配密钥、实际请求、正文完成与错误。测试未调用会话工作者，不做第二轮模型审校。

2026-10-16 23:50:48 JST真实探针38919032806结果：Token已传入，Account ID缺失，0请求/0篇。等待添加CLOUDFLARE_ACCOUNT_ID；不能称接通或产生译文。配置状态以之后真实报告为准。
