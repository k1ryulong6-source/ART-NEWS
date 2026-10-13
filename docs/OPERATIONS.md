# 运行与托管 v0.10

完整启动、静态构建、模型和邮件配置见 README.md。

## 两种数据保存方式

静态网站使用当前浏览器的 localStorage；不同设备可通过 JSON 导出／导入迁移，不自动共享私人状态。来源开关只控制本浏览器显示。

本地／私人服务使用 SQLite；多个浏览器访问同一个受保护服务时共享个人收藏与偏好。CULTURE_DESK_PASSWORD 可启用 HTTP Basic，用户名 owner；远程访问由 HTTPS 网关提供。Compose 默认只绑定 127.0.0.1:8000。

## Docker

执行 docker compose up -d --build。app 提供网页，updater 每 12 小时运行一次，二者共用 personal-data 数据卷。首次数据库创建恢复公开快照；既有数据库不会被覆盖。

在本次管理环境构建时使用 combined CA 的 BuildKit secret：docker build --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t culture-desk:0.2 .。普通机器无需该 secret。镜像不保存会话 CA、密钥或本地数据库。

管理环境中需要联网的运行容器应只读挂载系统 CA，并为 Python 设置 SSL_CERT_FILE；保留平台代理。不要把管理环境的地址写死到项目配置。正式服务器使用自己的标准系统信任与网络。

停止服务后备份数据库或持久数据卷。不要把 personal-data 放入 Git，也不要使用删除数据卷的命令作普通升级步骤。

## 自动更新

本地服务：python3 -m backend.jobs --schedule --interval-hours 12，可由 Compose 或系统服务管理。Ctrl+C／停止容器结束调度。

GitHub：refresh.yml 每天 UTC 01:15／13:15 运行，另有 workflow_dispatch。GitHub 定时任务可能延迟，Actions 显示真实执行结果。工作流恢复公开快照和当天模型请求账本，再采集、导出和提交元数据。

SMTP 仅用于用户主动配置的私人服务；公开快照工作流不持有个人收藏，因此不会发送个人收藏邮件。

## 快照、模型和提醒

资讯发布时间、抓取时间、活动日期分开。仅有月份的活动不进入具体日期提醒和 ICS；展览范围不代表每天开放。来源失败保留此前内容，并记录最近成功时间。

默认 NoOp 不请求外部模型。配置兼容服务后才进行摘要，每日上限在 SQLite 与快照账本中保留；模型错误不影响原文和活动日期。更换模型若希望重新处理既有摘要，先做备份，再针对所需记录重置 summary_status，不必删除资讯。

仅收藏且未看过的真实活动生成提醒；取消收藏或标为看过后，不再显示待提醒或邮件队列。邮件服务未配置时为 disabled；已发送标记防止重复发送。

## GitHub 协作

main 保留可运行版本；其他 AI 用分支与 Pull Request。tasks.json 是需求级任务记录，Issues 用于领取和讨论，HANDOFF 记录真实代码与验证。不要只改聊天里的进度。

## 当前外部依赖

模型密钥与 SMTP 未配置，实际外部摘要／邮件尚未启用。用户选择公开静态页，Pages 的 Actions 来源已开启。在线网址与发布验收见 HANDOFF。各读者收藏只在自己的浏览器保存；GitHub 定时刷新后自动重新发布。

公开摘要／图片补读继续在刷新任务中执行。v0.9已停用公共机翻，translation_usage仅恢复历史账本，不再增加；当前校译使用独立editorial_usage和EDITORIAL_*配置。图片加载依赖来源网络，静态离线正文仍可读。

正文采集随刷新执行，ARTICLE_PAGE_LIMIT=60为每轮上限；覆盖全部启用来源，失败不删除资讯。正文七天复核，失败两天后重试。当前AI校译处理完整语境，初译与校对进度独立保存；未完成时保留原文，不默认显示历史机翻。

一次批量补全可用：

```python
from backend.storage import Store
from backend.articles import collect_articles
s = Store('runtime/culture-desk.db')
s.restore_public_snapshot('data/live.json')
print(collect_articles(s, limit=1000))
```

之后运行 scripts/export_snapshot.py、scripts/audit_data.py --output data/quality.json --strict、scripts/build_static.py。仅在新内容／采集规则变化后针对所需来源复核，不重复强制抓取全部原文。查看 data/quality.json 的 article_source_counts；collected、partial、no_body、restricted、unavailable 分开统计。


## 当前默认：ChatGPT每日直接校译

任务“每日校译文化资讯”已在用户ChatGPT账户开启，Asia/Tokyo时区，上午约11:30的flexible_schedule；可在ChatGPT任务管理中修改或暂停。第一次定时执行尚未发生。任务账户ID只在忽略的本地runtime文件保存，不入公开仓库。该模式不需要配置额外网站模型API，仍受ChatGPT任务可用性、执行额度／时长及连接状态限制。

GitHub入口：docs/DAILY_TRANSLATION.md、data/translation-queue.json、逐篇data/translation-input。译稿写data/translations/ID.json，Publish daily AI translations验证并导出，workflow_run触发Pages。refresh与翻译发布使用同一个数据写入并发组，正常采集也导入未处理译稿和更新队列。已处理相同稿跳过，正文变更的陈旧稿留待重新校译。

手动验证：python scripts/import_daily_translations.py；python scripts/export_snapshot.py；python scripts/audit_data.py --output data/quality.json --strict；python scripts/prepare_translation_queue.py；python scripts/build_static.py。发布失败读取Actions日志修正具体译稿；不要删除原文以使检查通过。

每12小时的资讯抓取仍为东京时间10:15／22:15；每日ChatGPT校译安排在上午抓取后。源站数据仍可能限制访问，原文缺失／仅公开部分维持明确状态。

## 可选：外部模型API校译

此方案不是当前每日任务的前置。只有主动选择API模式时，才在GitHubActionsSecret设置EDITORIAL_API_KEY，并把EDITORIAL_PROVIDER设为openai-compatible。参考OpenAI https://api.openai.com/v1／gpt-4.1，或DeepSeek https://api.deepseek.com/v1／deepseek-chat；以账户实际可用模型为准。EDITORIAL_MODEL与EDITORIAL_REVIEW_MODEL可不同。默认每轮5篇、每天20次模型请求；这一账本仅统计外部API，与ChatGPT任务运行分开。不要向聊天或仓库提交密钥。

Google翻译保持停用。无需因缺少API密钥而停止当前ChatGPT直接校译路线。
