# 幕间休息 · 自托管字体

| 用途 | 上游字体 | CSS 字体名 |
| --- | --- | --- |
| 报头和页脚 | Ma Shan Zheng | Intermission Masthead |
| 中文新闻标题和正文 | Noto Serif SC 可变宋体，200–900 | Intermission Song |
| 拉丁字母原文和中英混排 | Newsreader 可变衬线，200–800，光学字号 | Intermission News |

三个字体均为 SIL Open Font License 1.1；许可原文分别保存为
mashanzheng-OFL.txt、notoserifsc-OFL.txt、newsreader-OFL.txt。修改后的内部家族名已改为上表名称，作者与许可元信息保留。favicon 的“幕”字轮廓取自 Ma Shan Zheng，适用同一许可。

字库放在本站，不调用 Google Fonts 服务或第三方字体CDN。字体未加载时用系统宋体/衬线回退，font-display:swap 保持文字立即可读。报头只含“幕间休息”4字，2576字节；宋体保留GB2312常用字与日文假名/标点，7605字，约2.77MB。新稿罕见字仍显示系统回退，不删除或替换文本。Newsreader约212KB。正常站点缓存字体；单文件预览内嵌全部字体。

`manifest.json`记录来源、原文件hash、产物hash和实际大小；
`song-charset.txt`固定覆盖集，不随每次采集重建，避免刷新让字库缓存失效。

复现（可选，日常构建/采集无需安装fonttools或联网取字库）：

1. 安装 `python -m pip install 'fonttools[woff]'`。
2. 从下列官方路径下载TTF和各目录OFL.txt；将许可分别命名为目录名-OFL.txt：
   - https://github.com/google/fonts/tree/main/ofl/mashanzheng
   - https://github.com/google/fonts/tree/main/ofl/notoserifsc
   - https://github.com/google/fonts/tree/main/ofl/newsreader
3. `python scripts/build_fonts.py --source-dir /path/to/upstream-fonts`。
4. `python -S scripts/build_static.py`。发布使用已提交的WOFF2，不打包上游31MB的TTF。

保留使用中的字库文件名，变更字库内容时递增v后缀并同步theme.css、index.html预加载、build_static.py和backend/app.py白名单。日常视觉修改只需CSS里的`--display`、`--serif`、`--sans`与字号/字重。
