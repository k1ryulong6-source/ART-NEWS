# GitHub Pages 打开成另一个网站 · T019

2026-10-13 用户报告资讯网址显示「Selah／私人学歌老师」，已实际复现。

## 原因和证据

- Pages API 返回资讯项目地址 `https://k1ryulong6-source.github.io/ART-NEWS/`，部署成功。
- 全新 Chromium 直接访问项目，显示「映间 · 个人文化信息台」，432 条资料／158 活动，无脚本错误。
- 同一浏览器先访问域名首页，等待其 Service Worker 激活，再打开完整项目地址：地址栏仍是 `/ART-NEWS/`，实际标题却是「Selah · 私人学歌老师」。
- 域名首页的 `/sw.js` 注册范围为整个域名，所有 navigate 请求都返回缓存中的 `/index.html`，没有限制学歌应用路径。
- 因而 HTTP 200 和全新浏览器验收不能覆盖已安装同域名其他 PWA 的情形。无痕窗口可作为临时访问方式，不代表永久修复。

## 修复范围

学歌发布仓库由 Selah 源码生成。永久修复应在其 `scripts/build-pwa.mjs` 中限制导航回退仅用于 `/` 与 `/index.html`，其他项目导航交给正常网络。保留根应用离线资源、缓存生命周期、IndexedDB 和用户媒体；不能通过清空所有站点数据解决。

两行补丁已准备，并完成 Node 回调验证和真实 Chromium Service Worker 回归（合成 HTML 外壳）：旧规则复现错误，新规则正确打开 `/ART-NEWS/`，根应用仍返回自己的缓存外壳。已在学歌生产站发布；部署成功：https://github.com/k1ryulong6-source/k1ryulong6-source.github.io/actions/runs/38393132033。同一个实际生产浏览器保留旧 Worker，升级前复现错误，点击“更新 Selah”后，完整资讯地址正确显示映间。合成存储标记保持；资讯 390px／1440px 五页与根站离线重开验证通过。

用户已明确允许修改 Selah。已修复私有源码生成脚本并重新生成发布文件；发布产物仅 sw.js 两行导航限制与生成版 README 改动，原 App 资源不变。私有源码 138 项 Node、TypeScript strict／生产构建、58 项恢复核验与 4 组 PWA 浏览器检查通过；没有公开私人源码或媒体。

浏览器已运行的旧 Worker 可能继续控制旧标签页。若仍显示 Selah，待页面出现“更新 Selah”，点击一次，再重新打开完整资讯地址；这是保留数据的正常更新。无需清空浏览器、删除个人存储或重装。新安装 Worker 已正确限制导航范围。
