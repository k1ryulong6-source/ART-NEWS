# 运行与托管 v0.6

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

公共机器翻译与公开摘要／图片补读在刷新任务中执行。TRANSLATION_PROVIDER=disabled 可停用；每日请求账本存于 SQLite／公开快照，默认 1000 次上限；翻译失败保留已有内容，不修改活动事实。图片加载依赖来源网络，静态离线文字仍可读。
