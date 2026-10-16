# 幕間休息 · 宣傳片「明日新聞台」

46.5秒、1920×1080、30fps的品牌宣传片：黑白五十年代电视卡通，风格参照《辐射》系列的公益小动画，做成老胶片的手绘质感（lo-fi）；原创主持人「幕間先生」，英文旁白，中文字幕，原创配乐。`promo/index.html`可直接在浏览器播放（右下角「開聲音」开启旁白与音乐，点击画面暂停，重播）；`intermission-promo.mp4`是逐帧渲染并混入旁白与配乐的成片。

不属于网站运行代码：静态构建、API白名单、data.js与采集/翻译工作流都不读取本目录。之前的几版（胶片倒数＋报版、世界点阵、一束光、幕間新聞片、彩色原子朋克）见Git历史。

## 分镜

| 时间 | 场景 | 旁白（英文）／字幕（中文） |
| --- | --- | --- |
| 0–6.6s | 老电视开机，测试卡「幕間休息電視台」，主持人在旁招手；镜头推进屏幕 | Good evening, citizens of tomorrow! You're watching Intermission TV! ／ 各位明日世界的公民，晚上好！您正在收看幕間休息電視台！ |
| 6.6–14.6s | 地球与雷达信号汇入「新聞機」，主持人指向机器 | Every two hours, our marvelous news machine gathers the latest in film, photography and art, from every corner of the globe! ／ 每兩小時，我們神奇的新聞機，從全球各地收集電影、攝影與藝術的最新消息！ |
| 14.6–21.4s | 东京、釜山、伦敦、纽约、威尼斯的头条，以撕边旧报纸剪报飞到惊讶的主持人身边 | From Tokyo to London, Busan to New York — the world's culture headlines meet right here! ／ 從東京到倫敦，從釜山到紐約——世界的藝文頭條，在這裏相遇！ |
| 21.4–30s | 主持人坐单轨列车经过世博会的電影館、攝影館、藝術館，招牌是真实头条 | Film! Photography! Art! Step right up — the stories are fresh off the wire! ／ 電影！攝影！藝術！快來看——消息剛剛到站！ |
| 30–36.2s | 挂「一種關注」旗的火箭飞向南方，视野扩开，六家成员亮成星星 | And with "A Kind of Attention", we look farther — to the corners of the map you've never seen! ／ 還有「一種關注」，帶您看得更遠——看見地圖上從未見過的角落！ |
| 36.2–46.5s | 「日」为原子核，電影／攝影／藝術三颗电子；字标幕間休息与网址；主持人眨眼竖拇指；老电视关机 | Intermission — art, film and photography news from around the world. Mujian rest dot work! Stay curious, citizens! ／ 幕間休息——全球藝術、電影、攝影新聞。mujianrest.work，保持好奇，公民們！ |

## 手绘与年代感

- 手描墨线：页面载入后，`handInk()`把每个SVG图形（主持人、胶片盘、原子轨道）和带描边的CSS盒子（电视、新闻机、展馆、火箭等）重画成手描：轮廓沿线轻微走样，描边改成粗细起伏、两端收笔的毛笔线；没有描边的盒子用走样的`clip-path`得到不规整边缘。字标与文字不重画。每个图形画三张（cel），每隔一张画面换一张，线条像手描动画那样轻轻“沸腾”，画面本身不扭曲。再加灰度、轻对比与轻微模糊，叠一层纤维纸纹。
- 一拍二：`seekPromo`把CSS动画与画布都量化到每秒12张，像老卡通；胶片磨损（闪烁、划痕、灰尘、毛发、片门晃动与偶发跳格）仍按每秒24格变化。
- 剪报：报头「幕間休息」与日期、电头、半调照片、栏线与来源；撕边由脚本生成的`clip-path`多边形。

## 内容依据

- 卡片与招牌上的新闻都取自`data/live.json`：中文是网站`editorial_title_zh`（AI全文翻译）原句，并附来源与日期；Tate Modern展期来自活动记录。卡片上的城市只用标题写明或可确定的地点。
- 「一種關注」成员与关注范围取自`config/attention-units.json`。
- 旁白说的「每兩小時」对应自动采集约每2小时一次。
- 主持人「幕間先生」是为本站原创的角色（`src/host.py`），刻意与《辐射》的Vault Boy区分（黑色侧分发、西装领结、胸前「日」徽章），片中不使用任何《辐射》或Vault-Tec的名称与标志。

## 声音

- 旁白：微软Edge神经语音`en-US-GuyNeural`（语速+8%、音高+6Hz），由用户在三个声音中选定，`voice.py`可重新生成`voice/l1–l6.mp3`。该在线服务用于公开发布的授权不明确；正式公开前建议请真人按同一台词录音（同名文件、长度相近），替换后重新运行`score.py`即可。
- 配乐：`score.py`用numpy/scipy合成五十年代太空时代轻音乐（颤音琴、特雷门琴式滑音旋律、行走低音、刷子鼓、铜管点缀、结尾小旋律）和音效（电视开关、推镜、火箭、视野扩开）。旁白做老电台音色（磁带抖动、360–3300 Hz窄频、采样保持颗粒、饱和、底噪与爆音），配乐总线加抖动与90–6500 Hz限频，每句旁白期间音乐整体压低约14 dB，人声比音乐高12–21 dB。
- 网页用`score.mp3`（约-16 LUFS）；播放时以声音为主时钟，声音从不中途跳转，画面若有偏差就让画面对齐声音。

## 修改与重新生成

1. 改`src/promo.html`（CSS关键帧与`render(t)`共用同一条46.5秒时间轴，按12fps取样；字幕时间与`score.py`的`VOICE_AT`一致）；主持人姿势在`src/host.py`。
2. 需要时`python promo/voice.py [--cafile 代理CA]`重新生成旁白。
3. `python promo/score.py score.wav`，再`ffmpeg -i score.wav -af volume=-4.3dB -b:a 160k promo/score.mp3`。
4. `python promo/build.py [--land …] [--serif-source …] [--sans-source …] [--retro-source ZCOOLQingKeHuangYou-Regular.ttf] [--righteous Righteous-Regular.ttf]`：注入字标、主持人、胶片盘、地球点阵与声音，按片中文字子集化字体，输出`index.html`。不增减文字时可省略字体参数。
5. `NODE_PATH="$(npm root -g)" node promo/record.cjs silent.mp4`逐帧渲染（约40分钟），再`ffmpeg -i silent.mp4 -i score.wav -c:v copy -af volume=-4.3dB -c:a aac -b:a 192k -shortest promo/intermission-promo.mp4`。

需要`pip install numpy scipy 'fonttools[woff]' edge-tts`。地图数据：world-atlas land-110m（ISC；Natural Earth，公有领域）。

## 字体许可

`fonts/`：Noto Serif TC、Noto Sans SC、Newsreader（网站已用字体的子集）与ZCOOL QingKe HuangYou（站酷庆科黄油体子集），均为SIL OFL 1.1；Righteous（OFL，含保留字体名，故原样提供未改动）。许可原文见`frontend/fonts/*-OFL.txt`与`fonts/zcoolqingkehuangyou-OFL.txt`、`fonts/righteous-OFL.txt`。
