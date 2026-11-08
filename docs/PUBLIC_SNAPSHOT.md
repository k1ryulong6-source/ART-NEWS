# 公共数据存档

`data/live.json` 是存档入口。小存档可保留旧版完整 JSON；大存档使用 `snapshot_storage.format=content-shards-v1`：入口保存活动、来源、预算等原有元数据，正文记录按稳定 ID 哈希分布在 `data/snapshot-content/*.json`。

Python 读取统一使用 `backend.snapshot_files.read_snapshot(path)`，写入使用 `write_snapshot(path, snapshot)`。不要直接对入口 `json.loads(...)["content"]`；分片入口故意不放空的 content 数组，以免旧代码误认为文章被清空。命令行恢复仍使用 `python scripts/import_snapshot.py`，导出仍使用 `python scripts/export_snapshot.py`。

每个分片包含完整文章记录，原文、图注、链接、AI/机翻正文、模型身份、hash、审核状态均原样保存。入口记录全部 ID 的原顺序及每片路径、SHA-256、字节数、条数；缺片、损坏、重复 ID、越界路径或漏条时拒绝恢复，不能以部分内容继续发布。默认每片最多4 MiB、入口最多8 MiB；单篇过大则明确失败，不截正文。旧版JSON兼容，不需要Git LFS或付费服务。

所有数据写工作流必须把 `data/live.json` 与 `data/snapshot-content/` 在同次提交保存。推送器会阻止漏提分片或超100 MiB的新Git blob，并把脱敏错误分类、返回码及安全错误片段保存在 `runtime/public-update-evidence/git-push-report.json`；已接受的完整原文/译文另存运行产物，禁止强推或自动覆盖正文冲突。

静态发布的 `bodies/`、巴别塔JSON、搜索索引、CultureUI接口和读者链接保持原协议。分片仅改变仓库存档格式，不改变原文/译文内容，不算新增翻译或正文补齐。
