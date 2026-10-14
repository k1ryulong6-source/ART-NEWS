# 无人值守采集、翻译与发布

网站：https://k1ryulong6-source.github.io/ART-NEWS/

当前主链在GitHub Actions上执行，不依赖打开ChatGPT，也不需要独立模型API密钥。

| 阶段 | 执行方式 | 实际产物 |
| --- | --- | --- |
| 采集 | refresh.yml，UTC每两小时15分附近 | 原文/图片/日期/逐源成功失败/全量队列 |
| 翻译 | autotranslate.yml，采集结束触发；另有每4小时45分备用调度 | 免费离线M2M100机翻/逐单元断点/真实完成报告 |
| 发布 | pages.yml，采集/翻译工作流结束触发 | 最新公开网页，机器译文与AI稿分别标注 |
| 检查 | automation-health.yml，每6小时及上述工作流结束 | 真实Actions记录、成功时间、失败/超过6小时不推进 |

调度是GitHub的尽力执行，运行可能排队；时间不是精确到点的承诺。采集/AI导入/离线翻译共用数据写锁并checkout最新main；健康记录使用独立锁，不抢占采集和翻译的待执行名额。健康提交不触发Pages，避免监测→发布→监测循环。覆盖页读取最新公开健康记录，网站长期未更新时也能看到停滞。

## 翻译选择与成本

用户不想另配API，允许未译正文使用机械翻译。选免费离线M2M100 418M int8，由CTranslate2 CPU推理；预训练模型支持100种语言，当前全部外文来源的英/日/法/葡/西已实际试跑。机翻不是语境大模型精译或人工审核，专名/表达可能出错，阅读页原文始终可切换。已有44篇AI全文优先保留，不被机翻覆盖；AI队列继续存在，机器译文不算AI精译完成。

公开仓库使用GitHub标准Ubuntu托管runner，不调用任何付费推理API、不使用大型runner。不承诺后台AI精译：原ChatGPT每日任务没有实际运行记录，只是可选增强，不构成主链依赖。GitHub Models官方明确2026-07-30退役，不能使用过期的免费模型方案：https://docs.github.com/en/github-models/prototyping-with-ai-models 。

config/automation.json固定模型仓库、revision及4份文件SHA256；首次下载约499MB，后续缓存，校验不符重新获取/失败退出，不运行远程模型代码。MIT上游：https://huggingface.co/facebook/m2m100_418M ；量化副本：https://huggingface.co/gn64/M2M100_418M_CTranslate2 。字库和模型是资源，原文不发送给推理服务。

## 接续和故障

每批最多40篇/60,000原文字符/900秒（先到的停止），不是每天固定翻译量。最高优先级在前，8个旧稿名额交错进入，防止资源限额使旧稿永远排在批尾。整个队列保留；不按来源、长度、语种永久删除。短源片段128 tokens，拼接前后严格保持源字符完整；检查段落、数字、URL与出处。数值缺失时仅重新处理该单元，保留数值/作品代码原貌；错误不冒称完成。

每个通过的单元立即写data/auto-translation-progress/ID.json，完整通过后才写正文译文并删除断点。源码hash/标题/摘录/引擎配置变更使旧断点失效；失败记录6小时退避并继续其他稿。即使后续单元失败，也不用重译已通过部分。900秒提前停止，为快照导出、审计、提交留余量；出错后的安全步骤和7日Artifacts保留已接受工作。发布只使用完成的正文，不在待译空白里假称已译。原文缺失/仅公开部分照常标注。

机器正文复用已有article_translation字段；编辑AI稿与机器字段分开。浏览器只传有效新离线机翻，不恢复旧未核实机器稿；源码/图片/出处独立保留。backend.coverage分别记录AI全文、离线机翻、尚无中文正文与尚未取得正文。

## 验证与手动维修（不属于每日操作）

- Actions页面核查Refresh cultural news → Automatic full-text translation → Publish public news page的实际conclusion和提交。
- data/auto-translation-status.json记录本批实际ID、字符、单元、耗时、失败与剩余，不用“已启用”替代产量。
- data/automation-health.json核查各阶段最近成功和失败；首次运行未完成不能称正常。
- 修复后可从Actions手动dispatch，正常情况下按计划自行接续。
- 本地使用新的完整快照数据库：CULTURE_DESK_DB=runtime/auto.db python scripts/import_snapshot.py；安装requirements.txt和requirements-translation.txt；同一DB运行scripts/run_auto_translation.py。不要导出旧runtime/culture-desk.db覆盖新资料。

采集来源仍为有限名单；来源403、滚动RSS与未知地区保留覆盖缺口，自动执行不等于全球所有重要资讯收齐。
