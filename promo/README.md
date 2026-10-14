# 幕間休息 · 宣傳片

36秒、1920×1080、30fps的品牌宣传动画。网页版 `promo/index.html` 可直接在浏览器播放（点击画面暂停，右下角重播）；`intermission-promo.mp4` 是逐帧渲染的视频成片，无声，可自行配乐。

不属于网站运行代码：静态构建、API白名单、data.js与采集/翻译工作流都不读取本目录。

## 分镜

| 时间 | 场景 | 说明 |
| --- | --- | --- |
| 0–3.6s | 片头倒数 | 学院式倒数环 3·2·1，两侧胶片齿孔在走 |
| 3.7–11.4s | 竖排字幕 | 胶片停下（幕间），細明體竖排：燈亮了／散場／落幕／快門之間，引出「這段時間，叫作」 |
| 11.5–16.5s | 扉页 | 与网站同一套左半页光泽纸扉页：角线、竖排字标自上而下显影、「間」中「日」如霓虹点亮；按D037先淡文字再淡纸页 |
| 16.6–21s | 头版 | 报头、35mm胶片边、头条与電影／藝術／攝影三栏依次排版 |
| 21–27s | 阅读页 | 中文（AI翻译）一键切到保存的原文 |
| 27–31s | 放映與展期 | 伦敦／东京／首尔／班加罗尔的真实展期，日期滚入 |
| 31–36s | 片尾 | 字标、胶片边、「在兩場之間，讀世界。」、mujianrest.work |

画面中的标题、来源、日期与展期均取自 2026-10-14 的 `data/live.json` 实际条目；外文条目按网站规则标「原文·待译」，未补造信息。

## 修改与重新生成

1. 改 `src/promo.html`（所有动画写成同一条36秒时间轴上的CSS关键帧，`animation-delay`即该镜头的秒数）。字标轮廓与胶片边字由构建脚本从 `frontend/index.html` 注入，不要手抄。
2. `python promo/build.py --serif-source NotoSerifTC[wght].ttf --sans-source NotoSansSC[wght].ttf`  
   按片中实际文字子集化字体到 `fonts/`，生成 `index.html`。只改动画、不增减文字时可省略两个 `--*-source`，复用已提交的子集。需要 `pip install 'fonttools[woff]'`。上游TTF来自 google/fonts 的 `ofl/notoseriftc`、`ofl/notosanssc`（hash 与 `frontend/fonts/manifest.json` 一致）。
3. `NODE_PATH="$(npm root -g)" node promo/record.cjs promo/intermission-promo.mp4`  
   Playwright 暂停全部动画并逐帧定位到 t，PNG 经 ffmpeg 编码为 H.264；与机器速度无关，约需十几分钟。`--still 19.6 out.png` 只截一帧用于检查。

## 字体许可

`fonts/` 为网站已使用字体的子集：Noto Serif TC（promo-title）、Noto Sans SC（promo-sans）、Newsreader（promo-news），均为 SIL Open Font License 1.1，许可原文见 `frontend/fonts/notoseriftc-OFL.txt`、`notosanssc-OFL.txt`、`newsreader-OFL.txt`。
