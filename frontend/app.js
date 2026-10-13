(async function () {
  'use strict';
  const C = window.CultureCore, boot = window.CULTURE_BOOTSTRAP;
  const $ = id => document.getElementById(id), e = C.escape;
  const paths = { today: 'M3 12h18M12 3v18M5.6 5.6l12.8 12.8M5.6 18.4 18.4 5.6', explore: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z', calendar: 'M5 5h14v16H5zM8 3v4M16 3v4M5 10h14', bookmarks: 'M6 3h12v18l-6-4-6 4z', settings: 'M4 7h16M4 17h16M9 4v6M15 14v6', bookmark: 'M6 3h12v18l-6-4-6 4z' };
  const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.bookmark}"/></svg>`;
  let dataset = boot.live?.content?.length ? boot.live : boot.dataset, preferences = structuredClone(boot.preferences), bookmarks = [], server = false;
  let localWritable = true, toastTimer, refreshTimer;
  let notifications = [], sourceStatus = dataset.source_status || [];
  const makeId = () => typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const state = { view: 'today', channel: 'all', kind: 'all', country: 'all', city: 'all', language: 'all', query: '', mode: 'demo', month: '2026-10', selectedDate: null, bookmarkStatus: 'all', readerId: null, readerTab: 'original', readerReturn: 'today', readerForced: false };
  function readLocal() {
    try {
      const stored = JSON.parse(localStorage.getItem('culture-desk-v1') || 'null');
      if (stored) {
        const valid = C.validateImport(stored, { ...boot.dataset, content: [...boot.dataset.content, ...(boot.live?.content || [])], events: [...boot.dataset.events, ...(boot.live?.events || [])] }, boot.preferences);
        preferences = valid.preferences; bookmarks = valid.bookmarks;
      }
    } catch { toast('本地记录未能读取，已使用默认设置'); }
  }
  function writeLocal() {
    try { localStorage.setItem('culture-desk-v1', JSON.stringify({ schema_version: 1, preferences, bookmarks })); return true; }
    catch { localWritable = false; toast('浏览器禁止保存，请导出数据后再离开'); return false; }
  }
  async function api(path, options = {}) {
    const response = await fetch(`/api${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers }, signal: AbortSignal.timeout(5000) });
    if (!response.ok) { const error = await response.json().catch(() => ({})); throw new Error(typeof error.detail === 'string' ? error.detail : '保存失败，请重试'); }
    return response.json();
  }
  function toast(message) {
    $('toast').textContent = message; $('toast').classList.add('show'); clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $('toast').classList.remove('show'), 3500);
  }
  if (location.protocol !== 'file:') {
    try {
      const response = await fetch('/api/health', { signal: AbortSignal.timeout(1500) });
      if (response.ok && (await response.json()).storage === 'sqlite') {
        [dataset, preferences, bookmarks] = await Promise.all([api('/dataset'), api('/preferences'), api('/bookmarks')]);
        server = true;
      }
    } catch { /* Static hosting deliberately uses the browser storage adapter. */ }
  }
  if (!server) readLocal();
  state.mode = dataset.mode || 'demo'; state.month = (state.mode === 'demo' ? dataset.reference_date : C.localDate(preferences.reading_timezone)).slice(0, 7); sourceStatus = dataset.source_status || [];
  if (server) notifications = await api('/notifications').catch(() => []);
  function artworkIllustration(row, large = false) {
    const id = e(row.id.replace(/[^a-z0-9]/gi, '')) + (large ? 'large' : 'small');
    const variant = [...row.id].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 3;
    if (row.channel === 'film') return `<svg viewBox="0 0 900 480" preserveAspectRatio="xMidYMid slice" role="img" aria-label="电影主题原创示意图"><defs><linearGradient id="sky${id}" x2="0" y2="1"><stop stop-color="#d0cbb5"/><stop offset="1" stop-color="#a6b7a5"/></linearGradient><linearGradient id="hill${id}" x2="0" y2="1"><stop stop-color="#394a42"/><stop offset="1" stop-color="#1b2e29"/></linearGradient></defs><rect width="900" height="480" fill="url(#sky${id})"/><circle cx="${650 + variant * 30}" cy="130" r="67" fill="#a34c3a" opacity=".9"/><path d="M0 300 110 230 195 276 292 163 414 278 580 201 670 300 810 215 900 246V480H0z" fill="#718676"/><path d="M0 341 153 282 297 362 402 256 582 336 704 266 900 329V480H0z" fill="url(#hill${id})"/><path d="M0 413 Q210 353 460 435 T900 418V480H0" fill="#1c2925"/><path d="M460 480 469 380 496 363 518 480" fill="#b5aa8e" opacity=".65"/><g fill="#17261f"><rect x="119" y="281" width="4" height="110"/><path d="m121 254-34 88h68z"/><rect x="752" y="301" width="4" height="95"/><path d="m754 272-30 82h60z"/></g><g opacity=".08" stroke="#fff"><path d="M0 70h900M0 140h900M0 210h900M0 280h900M0 350h900M0 420h900"/></g><text x="39" y="62" font-size="13" letter-spacing="5" fill="#3e4d43" font-family="Georgia">THE SPACE BETWEEN FRAMES</text></svg>`;
    if (row.channel === 'art') return `<svg viewBox="0 0 900 480" preserveAspectRatio="xMidYMid slice" role="img" aria-label="艺术主题原创示意图"><rect width="900" height="480" fill="${['#ded7c6', '#b8bdae', '#e3d9c4'][variant]}"/><rect x="235" y="-45" width="360" height="610" transform="rotate(-13 450 240)" fill="#ece8d9"/><circle cx="405" cy="218" r="150" fill="${['#4b6574', '#a8533d', '#656b54'][variant]}"/><path d="M405 69a150 150 0 0 1 0 300z" fill="#bbb5a3" opacity=".72"/><rect x="517" y="225" width="164" height="210" fill="#b87c51"/><path d="M158 400h580M202 55v389" stroke="#7d8170" stroke-width="2" opacity=".35"/><circle cx="599" cy="110" r="25" fill="#aa4335"/><text x="38" y="52" font-size="13" letter-spacing="6" fill="#6b675b" font-family="Georgia">FORMS / IN EVERYDAY LIFE</text></svg>`;
    return `<svg viewBox="0 0 900 480" preserveAspectRatio="xMidYMid slice" role="img" aria-label="摄影主题原创街景示意图"><rect width="900" height="480" fill="#c6c8bf"/><path d="M0 0h280v367H0z" fill="#626b61"/><path d="M0 0h160v400H0z" fill="#3f4940"/><path d="M590 0h310v400H590z" fill="#777b6e"/><path d="M730 0h170v450H730z" fill="#414b43"/><path d="M280 85h310v255H280z" fill="#a4aa9c"/><path d="M0 480 358 290h186l356 190" fill="#697368"/><path d="m367 290-181 190M535 290l196 190" stroke="#b9bba8" stroke-width="3"/><g fill="#b6b9a9"><path d="M25 55h48v64H25zm89 0h34v64h-34zM25 169h48v64H25zm89 0h34v64h-34zM610 58h71v86h-71zm100 0h34v86h-34zM610 185h71v86h-71z"/></g><path d="m180 126 400 41M183 99l398 40" stroke="#475347" stroke-width="3"/><path d="M204 0v377M579 0v349" stroke="#364638" stroke-width="5"/><circle cx="469" cy="298" r="10" fill="#27372c"/><path d="M458 309h23l5 51h-32zM461 352l-6 42m22-42 8 42" stroke="#28392d" stroke-width="6" fill="#27372c"/><path d="M370 220h119v13H370z" fill="#a04735" opacity=".8"/><text x="38" y="445" font-size="13" letter-spacing="6" fill="#e2e2d4" font-family="Georgia">NOTES FROM THE CITY</text></svg>`;
  }
  function artwork(row, large = false) {
    if (!row.image_url && row.event_type) {
      const link = dataset.content_events.find(item => item.event_id === row.id);
      const content = dataset.content.find(item => item.id === link?.content_id);
      if (content?.image_url) row = { ...row, image_url: content.image_url, image_alt: content.image_alt, image_credit: content.image_credit, source_id: content.source_id };
    }
    const image = C.safeImageUrl(row.image_url), illustration = artworkIllustration(row, large);
    return image ? `<div class="source-art"><img class="source-photo" src="${e(image)}" alt="${e(row.image_alt || C.displayTitle(row))}" loading="${large ? 'eager' : 'lazy'}" referrerpolicy="no-referrer" data-source-photo><div class="art-fallback" hidden>${illustration}</div><span class="image-caption">配图来源：${e(row.image_credit || sourceName(row))}</span></div>` : `<div class="source-art">${illustration}<span class="image-caption">暂无来源配图 · 原创示意</span></div>`;
  }
  document.addEventListener('error', event => {
    const img = event.target;
    if (!img.matches?.('img[data-source-photo]')) return;
    img.hidden = true; const box = img.closest('.source-art');
    box.querySelector('.art-fallback').hidden = false;
    box.querySelector('.image-caption').textContent = '来源配图暂不可用 · 请查看原文';
  }, true);
  function readingBody(row) {
    const translated = !row.summary_zh && row.translated_excerpt_zh;
    return `<section class="reading-section"><h3>中文${translated ? '译文' : '摘要'}</h3><p class="detail-summary">${e(row.summary_zh || translated || (row.language === 'zh' ? row.excerpt_original : '') || '此来源暂未提供中文摘要；可使用下方翻译全文入口。')}</p>${row.translated_title_zh || translated ? '<p class="reading-note">机器翻译，仅供阅读参考；专名与事实请核对原文。</p>' : ''}<h3>原文摘录</h3>${row.excerpt_original ? `<p class="original-excerpt" lang="${e(row.language)}">${e(row.excerpt_original)}</p><p class="reading-note">来源公开摘要或短摘录，非文章全文。</p>` : '<p class="reading-note">来源尚未提供可读摘录，原标题与全文入口保留。</p>'}<div class="reading-links"><a class="button secondary" href="${e(C.safeUrl(row.original_page_url || row.canonical_url))}" target="_blank" rel="noopener noreferrer">阅读全文 ↗</a><a class="button secondary" href="${e(C.translatedArticleUrl(row))}" target="_blank" rel="noopener noreferrer">翻译原文全文 ↗</a></div></section>`;
  }
  function sourceName(row) { return dataset.sources.find(s => s.id === row.source_id)?.name || '来源待确认'; }
  function filters() {
    const disabled = state.view === 'bookmarks' ? [] : preferences.disabled_sources || [];
    const disabledEventIds = dataset.events.filter(event => { const links = dataset.content_events.filter(link => link.event_id === event.id); return links.length && links.every(link => disabled.includes(dataset.content.find(row => row.id === link.content_id)?.source_id)); }).map(event => event.id);
    return { channel: state.channel, kind: state.kind, country: state.country, city: state.city, language: state.language, query: state.query, buzz: preferences.industry_buzz.enabled, disabledSources: disabled, disabledEventIds };
  }
  function findBookmark(type, id) { return bookmarks.find(b => b[type === 'content' ? 'content_id' : 'event_id'] === id); }
  function nav() {
    const labels = { today: '今日', explore: '探索', calendar: '日历', bookmarks: '收藏', settings: '设置' };
    $('navigation').innerHTML = Object.entries(labels).map(([key, label]) => `<button class="nav-button ${state.view === key ? 'active' : ''}" data-view="${key}" ${state.view === key ? 'aria-current="page"' : ''}><span class="nav-icon">${icon(key)}</span>${label}${key === 'bookmarks' ? `<span class="nav-count">${bookmarks.length}</span>` : ''}</button>`).join('');
    $('coordinate-button').innerHTML = `${e(preferences.news_scope === 'global' ? '全球视野' : preferences.default_city)} <span>↗</span>`;
  }
  function heading(title, subtitle, eyebrow) {
    return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="subtitle">${subtitle}</p></div><div class="date-stamp"><strong>${C.dateLabel(readingDate())}</strong>${state.mode === 'demo' ? '示例参考日 · 非真实安排' : '你的文化日常'}</div></div>`;
  }
  function notice() {
    const last = sourceStatus.map(source => source.last_success_at).filter(Boolean).sort().at(-1);
    const label = last ? new Intl.DateTimeFormat('zh-CN', { timeZone: preferences.reading_timezone, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(last)) : '未更新';
    return `<div class="notice"><span>${state.mode === 'demo' ? '<b>演示模式</b> · 内容与日期均为虚构示例，图形为原创示意。' : dataset.content.length ? `<b>真实资讯</b> · ${dataset.content.length} 条内容 / ${dataset.events.length} 项活动 · ${server ? '最后读取' : '资讯快照'} ${e(label)}` : '<b>真实资讯</b> · 还没有读取到内容，可点击更新或查看来源状态。'}</span><button data-action="mode">${state.mode === 'demo' ? '查看真实资讯' : '体验示例'} ↗</button></div>`;
  }
  function filterBar(withTabs = true) {
    return `<div class="filters">${withTabs ? `<div class="tabs" role="group" aria-label="频道筛选">${[['all', '全部'], ...Object.entries(C.channels)].map(([key, label]) => `<button class="tab ${state.channel === key && state.kind !== 'industry_buzz' ? 'active' : ''}" data-channel="${key}" aria-pressed="${state.channel === key && state.kind !== 'industry_buzz'}">${label}</button>`).join('')}<button class="tab ${state.kind === 'industry_buzz' ? 'active' : ''}" data-kind="industry_buzz" aria-pressed="${state.kind === 'industry_buzz'}">圈内动态</button></div>` : ''}<div class="filter-selects"><select id="country-filter" aria-label="国家筛选"><option value="all">所有地区</option>${Object.entries(C.countryLabels).map(([code, label]) => `<option value="${code}" ${state.country === code ? 'selected' : ''}>${e(label)}</option>`).join('')}<option value="unknown" ${state.country === 'unknown' ? 'selected' : ''}>地点未说明</option></select><select id="city-filter" aria-label="城市筛选"><option value="all">所有城市</option>${Object.keys(C.cityCountries).filter(city => state.country === 'all' || C.cityCountries[city] === state.country).map(city => `<option ${state.city === city ? 'selected' : ''}>${e(city)}</option>`).join('')}</select>${state.view !== 'calendar' ? `<select id="language-filter" aria-label="资讯原文语言"><option value="all">原文语言 · 全部</option>${Object.entries(C.languageLabels).map(([code, label]) => `<option value="${code}" ${state.language === code ? 'selected' : ''}>${e(label)}</option>`).join('')}</select>` : ''}<button class="text-link" data-scope="global">全球</button><button class="text-link" data-scope="japan">日本专题</button><button class="text-link" data-action="photo-calls">摄影征集</button>${state.view === 'calendar' ? `<select id="event-type-filter" aria-label="活动类型"><option value="all">全部活动类型</option>${Object.entries(C.eventTypes).map(([code,label]) => `<option value="${code}" ${state.kind === code ? 'selected' : ''}>${e(label)}</option>`).join('')}</select>` : ''}<label class="toggle-label"><input id="buzz-filter" type="checkbox" ${preferences.industry_buzz.enabled ? 'checked' : ''}>圈内动态</label></div></div>`;
  }
  function empty(title, text, action = '') { return `<div class="empty"><div class="empty-icon">◯</div><h2>${title}</h2><p>${text}</p>${action}</div>`; }
  function meta(row) { return `<div class="meta"><span class="channel-tag">${C.channels[row.channel]}</span><span class="meta-dot">/</span><span>${e(C.kinds[row.kind] || C.eventTypes[row.event_type] || '资讯')}</span><span class="meta-dot">·</span><span>${e(C.locationLabel(row))}</span></div>`; }
  function saveButton(type, id, inline = false) {
    const saved = findBookmark(type, id);
    return `<button class="${inline ? 'save-inline' : 'save-button'} ${saved ? 'saved' : ''}" data-save-type="${type}" data-save-id="${e(id)}" aria-label="${saved ? '取消收藏' : '收藏'}" aria-pressed="${Boolean(saved)}">${inline ? (saved ? '已收藏 ✓' : '＋ 收藏') : icon('bookmark')}</button>`;
  }
  const readingDate = () => state.mode === 'demo' ? dataset.reference_date : C.localDate(preferences.reading_timezone);
  function publicationLabel(row) { const day = row.published_at?.slice(0, 10); const age = C.daysBetween(day, readingDate()); return age === null ? '发布日期未提供' : (age > (preferences.recent_news_days || 30) ? '旧资料 · ' : '') + C.dateLabel(day); }
  function card(row, showStatus = false) {
    const saved = findBookmark('content', row.id);
    return `<article class="content-card"><div class="card-art">${artwork(row)}${saveButton('content', row.id)}</div><div class="card-body">${meta(row)}<h3><button class="card-title" data-detail="${e(row.id)}" data-type="content">${e(C.displayTitle(row))}</button></h3><p class="card-summary">${e(C.readingSummary(row))}</p><div class="card-footer"><span>${e(sourceName(row).replace('（虚构）', ''))}</span><span class="demo-label">${row.is_demo ? '示例内容' : e(publicationLabel(row))}</span></div>${showStatus && saved ? `<select class="bookmark-status" data-bookmark-status="${e(saved.id)}" aria-label="收藏状态">${Object.entries(C.statusNames).map(([k, v]) => `<option value="${k}" ${saved.status === k ? 'selected' : ''}>${v}</option>`).join('')}</select>` : ''}</div></article>`;
  }
  const referenceFor = row => row.is_demo ? dataset.reference_date : C.localDate(row.timezone || 'UTC');
  function eventRow(row, detailed = true) {
    const status = C.eventState(row, referenceFor(row));
    const date = row.start_date?.split('-') || [];
    return `<div class="event-row"><div class="date-block"><small>${date[1] || '—'} 月</small><strong>${row.date_precision === 'day' ? date[2] : '—'}</strong></div><div class="event-row-main"><span class="event-badge ${status.tone}">${status.label}</span><h3><button class="card-title" data-detail="${e(row.id)}" data-type="event">${e(C.displayTitle(row))}</button></h3><p>${e(C.locationLabel(row))} · ${C.eventTypes[row.event_type]}${detailed ? ` · ${e(C.timeLabel(row))}${row.end_date ? ' — ' + C.dateLabel(row.end_date) : ''}` : ''}</p></div>${saveButton('event', row.id, true)}</div>`;
  }
  function upcoming() {
    return dataset.events.filter(row => C.matches(row, { ...filters(), kind: 'all' }) && row.date_precision === 'day' && ((C.daysBetween(referenceFor(row), row.start_date) >= 0 && C.daysBetween(referenceFor(row), row.start_date) <= (preferences.upcoming_window_days || 14)) || (row.end_date && C.daysBetween(referenceFor(row), row.end_date) >= 0 && C.daysBetween(referenceFor(row), row.end_date) <= 7)))
      .sort((a, b) => { const aEnd = C.daysBetween(referenceFor(a), a.end_date), bEnd = C.daysBetween(referenceFor(b), b.end_date); const aSoon = aEnd !== null && aEnd <= 7, bSoon = bEnd !== null && bEnd <= 7; return Number(bSoon) - Number(aSoon) || String(a.start_date).localeCompare(String(b.start_date)); }).slice(0, 3);
  }
  function agenda() {
    const rows = upcoming();
    return `<aside class="agenda"><div class="section-title"><h2>接下来，去看看</h2><span>ON THE CALENDAR</span></div><p class="agenda-intro">新片、开幕，以及别错过的最后几天。</p>${rows.map(row => { const date = row.start_date.split('-'), status = C.eventState(row, referenceFor(row)); return `<button class="agenda-item" data-detail="${e(row.id)}" data-type="event"><div class="date-block"><small>${date[1]} 月</small><strong>${date[2]}</strong></div><div><span class="event-badge ${status.tone}">${status.label}</span><h3>${e(C.displayTitle(row))}</h3><p>${e(C.locationLabel(row))} · ${C.eventTypes[row.event_type]}</p></div></button>`; }).join('') || '<p class="compact-note">没有符合条件的近期活动。</p>'}<button class="agenda-more" data-view="calendar">打开完整日历 →</button><div class="quote-note">“在赶路的日子里，<br>也别忘了停下来看看。”</div></aside>`;
  }
  function today() {
    const rows = C.selectToday(dataset.content.filter(row => C.matches(row, filters())), preferences, { ...dataset, reference_date: readingDate() });
    const feature = rows.find(row => row.id === 'demo-film') || rows[0];
    const others = rows.filter(row => row.id !== feature?.id);
    return heading('留一点时间，给值得看的世界。', '世界各地的电影、艺术、摄影，还有一点圈内故事。日本上映与展览可单独查看。', 'A DAILY DOSE OF CULTURE') + notice() + filterBar() + (feature ? `<div class="hero-grid"><article class="feature"><div class="feature-art">${artwork(feature, true)}<span class="feature-number">EDITOR’S PICK / 01</span></div><div class="feature-body">${meta(feature)}<h2><button class="card-title" data-detail="${e(feature.id)}" data-type="content">${e(C.displayTitle(feature))}</button></h2><p class="feature-summary">${e(C.readingSummary(feature))}</p><div class="feature-footer"><span>${e(feature.selection_reason)} · ${feature.is_demo ? '示例内容' : e(sourceName(feature))}</span><button class="text-link" data-detail="${e(feature.id)}" data-type="content">阅读这条资讯 <span>↗</span></button></div></div></article>${agenda()}</div><section class="content-section"><div class="section-title"><h2>今日值得留意<span class="count-label">${rows.length} 条精选</span></h2><button class="text-link" data-view="explore">探索全部 ↗</button></div><div class="card-grid">${others.map(row => card(row)).join('')}</div></section>` : empty('给新发现留一点空间', state.mode === 'live' ? '当前筛选没有近期资讯。旧资料仍可在探索中查阅，也可清除筛选或更新来源。' : '没有符合筛选条件的精选，试着换一个频道或关键词。', '<button class="button secondary" data-action="reset-filters">清除筛选</button>'));
  }
  function explore() {
    const rows = dataset.content.filter(row => C.matches(row, filters()));
    return heading('发现，发生在好奇之后。', '从一部电影、一场展览，或一本摄影集开始。', 'FOLLOW YOUR CURIOSITY') + notice() + filterBar() + `<div class="filter-summary">${rows.length} 条内容${state.query ? ' · 搜索：' + e(state.query) : ''} · 原文与出处保留在详情中</div>` + (rows.length ? `<div class="card-grid">${rows.map(row => card(row)).join('')}</div>` : empty('还没有找到这条线索', '试着清除筛选，或换一个关键词。', '<button class="button secondary" data-action="reset-filters">清除筛选</button>'));
  }
  function calendar() {
    const [year, month] = state.month.split('-').map(Number), first = new Date(Date.UTC(year, month - 1, 1)).getUTCDay(), count = new Date(Date.UTC(year, month, 0)).getUTCDate();
    const rows = dataset.events.filter(row => C.matches(row, filters()));
    const activeOn = day => rows.filter(row => row.date_precision === 'day' && row.start_date <= day && (row.end_date || row.start_date) >= day);
    const days = Array.from({ length: first }, () => '<div class="calendar-day blank" aria-hidden="true"></div>');
    for (let n = 1; n <= count; n++) {
      const day = `${state.month}-${String(n).padStart(2, '0')}`, active = activeOn(day);
      days.push(`<button class="calendar-day ${day === readingDate() ? 'reference' : ''} ${day === state.selectedDate ? 'selected' : ''}" data-date="${day}" aria-label="${day}，${active.length} 项活动" aria-pressed="${day === state.selectedDate}"><span>${n}</span>${active.slice(0, 2).map(row => `<span class="calendar-dot ${row.channel}">${C.eventTypes[row.event_type]}</span>`).join('')}${active.length > 2 ? `<span class="calendar-dot">＋${active.length - 2}</span>` : ''}</button>`);
    }
    while (days.length % 7) days.push('<div class="calendar-day blank" aria-hidden="true"></div>');
    const visible = state.selectedDate ? activeOn(state.selectedDate) : rows.filter(row => row.start_date?.slice(0, 7) === state.month || row.end_date?.slice(0, 7) === state.month || (row.date_precision === 'day' && row.start_date < state.month + '-01' && row.end_date >= state.month + '-01'));
    return heading('把想看的，放进日历。', '上映、开幕、闭展。世界各地的活动，按当地日期展示。', 'MAKE ROOM FOR WHAT MATTERS') + notice() + filterBar() + `<div class="calendar-layout"><div><div class="calendar-panel"><div class="calendar-toolbar"><h2>${year} 年 ${month} 月</h2><div class="month-controls"><button data-month="-1" aria-label="上个月">←</button><button data-action="reference-month">参考月</button><button data-month="1" aria-label="下个月">→</button></div></div><div class="week-row">${['日', '一', '二', '三', '四', '五', '六'].map(day => `<div>${day}</div>`).join('')}</div><div class="calendar-days">${days.join('')}</div><div class="calendar-legend"><span><i></i>电影</span><span><i class="art"></i>艺术</span><span><i class="photography"></i>摄影</span></div></div><section class="event-list"><div class="section-title"><h2>${state.selectedDate ? C.dateLabel(state.selectedDate) : '本月活动'}<span class="count-label">${visible.length} 项</span></h2>${state.selectedDate ? '<button class="text-link" data-action="clear-date">显示全月</button>' : ''}</div>${visible.map(row => eventRow(row)).join('') || '<p class="compact-note">该日期范围内没有符合条件的活动。</p>'}</section></div>${agenda()}</div><p class="compact-note" style="margin-top:20px">仅公布月份的活动列在清单，不填入具体日期；展览日期范围不代表每天开放，请查看休馆说明。</p>`;
  }
  function bookmarkPage() {
    const saved = bookmarks.filter(row => state.bookmarkStatus === 'all' || row.status === state.bookmarkStatus);
    const records = saved.map(row => ({ bookmark: row, record: (row.content_id ? dataset.content : dataset.events).find(x => x.id === (row.content_id || row.event_id)) })).filter(item => item.record && C.matches(item.record, filters()));
    const contents = records.filter(item => item.bookmark.content_id), events = records.filter(item => item.bookmark.event_id);
    return heading('一些值得留住的念头。', '想看、准备去、已看过。让好奇心有自己的去处。', 'YOUR PERSONAL COLLECTION') + notice() + filterBar() + `<div class="tabs" style="margin-bottom:23px">${[['all', '全部状态'], ...Object.entries(C.statusNames)].map(([key, label]) => `<button class="tab ${state.bookmarkStatus === key ? 'active' : ''}" data-status="${key}">${label}</button>`).join('')}</div>` + (records.length ? `<div class="card-grid">${contents.map(item => card(item.record, true)).join('')}</div>${events.length ? `<section class="event-list"><div class="section-title"><h2>收藏的活动</h2></div>${events.map(item => eventRow(item.record) + `<select class="bookmark-status" data-bookmark-status="${e(item.bookmark.id)}" aria-label="活动收藏状态">${Object.entries(C.statusNames).map(([k, v]) => `<option value="${k}" ${item.bookmark.status === k ? 'selected' : ''}>${v}</option>`).join('')}</select>`).join('')}</section>` : ''}` : empty('你的收藏，从一次心动开始。', '点击资讯卡片上的书签，或收藏一个活动。当前模式与筛选条件会影响可见收藏。', '<button class="button" data-view="explore">去探索 →</button>'));
  }
  function settings() {
    const topics = [...new Set([...boot.preferences.interests, '街头摄影', '电影访谈', '摄影征集', ...preferences.interests])];
    const timezones = [...new Set([preferences.reading_timezone, 'UTC', 'America/Los_Angeles', ...C.registry.regions.map(r => r.timezone)])];
    return heading('把它调成你的样子。', '选择想关注的城市与主题，留下属于自己的阅读节奏。', 'A SPACE THAT FEELS LIKE YOU') + notice() + `<div class="settings-grid"><div><form class="settings-panel" id="preferences-form"><h2>我的文化坐标</h2><p>这些设置会影响今日精选和关注排序。</p><label class="form-field">阅读范围<select name="news_scope"><option value="global" ${preferences.news_scope === 'global' ? 'selected' : ''}>全球资讯</option><option value="follow_city" ${preferences.news_scope === 'follow_city' ? 'selected' : ''}>优先关注城市</option></select></label><label class="form-field">主要关注城市<select name="default_city">${[...new Set([preferences.default_city, ...Object.keys(C.cityCountries)])].map(city => `<option ${preferences.default_city === city ? 'selected' : ''}>${e(city)}</option>`).join('')}</select></label><div class="form-field"><span>感兴趣的主题</span><div class="interest-options">${topics.map(topic => `<label class="interest-chip"><input type="checkbox" name="interests" value="${e(topic)}" ${preferences.interests.includes(topic) ? 'checked' : ''}>${e(topic)}</label>`).join('')}</div></div><label class="form-field">关注对象<textarea name="followed_entities" placeholder="导演、摄影师、艺术家或场馆；每行一个">${e(preferences.followed_entities.join('\n'))}</textarea><small>名称会与标题和摘要匹配，用来提高相关内容的排序。</small></label><label class="form-field">阅读时区<select name="reading_timezone">${timezones.map(zone => `<option ${preferences.reading_timezone === zone ? 'selected' : ''}>${e(zone)}</option>`).join('')}</select><small>活动倒计时始终使用活动当地日期。</small></label><label class="form-field">每天精选数量<select name="daily_selection_limit">${[5, 10, 15, 20].map(n => `<option value="${n}" ${preferences.daily_selection_limit === n ? 'selected' : ''}>${n} 条</option>`).join('')}</select></label><label class="toggle-label" style="font-size:11px;margin-bottom:20px"><input type="checkbox" name="buzz" ${preferences.industry_buzz.enabled ? 'checked' : ''}>收录少量圈内动态（精选约 10%）</label><p class="compact-note">器材评测已排除。未证实消息不进入今日精选。</p><button class="button accent" type="submit">保存我的偏好 →</button></form><section class="settings-panel"><h2>带走你的收藏</h2><p>导出收藏和偏好，再导入到另一个浏览器或本地版本。</p><div class="button-row"><button class="button" data-action="export">导出 JSON ↓</button><button class="button secondary" data-action="import">导入记录 ↑</button><button class="button secondary" data-action="ics">导出日历 ↓</button><input id="import-input" type="file" accept="application/json,.json" hidden></div><div class="storage-note">${server ? '当前保存于本地 SQLite 数据库。' : localWritable ? '当前保存于此浏览器；换设备前请导出备份。' : '当前浏览器无法持久保存，请及时导出。'}导出不包含任何模型密钥。</div></section></div><div><section class="settings-panel"><h2>资讯从哪里来</h2><p>来源按实际读取结果标记，日期与原文始终可核对。</p>${boot.sources.sources.map(source => { const status = sourceStatus.find(row => row.id === source.id); const enabled = source.enabled && !(preferences.disabled_sources || []).includes(source.id); return `<div class="source-row"><a href="${e(C.safeUrl(source.homepage_url))}" target="_blank" rel="noopener noreferrer">${e(source.name)} ↗</a><span>${enabled ? status?.last_run?.status === 'failed' ? '上次读取失败' : status?.last_success_at ? '已读取' : '已接入' : source.enabled ? '已停用' : '待核实'}</span>${source.enabled ? `<input type="checkbox" data-source-toggle="${e(source.id)}" ${enabled ? 'checked' : ''} aria-label="启用${e(source.name)}">` : ''}</div>`; }).join('')}<p class="compact-note" style="margin-top:17px">真实资讯与虚构示例分开显示。来源读取失败时保留上次成功内容，并显示读取状态。</p></section><section class="settings-panel"><h2>为接力而建设</h2><p>作品之外，这也是一个可以继续生长的项目。</p><p class="compact-note">源码包包含需求、任务清单、数据契约和 AI 交接记录。下一位建设者可以按任务编号继续。</p><div class="source-row"><span>当前版本</span><span>0.7 · 站内原文阅读</span></div><div class="source-row"><span>网页内容</span><span>示例模式 / 真实模式分离</span></div><div class="source-row"><span>接下来</span><span>更多城市 · 更多官方来源</span></div></section></div></div>`;
  }
  function readerPage() {
    const row = dataset.content.find(item => item.id === state.readerId);
    if (!row) return empty('这条资讯暂不在当前资料中', '可以返回资讯列表，或查看真实资料模式。', '<button class="button" data-action="reader-back">返回资讯</button>');
    const url = C.originalPageUrl(row), saved = findBookmark('content', row.id);
    const canLoad = !row.is_demo && url && (row.original_embed_status !== 'blocked' || state.readerForced);
    const restricted = row.original_embed_status === 'blocked';
    const message = row.is_demo ? '这是虚构示例，没有真实原网页。' : restricted ? '该来源限制在其他网站内显示原网页。这条资讯及来源已保留。' : '原网页当前未能确认可加载。这条资讯及来源已保留，可以重试。';
    const original = canLoad ? `<div class="original-page-header"><span>来源原网页 · ${e(sourceName(row))}</span><button class="text-link" data-action="reader-reload">重新载入</button></div>${restricted ? '<p class="reading-note">该来源已限制嵌入；尝试加载不会更改来源的访问规则。</p>' : ''}<iframe class="original-frame" title="${e(sourceName(row))}原文：${e(row.title_original)}" src="${e(url)}" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer" allow="fullscreen" loading="eager"></iframe><p class="reading-note">这是来源网站的原网页。登录、订阅及来源访问规则由该网站提供。</p>` : `<div class="original-unavailable" role="status"><h2>原网页暂不能在此显示</h2><p>${message}</p>${!row.is_demo && url ? '<button class="button secondary" data-action="reader-try">重试站内原网页</button>' : ''}<p class="reading-note">以下是原文摘录，不是完整原文。</p>${row.excerpt_original ? `<p class="original-excerpt" lang="${e(row.language)}">${e(row.excerpt_original)}</p>` : '<p class="reading-note">来源未提供原文摘录，原始标题与原文地址保留。</p>'}</div>`;
    return `<article class="reader-page"><div class="reader-toolbar"><button class="text-link" data-action="reader-back">← 返回资讯</button><button class="button secondary reader-save" data-save-type="content" data-save-id="${e(row.id)}">${saved ? '已收藏 ✓' : '收藏这篇资讯'}</button></div><div class="eyebrow">${e(sourceName(row))} · ${e(publicationLabel(row))}</div><h1>${e(C.displayTitle(row))}</h1><p class="reader-original-title" lang="${e(row.language)}">${e(row.title_original)}</p><div class="reader-tabs" role="tablist" aria-label="阅读内容"><button role="tab" aria-selected="${state.readerTab === 'original'}" data-reader-tab="original">原文</button><button role="tab" aria-selected="${state.readerTab === 'chinese'}" data-reader-tab="chinese">中文摘要／译文</button><button role="tab" aria-selected="${state.readerTab === 'info'}" data-reader-tab="info">资料与活动</button></div><div class="reader-content" role="tabpanel">${state.readerTab === 'original' ? original : state.readerTab === 'chinese' ? `<div class="reader-translation">${row.image_url ? `<div class="detail-art">${artwork(row, true)}</div>` : ''}${row.is_demo ? `<p>${e(row.summary_zh)}</p>` : readingBody(row)}</div>` : `<div class="reader-information">${meta(row)}<p>原始来源：${e(sourceName(row))} · ${e(C.languageLabels[row.language] || row.language)}</p>${dataset.content_events.filter(link => link.content_id === row.id).map(link => dataset.events.find(item => item.id === link.event_id)).filter(Boolean).map(item => eventRow(item)).join('') || '<p>这篇资讯没有关联的日历活动。</p>'}</div>`}</div>${!row.is_demo && url ? `<div class="reader-source-link"><span>原文地址</span><a href="${e(url)}" target="_blank" rel="noopener noreferrer">${e(url)}</a></div>` : ''}</article>`;
  }
  function openReader(id, route = true) {
    if (state.view !== 'reader') state.readerReturn = state.view;
    state.readerId = id; state.readerTab = 'original'; state.readerForced = false; state.view = 'reader';
    if ($('detail-dialog').open) $('detail-dialog').close();
    if (route) history.pushState(null, '', C.readerRoute(id));
    render(); window.scrollTo({ top: 0 });
  }
  function render() {
    nav(); $('inbox-button').textContent = notifications.filter(row => !row.read).length || '铃'; document.querySelector('footer span').textContent = state.mode === 'demo' ? '所有示例均为虚构；图形为作品示意。' : '来源配图与机器翻译均有标注；缺图使用原创示意。'; $('main').innerHTML = ({ today, explore, calendar, bookmarks: bookmarkPage, settings, reader: readerPage }[state.view] || today)();
    const hash = state.view === 'reader' ? C.readerRoute(state.readerId) : '#' + state.view;
    if (location.hash !== hash) history.replaceState(null, '', hash);
  }
  function showDetail(type, id) {
    if (type === 'content') { openReader(id); return; }
    const row = (type === 'content' ? dataset.content : dataset.events).find(item => item.id === id);
    if (!row) return;
    const source = type === 'content' ? sourceName(row) : '活动日期证据';
    const href = C.safeUrl(type === 'content' ? row.canonical_url : row.evidence_url), isDemo = Boolean(row.is_demo);
    const related = type === 'content' ? dataset.content_events.filter(link => link.content_id === id).map(link => dataset.events.find(event => event.id === link.event_id)).filter(Boolean) : [];
    $('detail-body').innerHTML = `<div class="detail-art">${artwork(row, true)}</div><div class="detail-tag">${meta(row)}</div><h2 id="detail-title" class="detail-title">${e(C.displayTitle(row))}</h2><p class="detail-original">原标题：${e(row.title_original)}</p>${type === 'content' ? (isDemo ? `<p class="detail-summary">${e(row.summary_zh)}</p>` : readingBody(row)) : `<p class="detail-summary">${e(C.timeLabel(row))}${row.end_date ? ' — ' + C.dateLabel(row.end_date) : ''} · ${C.eventTypes[row.event_type]}</p>`}<dl class="detail-facts"><dt>消息状态</dt><dd><span class="evidence ${row.evidence_status === 'unverified' ? 'unverified' : ''}">${C.evidenceNames[row.evidence_status]}</span></dd><dt>信息来源</dt><dd>${e(source)}</dd><dt>地区</dt><dd>${e(C.locationLabel(row))}</dd>${type === 'event' ? `<dt>当地时区</dt><dd>${e(row.timezone)}</dd><dt>准确时刻</dt><dd>${e(C.timeLabel(row))}</dd>${row.time_note ? `<dt>时刻说明</dt><dd>${e(row.time_note)}</dd>` : ''}${row.eligibility_note ? `<dt>参赛资格</dt><dd>${e(row.eligibility_note)}</dd>` : ''}${row.booking_status ? `<dt>余票状态</dt><dd>${row.booking_status === 'sold_out' ? '官网显示已售罄；变动请核对原文' : '请核对官网实时余票'}</dd>` : ''}${row.booking_url ? `<dt>预约／报名</dt><dd><a href="${e(C.safeUrl(row.booking_url))}" target="_blank" rel="noopener noreferrer">打开官方入口 ↗</a></dd>` : ''}${row.event_type !== 'call_deadline' ? `<dt>场馆</dt><dd>${e(row.venue || '待确认')}</dd>` : ''}<dt>票价</dt><dd>${e(row.price_text || '待确认')}</dd>${row.event_type !== 'call_deadline' ? `<dt>休馆说明</dt><dd>${e(row.closure_note || '请以场馆官方说明为准')}</dd>` : ''}<dt>日期精度</dt><dd>${row.date_precision === 'day' ? '具体日期' : row.date_precision === 'month' ? '仅月份，具体日期待公布' : '待公布'}</dd>` : `<dt>原文语言</dt><dd>${e(C.languageLabels[row.language] || row.language || '待确认')}</dd><dt>发布时间</dt><dd>${e(publicationLabel(row))}</dd>`}<dt>数据状态</dt><dd>${isDemo ? '虚构示例 · 不可据此安排出行' : '真实资讯'}</dd><dt>原文链接</dt><dd>${isDemo ? '示例链接，不提供真实页面' : href ? `<a href="${e(href)}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>` : '链接待确认'}</dd></dl>${related.map(event => `<div class="detail-activity"><span class="event-badge">${e(C.countryLabels[event.country] || event.country)} · ${C.eventTypes[event.event_type]}</span><h3>${e(C.displayTitle(event))}</h3><p>${e(C.timeLabel(event))}${event.end_date ? ' — ' + C.dateLabel(event.end_date) : ''} · ${e(event.timezone)}</p><button class="text-link" style="margin-top:10px" data-detail="${e(event.id)}" data-type="event">查看活动信息 ↗</button></div>`).join('')}<div class="detail-controls"><button class="button accent" data-detail-save="${e(id)}" data-type="${type}">${findBookmark(type, id) ? '取消收藏' : '加入收藏'} ${findBookmark(type, id) ? '✓' : '＋'}</button>${!isDemo && href ? `<a class="button secondary" href="${e(href)}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>` : ''}</div>`;
    $('detail-dialog').dataset.type = type; $('detail-dialog').dataset.recordId = id;
    if (!$('detail-dialog').open) $('detail-dialog').showModal();
  }
  async function toggleSave(type, id) {
    const old = findBookmark(type, id);
    try {
      if (old) {
        if (server) await api(`/bookmarks/${encodeURIComponent(old.id)}`, { method: 'DELETE' });
        bookmarks = bookmarks.filter(row => row.id !== old.id);
      } else {
        const row = server ? await api('/bookmarks', { method: 'POST', body: JSON.stringify({ target_type: type, target_id: id }) }) : { id: makeId(), content_id: type === 'content' ? id : null, event_id: type === 'event' ? id : null, status: 'want_to_see', note: '', created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
        bookmarks.unshift(row);
      }
      const persisted = server || writeLocal();
      if (state.view === 'reader') { nav(); const button = document.querySelector('.reader-save'); if (button) button.textContent = findBookmark('content', state.readerId) ? '已收藏 ✓' : '收藏这篇资讯'; }
      else render();
      if (persisted) toast(old ? '已移除收藏' : '已收藏，给好作品留个位置');
      if ($('detail-dialog').open) showDetail($('detail-dialog').dataset.type, $('detail-dialog').dataset.recordId);
    } catch (error) { toast(error.message); }
  }
  async function savePreferences(next) {
    preferences = server ? await api('/preferences', { method: 'PUT', body: JSON.stringify(next) }) : next;
    const persisted = server || writeLocal(); render(); return persisted;
  }
  async function pollRefresh() {
    try {
      const status = await api('/jobs/status');
      if (status.running) { refreshTimer = setTimeout(pollRefresh, 2000); return; }
      dataset = await api(`/dataset?mode=${state.mode}`); sourceStatus = dataset.source_status || []; notifications = await api('/notifications'); render();
      document.querySelector('.refresh-control').disabled = false;
      const failures = status.last_refresh?.sources?.filter(source => source.status === 'failed').length || 0;
      toast(failures ? `更新结束，${failures} 个来源未能读取；可查看来源状态` : '资讯已更新');
    } catch (error) { document.querySelector('.refresh-control').disabled = false; toast(error.message); }
  }
  function inbox() {
    const rows = server ? notifications : bookmarks.filter(row => row.event_id && row.status !== 'seen').map(row => (boot.live?.events || []).find(event => event.id === row.event_id)).filter(Boolean).filter(event => { const delta = C.daysBetween(C.localDate(event.timezone), event.end_date || event.start_date); return delta >= 0 && delta <= 7; }).map(event => ({ id: event.id, event_id: event.id, title: (event.title_zh || event.title_original) + ' · ' + C.eventState(event, C.localDate(event.timezone)).label }));
    $('detail-body').innerHTML = `<h2 id="detail-title" class="detail-title">给好作品留的提醒</h2><p class="compact-note">仅提醒你收藏且还未看过的真实活动。${server ? '' : '静态版在打开页面时检查日期。'}</p>${rows.length ? rows.map(row => `<div class="detail-activity"><h3>${e(row.title)}</h3><div class="button-row"><button class="text-link" data-detail="${e(row.event_id)}" data-type="event">查看活动 ↗</button>${server && !row.read ? `<button class="text-link" data-read-notification="${e(row.id)}">标为已读</button>` : row.read ? '<span class="compact-note">已读</span>' : ''}</div></div>`).join('') : '<p class="compact-note">暂无近期提醒，收藏活动后会在开始／结束前提醒你。</p>'}`;
    if (!$('detail-dialog').open) $('detail-dialog').showModal();
  }
  document.addEventListener('click', async event => {
    const button = event.target.closest('button'); if (!button) return;
    if (button.dataset.view) { state.kind = 'all'; state.view = button.dataset.view; state.selectedDate = null; render(); window.scrollTo({ top: 0 }); }
    else if (button.dataset.readerTab) { state.readerTab = button.dataset.readerTab; state.readerForced = false; render(); }
    else if (button.dataset.action === 'reader-back') { state.view = state.readerReturn || 'today'; render(); window.scrollTo({ top: 0 }); }
    else if (button.dataset.action === 'reader-try') { state.readerForced = true; render(); }
    else if (button.dataset.action === 'reader-reload') { const frame = document.querySelector('.original-frame'); if (frame) frame.src = frame.getAttribute('src'); }
    else if (button.dataset.channel) { state.channel = button.dataset.channel; state.kind = 'all'; render(); }
    else if (button.dataset.kind) { state.kind = state.kind === button.dataset.kind ? 'all' : button.dataset.kind; state.channel = 'all'; state.view = 'explore'; render(); }
    else if (button.dataset.detail) showDetail(button.dataset.type, button.dataset.detail);
    else if (button.dataset.saveId) await toggleSave(button.dataset.saveType, button.dataset.saveId);
    else if (button.dataset.detailSave) await toggleSave(button.dataset.type, button.dataset.detailSave);
    else if (button.dataset.status) { state.bookmarkStatus = button.dataset.status; render(); }
    else if (button.dataset.date) { state.selectedDate = state.selectedDate === button.dataset.date ? null : button.dataset.date; render(); }
    else if (button.dataset.month) { const [y, m] = state.month.split('-').map(Number); const date = new Date(Date.UTC(y, m - 1 + Number(button.dataset.month), 1)); state.month = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`; state.selectedDate = null; render(); }
    else if (button.dataset.action === 'photo-calls') { state.view = 'calendar'; state.channel = 'photography'; state.kind = 'call_deadline'; state.query = ''; $('search').value = ''; state.country = state.city = state.language = 'all'; state.selectedDate = null; const next = dataset.events.filter(e => e.event_type === 'call_deadline' && e.start_date >= readingDate()).sort((a,b) => a.start_date.localeCompare(b.start_date))[0]; if (next) state.month = next.start_date.slice(0,7); render(); }
    else if (button.dataset.scope) { state.country = button.dataset.scope === 'japan' ? 'JP' : 'all'; state.city = 'all'; state.language = 'all'; render(); }
    else if (button.dataset.action === 'reset-filters') { state.channel = state.kind = state.country = state.city = state.language = 'all'; state.query = ''; $('search').value = ''; render(); }
    else if (button.dataset.action === 'mode') {
      const next = state.mode === 'demo' ? 'live' : 'demo'; button.disabled = true;
      try { dataset = server ? await api(`/dataset?mode=${next}`) : next === 'demo' ? boot.dataset : boot.live || { ...boot.dataset, mode: 'live', content: [], events: [], content_events: [], sources: [], reference_date: C.localDate(preferences.reading_timezone) }; state.mode = next; sourceStatus = dataset.source_status || []; state.month = (state.mode === 'demo' ? dataset.reference_date : C.localDate(preferences.reading_timezone)).slice(0, 7); state.selectedDate = null; render(); }
      catch (error) { button.disabled = false; toast(error.message); }
    }
    else if (button.dataset.action === 'reference-month') { state.month = (state.mode === 'demo' ? dataset.reference_date : C.localDate(preferences.reading_timezone)).slice(0, 7); state.selectedDate = null; render(); }
    else if (button.dataset.action === 'clear-date') { state.selectedDate = null; render(); }
    else if (button.dataset.action === 'export') {
      const blob = new Blob([JSON.stringify({ schema_version: 1, exported_at: new Date().toISOString(), preferences, bookmarks }, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = `culture-desk-${new Date().toISOString().slice(0, 10)}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 3000); toast('收藏与偏好已导出');
    }
    else if (button.dataset.action === 'import') $('import-input').click();
    else if (button.dataset.action === 'ics') {
      const all = [...(boot.live?.events || []), ...dataset.events], ids = new Set(bookmarks.map(row => row.event_id).filter(Boolean));
      const events = [...new Map(all.filter(event => ids.has(event.id)).map(event => [event.id, event])).values()];
      if (!events.some(event => event.date_precision === 'day')) { toast('请先收藏一项有确切日期的活动'); return; }
      const url = URL.createObjectURL(new Blob([C.calendarFile(events)], { type: 'text/calendar;charset=utf-8' })); const link = document.createElement('a'); link.href = url; link.download = 'culture-desk.ics'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 3000); toast('已导出确切日期的活动；仅到月份的活动未导出');
    }
    else if (button.dataset.action === 'refresh') {
      if (!server) { toast('此版本是资讯快照；运行本地服务可自动更新'); return; }
      button.disabled = true; try { const result = await api('/refresh', { method: 'POST' }); toast(result.status === 'busy' ? '更新已在进行' : '正在读取来源，完成后自动刷新'); clearTimeout(refreshTimer); refreshTimer = setTimeout(pollRefresh, 1500); } catch (error) { button.disabled = false; toast(error.message); }
    }
    else if (button.dataset.action === 'inbox') inbox();
    else if (button.dataset.readNotification) {
      try { await api('/notifications/' + encodeURIComponent(button.dataset.readNotification), { method: 'PATCH' }); notifications = await api('/notifications'); render(); inbox(); } catch (error) { toast(error.message); }
    }
  });
  document.addEventListener('change', async event => {
    const input = event.target;
    if (input.id === 'event-type-filter') { state.kind = input.value; if (['cinema_release','festival_screening','streaming_release'].includes(input.value)) state.channel = 'film'; else if (input.value === 'call_deadline') state.channel = 'photography'; else if (input.value === 'exhibition' && state.channel === 'film') state.channel = 'all'; render(); }
    if (input.id === 'language-filter') { state.language = input.value; render(); }
    if (input.id === 'country-filter') { state.country = input.value; state.city = 'all'; render(); }
    else if (input.id === 'city-filter') { state.city = input.value; render(); }
    else if (input.id === 'buzz-filter') {
      try { await savePreferences({ ...preferences, industry_buzz: { ...preferences.industry_buzz, enabled: input.checked } }); } catch (error) { toast(error.message); render(); }
    }
    else if (input.dataset.sourceToggle) {
      const disabled = new Set(preferences.disabled_sources || []); input.checked ? disabled.delete(input.dataset.sourceToggle) : disabled.add(input.dataset.sourceToggle);
      try { await savePreferences({ ...preferences, disabled_sources: [...disabled] }); toast(server ? '来源设置已保存，采集开关在下次更新生效' : '已保存当前浏览器的来源显示设置'); } catch (error) { toast(error.message); render(); }
    }
    else if (input.dataset.bookmarkStatus) {
      const bookmark = bookmarks.find(row => row.id === input.dataset.bookmarkStatus); if (!bookmark) return;
      try {
        if (server) await api('/bookmarks', { method: 'POST', body: JSON.stringify({ target_type: bookmark.content_id ? 'content' : 'event', target_id: bookmark.content_id || bookmark.event_id, status: input.value, note: bookmark.note || '' }) });
        bookmark.status = input.value; bookmark.updated_at = new Date().toISOString(); const persisted = server || writeLocal(); render(); if (persisted) toast('收藏状态已更新');
      } catch (error) { toast(error.message); render(); }
    }
    else if (input.id === 'import-input' && input.files?.[0]) {
      try {
        if (input.files[0].size > 2_000_000) throw new Error('文件过大，请使用 2 MB 以内的导出文件');
        const allData = server ? await api('/dataset?mode=demo') : { ...boot.dataset, content: [...boot.dataset.content, ...(boot.live?.content || [])], events: [...boot.dataset.events, ...(boot.live?.events || [])] };
        if (server) { const live = await api('/dataset?mode=live'); allData.content.push(...live.content); allData.events.push(...live.events); }
        const imported = C.validateImport(JSON.parse(await input.files[0].text()), allData, boot.preferences);
        if (server) { await api('/import', { method: 'POST', body: JSON.stringify(imported) }); [preferences, bookmarks] = await Promise.all([api('/preferences'), api('/bookmarks')]); }
        else { preferences = imported.preferences; const map = new Map(bookmarks.map(row => [row.content_id ? `content:${row.content_id}` : `event:${row.event_id}`, row])); for (const row of imported.bookmarks) { const key = row.content_id ? `content:${row.content_id}` : `event:${row.event_id}`; map.set(key, { ...row, id: map.get(key)?.id || makeId() }); } bookmarks = [...map.values()]; }
        const persisted = server || writeLocal(); render(); if (persisted) toast(`已恢复 ${imported.bookmarks.length} 条收藏和偏好`);
      } catch (error) { toast(error.message || '导入失败'); input.value = ''; }
    }
  });
  document.addEventListener('submit', async event => {
    if (event.target.id !== 'preferences-form') return; event.preventDefault();
    const form = new FormData(event.target), button = event.target.querySelector('button[type=submit]'); button.disabled = true;
    const next = { ...preferences, default_city: form.get('default_city'), news_scope: form.get('news_scope'), reading_timezone: form.get('reading_timezone'), interests: form.getAll('interests'), followed_entities: form.get('followed_entities').split(/[\n,，]/).map(x => x.trim()).filter(Boolean).slice(0, 100), daily_selection_limit: Number(form.get('daily_selection_limit')), industry_buzz: { ...preferences.industry_buzz, enabled: form.has('buzz'), max_share: 0.1, include_unverified_in_today: false } };
    try { if (await savePreferences(next)) toast('偏好已保存，今日精选会跟着你改变'); } catch (error) { button.disabled = false; toast(error.message); }
  });
  $('search').addEventListener('input', event => { state.query = event.target.value; if (['settings','reader'].includes(state.view)) state.view = 'explore'; render(); });
  $('coordinate-button').addEventListener('click', () => { state.view = 'settings'; render(); });
  $('close-detail').addEventListener('click', () => $('detail-dialog').close());
  $('detail-dialog').addEventListener('click', event => { if (event.target === $('detail-dialog')) { const r = $('detail-dialog').getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) $('detail-dialog').close(); } });
  window.addEventListener('hashchange', () => { const route = C.parseRoute(location.hash); if (route.view === 'reader') openReader(route.id, false); else { state.view = route.view; render(); } });
  const initialRoute = C.parseRoute(location.hash); state.view = initialRoute.view; if (initialRoute.id) state.readerId = initialRoute.id;
  render();
})();
