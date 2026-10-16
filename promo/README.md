# 幕間休息 · 宣傳片（第二版）

40秒、1920×1080、30fps的品牌宣传片。`promo/index.html`可直接在浏览器播放（点击画面暂停，右下角重播）；`intermission-promo.mp4`是逐帧渲染的成片，无声，可自行配乐。

不属于网站运行代码：静态构建、API白名单、data.js与采集/翻译工作流都不读取本目录。第一版（胶片倒数＋报版，T051分支稿）已由本版替换，见Git历史。

## 分镜：世界在別處開幕

| 时间 | 场景 | 内容 |
| --- | --- | --- |
| 0–3s | 聚星 | 散落的光点聚成世界陆地（Natural Earth 110m，每1.5°一点）。「此刻，世界某處正在開幕。」 |
| 3–13s | 曙光 | 十月中旬（赤纬−9°）的日出线自东向西扫过；东京、釜山、班加罗尔、阿布扎比、开普敦、的里雅斯特、卡达克斯、伦敦、纽约、墨西哥依次亮起红点，并以原文显示当地报道 |
| 13.5–21s | 九种语言 | 英、法、德、意、西、荷、日、葡、中九种原文标题逐字转成本站AI中文译文；葡文ZUM尚无译文，如实标「原文·待譯」，香港中文原稿标「中文原文」 |
| 21–29s | 一種關注 | 南方大陆亮起，六家成员按各自关注范围落点并连成星座：Artishock、ZUM、ART AFRICA、ArtThrob、TAKE on Art、Matca |
| 29.6–32s | 合幕 | 由真实原文标题织成的两扇幕布合上，缝里透出光 |
| 31.6–40s | 門中見日 | 光成为「間」中的日（霓虹点亮），拉远成字标「幕間休息」；「世界在別處開幕，你在幕間讀到。」mujianrest.work |

## 内容依据

- 城市卡片只选标题或活动数据中明确写出地点的条目（如「東京・神保町」「Busan Award」「Met Exhibition」「Zeitz MOCAA」），不按媒体所在地或语种推定地点；长标题在卡片中截断显示。
- 第二幕的中文全部是网站`editorial_title_zh`（AI全文翻译）原句；未译的保持原文并标注。
- 「一種關注」成员与关注范围取自`config/attention-units.json`；落点为关注范围的代表位置，不代表单篇报道发生地。
- 幕布文字由构建脚本从`data/live.json`按来源轮流选取最近的原文标题。
- 日出线是示意：只扫一次、亮后不再入夜，不对应真实时刻。

## 修改与重新生成

1. 改`src/promo.html`。CSS关键帧与脚本中的`CITIES`/`LINES`/`MEMBERS`共用同一条40秒时间轴（秒）。地图、城市卡片、逐字翻译由`render(t)`按时间绘制，其余为CSS动画。
2. `python promo/build.py --land land-110m.json --serif-source NotoSerifTC[wght].ttf --sans-source NotoSansSC[wght].ttf`
   生成陆地点（`land-dots.json`）、按字拆分的字标、幕布和字体子集，输出`index.html`。只改动画、不增减文字时可省略全部参数，复用已提交的点阵与字体。需要`pip install numpy 'fonttools[woff]'`。地图数据：https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json（ISC；Natural Earth，公有领域）。字体上游为google/fonts的`ofl/notoseriftc`、`ofl/notosanssc`（hash与`frontend/fonts/manifest.json`一致）。
3. `NODE_PATH="$(npm root -g)" node promo/record.cjs promo/intermission-promo.mp4`
   Playwright暂停全部动画并逐帧定位，再调用`render(t)`绘制画布，PNG经ffmpeg编码为H.264；与机器速度无关，约需半小时。`--still 19.6 out.png`只截一帧检查。

## 许可

`fonts/`为网站已用字体的子集：Noto Serif TC（promo-title）、Noto Sans SC（promo-sans）、Newsreader（promo-news），均为SIL Open Font License 1.1，许可原文见`frontend/fonts/notoseriftc-OFL.txt`、`notosanssc-OFL.txt`、`newsreader-OFL.txt`。`land-dots.json`派生自Natural Earth公有领域数据。
