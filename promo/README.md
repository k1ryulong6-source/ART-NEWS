# 幕間休息 · 宣傳片「一束光」

40秒、1920×1080、30fps的品牌宣传片，带原创配乐。`promo/index.html`可直接在浏览器播放（右下角「開聲音」开启配乐，点击画面暂停，重播）；`intermission-promo.mp4`是逐帧渲染并混入配乐的成片。

不属于网站运行代码：静态构建、API白名单、data.js与采集/翻译工作流都不读取本目录。之前的两版（胶片倒数＋报版；世界点阵）见Git历史。

## 分镜：一束光贯穿全片

字幕连成一句话：「放映機的光，放大機的光，展廳裡的光，——在光與光之間。」

| 时间 | 场景 | 内容 |
| --- | --- | --- |
| 0–10s | 電影 | 黑暗的影院，放映窗亮起，光束里浮着灰尘，打在侧面的银幕上；默片字幕卡：Variety报道「路易·马勒《通往绞刑架的电梯》将推出70周年4K版；《贝蒂·蓝》时隔35年重返大银幕」 |
| 10–19.5s | 攝影 | 银幕亮成一片白，化为放大机下的相纸：负像里的字发光，计时器倒数；灯灭，红色安全灯下相纸在显影盘里摇动，IMA报道「中野道通过摄影展“Meimetsu”告别青春，代官山开展」与日文原题慢慢显影 |
| 19.5–28.6s | 藝術 | 安全灯由红转白，成为展厅射灯；光圈落在墙上，照出Tate Modern展名「光影幻境：艺术摄影的诞生 / Light and Magic: The Birth of Art Photography」及展期 |
| 28.6–32s | 門 | 墙上的光收成一道门缝，光洒在地上，门缝成为「間」中的日（霓虹点亮） |
| 33–40s | 字標 | 拉远成「幕間休息」；「在光與光之間。」「藝術・電影・攝影　全球新聞　中文閱讀」mujianrest.work |

## 镜头衔接

- 影院→暗房：镜头推进银幕直到画面全白，白色即放大机下的相纸，暗房画面由放大回落。
- 曝光→显影：相纸位置不变，放大机的光淡出、红色安全灯淡入，显影盘在相纸四周出现。
- 暗房→展厅：安全灯就在画面正上方，由红转白成为射灯的灯头，光束从同一点落到墙上。
- 展厅→门→字标：墙上光圈收成门缝，门缝成为「間」中的日，再拉远成字标。

## 配乐

`score.py`用numpy/scipy合成全部声音，不用采样或第三方录音：毡音钢琴与慢速弦乐垫，D小调（Dm9→B♭maj7→Gm9→Fmaj7→C/E→Dm9→Asus4），「日」亮起时转入D大调；音效与画面同一时间轴——放映机开灯与24格快门声、推进时的气流、放大机开关与计时器提示音、显影盘摇动的水声、射灯开启的低频、门缝的风声、霓虹的电流声。`python promo/score.py score.wav`生成母带，网页用`score.mp3`（-16 LUFS，峰值约-5 dBFS）。

## 内容依据

- 三条新闻都取自`data/live.json`：银幕和相纸上的中文是网站`editorial_title_zh`（AI全文翻译）原句，相纸同时显影日文原题；展名、场馆与展期来自活动记录（2026-10-14至2027-02-21），中文展名为站内AI译名。
- 片中的影院、暗房、展厅和光都是绘制的场景，不是任何报道或展览的现场画面；字幕卡上的银幕号、相纸版式均为示意。

## 修改与重新生成

1. 改`src/promo.html`。CSS关键帧与`render(t)`共用同一条40秒时间轴（秒）：光束与灰尘、计时器、显影、摇盘反光、安全灯变色、墙上光圈与门缝由`render(t)`按时间绘制，其余为CSS动画。
2. `python promo/build.py --serif-source NotoSerifTC[wght].ttf --sans-source NotoSansSC[wght].ttf`
   注入按字拆分的字标、影院座椅与配乐，按片中文字子集化字体，输出`index.html`。只改动画、不增减文字时可省略两个参数，复用已提交的字体子集。需要`pip install numpy scipy 'fonttools[woff]'`；字体上游为google/fonts的`ofl/notoseriftc`、`ofl/notosanssc`（hash与`frontend/fonts/manifest.json`一致）。
3. `python promo/score.py score.wav`，再`ffmpeg -i score.wav -af volume=-3.8dB -b:a 160k promo/score.mp3`（改了时间轴就要同步改`score.py`里的提示点）。
4. `NODE_PATH="$(npm root -g)" node promo/record.cjs silent.mp4`
   Playwright暂停全部动画并逐帧定位，再调用`render(t)`绘制画布，PNG经ffmpeg编码为H.264；与机器速度无关，约需半小时。`--still 19.6 out.png`只截一帧检查。
5. `ffmpeg -i silent.mp4 -i score.wav -c:v copy -af volume=-3.8dB -c:a aac -b:a 192k -shortest promo/intermission-promo.mp4`混入配乐。

## 许可

`fonts/`为网站已用字体的子集：Noto Serif TC（promo-title）、Noto Sans SC（promo-sans）、Newsreader（promo-news），均为SIL Open Font License 1.1，许可原文见`frontend/fonts/notoseriftc-OFL.txt`、`notosanssc-OFL.txt`、`newsreader-OFL.txt`。
