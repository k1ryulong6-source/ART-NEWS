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
  const state = { view: 'today', channel: 'all', kind: 'all', country: 'all', city: 'all', query: '', mode: 'demo', month: '2026-10', selectedDate: null, bookmarkStatus: 'all' };
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
  state.mode = dataset.mode || 'demo'; state.month = dataset.reference_date.slice(0, 7); sourceStatus = dataset.source_status || [];
  if (server) notifications = await api('/notifications').catch(() => []);
  function artwork(row, large = false) {
    const id = e(row.id.replace(/[^a-z0-9]/gi, '')) + (large ? 'large' : 'small');
    const variant = [...row.id].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 3;
    if (row.channel === 'film') return `<svg viewBox="0 0 900 480" preserveAspectRatio="xMidYMid slice" role="img" aria-label="电影主题原创示意图"><defs><linearGradient id="sky${id}" x2="0" y2="1"><stop stop-color="#d0cbb5"/><stop offset="1" stop-color="#a6b7a5"/></linearGradient><linearGradient id="hill${id}" x2="0" y2="1"><stop stop-color="#394a42"/><stop offset="1" stop-color="#1b2e29"/></linearGradient></defs><rect width="900" height="480" fill="url(#sky${id})"/><circle cx="${650 + variant * 30}" cy="130" r="67" fill="#a34c3a" opacity=".9"/><path d="M0 300 110 230 195 276 292 163 414 278 580 201 670 300 810 215 900 246V480H0z" fill="#718676"/><path d="M0 341 153 282 297 362 402 256 582 336 704 266 900 329V480H0z" fill="url(#hill${id})"/><path d="M0 413 Q210 353 460 435 T900 418V480H0" fill="#1c2925"/><path d="M460 480 469 380 496 363 518 480" fill="#b5aa8e" opacity=".65"/><g fill="#17261f"><rect x="119" y="281" width="4" height="110"/><path d="m121 254-34 88h68z"/><rect x="752" y="301" width="4" height="95"/><path d="m754 272-30 82h60z"/></g><g opacity=".08" stroke="#fff"><path d="M0 70h900M0 140h900M0 210h900M0 280h900M0 350h900M0 420h900"/></g><text x="39" y="62" font-size="13" letter-spacing="5" fill="#3e4d43" font-family="Georgia">THE SPACE BETWEEN FRAMES</text></svg>`;
    if (row.channel === 'art') return `<svg viewBox="0 0 900 480" preserveAspectRatio="xMidYMid slice" role="img" aria-label="艺术主题原创示意图"><rect width="900" height="480" fill="${['#ded7c6', '#b8bdae', '#e3d9c4'][variant]}"/><rect x="235" y="-45" width="360" height="610" transform="rotate(-13 450 240)" fill="#ece8d9"/><circle cx="405" cy="218" r="150" fill="${['#4b6574', '#a8533d', '#656b54'][variant]}"/><path d="M405 69a150 150 0 0 1 0 300z" fill="#bbb5a3" opacity=".72"/><rect x="517" y="225" width="164" height="210" fill="#b87c51"/><path d="M158 400h580M202 55v389" stroke="#7d8170" stroke-width="2" opacity=".35"/><circle cx="599" cy="110" r="25" fill="#aa4335"/><text x="38" y="52" font-size="13" letter-spacing="6" fill="#6b675b" font-family="Georgia">FORMS / IN EVERYDAY LIFE</text></svg>`;
    return `<svg viewBox="0 0 900 480" preserveAspectRatio="xMidYMid slice" role="img" aria-label="摄影主题原创街景示意图"><rect width="900" height="480" fill="#c6c8bf"/><path d="M0 0h280v367H0z" fill="#626b61"/><path d="M0 0h160v400H0z" fill="#3f4940"/><path d="M590 0h310v400H590z" fill="#777b6e"/><path d="M730 0h170v450H730z" fill="#414b43"/><path d="M280 85h310v255H280z" fill="#a4aa9c"/><path d="M0 480 358 290h186l356 190" fill="#697368"/><path d="m367 290-181 190M535 290l196 190" stroke="#b9bba8" stroke-width="3"/><g fill="#b6b9a9"><path d="M25 55h48v64H25zm89 0h34v64h-34zM25 169h48v64H25zm89 0h34v64h-34zM610 58h71v86h-71zm100 0h34v86h-34zM610 185h71v86h-71z"/></g><path d="m180 126 400 41M183 99l398 40" stroke="#475347" stroke-width="3"/><path d="M204 0v377M579 0v349" stroke="#364638" stroke-width="5"/><circle cx="469" cy="298" r="10" fill="#27372c"/><path d="M458 309h23l5 51h-32zM461 352l-6 42m22-42 8 42" stroke="#28392d" stroke-width="6" fill="#27372c"/><path d="M370 220h119v13H370z" fill="#a04735" opacity=".8"/><text x="38" y="445" font-size="13" letter-spacing="6" fill="#e2e2d4" font-family="Georgia">NOTES FROM THE CITY</text></svg>`;
  }
  function sourceName(row) { return dataset.sources.find(s => s.id === row.source_id)?.name || '来源待确认'; }
  function filters() {
    const disabled = state.view === 'bookmarks' ? [] : preferences.disabled_sources || [];
    const disabledEventIds = dataset.events.filter(event => { const links = dataset.content_events.filter(link => link.event_id === event.id); return links.length && links.every(link => disabled.includes(dataset.content.find(row => row.id === link.content_id)?.source_id)); }).map(event => event.id);
    return { channel: state.channel, kind: state.kind, country: state.country, city: state.city, query: state.query, buzz: preferences.industry_buzz.enabled, disabledSources: disabled, disabledEventIds };
  }
  function findBookmark(type, id) { return bookmarks.find(b => b[type === 'content' ? 'content_id' : 'event_id'] === id); }
  function nav() {
    const labels = { today: '今日', explore: '探索', calendar: '日历', bookmarks: '收藏', settings: '设置' };
    $('navigation').innerHTML = Object.entries(labels).map(([key, label]) => `<button class="nav-button ${state.view === key ? 'active' : ''}" data-view="${key}" ${state.view === key ? 'aria-current="page"' : ''}><span class="nav-icon">${icon(key)}</span>${label}${key === 'bookmarks' ? `<span class="nav-count">${bookmarks.length}</span>` : ''}</button>`).join('');
    $('coordinate-button').innerHTML = `${e(preferences.default_city)} <span>↗</span>`;
  }
  function heading(title, subtitle, eyebrow) {
    return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="subtitle">${subtitle}</p></div><div class="date-stamp"><strong>${C.dateLabel(dataset.reference_date)}</strong>${state.mode === 'demo' ? '示例参考日 · 非真实安排' : '你的文化日常'}</div></div>`;
  }
  function notice() {
    const last = sourceStatus.map(source => source.last_success_at).filter(Boolean).sort().at(-1);
    const label = last ? new Intl.DateTimeFormat('zh-CN', { timeZone: preferences.reading_timezone, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(last)) : '未更新';
    return `<div class="notice"><span>${state.mode === 'demo' ? '<b>演示模式</b> · 内容与日期均为虚构示例，图形为原创示意。' : dataset.content.length ? `<b>真实资讯</b> · ${dataset.content.length} 条内容 / ${dataset.events.length} 项活动 · ${server ? '最后读取' : '资讯快照'} ${e(label)}` : '<b>真实资讯</b> · 还没有读取到内容，可点击更新或查看来源状态。'}</span><button data-action="mode">${state.mode === 'demo' ? '查看真实资讯' : '体验示例'} ↗</button></div>`;
  }
  function filterBar(withTabs = true) {
    return `<div class="filters">${withTabs ? `<div class="tabs" role="group" aria-label="频道筛选">${[['all', '全部'], ...Object.entries(C.channels)].map(([key, label]) => `<button class="tab ${state.channel === key && state.kind !== 'industry_buzz' ? 'active' : ''}" data-channel="${key}" aria-pressed="${state.channel === key && state.kind !== 'industry_buzz'}">${label}</button>`).join('')}<button class="tab ${state.kind === 'industry_buzz' ? 'active' : ''}" data-kind="industry_buzz" aria-pressed="${state.kind === 'industry_buzz'}">圈内动态</button></div>` : ''}<div class="filter-selects"><select id="country-filter" aria-label="国家筛选"><option value="all">所有地区</option><option value="JP" ${state.country === 'JP' ? 'selected' : ''}>日本</option><option value="CN" ${state.country === 'CN' ? 'selected' : ''}>中国</option></select><select id="city-filter" aria-label="城市筛选"><option value="all">所有城市</option>${boot.preferences.cities.map(city => `<option ${state.city === city ? 'selected' : ''}>${e(city)}</option>`).join('')}</select><label class="toggle-label"><input id="buzz-filter" type="checkbox" ${preferences.industry_buzz.enabled ? 'checked' : ''}>圈内动态</label></div></div>`;
  }
  function empty(title, text, action = '') { return `<div class="empty"><div class="empty-icon">◯</div><h2>${title}</h2><p>${text}</p>${action}</div>`; }
  function meta(row) { return `<div class="meta"><span class="channel-tag">${C.channels[row.channel]}</span><span class="meta-dot">/</span><span>${e(C.kinds[row.kind] || C.eventTypes[row.event_type] || '资讯')}</span><span class="meta-dot">·</span><span>${e(C.locationLabel(row))}</span></div>`; }
  function saveButton(type, id, inline = false) {
    const saved = findBookmark(type, id);
    return `<button class="${inline ? 'save-inline' : 'save-button'} ${saved ? 'saved' : ''}" data-save-type="${type}" data-save-id="${e(id)}" aria-label="${saved ? '取消收藏' : '收藏'}" aria-pressed="${Boolean(saved)}">${inline ? (saved ? '已收藏 ✓' : '＋ 收藏') : icon('bookmark')}</button>`;
  }
  function card(row, showStatus = false) {
    const saved = findBookmark('content', row.id);
    return `<article class="content-card"><div class="card-art">${artwork(row)}${saveButton('content', row.id)}</div><div class="card-body">${meta(row)}<h3><button class="card-title" data-detail="${e(row.id)}" data-type="content">${e(row.title_zh || row.title_original)}</button></h3><p class="card-summary">${e(row.summary_zh || '中文摘要待整理，可查看原标题与来源。')}</p><div class="card-footer"><span>${e(sourceName(row).replace('（虚构）', ''))}</span><span class="demo-label">${row.is_demo ? '示例内容' : C.dateLabel(row.published_at?.slice(0, 10))}</span></div>${showStatus && saved ? `<select class="bookmark-status" data-bookmark-status="${e(saved.id)}" aria-label="收藏状态">${Object.entries(C.statusNames).map(([k, v]) => `<option value="${k}" ${saved.status === k ? 'selected' : ''}>${v}</option>`).join('')}</select>` : ''}</div></article>`;
  }
  function eventRow(row, detailed = true) {
    const status = C.eventState(row, dataset.reference_date);
    const date = row.start_date?.split('-') || [];
    return `<div class="event-row"><div class="date-block"><small>${date[1] || '—'} 月</small><strong>${row.date_precision === 'day' ? date[2] : '—'}</strong></div><div class="event-row-main"><span class="event-badge ${status.tone}">${status.label}</span><h3><button class="card-title" data-detail="${e(row.id)}" data-type="event">${e(row.title_zh || row.title_original)}</button></h3><p>${e(C.locationLabel(row))} · ${C.eventTypes[row.event_type]}${detailed ? ` · ${C.dateLabel(row.start_date)}${row.end_date ? ' — ' + C.dateLabel(row.end_date) : ''}` : ''}</p></div>${saveButton('event', row.id, true)}</div>`;
  }
  function upcoming() {
    return dataset.events.filter(row => C.matches(row, { ...filters(), kind: 'all' }) && row.date_precision === 'day' && ((C.daysBetween(dataset.reference_date, row.start_date) >= 0 && C.daysBetween(dataset.reference_date, row.start_date) <= (preferences.upcoming_window_days || 14)) || (row.end_date && C.daysBetween(dataset.reference_date, row.end_date) >= 0 && C.daysBetween(dataset.reference_date, row.end_date) <= 7)))
      .sort((a, b) => { const aEnd = C.daysBetween(dataset.reference_date, a.end_date), bEnd = C.daysBetween(dataset.reference_date, b.end_date); const aSoon = aEnd !== null && aEnd <= 7, bSoon = bEnd !== null && bEnd <= 7; return Number(bSoon) - Number(aSoon) || String(a.start_date).localeCompare(String(b.start_date)); }).slice(0, 3);
  }
  function agenda() {
    const rows = upcoming();
    return `<aside class="agenda"><div class="section-title"><h2>接下来，去看看</h2><span>ON THE CALENDAR</span></div><p class="agenda-intro">新片、开幕，以及别错过的最后几天。</p>${rows.map(row => { const date = row.start_date.split('-'), status = C.eventState(row, dataset.reference_date); return `<button class="agenda-item" data-detail="${e(row.id)}" data-type="event"><div class="date-block"><small>${date[1]} 月</small><strong>${date[2]}</strong></div><div><span class="event-badge ${status.tone}">${status.label}</span><h3>${e(row.title_zh)}</h3><p>${e(C.locationLabel(row))} · ${C.eventTypes[row.event_type]}</p></div></button>`; }).join('') || '<p class="compact-note">没有符合条件的近期活动。</p>'}<button class="agenda-more" data-view="calendar">打开完整日历 →</button><div class="quote-note">“在赶路的日子里，<br>也别忘了停下来看看。”</div></aside>`;
  }
  function today() {
    const rows = C.selectToday(dataset.content.filter(row => C.matches(row, filters())), preferences);
    const feature = rows.find(row => row.id === 'demo-film') || rows[0];
    const others = rows.filter(row => row.id !== feature?.id);
    return heading('留一点时间，给值得看的世界。', '电影、艺术、摄影，还有一点圈内故事。每天五分钟，找到下一次出发。', 'A DAILY DOSE OF CULTURE') + notice() + filterBar() + (feature ? `<div class="hero-grid"><article class="feature"><div class="feature-art">${artwork(feature, true)}<span class="feature-number">EDITOR’S PICK / 01</span><span class="art-caption">原创图形 · 作品示意</span></div><div class="feature-body">${meta(feature)}<h2><button class="card-title" data-detail="${e(feature.id)}" data-type="content">${e(feature.title_zh || feature.title_original)}</button></h2><p class="feature-summary">${e(feature.summary_zh || '中文摘要待整理。')}</p><div class="feature-footer"><span>${e(feature.selection_reason)} · ${feature.is_demo ? '示例内容' : e(sourceName(feature))}</span><button class="text-link" data-detail="${e(feature.id)}" data-type="content">阅读这条资讯 <span>↗</span></button></div></div></article>${agenda()}</div><section class="content-section"><div class="section-title"><h2>今日值得留意<span class="count-label">${rows.length} 条精选</span></h2><button class="text-link" data-view="explore">探索全部 ↗</button></div><div class="card-grid">${others.map(row => card(row)).join('')}</div></section>` : empty('给新发现留一点空间', state.mode === 'live' ? '当前筛选没有匹配内容。可清除筛选，或点击更新读取来源。' : '没有符合筛选条件的精选，试着换一个频道或关键词。', '<button class="button secondary" data-action="reset-filters">清除筛选</button>'));
  }
  function explore() {
    const rows = dataset.content.filter(row => C.matches(row, filters()));
    return heading('发现，发生在好奇之后。', '从一部电影、一场展览，或一本摄影集开始。', 'FOLLOW YOUR CURIOSITY') + notice() + filterBar() + `<div class="filter-summary">${rows.length} 条内容${state.query ? ' · 搜索：' + e(state.query) : ''} · 原文与出处保留在详情中</div>` + (rows.length ? `<div class="card-grid">${rows.map(row => card(row)).join('')}</div>` : empty('还没有找到这条线索', '试着清除筛选，或换一个关键词。', '<button class="button secondary" data-action="reset-filters">清除筛选</button>'));
  }
  function calendar() {
    const [year, month] = state.month.split('-').map(Number), first = new Date(Date.UTC(year, month - 1, 1)).getUTCDay(), count = new Date(Date.UTC(year, month, 0)).getUTCDate();
    const rows = dataset.events.filter(row => C.matches(row, { ...filters(), kind: 'all' }));
    const activeOn = day => rows.filter(row => row.date_precision === 'day' && row.start_date <= day && (row.end_date || row.start_date) >= day);
    const days = Array.from({ length: first }, () => '<div class="calendar-day blank" aria-hidden="true"></div>');
    for (let n = 1; n <= count; n++) {
      const day = `${state.month}-${String(n).padStart(2, '0')}`, active = activeOn(day);
      days.push(`<button class="calendar-day ${day === dataset.reference_date ? 'reference' : ''} ${day === state.selectedDate ? 'selected' : ''}" data-date="${day}" aria-label="${day}，${active.length} 项活动" aria-pressed="${day === state.selectedDate}"><span>${n}</span>${active.slice(0, 2).map(row => `<span class="calendar-dot ${row.channel}">${C.eventTypes[row.event_type]}</span>`).join('')}${active.length > 2 ? `<span class="calendar-dot">＋${active.length - 2}</span>` : ''}</button>`);
    }
    while (days.length % 7) days.push('<div class="calendar-day blank" aria-hidden="true"></div>');
    const visible = state.selectedDate ? activeOn(state.selectedDate) : rows.filter(row => row.start_date?.slice(0, 7) === state.month || row.end_date?.slice(0, 7) === state.month || (row.date_precision === 'day' && row.start_date < state.month + '-01' && row.end_date >= state.month + '-01'));
    return heading('把想看的，放进日历。', '上映、开幕、闭展。中日日期分开，按活动当地日期展示。', 'MAKE ROOM FOR WHAT MATTERS') + notice() + filterBar() + `<div class="calendar-layout"><div><div class="calendar-panel"><div class="calendar-toolbar"><h2>${year} 年 ${month} 月</h2><div class="month-controls"><button data-month="-1" aria-label="上个月">←</button><button data-action="reference-month">参考月</button><button data-month="1" aria-label="下个月">→</button></div></div><div class="week-row">${['日', '一', '二', '三', '四', '五', '六'].map(day => `<div>${day}</div>`).join('')}</div><div class="calendar-days">${days.join('')}</div><div class="calendar-legend"><span><i></i>电影</span><span><i class="art"></i>艺术</span><span><i class="photography"></i>摄影</span></div></div><section class="event-list"><div class="section-title"><h2>${state.selectedDate ? C.dateLabel(state.selectedDate) : '本月活动'}<span class="count-label">${visible.length} 项</span></h2>${state.selectedDate ? '<button class="text-link" data-action="clear-date">显示全月</button>' : ''}</div>${visible.map(row => eventRow(row)).join('') || '<p class="compact-note">该日期范围内没有符合条件的活动。</p>'}</section></div>${agenda()}</div><p class="compact-note" style="margin-top:20px">仅公布月份的活动列在清单，不填入具体日期；展览日期范围不代表每天开放，请查看休馆说明。</p>`;
  }
  function bookmarkPage() {
    const saved = bookmarks.filter(row => state.bookmarkStatus === 'all' || row.status === state.bookmarkStatus);
    const records = saved.map(row => ({ bookmark: row, record: (row.content_id ? dataset.content : dataset.events).find(x => x.id === (row.content_id || row.event_id)) })).filter(item => item.record && C.matches(item.record, filters()));
    const contents = records.filter(item => item.bookmark.content_id), events = records.filter(item => item.bookmark.event_id);
    return heading('一些值得留住的念头。', '想看、准备去、已看过。让好奇心有自己的去处。', 'YOUR PERSONAL COLLECTION') + notice() + filterBar() + `<div class="tabs" style="margin-bottom:23px">${[['all', '全部状态'], ...Object.entries(C.statusNames)].map(([key, label]) => `<button class="tab ${state.bookmarkStatus === key ? 'active' : ''}" data-status="${key}">${label}</button>`).join('')}</div>` + (records.length ? `<div class="card-grid">${contents.map(item => card(item.record, true)).join('')}</div>${events.length ? `<section class="event-list"><div class="section-title"><h2>收藏的活动</h2></div>${events.map(item => eventRow(item.record) + `<select class="bookmark-status" data-bookmark-status="${e(item.bookmark.id)}" aria-label="活动收藏状态">${Object.entries(C.statusNames).map(([k, v]) => `<option value="${k}" ${item.bookmark.status === k ? 'selected' : ''}>${v}</option>`).join('')}</select>`).join('')}</section>` : ''}` : empty('你的收藏，从一次心动开始。', '点击资讯卡片上的书签，或收藏一个活动。当前模式与筛选条件会影响可见收藏。', '<button class="button" data-view="explore">去探索 →</button>'));
  }
  function settings() {
    const topics = [...new Set([...boot.preferences.interests, '街头摄影', '电影访谈', '摄影征集', ...preferences.interests])];
    return heading('把它调成你的样子。', '选择想关注的城市与主题，留下属于自己的阅读节奏。', 'A SPACE THAT FEELS LIKE YOU') + notice() + `<div class="settings-grid"><div><form class="settings-panel" id="preferences-form"><h2>我的文化坐标</h2><p>这些设置会影响今日精选和关注排序。</p><label class="form-field">主要关注城市<select name="default_city">${boot.preferences.cities.map(city => `<option ${preferences.default_city === city ? 'selected' : ''}>${e(city)}</option>`).join('')}</select></label><div class="form-field"><span>感兴趣的主题</span><div class="interest-options">${topics.map(topic => `<label class="interest-chip"><input type="checkbox" name="interests" value="${e(topic)}" ${preferences.interests.includes(topic) ? 'checked' : ''}>${e(topic)}</label>`).join('')}</div></div><label class="form-field">关注对象<textarea name="followed_entities" placeholder="导演、摄影师、艺术家或场馆；每行一个">${e(preferences.followed_entities.join('\n'))}</textarea><small>名称会与标题和摘要匹配，用来提高相关内容的排序。</small></label><label class="form-field">每天精选数量<select name="daily_selection_limit">${[5, 10, 15, 20].map(n => `<option value="${n}" ${preferences.daily_selection_limit === n ? 'selected' : ''}>${n} 条</option>`).join('')}</select></label><label class="toggle-label" style="font-size:11px;margin-bottom:20px"><input type="checkbox" name="buzz" ${preferences.industry_buzz.enabled ? 'checked' : ''}>收录少量圈内动态（精选约 10%）</label><p class="compact-note">器材评测已排除。未证实消息不进入今日精选。</p><button class="button accent" type="submit">保存我的偏好 →</button></form><section class="settings-panel"><h2>带走你的收藏</h2><p>导出收藏和偏好，再导入到另一个浏览器或本地版本。</p><div class="button-row"><button class="button" data-action="export">导出 JSON ↓</button><button class="button secondary" data-action="import">导入记录 ↑</button><button class="button secondary" data-action="ics">导出日历 ↓</button><input id="import-input" type="file" accept="application/json,.json" hidden></div><div class="storage-note">${server ? '当前保存于本地 SQLite 数据库。' : localWritable ? '当前保存于此浏览器；换设备前请导出备份。' : '当前浏览器无法持久保存，请及时导出。'}导出不包含任何模型密钥。</div></section></div><div><section class="settings-panel"><h2>资讯从哪里来</h2><p>来源按实际读取结果标记，日期与原文始终可核对。</p>${boot.sources.sources.map(source => { const status = sourceStatus.find(row => row.id === source.id); const enabled = source.enabled && !(preferences.disabled_sources || []).includes(source.id); return `<div class="source-row"><a href="${e(C.safeUrl(source.homepage_url))}" target="_blank" rel="noopener noreferrer">${e(source.name)} ↗</a><span>${enabled ? status?.last_run?.status === 'failed' ? '上次读取失败' : status?.last_success_at ? '已读取' : '已接入' : source.enabled ? '已停用' : '待核实'}</span>${source.enabled ? `<input type="checkbox" data-source-toggle="${e(source.id)}" ${enabled ? 'checked' : ''} aria-label="启用${e(source.name)}">` : ''}</div>`; }).join('')}<p class="compact-note" style="margin-top:17px">真实资讯与虚构示例分开显示。来源读取失败时保留上次成功内容，并显示读取状态。</p></section><section class="settings-panel"><h2>为接力而建设</h2><p>作品之外，这也是一个可以继续生长的项目。</p><p class="compact-note">源码包包含需求、任务清单、数据契约和 AI 交接记录。下一位建设者可以按任务编号继续。</p><div class="source-row"><span>当前版本</span><span>0.2 · 真实资讯与日历</span></div><div class="source-row"><span>网页内容</span><span>示例模式 / 真实模式分离</span></div><div class="source-row"><span>接下来</span><span>更多城市 · 更多官方来源</span></div></section></div></div>`;
  }
  function render() {
    nav(); $('inbox-button').textContent = notifications.filter(row => !row.read).length || '铃'; document.querySelector('footer span').textContent = state.mode === 'demo' ? '所有示例均为虚构；图形为作品示意。' : '日期和标题来自来源；图形为主题示意，不是实际作品。'; $('main').innerHTML = ({ today, explore, calendar, bookmarks: bookmarkPage, settings }[state.view] || today)();
    if (location.hash !== '#' + state.view) history.replaceState(null, '', '#' + state.view);
  }
  function showDetail(type, id) {
    const row = (type === 'content' ? dataset.content : dataset.events).find(item => item.id === id);
    if (!row) return;
    const source = type === 'content' ? sourceName(row) : '活动日期证据';
    const href = C.safeUrl(type === 'content' ? row.canonical_url : row.evidence_url), isDemo = Boolean(row.is_demo);
    const related = type === 'content' ? dataset.content_events.filter(link => link.content_id === id).map(link => dataset.events.find(event => event.id === link.event_id)).filter(Boolean) : [];
    $('detail-body').innerHTML = `<div class="detail-art">${artwork(row, true)}</div><div class="detail-tag">${meta(row)}</div><h2 id="detail-title" class="detail-title">${e(row.title_zh || row.title_original)}</h2><p class="detail-original">原标题：${e(row.title_original)}</p>${type === 'content' ? `<p class="detail-summary">${e(row.summary_zh || '中文摘要尚未整理，请查看原标题及原文。')}</p>` : `<p class="detail-summary">${C.dateLabel(row.start_date)}${row.end_date ? ' — ' + C.dateLabel(row.end_date) : ''} · ${C.eventTypes[row.event_type]}</p>`}<dl class="detail-facts"><dt>消息状态</dt><dd><span class="evidence ${row.evidence_status === 'unverified' ? 'unverified' : ''}">${C.evidenceNames[row.evidence_status]}</span></dd><dt>信息来源</dt><dd>${e(source)}</dd><dt>地区</dt><dd>${e(C.locationLabel(row))}</dd>${type === 'event' ? `<dt>当地时区</dt><dd>${e(row.timezone)}</dd><dt>场馆</dt><dd>${e(row.venue || '待确认')}</dd><dt>票价</dt><dd>${e(row.price_text || '待确认')}</dd><dt>休馆说明</dt><dd>${e(row.closure_note || '请以场馆官方说明为准')}</dd><dt>日期精度</dt><dd>${row.date_precision === 'day' ? '具体日期' : row.date_precision === 'month' ? '仅月份，具体日期待公布' : '待公布'}</dd>` : `<dt>发布时间</dt><dd>${C.dateLabel(row.published_at?.slice(0, 10))}</dd>`}<dt>数据状态</dt><dd>${isDemo ? '虚构示例 · 不可据此安排出行' : '真实资讯'}</dd><dt>原文链接</dt><dd>${isDemo ? '示例链接，不提供真实页面' : href ? `<a href="${e(href)}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>` : '链接待确认'}</dd></dl>${related.map(event => `<div class="detail-activity"><span class="event-badge">${e(event.country === 'JP' ? '日本' : '中国')} · ${C.eventTypes[event.event_type]}</span><h3>${e(event.title_zh)}</h3><p>${C.dateLabel(event.start_date)}${event.end_date ? ' — ' + C.dateLabel(event.end_date) : ''} · ${e(event.timezone)}</p><button class="text-link" style="margin-top:10px" data-detail="${e(event.id)}" data-type="event">查看活动信息 ↗</button></div>`).join('')}<div class="detail-controls"><button class="button accent" data-detail-save="${e(id)}" data-type="${type}">${findBookmark(type, id) ? '取消收藏' : '加入收藏'} ${findBookmark(type, id) ? '✓' : '＋'}</button>${!isDemo && href ? `<a class="button secondary" href="${e(href)}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>` : ''}</div>`;
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
      const persisted = server || writeLocal(); render();
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
    const rows = server ? notifications : bookmarks.filter(row => row.event_id && row.status !== 'seen').map(row => (boot.live?.events || []).find(event => event.id === row.event_id)).filter(Boolean).filter(event => { const delta = C.daysBetween(C.localDate(preferences.reading_timezone), event.end_date || event.start_date); return delta >= 0 && delta <= 7; }).map(event => ({ id: event.id, event_id: event.id, title: (event.title_zh || event.title_original) + ' · ' + C.eventState(event, C.localDate(preferences.reading_timezone)).label }));
    $('detail-body').innerHTML = `<h2 id="detail-title" class="detail-title">给好作品留的提醒</h2><p class="compact-note">仅提醒你收藏且还未看过的真实活动。${server ? '' : '静态版在打开页面时检查日期。'}</p>${rows.length ? rows.map(row => `<div class="detail-activity"><h3>${e(row.title)}</h3><div class="button-row"><button class="text-link" data-detail="${e(row.event_id)}" data-type="event">查看活动 ↗</button>${server && !row.read ? `<button class="text-link" data-read-notification="${e(row.id)}">标为已读</button>` : row.read ? '<span class="compact-note">已读</span>' : ''}</div></div>`).join('') : '<p class="compact-note">暂无近期提醒，收藏活动后会在开始／结束前提醒你。</p>'}`;
    if (!$('detail-dialog').open) $('detail-dialog').showModal();
  }
  document.addEventListener('click', async event => {
    const button = event.target.closest('button'); if (!button) return;
    if (button.dataset.view) { state.view = button.dataset.view; state.selectedDate = null; render(); window.scrollTo({ top: 0 }); }
    else if (button.dataset.channel) { state.channel = button.dataset.channel; state.kind = 'all'; render(); }
    else if (button.dataset.kind) { state.kind = state.kind === button.dataset.kind ? 'all' : button.dataset.kind; state.channel = 'all'; state.view = 'explore'; render(); }
    else if (button.dataset.detail) showDetail(button.dataset.type, button.dataset.detail);
    else if (button.dataset.saveId) await toggleSave(button.dataset.saveType, button.dataset.saveId);
    else if (button.dataset.detailSave) await toggleSave(button.dataset.type, button.dataset.detailSave);
    else if (button.dataset.status) { state.bookmarkStatus = button.dataset.status; render(); }
    else if (button.dataset.date) { state.selectedDate = state.selectedDate === button.dataset.date ? null : button.dataset.date; render(); }
    else if (button.dataset.month) { const [y, m] = state.month.split('-').map(Number); const date = new Date(Date.UTC(y, m - 1 + Number(button.dataset.month), 1)); state.month = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`; state.selectedDate = null; render(); }
    else if (button.dataset.action === 'reset-filters') { state.channel = state.kind = state.country = state.city = 'all'; state.query = ''; $('search').value = ''; render(); }
    else if (button.dataset.action === 'mode') {
      const next = state.mode === 'demo' ? 'live' : 'demo'; button.disabled = true;
      try { dataset = server ? await api(`/dataset?mode=${next}`) : next === 'demo' ? boot.dataset : boot.live || { ...boot.dataset, mode: 'live', content: [], events: [], content_events: [], sources: [], reference_date: C.localDate(preferences.reading_timezone) }; state.mode = next; sourceStatus = dataset.source_status || []; state.month = dataset.reference_date.slice(0, 7); state.selectedDate = null; render(); }
      catch (error) { button.disabled = false; toast(error.message); }
    }
    else if (button.dataset.action === 'reference-month') { state.month = dataset.reference_date.slice(0, 7); state.selectedDate = null; render(); }
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
    const next = { ...preferences, default_city: form.get('default_city'), interests: form.getAll('interests'), followed_entities: form.get('followed_entities').split(/[\n,，]/).map(x => x.trim()).filter(Boolean).slice(0, 100), daily_selection_limit: Number(form.get('daily_selection_limit')), industry_buzz: { ...preferences.industry_buzz, enabled: form.has('buzz'), max_share: 0.1, include_unverified_in_today: false } };
    try { if (await savePreferences(next)) toast('偏好已保存，今日精选会跟着你改变'); } catch (error) { button.disabled = false; toast(error.message); }
  });
  $('search').addEventListener('input', event => { state.query = event.target.value; if (state.view === 'settings') state.view = 'explore'; render(); });
  $('coordinate-button').addEventListener('click', () => { state.view = 'settings'; render(); });
  $('close-detail').addEventListener('click', () => $('detail-dialog').close());
  $('detail-dialog').addEventListener('click', event => { if (event.target === $('detail-dialog')) { const r = $('detail-dialog').getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) $('detail-dialog').close(); } });
  window.addEventListener('hashchange', () => { const view = location.hash.slice(1); if (['today', 'explore', 'calendar', 'bookmarks', 'settings'].includes(view)) { state.view = view; render(); } });
  const initialView = location.hash.slice(1); if (['today', 'explore', 'calendar', 'bookmarks', 'settings'].includes(initialView)) state.view = initialView;
  render();
})();
