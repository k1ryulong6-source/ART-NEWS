(async function () {
  'use strict';
  const C = window.CultureCore, boot = window.CULTURE_BOOTSTRAP;
  const $ = id => document.getElementById(id), e = C.escape;
  let dataset = boot.live?.content?.length ? boot.live : boot.dataset, preferences = structuredClone(boot.preferences), bookmarks = [], server = false;
  let localWritable = true, toastTimer, refreshTimer;
  let notifications = [], sourceStatus = dataset.source_status || [];
  const makeId = () => typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const state = { view: 'today', channel: 'all', kind: 'all', country: 'all', city: 'all', language: 'all', query: '', mode: 'demo', month: '2026-10', selectedDate: null, bookmarkStatus: 'all', readerId: null, readerTab: 'chinese', readerReturn: 'today', editorialOnly: false, priority: 'all', advancedOpen: false, listPage: 1 };
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
  function artwork(row, large = false) {
    if (!row.image_url && row.event_type) {
      const link = dataset.content_events.find(item => item.event_id === row.id);
      const content = dataset.content.find(item => item.id === link?.content_id);
      if (content?.image_url) row = { ...row, image_url: content.image_url, image_alt: content.image_alt, image_credit: content.image_credit, source_id: content.source_id };
    }
    const image = C.safeImageUrl(row.image_url);
    return image ? `<span class="source-art"><img class="source-photo" src="${e(image)}" alt="${e(row.image_alt || C.displayTitle(row))}" loading="${large ? 'eager' : 'lazy'}" referrerpolicy="no-referrer" data-source-photo></span><span class="image-caption">图／${e(row.image_credit || sourceName(row))}</span>` : '';
  }
  document.addEventListener('error', event => {
    const img = event.target;
    if (img.matches?.('.article-image img')) {
      img.hidden = true;
      const caption = img.closest('figure').querySelector('figcaption');
      caption.textContent = '这张来源图片暂时无法加载。' + caption.textContent;
      return;
    }
    if (!img.matches?.('img[data-source-photo]')) return;
    const box = img.closest('.card-art, .feature-art, .reader-cover, .detail-art');
    if (box) box.hidden = true; else img.hidden = true;
    img.closest('.has-art')?.classList.remove('has-art');
  }, true);
  function readingBody(row) {
    const ready = C.editorialReady(row);
    const chinese = ready ? row.editorial_excerpt_zh : row.summary_zh || (row.language === 'zh' ? row.excerpt_original : null);
    return `<section class="reading-section"><h3>${ready ? '中文译文摘录' : '中文资料'}</h3><p class="detail-summary">${e(chinese || '这篇文章的中文译文尚未完成；原文已保留，可在原文页直接阅读。')}</p>${ready ? `<p class="reading-note">${row.editorial_status === 'translated' ? 'AI 按全文语境翻译。' : 'AI 按全文语境翻译并校对，非人工译者审核。'}</p>` : ''}<h3>原文摘录</h3>${row.excerpt_original ? `<p class="original-excerpt" lang="${e(row.language)}">${e(row.excerpt_original)}</p><p class="reading-note">来源短摘录，文章正文见原文页。</p>` : '<p class="reading-note">来源未提供短摘录，原标题与正文保留。</p>'}</section>`;
  }
  function sourceName(row) { return dataset.sources.find(s => s.id === row.source_id)?.name || '来源待确认'; }
  function filters() {
    const disabled = state.view === 'bookmarks' ? [] : preferences.disabled_sources || [];
    const disabledEventIds = dataset.events.filter(event => { const links = dataset.content_events.filter(link => link.event_id === event.id); return links.length && links.every(link => disabled.includes(dataset.content.find(row => row.id === link.content_id)?.source_id)); }).map(event => event.id);
    return { channel: state.channel, kind: state.kind, country: state.country, city: state.city, language: state.language, query: state.query, buzz: preferences.industry_buzz.enabled, disabledSources: disabled, disabledEventIds, priority: state.view === 'explore' ? state.priority : 'all', reviewedOnly: state.view === 'explore' && state.editorialOnly };
  }
  function findBookmark(type, id) { return bookmarks.find(b => b[type === 'content' ? 'content_id' : 'event_id'] === id); }
  function nav() {
    const labels = { today: '头版', explore: '资讯', calendar: '日历', bookmarks: '剪报' };
    $('navigation').innerHTML = Object.entries(labels).map(([key, label]) => `<button class="nav-button ${state.view === key ? 'active' : ''}" data-view="${key}" ${state.view === key ? 'aria-current="page"' : ''}>${label}${key === 'bookmarks' && bookmarks.length ? `<span class="nav-count">${bookmarks.length}</span>` : ''}</button>`).join('');
    const [y, m, d] = readingDate().split('-').map(Number);
    $('edition-date').textContent = `${y}年${m}月${d}日 星期${'日一二三四五六'[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]}`;
    $('edition-date').dateTime = readingDate();
    const last = sourceStatus.map(source => source.last_success_at).filter(Boolean).sort().at(-1);
    $('edition-updated').textContent = state.mode === 'demo' ? '示例版 · 内容虚构' : last ? '更新于 ' + new Intl.DateTimeFormat('zh-CN', { timeZone: preferences.reading_timezone, month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(last)) : '';
    document.querySelector('.refresh-control').hidden = !server;
    const unread = notifications.filter(row => !row.read).length;
    $('inbox-button').hidden = !server || !unread; $('inbox-button').textContent = `提醒 ${unread}`;
  }
  function heading(title, subtitle) { return ui.heading(title, subtitle); }
  function notice() {
    if (state.mode !== 'demo') return '';
    return `<div class="notice"><span><b>示例版</b> · 内容与日期均为虚构。</span><button class="text-link" data-action="mode">返回真实资讯</button></div>`;
  }
  function filterBar(withTabs = true) {
    return `<div class="filters">${withTabs ? `<div class="tabs" role="group" aria-label="频道筛选">${[['all', '综合'], ...['art','film','photography'].map(key=>[key,C.channels[key]])].map(([key, label]) => `<button class="tab ${state.channel === key && state.kind !== 'industry_buzz' ? 'active' : ''}" data-channel="${key}" aria-pressed="${state.channel === key && state.kind !== 'industry_buzz'}">${label}</button>`).join('')}<button class="tab ${state.kind === 'industry_buzz' ? 'active' : ''}" data-kind="industry_buzz" aria-pressed="${state.kind === 'industry_buzz'}">圈内</button></div>` : ''}<div class="scope-links"><button class="text-link" data-scope="global" aria-pressed="${state.country === 'all'}">全球</button><button class="text-link" data-scope="japan" aria-pressed="${state.country === 'JP'}">日本</button></div><details class="advanced-filters" id="advanced-filters" ${state.advancedOpen ? 'open' : ''}><summary>筛选${[state.city,state.language,state.priority].filter(v=>v!=='all').length || state.kind!=='all' ? ' · 已启用' : ''}</summary><div class="filter-selects"><select id="country-filter" aria-label="国家筛选"><option value="all">所有地区</option>${Object.entries(C.countryLabels).map(([code, label]) => `<option value="${code}" ${state.country === code ? 'selected' : ''}>${e(label)}</option>`).join('')}<option value="unknown" ${state.country === 'unknown' ? 'selected' : ''}>地点未说明</option></select><select id="city-filter" aria-label="城市筛选"><option value="all">所有城市</option>${Object.keys(C.cityCountries).filter(city => state.country === 'all' || C.cityCountries[city] === state.country).map(city => `<option ${state.city === city ? 'selected' : ''}>${e(city)}</option>`).join('')}</select>${state.view !== 'calendar' ? `<select id="language-filter" aria-label="资讯原文语言"><option value="all">原文语言 · 全部</option>${Object.entries(C.languageLabels).map(([code, label]) => `<option value="${code}" ${state.language === code ? 'selected' : ''}>${e(label)}</option>`).join('')}</select>` : ''}${state.view === 'explore' ? `<select id="priority-filter" aria-label="翻译优先级"><option value="all">所有优先级</option>${Object.entries({P0:'紧急',P1:'优先',P2:'普通',P3:'资料'}).map(([key,label])=>`<option value="${key}" ${state.priority === key ? 'selected' : ''}>${label}</option>`).join('')}</select>` : ''}<button class="text-link" data-action="photo-calls">摄影征集</button>${state.mode !== 'demo' ? `<button class="text-link" data-action="${state.editorialOnly ? 'all-news' : 'editorial-news'}" aria-pressed="${state.editorialOnly}">只看AI译文</button>` : ''}${state.view === 'calendar' ? `<select id="event-type-filter" aria-label="活动类型"><option value="all">全部活动类型</option>${Object.entries(C.eventTypes).map(([code,label]) => `<option value="${code}" ${state.kind === code ? 'selected' : ''}>${e(label)}</option>`).join('')}</select>` : ''}<label class="toggle-label"><input id="buzz-filter" type="checkbox" ${preferences.industry_buzz.enabled ? 'checked' : ''}>圈内动态</label></div></details></div>`;
  }
  function empty(title, text, action = '') { return `<div class="empty"><h2>${title}</h2>${text ? `<p>${text}</p>` : ''}${action}</div>`; }
  function meta(row) { return ui.meta(row); }
  function saveButton(type, id, inline = false) {
    const saved = findBookmark(type, id);
    return `<button class="${inline ? 'save-inline' : 'save-button'} ${saved ? 'saved' : ''}" data-save-type="${type}" data-save-id="${e(id)}" aria-label="${saved ? '移出剪报' : '加入剪报'}" aria-pressed="${Boolean(saved)}">${inline ? (saved ? '★ 已剪报' : '☆ 剪报') : saved ? '★' : '☆'}</button>`;
  }
  const readingDate = () => state.mode === 'demo' ? dataset.reference_date : C.localDate(preferences.reading_timezone);
  function publicationLabel(row) { const day = row.published_at?.slice(0, 10); const age = C.daysBetween(day, readingDate()); return age === null ? '发布日期未提供' : (age > (preferences.recent_news_days || 30) ? '旧资料 · ' : '') + C.dateLabel(day); }
  function priorityBadge(row) { const p = C.priorityOf(row); return p ? `<span class="priority-tag priority-${e(p.priority)}" title="${e(p.reasons.join('；'))}">${e(p.label)}${p.time_sensitive ? ' · 有时效' : ''}</span>` : ''; }
  const ui = window.CultureUI.create({ C, artwork, saveButton, findBookmark, sourceName, publicationLabel, priorityBadge });
  function card(row, showStatus = false) { return ui.card(row, showStatus); }
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
    return `<aside class="agenda"><div class="section-title"><h2>日程</h2></div>${rows.map(row => { const ref = referenceFor(row), closes = row.end_date && C.daysBetween(ref,row.end_date) >= 0 && C.daysBetween(ref,row.end_date) <= 7; const date = (closes ? row.end_date : row.start_date).split('-'), status = C.eventState(row,ref); return `<button class="agenda-item" data-detail="${e(row.id)}" data-type="event"><div class="date-block"><small>${date[1]} 月</small><strong>${date[2]}</strong></div><div><span class="event-badge ${status.tone}">${status.label}</span><h3>${e(C.displayTitle(row))}</h3><p>${e(C.locationLabel(row))} · ${C.eventTypes[row.event_type]}</p></div></button>`; }).join('') || '<p class="compact-note">没有符合条件的近期活动。</p>'}<button class="agenda-more" data-view="calendar">全部日程 ›</button></aside>`;
  }
  function today() {
    const available = dataset.content.filter(row => C.matches(row, filters()));
    const context = { ...dataset, reference_date: readingDate() };
    const selected = C.selectToday(available, preferences, context);
    const lead = [...selected].sort(C.priorityCompare).find(row => row.kind !== 'industry_buzz' && row.evidence_status !== 'unverified') || selected[0];
    const chosen = lead ? [lead,...selected.filter(row=>row.id!==lead.id)] : [];
    // The front page keeps the daily selection on top and fills the lower band with the next most important reports.
    const ids = new Set(chosen.map(row => row.id)), more = chosen.length ? available.filter(row => !ids.has(row.id) && row.evidence_status !== 'unverified').sort(C.priorityCompare) : [];
    const rows = [...chosen, ...more].slice(0, Math.max(chosen.length, 18));
    return heading('头版') + filterBar() + (rows.length ? ui.frontpage(rows,agenda()) : empty('暂无符合条件的新闻', '', '<button class="text-link" data-action="reset-filters">清除筛选</button>'));
  }
  function explore() {
    const rows = dataset.content.filter(row => C.matches(row, filters())).sort(C.priorityCompare);
    const size = 18, pages = Math.max(1, Math.ceil(rows.length / size));
    state.listPage = Math.min(pages, Math.max(1, state.listPage));
    const pageRows = rows.slice((state.listPage - 1) * size, state.listPage * size);
    return heading(state.query ? `检索：${state.query}` : state.editorialOnly ? 'AI译文' : '资讯') + notice() + filterBar() + `<div class="filter-summary">共 ${rows.length} 篇</div>` + (rows.length ? `<div class="card-grid">${pageRows.map(row => card(row)).join('')}</div>${ui.pagination(rows.length,state.listPage,size)}` : empty('没有符合条件的报道', '', '<button class="text-link" data-action="reset-filters">清除筛选</button>'));
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
    return heading('上映与展期') + notice() + filterBar() + `<div class="calendar-layout"><div><div class="calendar-panel"><div class="calendar-toolbar"><h2>${year} 年 ${month} 月</h2><div class="month-controls"><button data-month="-1" aria-label="上个月">←</button><button data-action="reference-month">参考月</button><button data-month="1" aria-label="下个月">→</button></div></div><div class="week-row">${['日', '一', '二', '三', '四', '五', '六'].map(day => `<div>${day}</div>`).join('')}</div><div class="calendar-days">${days.join('')}</div><div class="calendar-legend"><span><i></i>电影</span><span><i class="art"></i>艺术</span><span><i class="photography"></i>摄影</span></div></div><section class="event-list"><div class="section-title"><h2>${state.selectedDate ? C.dateLabel(state.selectedDate) : '本月活动'}<span class="count-label">${visible.length} 项</span></h2>${state.selectedDate ? '<button class="text-link" data-action="clear-date">显示全月</button>' : ''}</div>${visible.map(row => eventRow(row)).join('') || '<p class="compact-note">该日期范围内没有符合条件的活动。</p>'}</section></div>${agenda()}</div><details class="explanation"><summary>日期说明</summary><p>仅公布月份的活动列在清单，不填入具体日期；展览日期范围不代表每天开放，请查看休馆说明。</p></details>`;
  }
  function bookmarkPage() {
    const saved = bookmarks.filter(row => state.bookmarkStatus === 'all' || row.status === state.bookmarkStatus);
    const records = saved.map(row => ({ bookmark: row, record: (row.content_id ? dataset.content : dataset.events).find(x => x.id === (row.content_id || row.event_id)) })).filter(item => item.record && C.matches(item.record, filters()));
    const contents = records.filter(item => item.bookmark.content_id), events = records.filter(item => item.bookmark.event_id);
    return heading('剪报') + notice() + filterBar() + `<div class="tabs" style="margin-bottom:23px">${[['all', '全部状态'], ...Object.entries(C.statusNames)].map(([key, label]) => `<button class="tab ${state.bookmarkStatus === key ? 'active' : ''}" data-status="${key}">${label}</button>`).join('')}</div>` + (records.length ? `<div class="card-grid">${contents.map(item => card(item.record, true)).join('')}</div>${events.length ? `<section class="event-list"><div class="section-title"><h2>收藏的活动</h2></div>${events.map(item => eventRow(item.record) + `<select class="bookmark-status" data-bookmark-status="${e(item.bookmark.id)}" aria-label="活动收藏状态">${Object.entries(C.statusNames).map(([k, v]) => `<option value="${k}" ${item.bookmark.status === k ? 'selected' : ''}>${v}</option>`).join('')}</select>`).join('')}</section>` : ''}` : empty('剪报为空', '报道下方的 ☆ 可加入剪报。'));
  }
  let workflowHealth = boot.automation?.health, healthRequested = false;
  function automationPanel(stamp) {
    if (!healthRequested && location.hostname.endsWith('github.io')) {
      healthRequested = true;
      fetch('https://raw.githubusercontent.com/k1ryulong6-source/ART-NEWS/main/data/automation-health.json', {cache:'no-cache'})
        .then(response => response.ok ? response.json() : Promise.reject())
        .then(value => { if (value && value.stages && typeof value.checked_at === 'string') { workflowHealth = value; if (state.view === 'coverage') render(); } })
        .catch(() => {});
    }
    const statuses = {healthy:'正常',running:'正在运行',failed:'运行失败',stale:'超过6小时没有成功记录',unknown:'状态未核实'};
    const translation = boot.automation?.translation;
    return `<section class="settings-panel" data-ui="automation-status"><h2>自动运行</h2><p>资讯每2小时采集；现存与新增正文自动接续翻译。自动机翻与AI译文分别标注。</p>${[['collection','采集'],['translation','自动翻译'],['publication','公开发布']].map(([key,label]) => { const stage=workflowHealth?.stages?.[key]; const url=C.safeUrl(stage?.latest?.html_url); return `<p>${label}：${e(statuses[stage?.status] || '首次运行待验证')} · 最近成功 ${e(stamp(stage?.last_success?.updated_at))}${url ? ` · <a class="text-link" href="${e(url)}" target="_blank" rel="noopener noreferrer">记录 ↗</a>` : ''}</p>`; }).join('')}<p class="compact-note">最近翻译批次：${e(stamp(translation?.finished_at))}；实际完成 ${translation?.translated?.length || 0} 篇。${translation?.failed?.length ? `${translation.failed.length} 篇检查失败，保留原文并稍后重试。` : ''}${['time_budget','character_budget'].includes(translation?.status) ? '本批进度已保存，下一批自动继续。' : ''}</p></section>`;
  }
  function coveragePage() {
    const report = boot.coverage;
    if (!report) return empty('覆盖记录尚未生成', '刷新公开资料后再查看。');
    const p = report.progress, checks = report.sources.map(s => s.list_audit).filter(Boolean);
    const missing = checks.reduce((sum, check) => sum + (check.missing?.length || 0), 0);
    const stamp = value => value ? new Intl.DateTimeFormat('zh-CN', { timeZone: preferences.reading_timezone, dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : '未记录';
    return heading('收录与译文') + automationPanel(stamp) +
      `<section class="settings-panel"><h2>翻译进度</h2><details class="explanation"><summary>处理规则</summary><p>翻译按重要性和时效性排序：紧急、优先、普通、资料；每批保留旧稿份额。分级是自动初判，可在资料页查看依据，不代表消息已核实或艺术价值判断。非日本普通展览稍后处理，日本与重大展览按原规则；地点不明不按语种推断。</p><p>现存稿与新增稿均需全文翻译，精选只决定阅读排序。中文标题不计入正文完成数；订阅稿只翻译已取得的公开部分。</p></details><div class="coverage-stats">${[['保存的资料',p.total],['AI全文译文',p.completed],['自动机翻正文',p.machine_completed || 0],['全文尚无中文',p.without_chinese_body ?? p.pending],['原生中文正文',p.native_chinese],['等待AI精译',p.pending],['尚未取得正文',p.without_body],['待译原文字符',(p.pending_characters/10000).toFixed(1)+'万']].map(([label,value])=>`<div><strong>${value}</strong><span>${label}</span></div>`).join('')}</div><p class="compact-note">直接AI翻译 ${p.direct_translated} 篇；此前已校译 ${p.reviewed} 篇。已翻译正文中 ${p.completed_partial} 篇只取得公开部分。自动机翻与AI译文分别计数；自动机翻不算AI精译。未取得正文继续保留并重试。资料快照：${e(stamp(report.snapshot_at))}。</p></section>` +
      `<section class="settings-panel"><h2>全球是否收齐？目前无法证明</h2><p>${report.sources.length} 个来源是有限名单。来源读取成功只说明某次页面可读；RSS通常只有近期条目，官方首页也可能只列精选。</p><ul>${report.known_gaps.map(note=>`<li>${e(note)}</li>`).join('')}</ul><p>最近列表核对：${e(stamp(report.source_audit_at))}。已检查 ${checks.filter(c=>c.status==='checked').length} 个RSS；尚有 ${missing} 条该次列表条目未入库。${checks.filter(c=>c.status==='failed').length} 个核对失败，不能按“无遗漏”计算。官方页面全站完整性未独立验证。</p><p class="compact-note">“当次列表已入库”只适用于这一份RSS及其时间范围；不显示没有可靠分母的全球覆盖率。</p><p>各频道资料：${Object.entries(report.channels).map(([key,count])=>`${e(C.channels[key]||key)} ${count}`).join(' · ')}。</p><p>已收录活动地区：${Object.entries(report.event_regions).map(([key,count])=>`${e(C.countryLabels[key]||key)} ${count}`).join(' · ')}。没有列出的地区，当前活动日历覆盖为空。</p></section>` +
      `<section class="settings-panel"><h2>逐源证据与翻译进度</h2>${report.sources.map(source=>{ const check=source.list_audit, progress=source.progress; return `<details class="coverage-source"><summary><span>${e(source.name)}</span><span>${progress.total} 条 · ${progress.completed} 已译 · ${progress.pending} 待译</span></summary><p>最近成功读取：${e(stamp(source.last_success_at))}。${source.last_run?.status==='failed'?'上次采集失败，旧资料仍保留。':''}</p><p>${check?.status==='checked'?`当次RSS原始条目 ${check.observed}；符合范围 ${check.eligible}；库内 ${check.in_inventory}；未入库 ${check.missing.length}。${check.excluded?.length?`另有 ${check.excluded.length} 条被排除，可展开查看原因。`:''}`:check?.status==='failed'?`核对失败：${e(check.error)}，覆盖未知。`:'配置的官方页面；全站／整个影展完整性尚未核验。'}</p>${check?.continuity==='possible_rollover_gap'?'<p class="article-status">本次与上次RSS列表没有共同条目，可能发生滚动漏采，需要回补核验。</p>':''}${check?.oldest_publication?`<p class="compact-note">本次RSS发布时间范围：${e(stamp(check.oldest_publication))} 至 ${e(stamp(check.newest_publication))}。</p>`:''}${check?.missing?.map(row=>`<p><a href="${e(C.safeUrl(row.url))}" target="_blank" rel="noopener noreferrer">未入库原标题：${e(row.title_original)} ↗</a></p>`).join('')||''}${check?.excluded?.length?`<details><summary>查看排除条目及原因</summary>${check.excluded.map(row=>`<p>${e(row.title_original)} · ${row.reason==='equipment_review'?'器材评测':row.reason==='source_config_filter'?'来源配置过滤':'条目缺少标题或链接'}</p>`).join('')}</details>`:''}<p><a class="text-link" href="${e(C.safeUrl(check?.reference_url||source.homepage_url))}" target="_blank" rel="noopener noreferrer">打开来源列表，独立核对 ↗</a></p></details>`;}).join('')}</section>` +
      `<section class="settings-panel"><h2>跨来源抽查：已知缺口</h2><p>不能只用采集器自己的来源证明没有遗漏。以下来自另外查找的官方页面，按标题与库存对照；匹配结果仍需语义复核。这只是样本，不能代表全部重要信息。</p>${report.benchmarks.map(item=>`<div class="coverage-probe"><h3>${e(item.title_zh)}</h3><p>${item.inventory_status==='not_found_in_inventory'?'库存未检出对应标题':item.inventory_status==='related_report_only'?'已有相关报道，未检出对应活动日历':'已有相关记录，完整性仍需复核'} · 抽查 ${e(item.checked_at)}</p><p>${e(item.evidence)}</p><p>${e(item.follow_up)}</p><a class="text-link" href="${e(C.safeUrl(item.reference_url))}" target="_blank" rel="noopener noreferrer">核对官方出处 ↗</a></div>`).join('')}</section>` +
      `<details class="settings-panel explanation"><summary>如何检查重要新闻遗漏</summary><ol><li>先看来源是否持续读取成功，以及当次列表的未入库条目。</li><li>看报道与官方日历是否对应；有新闻不等于已收齐上映、展期或截止日期。</li><li>用片方、影展、美术馆和摄影机构的官方公告，再加未接入的媒体，交叉核对重大获奖、发行、重要展览和征集。至少对照两个独立出处。</li><li>发现遗漏时，把链接发给我；核对后补采，并检查是来源缺失、RSS滚动、解析失败还是首页精选没有展示。</li></ol><p class="compact-note">首页精选有数量限制，某条未出现在首页不一定漏采；先在“探索”清除筛选并搜索原标题或作品名。</p><button class="button secondary" data-view="explore">打开全部资讯 →</button></details>`;
  }
  function settings() {
    const topics = [...new Set([...boot.preferences.interests, '街头摄影', '电影访谈', '摄影征集', ...preferences.interests])];
    const timezones = [...new Set([preferences.reading_timezone, 'UTC', 'America/Los_Angeles', ...C.registry.regions.map(r => r.timezone)])];
    return heading('阅读设置') + notice() + `<div class="settings-grid"><div><form class="settings-panel" id="preferences-form"><h2>偏好</h2><label class="form-field">阅读范围<select name="news_scope"><option value="global" ${preferences.news_scope === 'global' ? 'selected' : ''}>全球资讯</option><option value="follow_city" ${preferences.news_scope === 'follow_city' ? 'selected' : ''}>优先关注城市</option></select></label><label class="form-field">主要关注城市<select name="default_city">${[...new Set([preferences.default_city, ...Object.keys(C.cityCountries)])].map(city => `<option ${preferences.default_city === city ? 'selected' : ''}>${e(city)}</option>`).join('')}</select></label><div class="form-field"><span>感兴趣的主题</span><div class="interest-options">${topics.map(topic => `<label class="interest-chip"><input type="checkbox" name="interests" value="${e(topic)}" ${preferences.interests.includes(topic) ? 'checked' : ''}>${e(topic)}</label>`).join('')}</div></div><label class="form-field">关注对象<textarea name="followed_entities" placeholder="导演、摄影师、艺术家或场馆；每行一个">${e(preferences.followed_entities.join('\n'))}</textarea><small>名称会与标题和摘要匹配，用来提高相关内容的排序。</small></label><label class="form-field">阅读时区<select name="reading_timezone">${timezones.map(zone => `<option ${preferences.reading_timezone === zone ? 'selected' : ''}>${e(zone)}</option>`).join('')}</select><small>活动倒计时始终使用活动当地日期。</small></label><label class="form-field">每天精选数量<select name="daily_selection_limit">${[5, 10, 15, 20].map(n => `<option value="${n}" ${preferences.daily_selection_limit === n ? 'selected' : ''}>${n} 条</option>`).join('')}</select></label><label class="toggle-label" style="font-size:11px;margin-bottom:20px"><input type="checkbox" name="buzz" ${preferences.industry_buzz.enabled ? 'checked' : ''}>收录少量圈内动态（精选约 10%）</label><button class="button" type="submit">保存</button></form><section class="settings-panel"><h2>导出与导入</h2><div class="button-row"><button class="button secondary" data-action="export">导出 JSON</button><button class="button secondary" data-action="import">导入</button><button class="button secondary" data-action="ics">导出日历 ICS</button><input id="import-input" type="file" accept="application/json,.json" hidden></div><div class="storage-note">${server ? '当前保存于本地 SQLite 数据库。' : localWritable ? '当前保存于此浏览器；换设备前请导出备份。' : '当前浏览器无法持久保存，请及时导出。'}导出不包含任何模型密钥。</div></section></div><div><section class="settings-panel"><h2>来源</h2>${boot.sources.sources.map(source => { const status = sourceStatus.find(row => row.id === source.id); const enabled = source.enabled && !(preferences.disabled_sources || []).includes(source.id); return `<div class="source-row"><a href="${e(C.safeUrl(source.homepage_url))}" target="_blank" rel="noopener noreferrer">${e(source.name)} ↗</a><span>${enabled ? status?.last_run?.status === 'failed' ? '上次读取失败' : status?.last_success_at ? '已读取' : '已接入' : source.enabled ? '已停用' : '待核实'}</span>${source.enabled ? `<input type="checkbox" data-source-toggle="${e(source.id)}" ${enabled ? 'checked' : ''} aria-label="启用${e(source.name)}">` : ''}</div>`; }).join('')}<p class="compact-note" style="margin-top:17px">真实资讯与虚构示例分开显示。来源读取失败时保留上次成功内容，并显示读取状态。</p></section><details class="settings-panel project-details"><summary>项目与交接</summary><button class="text-link" data-action="mode">${state.mode === 'demo' ? '返回真实资讯' : '体验示例'} →</button><p class="compact-note">源码包包含需求、任务清单、数据契约和 AI 交接记录。下一位建设者可以按任务编号继续。</p><div class="source-row"><span>当前版本</span><span>0.15 · 公共艺术新闻</span></div><div class="source-row"><span>网页内容</span><span>示例模式 / 真实模式分离</span></div><div class="source-row"><span>接下来</span><span>更多城市 · 更多官方来源</span></div></details></div></div>`;
  }
  function articleMarkup(blocks, translated = false) {
    return blocks.map(block => {
      if (block.type === 'image') return `<figure class="article-image"><img src="${e(block.url)}" alt="${e(block.alt || '')}" loading="lazy" referrerpolicy="no-referrer"><figcaption>${e(block.caption || '')}${block.caption ? ' · ' : ''}图片来源：${e(block.credit || '')}</figcaption></figure>`;
      const tag = block.type === 'heading' ? 'h2' : block.type === 'quote' ? 'blockquote' : 'p';
      const pending = translated && block.translated === false;
      return `<${tag} class="article-${e(block.type)}${pending ? ' translation-pending' : ''}">${pending ? '<small class="reading-note">本段待翻译 · 原文</small><br>' : ''}${e(block.text)}</${tag}>${block.links?.length ? `<div class="article-references">${block.links.map(link => `<a href="${e(link.url)}" target="_blank" rel="noopener noreferrer">${e(link.text || '文内链接')} ↗</a>`).join(' · ')}</div>` : ''}`;
    }).join('');
  }
  function newspaperBody(blocks, translated = false) {
    let html = '';
    for (let i = 0; i < blocks.length; i += 8) html += `<div class="article-columns">${articleMarkup(blocks.slice(i, i + 8), translated)}</div>`;
    return html;
  }
  function readerPage() {
    const row = dataset.content.find(item => item.id === state.readerId);
    if (!row) return empty('这条资讯暂不在当前资料中', '可以返回资讯列表，或查看真实资料模式。', '<button class="button" data-action="reader-back">返回资讯</button>');
    const url = C.originalPageUrl(row), saved = findBookmark('content', row.id);
    const blocks = C.articleBlocks(row), translatedBlocks = row.language === 'zh' ? C.articleBlocks(row) : C.articleBlocks(row, true);
    const partial = row.article_status === 'partial';
    const statusMessage = row.is_demo ? '这是虚构示例，没有来源正文。' : row.article_status === 'restricted' ? '来源目前要求登录、订阅或拒绝抓取，正文尚未取得。这条资讯及来源保留。' : row.article_status === 'no_body' ? '已读取来源页面，暂未提取到文章正文。这条资讯及来源保留。' : row.article_checked_at ? '本次未能取得正文，后续更新会重试。这条资讯及来源保留。' : '原文正在等待采集。这条资讯及来源保留。';
    const headerImage = row.image_url && !blocks.some(b => b.type === 'image' && b.url === row.image_url) ? `<div class="reader-cover">${artwork(row, true)}</div>` : '';
    const original = blocks.length ? `<div class="reader-document" lang="${e(row.language)}"><p class="reading-note">${row.article_author ? `作者：${e(row.article_author)} · ` : ''}来源：${e(sourceName(row))} · 正文采集于 ${e((row.article_fetched_at || '').slice(0,10))}</p>${partial ? '<p class="article-status">仅采集到公开可见的正文部分；来源的订阅内容或超出采集上限的内容未包含。</p>' : ''}${row.article_reason?.startsWith('cached_body_after_') ? '<p class="article-status">本次更新未成功，正在显示此前保存的原文。</p>' : ''}${headerImage}${newspaperBody(blocks)}</div>` : `<div class="original-unavailable" role="status"><h2>正文尚未取得</h2><p>${statusMessage}</p>${row.excerpt_original ? `<p class="reading-note">当前仅有来源短摘录：</p><p class="original-excerpt" lang="${e(row.language)}">${e(row.excerpt_original)}</p>` : ''}</div>`;
    let notes = []; try { notes = JSON.parse(row.editorial_notes_json || '[]'); } catch {}
    const chinese = translatedBlocks.length ? `<div class="reader-document" lang="zh-CN"><p class="reading-note">${row.language === 'zh' ? '来源原文为中文。' : !C.editorialReady(row) && C.machineReady(row) ? '自动机翻 · 免费离线模型 · 未经人工审核，专名与细节请对照原文。' : row.editorial_status === 'translated' ? 'AI 按全文语境翻译。' : 'AI 按全文语境翻译并校对 · 非人工译者审核。'}</p>${partial ? '<p class="article-status">来源仅取得公开部分，译文也仅包含这部分内容。</p>' : ''}${row.language !== 'zh' && notes.length ? `<div class="translation-notes"><h2>译名与表达说明</h2>${notes.map(note => `<p>${e(note)}</p>`).join('')}</div>` : ''}${headerImage}${newspaperBody(translatedBlocks, true)}</div>` : `<p class="article-status original-pending" role="status">${blocks.length ? `原文·待译 · 以下为${e(C.languageLabels[row.language] || '外文')}原文，中文译文尚未完成。` : '正文尚未取得。'}</p>${original}`;
    return `<article class="reader-page"><div class="reader-toolbar"><button class="text-link" data-action="reader-back">‹ 返回</button><button class="text-link reader-save" data-save-type="content" data-save-id="${e(row.id)}">${saved ? '★ 已剪报' : '☆ 剪报'}</button></div><div class="eyebrow"><span class="channel-tag">${e(C.channels[row.channel] || '文化')}</span>${e(sourceName(row))} · ${e(publicationLabel(row))}</div>${(() => { const title = state.readerTab === 'original' ? row.title_original : C.displayTitle(row); return `<h1 lang="${e(title === row.title_original && row.language !== 'zh' ? row.language : 'zh-CN')}">${e(title)}</h1>`; })()}<div class="reader-tabs" role="tablist" aria-label="阅读内容"><button role="tab" aria-selected="${state.readerTab === 'chinese'}" data-reader-tab="chinese">${translatedBlocks.length ? '中文' : '正文'}</button><button role="tab" aria-selected="${state.readerTab === 'original'}" data-reader-tab="original">原文</button><button role="tab" aria-selected="${state.readerTab === 'info'}" data-reader-tab="info">资料</button></div><div class="reader-content" role="tabpanel">${state.readerTab === 'original' ? original : state.readerTab === 'chinese' ? chinese : `<div class="reader-information">${meta(row)}${C.priorityOf(row) ? `<p>重要程度：${e({high:'高',medium:'中',normal:'一般'}[C.priorityOf(row).importance])} · 翻译优先级：${e(C.priorityOf(row).label)} · ${e(C.priorityOf(row).reasons.join('；'))}</p>` : ''}<p>原始来源：${e(sourceName(row))} · ${e(C.languageLabels[row.language] || row.language)}</p>${dataset.content_events.filter(link => link.content_id === row.id).map(link => dataset.events.find(item => item.id === link.event_id)).filter(Boolean).map(item => eventRow(item)).join('') || '<p>这篇资讯没有关联的日历活动。</p>'}</div>`}</div>${!row.is_demo && url ? `<div class="reader-source-link"><span>原文</span><a href="${e(url)}" target="_blank" rel="noopener noreferrer">${e(url)}</a></div>` : ''}</article>`;
  }
  function openReader(id, route = true) {
    if (state.view !== 'reader') state.readerReturn = state.view;
    state.readerId = id; state.readerTab = 'chinese'; state.view = 'reader';
    if ($('detail-dialog').open) $('detail-dialog').close();
    if (route) history.pushState(null, '', C.readerRoute(id));
    render(); window.scrollTo({ top: 0 });
  }
  function render() {
    const advanced = $('advanced-filters');
    if (advanced) state.advancedOpen = advanced.open;
    document.body.dataset.page = state.view;
    nav(); $('edition-note').textContent = state.mode === 'demo' ? '所有示例均为虚构。' : '原文与 AI 译文分开标注；配图注明来源。'; $('main').innerHTML = ({ today, explore, calendar, bookmarks: bookmarkPage, settings, coverage: coveragePage, reader: readerPage }[state.view] || today)();
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
    const picture = artwork(row, true);
    $('detail-body').innerHTML = `${picture ? `<div class="detail-art">${picture}</div>` : ''}<div class="detail-tag">${meta(row)}</div><h2 id="detail-title" class="detail-title">${e(C.displayTitle(row))}</h2><p class="detail-original">原标题：${e(row.title_original)}</p>${type === 'content' ? (isDemo ? `<p class="detail-summary">${e(row.summary_zh)}</p>` : readingBody(row)) : `<p class="detail-summary">${e(C.timeLabel(row))}${row.end_date ? ' — ' + C.dateLabel(row.end_date) : ''} · ${C.eventTypes[row.event_type]}</p>`}<dl class="detail-facts"><dt>消息状态</dt><dd><span class="evidence ${row.evidence_status === 'unverified' ? 'unverified' : ''}">${C.evidenceNames[row.evidence_status]}</span></dd><dt>信息来源</dt><dd>${e(source)}</dd><dt>地区</dt><dd>${e(C.locationLabel(row))}</dd>${type === 'event' ? `<dt>当地时区</dt><dd>${e(row.timezone)}</dd><dt>准确时刻</dt><dd>${e(C.timeLabel(row))}</dd>${row.time_note ? `<dt>时刻说明</dt><dd>${e(row.time_note)}</dd>` : ''}${row.eligibility_note ? `<dt>参赛资格</dt><dd>${e(row.eligibility_note)}</dd>` : ''}${row.booking_status ? `<dt>余票状态</dt><dd>${row.booking_status === 'sold_out' ? '官网显示已售罄；变动请核对原文' : '请核对官网实时余票'}</dd>` : ''}${row.booking_url ? `<dt>预约／报名</dt><dd><a href="${e(C.safeUrl(row.booking_url))}" target="_blank" rel="noopener noreferrer">打开官方入口 ↗</a></dd>` : ''}${row.event_type !== 'call_deadline' ? `<dt>场馆</dt><dd>${e(row.venue || '待确认')}</dd>` : ''}<dt>票价</dt><dd>${e(row.price_text || '待确认')}</dd>${row.event_type !== 'call_deadline' ? `<dt>休馆说明</dt><dd>${e(row.closure_note || '请以场馆官方说明为准')}</dd>` : ''}<dt>日期精度</dt><dd>${row.date_precision === 'day' ? '具体日期' : row.date_precision === 'month' ? '仅月份，具体日期待公布' : '待公布'}</dd>` : `<dt>原文语言</dt><dd>${e(C.languageLabels[row.language] || row.language || '待确认')}</dd><dt>发布时间</dt><dd>${e(publicationLabel(row))}</dd>`}<dt>数据状态</dt><dd>${isDemo ? '虚构示例 · 不可据此安排出行' : '真实资讯'}</dd><dt>原文链接</dt><dd>${isDemo ? '示例链接，不提供真实页面' : href ? `<a href="${e(href)}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>` : '链接待确认'}</dd></dl>${related.map(event => `<div class="detail-activity"><span class="event-badge">${e(C.countryLabels[event.country] || event.country)} · ${C.eventTypes[event.event_type]}</span><h3>${e(C.displayTitle(event))}</h3><p>${e(C.timeLabel(event))}${event.end_date ? ' — ' + C.dateLabel(event.end_date) : ''} · ${e(event.timezone)}</p><button class="text-link" style="margin-top:10px" data-detail="${e(event.id)}" data-type="event">查看活动信息 ↗</button></div>`).join('')}<div class="detail-controls"><button class="button secondary" data-detail-save="${e(id)}" data-type="${type}">${findBookmark(type, id) ? '★ 已剪报' : '☆ 剪报'}</button>${!isDemo && href ? `<a class="button secondary" href="${e(href)}" target="_blank" rel="noopener noreferrer">查看原文 ↗</a>` : ''}</div>`;
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
      if (state.view === 'reader') { nav(); const button = document.querySelector('.reader-save'); if (button) button.textContent = findBookmark('content', state.readerId) ? '★ 已剪报' : '☆ 剪报'; }
      else render();
      if (persisted) toast(old ? '已移出剪报' : '已加入剪报');
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
    const rows = server ? notifications : bookmarks.filter(row => row.event_id && row.status !== 'seen').map(row => (boot.live?.events || []).find(event => event.id === row.event_id)).filter(Boolean).filter(event => { const delta = C.daysBetween(C.localDate(event.timezone), event.end_date || event.start_date); return delta >= 0 && delta <= 7; }).map(event => ({ id: event.id, event_id: event.id, title: C.displayTitle(event) + ' · ' + C.eventState(event, C.localDate(event.timezone)).label }));
    $('detail-body').innerHTML = `<h2 id="detail-title" class="detail-title">提醒</h2>${rows.length ? rows.map(row => `<div class="detail-activity"><h3>${e(row.title)}</h3><div class="button-row"><button class="text-link" data-detail="${e(row.event_id)}" data-type="event">查看活动 ↗</button>${server && !row.read ? `<button class="text-link" data-read-notification="${e(row.id)}">标为已读</button>` : row.read ? '<span class="compact-note">已读</span>' : ''}</div></div>`).join('') : '<p class="compact-note">暂无提醒。</p>'}`;
    if (!$('detail-dialog').open) $('detail-dialog').showModal();
  }
  document.addEventListener('click', async event => {
    const button = event.target.closest('button'); if (!button) return;
    if (button.dataset.listPage) { state.listPage = Number(button.dataset.listPage); render(); $('main').scrollIntoView(); return; }
    if (button.dataset.view || button.dataset.channel || button.dataset.kind || button.dataset.scope || ['editorial-news','all-news','reset-filters','mode'].includes(button.dataset.action)) state.listPage = 1;
    if (button.dataset.view) { state.editorialOnly = false; state.kind = 'all'; state.view = button.dataset.view; state.selectedDate = null; render(); window.scrollTo({ top: 0 }); }
    else if (button.dataset.action === 'editorial-news') { state.view = 'explore'; state.editorialOnly = true; state.channel = state.kind = state.country = state.city = state.language = state.priority = 'all'; state.query = ''; $('search').value = ''; render(); }
    else if (button.dataset.action === 'all-news') { state.editorialOnly = false; state.priority = 'all'; state.view = 'explore'; render(); }
    else if (button.dataset.readerTab) { state.readerTab = button.dataset.readerTab; render(); }
    else if (button.dataset.action === 'reader-back') { state.view = state.readerReturn || 'today'; render(); window.scrollTo({ top: 0 }); }
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
    else if (button.dataset.action === 'reset-filters') { state.channel = state.kind = state.country = state.city = state.language = state.priority = 'all'; state.query = ''; $('search').value = ''; render(); }
    else if (button.dataset.action === 'mode') {
      const next = state.mode === 'demo' ? 'live' : 'demo'; button.disabled = true;
      try { dataset = server ? await api(`/dataset?mode=${next}`) : next === 'demo' ? boot.dataset : boot.live || { ...boot.dataset, mode: 'live', content: [], events: [], content_events: [], sources: [], reference_date: C.localDate(preferences.reading_timezone) }; state.mode = next; sourceStatus = dataset.source_status || []; state.month = (state.mode === 'demo' ? dataset.reference_date : C.localDate(preferences.reading_timezone)).slice(0, 7); state.selectedDate = null; render(); }
      catch (error) { button.disabled = false; toast(error.message); }
    }
    else if (button.dataset.action === 'reference-month') { state.month = (state.mode === 'demo' ? dataset.reference_date : C.localDate(preferences.reading_timezone)).slice(0, 7); state.selectedDate = null; render(); }
    else if (button.dataset.action === 'clear-date') { state.selectedDate = null; render(); }
    else if (button.dataset.action === 'export') {
      const blob = new Blob([JSON.stringify({ schema_version: 1, exported_at: new Date().toISOString(), preferences, bookmarks }, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = `幕间休息-${new Date().toISOString().slice(0, 10)}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 3000); toast('收藏与偏好已导出');
    }
    else if (button.dataset.action === 'import') $('import-input').click();
    else if (button.dataset.action === 'ics') {
      const all = [...(boot.live?.events || []), ...dataset.events], ids = new Set(bookmarks.map(row => row.event_id).filter(Boolean));
      const events = [...new Map(all.filter(event => ids.has(event.id)).map(event => [event.id, event])).values()];
      if (!events.some(event => event.date_precision === 'day')) { toast('请先收藏一项有确切日期的活动'); return; }
      const url = URL.createObjectURL(new Blob([C.calendarFile(events)], { type: 'text/calendar;charset=utf-8' })); const link = document.createElement('a'); link.href = url; link.download = '幕间休息.ics'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 3000); toast('已导出确切日期的活动；仅到月份的活动未导出');
    }
    else if (button.dataset.action === 'refresh') {
      if (!server) { location.reload(); return; }
      button.disabled = true; try { const result = await api('/refresh', { method: 'POST' }); toast(result.status === 'busy' ? '更新已在进行' : '正在读取来源，完成后自动刷新'); clearTimeout(refreshTimer); refreshTimer = setTimeout(pollRefresh, 1500); } catch (error) { button.disabled = false; toast(error.message); }
    }
    else if (button.dataset.action === 'inbox') inbox();
    else if (button.dataset.readNotification) {
      try { await api('/notifications/' + encodeURIComponent(button.dataset.readNotification), { method: 'PATCH' }); notifications = await api('/notifications'); render(); inbox(); } catch (error) { toast(error.message); }
    }
  });
  document.addEventListener('change', async event => {
    const input = event.target;
    if (input.id === 'article-page') { state.listPage = Number(input.value); render(); $('main').scrollIntoView(); return; }
    if (['priority-filter','country-filter','city-filter','language-filter','event-type-filter','buzz-filter'].includes(input.id)) state.listPage = 1;
    if (input.id === 'priority-filter') { state.priority = input.value; render(); return; }
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
    try { if (await savePreferences(next)) toast('已保存'); } catch (error) { button.disabled = false; toast(error.message); }
  });
  document.addEventListener('toggle', event => { if (event.target.id === 'advanced-filters' && event.target.isConnected) state.advancedOpen = event.target.open; }, true);
  $('search').addEventListener('input', event => { state.listPage = 1; state.query = event.target.value; state.view = 'explore'; render(); });
  $('coordinate-button').addEventListener('click', () => { state.view = 'settings'; render(); });
  $('close-detail').addEventListener('click', () => $('detail-dialog').close());
  $('detail-dialog').addEventListener('click', event => { if (event.target === $('detail-dialog')) { const r = $('detail-dialog').getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) $('detail-dialog').close(); } });
  window.addEventListener('hashchange', () => { if (location.hash === '#main') return; const route = C.parseRoute(location.hash); if (route.view === 'reader') openReader(route.id, false); else { state.view = route.view; render(); } });
  const initialRoute = C.parseRoute(location.hash); state.view = initialRoute.view; if (initialRoute.id) state.readerId = initialRoute.id;
  render();
})();
