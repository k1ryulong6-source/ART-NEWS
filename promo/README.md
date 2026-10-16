# 幕間休息 · 宣傳片「幕間新聞片」

46秒、1920×1080、30fps的品牌宣传片，带原创配乐。`promo/index.html`可直接在浏览器播放（右下角「開聲音」开启配乐，点击画面暂停，重播）；`intermission-promo.mp4`是逐帧渲染并混入配乐的成片。

不属于网站运行代码：静态构建、API白名单、data.js与采集/翻译工作流都不读取本目录。之前的几版（胶片倒数＋报版、世界点阵、一束光）见Git历史。

## 创意

老电影院在幕间和正片之前放的正是新闻片——「幕間休息」与新闻天然相连。全片做成一期复古黑白新闻片，只用品牌红点缀；每条新闻都是网站上真实的报道，以中文标题＋原文标题出现。

| 时间 | 场景 | 内容 |
| --- | --- | --- |
| 0–4.2s | 幕间幻灯片 | 影院的幕间幻灯片：INTERMISSION、字标、「新聞片即將開始」；灯光暗下 |
| 4.2–10s | 片头 | 旋转地球（Natural Earth陆地点阵）与探照灯，鼓点后片名「幕間新聞」砸入，「全球藝術・電影・攝影」与日期 |
| 10–18.5s | 電影 | 分区字卡→经典「旋转报纸」飞入，报头是幕間休息，头条为《卫报》查尔斯王子电影院获救；跑马灯框里两条电讯式导语：釜山（Screen Daily）、温哥华（Variety） |
| 18.5–26.5s | 攝影 | 记者闪光灯，取景框里三条：东京·代官山（IMA）、卡达克斯（Fisheye）、Aperture摄影书奖入围名单 |
| 26.5–34.8s | 藝術 | 画框里三条：伦敦Tate Modern「光影幻境：艺术摄影的诞生」及展期、威尼斯皮诺常设展（ARTnews）、ART AFRICA「当城市成为舞台」并盖上「一種關注」印章 |
| 34.8–38.6s | 电讯 | 三条电讯条（電影／攝影／藝術）滚动最近的真实中文标题；「全球來源　中文閱讀　原文對照」「每兩小時更新」 |
| 38.7–40.7s | 完 | 新闻片的「完」 |
| 40.7–42.6s | 下一期 | 钟面走过两小时：「下一期　兩小時後」 |
| 42.8–46s | 字标 | 幕間休息、「正片開始前，先看看世界。」、mujianrest.work |

## 内容依据

- 每条新闻的中文是网站`editorial_title_zh`（AI全文翻译）原句，并排原文标题与来源；导语地点只用标题或活动中写明的地点（釜山、温哥华、代官山、卡达克斯、Tate Modern、威尼斯），没写明的只署来源。
- 电讯条由构建脚本从`data/live.json`按频道取最近有AI全文的中文标题。
- 「每兩小時更新」对应自动采集约每2小时一次；片头日期是新闻片的形式，不代表期数。
- 旋转报纸版面是片中排的示意版，不是网站真实页面。

## 配乐

`score.py`用numpy/scipy合成全部声音，不用采样或第三方录音：幕间的钢琴圆舞曲（B♭），片头小军鼓与定音鼓滚奏后接铜管号角，三段进行曲（電影B♭、攝影C、藝術D，逐段升高），闪光灯的轻爆声、印章、电讯段加强、「完」的终止和弦、音乐盒走钟和收尾和弦。母带做了老式光学音轨的频带限制（85–8000 Hz）。网页用`score.mp3`（约-16 LUFS）；网页播放以配乐为主时钟，配乐从不中途跳转，画面若有偏差就让画面对齐配乐。

## 修改与重新生成

1. 改`src/promo.html`。CSS关键帧与`render(t)`共用同一条46秒时间轴（秒）：地球与探照灯、胶片磨损（闪烁、划痕、灰尘、片门晃动）、钟面由`render(t)`绘制，其余为CSS动画。改了时间就同步改`score.py`的提示点。
2. `python promo/score.py score.wav`，再`ffmpeg -i score.wav -af volume=-1.4dB -b:a 160k promo/score.mp3`。
3. `python promo/build.py [--land land-110m.json] [--serif-source NotoSerifTC[wght].ttf] [--sans-source NotoSansSC[wght].ttf]`
   注入按字拆分的字标、地球点阵、电讯条、钟面刻度与配乐，按片中文字子集化字体，输出`index.html`。不增减文字时可省略字体参数；不给`--land`则复用`land-dots.json`。地图数据：https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json（ISC；Natural Earth，公有领域）。字体上游为google/fonts的`ofl/notoseriftc`、`ofl/notosanssc`（hash与`frontend/fonts/manifest.json`一致）。需要`pip install numpy scipy 'fonttools[woff]'`。
4. `NODE_PATH="$(npm root -g)" node promo/record.cjs silent.mp4`：Playwright暂停全部动画逐帧定位并调用`render(t)`，PNG经ffmpeg编码为H.264；与机器速度无关，约需40分钟。`--still 19.6 out.png`只截一帧检查。
5. `ffmpeg -i silent.mp4 -i score.wav -c:v copy -af volume=-1.4dB -c:a aac -b:a 192k -shortest promo/intermission-promo.mp4`混入配乐。

## 许可

`fonts/`为网站已用字体的子集：Noto Serif TC（promo-title）、Noto Sans SC（promo-sans）、Newsreader（promo-news），均为SIL Open Font License 1.1，许可原文见`frontend/fonts/notoseriftc-OFL.txt`、`notosanssc-OFL.txt`、`newsreader-OFL.txt`。`land-dots.json`派生自Natural Earth公有领域数据。
