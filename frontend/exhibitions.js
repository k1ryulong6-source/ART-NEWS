(function (root) {
  'use strict';
  const types = {
    painting: '绘画与版画', sculpture: '雕塑', installation: '装置与空间', photography: '摄影',
    media: '影像与媒体艺术', design: '设计、建筑与工艺', history: '历史与古美术',
    literature: '漫画与插画', festival: '艺术节与双年展', other: '综合／待分类'
  };
  const statuses = { want: '想去', visited: '去过', uninterested: '不感兴趣' };
  const phases = { active: '正在展出', upcoming: '即将开幕', ended: '已闭展', unknown: '展期待定',
    cancelled: '已取消', postponed: '已延期', needs_confirmation: '展期待核对' };
  const signals = { festival: [20, '艺术节／双年展'], retrospective: [18, '回顾展'],
    milestone: [12, '重要周年或规模'], special: [6, '特别展／企划展'] };
  const logFormat = 'culture-desk-exhibition-log-v1';
  const validId = /^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$/;
  const paused = ['cancelled', 'postponed', 'needs_confirmation'];
  const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
  const normal = value => String(value || '').normalize('NFKC').toLowerCase();
  const ageOf = (C, timestamp, today) => C.daysBetween(timestamp?.slice(0, 10), today);

  function phase(C, row, today) {
    if (paused.includes(row.status)) return row.status;
    if (row.date_precision !== 'day') return 'unknown';
    const start = C.daysBetween(today, row.start_date), end = C.daysBetween(today, row.end_date);
    if (end !== null && end < 0) return 'ended';
    if (start !== null && start > 0) return 'upcoming';
    return start !== null && end !== null ? 'active' : 'unknown';
  }

  function closingDays(C, row, today) {
    if (row.date_precision !== 'day' || [...paused, 'tentative'].includes(row.status) || ageOf(C,row.last_seen,today) > 14) return null;
    const windows = row.date_conflict
      ? (row.evidence || []).filter(x => x.status === 'scheduled' && ageOf(C,x.last_seen,today) <= 14).map(x => [x.start,x.end])
      : [[row.start_date,row.end_date]];
    const ends = windows.filter(([start]) => { const days = C.daysBetween(today,start); return days !== null && days <= 7; })
      .map(([,end]) => C.daysBetween(today,end)).filter(days => days !== null && days >= 0 && days <= 7);
    return ends.length ? Math.min(...ends) : null;
  }

  function decorate(C, row, log, today, preference = {}) {
    const state = phase(C,row,today), close = closingDays(C,row,today), start = C.daysBetween(today,row.start_date);
    const flags = new Set(row.flags || []), fresh = ageOf(C,row.last_seen,today) <= 14;
    const reasons = Object.keys(signals).filter(key => flags.has(key));
    const sources = row.source_count ?? new Set((row.evidence || []).map(item => item.source)).size;
    const important = reasons.some(key => key !== 'special') || (flags.has('special') && row.official);
    let score = reasons.reduce((sum,key) => sum + signals[key][0], 0) + (row.official ? 5 : 0) + Math.min(2, Math.max(0,sources - 1));
    if (close !== null) score += 9 - close;
    if (start !== null && Math.abs(start) <= 7) score += 4;
    if (log?.status === 'want') score += 5;
    if ((preference.followed_entities || []).some(value => {
      const name = normal(value).trim();
      return name && normal(row.title_original + ' ' + (row.venue || '')).includes(name);
    })) score += 5;
    if (row.types?.includes('photography') && preference.interests?.includes('photography')) score += 3;
    if (flags.has('permanent')) score -= 14;
    if (row.date_conflict || row.status === 'tentative' || !fresh) score -= 9;
    if (log?.status === 'uninterested') score -= 30;
    return { ...row, phase: state, close, score, log, reasons, lead: important && fresh && !flags.has('permanent')
      && row.status !== 'tentative' && (state === 'active' || (state === 'upcoming' && start <= 45)) };
  }

  function rank(C, items, records, filters) {
    const needles = normal(filters.query).trim().split(/\s+/).filter(Boolean);
    return items.filter(row => {
      if (filters.scope === 'JP' && row.country !== 'JP') return false;
      if (filters.scope === 'world' && row.country === 'JP') return false;
      if (filters.prefecture !== 'all' && (row.prefecture || 'unknown') !== filters.prefecture) return false;
      if (filters.medium !== 'all' && !(row.types || []).includes(filters.medium)) return false;
      const log = records.get(row.id);
      if ((filters.personal === 'favorite' && !log?.favorite) || (filters.personal === 'records' && !log)) return false;
      if (own(statuses,filters.personal) && log?.status !== filters.personal) return false;
      const pref = filters.labels?.get(row.prefecture);
      const query = normal([row.title_original,row.title_zh,row.venue,row.area,row.city,pref?.name,pref?.original,
        ...(row.types || []).map(key => types[key])].join(' '));
      return needles.every(needle => query.includes(needle));
    }).map(row => decorate(C,row,records.get(row.id),filters.today(row.timezone),filters.preference))
      .filter(row => filters.stage === 'all' || (filters.stage === 'closing' && row.close !== null)
        || (filters.stage === 'important' && row.lead) || filters.stage === row.phase)
      .sort((a,b) => {
        if (filters.sort === 'closing' || filters.stage === 'closing') {
          const end = row => ['active','upcoming'].includes(row.phase) ? row.end_date || '9999' : '9999';
          const close = (a.close ?? 999) - (b.close ?? 999) || end(a).localeCompare(end(b));
          if (close) return close;
        }
        if (filters.sort === 'new') {
          const date = String(b.first_seen || '').localeCompare(String(a.first_seen || ''));
          if (date) return date;
        }
        const band = { active: 0, upcoming: 0, unknown: 1, ended: 2, cancelled: 2, postponed: 2, needs_confirmation: 2 };
        return band[a.phase] - band[b.phase] || b.score - a.score || (a.close ?? 999) - (b.close ?? 999)
          || String(a.start_date || '').localeCompare(String(b.start_date || '')) || a.id.localeCompare(b.id);
      });
  }

  function spotlight(rows, regional = false, limit = 6) {
    const chosen = [], venues = new Set(), regions = new Map();
    for (const row of rows) {
      if (!row.lead || ['visited','uninterested'].includes(row.log?.status)) continue;
      const venue = normal(row.venue).trim(), region = row.prefecture || row.country;
      if ((venue && venues.has(venue)) || (!regional && (regions.get(region) || 0) >= 2)) continue;
      if (venue) venues.add(venue);
      regions.set(region,(regions.get(region) || 0) + 1);
      chosen.push(row);
      if (chosen.length >= limit) break;
    }
    return chosen;
  }

  function parseLog(value) {
    if (value?.format !== logFormat || !Array.isArray(value.records) || value.records.length > 5000) throw new Error('观展记录文件格式无效');
    const result = new Map();
    for (const r of value.records) {
      if (!r || typeof r.id !== 'string' || !validId.test(r.id) || result.has(r.id) ||
          !(r.status === null || own(statuses,r.status)) || typeof r.favorite !== 'boolean' ||
          !(r.rating === null || Number.isInteger(r.rating) && r.rating >= 1 && r.rating <= 5) ||
          typeof r.note !== 'string' || r.note.length > 4000 || typeof r.title !== 'string' || r.title.length > 600)
        throw new Error('观展记录中有无效的标签、评分或笔记');
      result.set(r.id,{ id:r.id, status:r.status, favorite:r.favorite, rating:r.rating, note:r.note, title:r.title });
    }
    return result;
  }

  function create({ C, boot, server, toast, rerender, isActive }) {
    const e = C.escape, $ = id => document.getElementById(id), size = 18;
    const filter = { scope:'JP', prefecture:'all', medium:'all', stage:'all', personal:'all', sort:'recommended', query:'', page:1 };
    const sections = [['all','所有展期'],['active','正在展出'],['upcoming','即将开幕'],['closing','7 天内闭展'],['important','值得留意'],['ended','已闭展'],['unknown','展期待定']];
    const personal = [['all','全部展览'],['records','我的观展记录'],...Object.entries(statuses),['favorite','收藏']];
    let catalog = boot.japan_exhibitions || null, pending = false, failed = false, records = new Map(), current = new Map(), areas = new Map();
    let filtersOpen = matchMedia('(min-width: 840px)').matches;
    try {
      const saved = localStorage.getItem(logFormat);
      if (saved) records = parseLog(JSON.parse(saved));
    } catch { toast('浏览器的观展记录暂时无法读取'); }
    const log = () => ({ format:logFormat, records:[...records.values()] });
    function persist(message) {
      try { localStorage.setItem(logFormat,JSON.stringify(log())); toast(message); }
      catch { toast('浏览器未能保存观展记录，可先导出备份'); }
    }
    function load() {
      if (catalog || pending || failed) return;
      const url = server ? '/api/japan-exhibitions' : boot.exhibition_store;
      if (!url) return;
      pending = true;
      C.fetchTimed(url, {}, 15000).then(response => {
        if (!response.ok) throw new Error('catalogue_unavailable');
        return response.json();
      }).then(data => {
        if (data?.schema_version !== 1 || !Array.isArray(data.items)) throw new Error('catalogue_invalid');
        catalog = data;
      }).catch(() => { failed = true; }).finally(() => { pending = false; if (isActive()) rerender(); });
    }
    const title = row => row.title_zh || row.title_original || '未命名展览';
    const detailHref = row => (boot.exhibition_page && location.protocol !== 'file:' && !row.is_demo ? boot.exhibition_page + '?id=' : '#exhibition/') + encodeURIComponent(row.id);
    const town = row => [row.prefecture_name || areas.get(row.prefecture)?.name || row.city || C.countryLabels[row.country] || row.country,row.venue].filter(Boolean).join(' · ');
    const schedule = row => row.start_date
      ? C.dateLabel(row.start_date) + (row.end_date ? ' — ' + C.dateLabel(row.end_date) : row.date_precision === 'day' ? ' 起 · 闭展日期未公布' : ' · 具体日期待定')
      : '展期未公布';
    const option = (value,name,selected) => `<option value="${e(value)}" ${selected === value ? 'selected' : ''}>${e(name)}</option>`;
    const select = (field,pairs,label) => `<label class="exhibition-select">${label}<select data-ex-filter="${field}">${pairs.map(([v,n])=>option(v,n,filter[field])).join('')}</select></label>`;
    function card(row, featured = false, lead = false) {
      const due = row.close === null ? phases[row.phase] : (row.date_conflict ? '有来源显示' : '') + (row.close === 0 ? '今日闭展' : `${row.close} 天后闭展`);
      const tags = (row.types || []).filter(kind => kind !== 'other').map(kind => types[kind]);
      if (featured) tags.push(...row.reasons.map(key => signals[key][1]));
      const picture = C.safeImageUrl(row.image_url), credit = catalog?.coverage?.sources?.[row.image_source]?.name;
      return `<article class="exhibition-card${featured ? ' exhibition-card--feature' : ''}${lead ? ' exhibition-card--lead' : ''}${picture ? ' exhibition-card--pictured' : ''}">
        ${picture ? `<a class="exhibition-card-image" href="${e(detailHref(row))}" aria-label="查看${e(title(row))}"><img src="${e(picture)}" alt="" loading="${lead ? 'eager' : 'lazy'}" decoding="async" referrerpolicy="no-referrer" data-ex-image></a>` : ''}
        <div class="exhibition-card-body"><p class="exhibition-kicker"><span class="${row.close !== null ? 'exhibition-urgent' : ''}">${e(due)}</span>
        ${row.date_conflict ? '<span>日期有出入</span>' : ''}${row.status === 'tentative' ? '<span>暂定</span>' : ''}${row.official ? '<span>场馆官网</span>' : ''}</p>
        <h3><a class="exhibition-title" href="${e(detailHref(row))}" data-ex-detail="${e(row.id)}">${e(title(row))}</a></h3>
        <p class="exhibition-place">${e(town(row))}</p><p class="exhibition-dates">${e(schedule(row))}</p>
        ${tags.length ? `<p class="exhibition-kicker">${[...new Set(tags)].map(tag => `<span>${e(tag)}</span>`).join('')}</p>` : ''}
        ${row.log?.rating ? `<p class="exhibition-kicker">我的评分 ${row.log.rating} / 5</p>` : ''}
        ${credit && picture ? `<p class="exhibition-image-credit">图源 ${e(credit)}</p>` : ''}
        <div class="exhibition-actions">
          <button class="exhibition-chip" data-ex-want="${e(row.id)}" aria-pressed="${row.log?.status === 'want'}">${row.log?.status === 'want' ? '✓ 想去' : '想去'}</button>
          <button class="exhibition-chip" data-ex-favorite="${e(row.id)}" aria-pressed="${Boolean(row.log?.favorite)}">${row.log?.favorite ? '★ 已收藏' : '☆ 收藏'}</button>
          <a class="exhibition-chip" href="${e(detailHref(row))}" data-ex-detail="${e(row.id)}">${row.log?.status === 'visited' ? '✓ 去过 · 笔记' : row.log?.status === 'uninterested' ? '不感兴趣 · 设置' : '阅读展览详情 ↗'}</a>
        </div></div></article>`;
    }

    function coverage() {
      if (!catalog?.coverage) return '';
      const report = catalog.coverage, c = report.counts;
      const checked = new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Tokyo',dateStyle:'medium',timeStyle:'short'}).format(new Date(catalog.generated_at));
      const src = Object.values(report.sources).map(row => `<li><a href="${e(C.safeUrl(row.url))}" target="_blank" rel="noopener noreferrer">${e(row.name)} ↗</a> · ${row.complete ? '已核对' : '有待补核'} · ${row.pages} 页 · ${row.collected} 条展览记录${row.listed != null ? ` · 读取 ${row.observed}/${row.listed} 条目录记录` : ''}</li>`).join('');
      return `<details class="exhibition-coverage"><summary>日本覆盖 · ${c.prefectures_directory_complete}/47 个地方目录已核满 · ${c.official_calendars_checked}/${c.official_calendars_total} 个官网日历已核对</summary>
        <p>东京时间 ${e(checked)}。某地目录为零，仍可能有未登记的展览。${boot.exhibition_report ? ` <a class="text-link" href="${e(boot.exhibition_report)}">查看完整核对数据 ↗</a>` : ''}</p>
        <ul class="exhibition-source-list">${src}</ul>
        <div class="exhibition-table-wrap"><table><caption>按都道府县核对</caption><thead><tr><th scope="col">地区</th><th scope="col">公开目录</th><th scope="col">在展与待开展</th><th scope="col">场馆日历</th></tr></thead><tbody>
        ${report.prefectures.map(a => `<tr><th scope="row">${e(a.name)}</th><td>${a.directory.complete ? a.directory.listed + ' 条，已核满' : '待补核'}</td><td>${a.active_or_upcoming}</td><td>${a.official_calendars ? a.official_calendars_checked + '/' + a.official_calendars : '尚未直连'}</td></tr>`).join('')}
        </tbody></table></div>${c.unresolved_prefecture ? `<p>另有 ${c.unresolved_prefecture} 条地区待核对，可按「地点待确认」查询。</p>` : ''}</details>`;
    }

    function view(dataset, preference) {
      const previousFilters = document.querySelector('.exhibition-filter-panel');
      if (previousFilters) filtersOpen = previousFilters.open;
      const live = dataset.mode !== 'demo';
      if (live) load();
      areas = new Map((live ? catalog?.coverage?.prefectures || [] : []).map(area => [area.code,area]));
      const items = live && catalog ? [...catalog.items] : [];
      const urlKey = url => String(url || '').replace(/\/$/,'');
      const urls = new Set(items.flatMap(row => (row.evidence || []).map(item => urlKey(item.url))));
      for (const event of live && catalog?.includes_legacy_events ? [] : dataset.events || []) {
        if (event.event_type !== 'exhibition' || urls.has(urlKey(event.evidence_url))) continue;
        items.push({ ...event, official:event.evidence_status === 'official_confirmed', types:[event.channel === 'photography' ? 'photography' : 'other'], status:'scheduled' });
      }
      current = new Map(items.filter(r=>typeof r.id === 'string' && validId.test(r.id)).map(r=>[r.id,r]));
      if (filter.personal !== 'all' && live) for (const record of records.values()) {
        if (!current.has(record.id)) current.set(record.id,{ id:record.id, title_original:record.title, country:record.id.startsWith('jp-ex-') ? 'JP' : '', types:['other'], date_precision:'unknown' });
      }
      const dates = new Map();
      const today = (zone = 'Asia/Tokyo') => {
        if (!dates.has(zone)) dates.set(zone,live ? C.localDate(zone) : dataset.reference_date);
        return dates.get(zone);
      };
      const list = rank(C,[...current.values()],records,{...filter,labels:areas,today,preference});
      const highlights = filter.personal === 'all' && filter.stage === 'all' && !filter.query.trim();
      const leads = highlights ? spotlight(list,filter.prefecture !== 'all',5) : [];
      const due = highlights ? list.filter(r=>r.close !== null) : [];
      const savedDue = due.filter(r=>r.log?.status === 'want').length;
      const closing = due.filter(r=>!['uninterested','visited'].includes(r.log?.status))
        .sort((a,b)=>Number(b.log?.status === 'want') - Number(a.log?.status === 'want') || a.close - b.close || b.score - a.score);
      const pages = Math.max(1,Math.ceil(list.length / size));
      filter.page = Math.min(pages,Math.max(1,filter.page));
      const filterCount = ['prefecture','medium','stage','personal'].filter(key => filter[key] !== 'all').length + Number(filter.sort !== 'recommended');
      return `<div class="exhibition-page" data-ui="exhibition-desk"><div class="exhibition-controls"><div class="exhibition-toolbar">
        <div class="exhibition-scopes" role="group" aria-label="展览地区">${[['JP','日本'],['world','日本以外'],['all','全球']].map(([k,n])=>`<button class="exhibition-chip" data-ex-scope="${k}" aria-pressed="${filter.scope === k}">${n}</button>`).join('')}<button class="exhibition-chip" data-ex-mine aria-pressed="${filter.personal === 'records'}">我的观展记录</button></div>
        <input class="exhibition-search" type="search" aria-label="搜索展览" data-ex-search maxlength="180" placeholder="搜展名、场馆、都道府县" value="${e(filter.query)}"></div>
        <details class="exhibition-filter-panel" ${filtersOpen?'open':''}><summary>筛选展览${filterCount ? ' · 已启用 ' + filterCount : ''}</summary>
        <div class="exhibition-selects">${filter.scope !== 'world' ? select('prefecture',[['all','全部地区'],...[...areas.values()].map(a=>[a.code,a.name]),['unknown','地点待确认']],'都道府县') : ''}
          ${select('medium',[['all','全部类型'],...Object.entries(types)],'类型')}${select('stage',sections,'展期')}${select('personal',personal,'个人标签')}
          ${select('sort',[['recommended','推荐顺序'],['closing','闭展在先'],['new','最近收录']],'排序')}</div></details></div>
        ${pending ? '<p class="compact-note" role="status">正在读取日本展览目录…</p>' : failed ? '<p class="compact-note">日本目录暂未载入，以下显示现有活动。 <button class="text-link" data-ex-retry>重试</button></p>' : ''}
        ${due.length ? `<button class="exhibition-chip exhibition-deadline-jump" data-ex-closing>7 天内闭展 · ${due.length} 场${savedDue ? ' · 想去 ' + savedDue + ' 场' : ''} ↗</button>` : ''}
        ${leads.length ? `<section class="exhibition-section"><div class="exhibition-section-head"><h2>值得留意</h2><button class="text-link" data-ex-important>查看重点展 ↗</button></div><div class="exhibition-feature-grid">${leads.map((r, i)=>card(r,true,i===0)).join('')}</div></section>` : ''}
        ${closing.length ? `<section class="exhibition-section exhibition-deadlines"><div class="exhibition-section-head"><h2>7 天内闭展</h2><button class="text-link" data-ex-closing>查看闭展清单 ↗</button></div>
          <ul>${closing.slice(0,8).map(r=>`<li><span>${r.log?.status === 'want' ? '想去 · ' : ''}${r.close === 0 ? '今天' : r.close + ' 天后'}${r.date_conflict ? ' · 日期待核' : ''}</span>
          <a class="exhibition-title" href="${e(detailHref(r))}" data-ex-detail="${e(r.id)}">${e(title(r))}</a><span>${e(town(r))}</span></li>`).join('')}</ul></section>` : ''}
        <section class="exhibition-section" id="exhibition-results"><div class="exhibition-section-head"><h2>${filter.personal === 'all' ? '展览清单' : personal.find(([k])=>k===filter.personal)?.[1]}</h2><span class="count-label">${list.length} 场</span></div>
          <div class="exhibition-list">${list.slice(size*(filter.page-1),size*filter.page).map(r=>card(r)).join('') || '<p class="exhibition-empty">当前筛选没有展览。</p>'}</div>
          ${pages > 1 ? `<div class="exhibition-pager"><button class="exhibition-chip" data-ex-page="${filter.page-1}" ${filter.page===1?'disabled':''}>上一页</button>
            <label>第 <select data-ex-filter="page" aria-label="展览页码">${Array.from({length:pages},(_,i)=>option(i+1,i+1,filter.page)).join('')}</select> / ${pages} 页</label>
            <button class="exhibition-chip" data-ex-page="${filter.page+1}" ${filter.page===pages?'disabled':''}>下一页</button></div>` : ''}
        </section>${live ? coverage() : ''}
        <details class="exhibition-coverage"><summary>备份我的观展记录</summary><p>笔记、评分和标签保存在本浏览器。换设备可导出再导入。</p>
          <div class="exhibition-actions"><button class="exhibition-chip" data-ex-export>导出</button><button class="exhibition-chip" data-ex-import>导入</button><input type="file" id="exhibition-import" accept=".json,application/json" hidden></div>
        </details></div>`;
    }

    function reader(row, description = {}, names = {}) {
      const id = row.id, record = records.get(id);
      current.set(id, row);
      const origin = C.safeUrl(row.evidence_url);
      const sourceName = id => names[id] || catalog?.coverage?.sources?.[id]?.name || id;
      const image = C.safeImageUrl(description.image || row.image_url), credit = sourceName(description.image ? description.source : row.image_source);
      const official = C.safeUrl(description.official_url);
      const introUrl = C.safeUrl(description.url);
      const sourceList = (row.evidence || []).map(item => {
        const link = C.safeUrl(item.url), label = sourceName(item.source);
        return link ? `<li><a href="${e(link)}" target="_blank" rel="noopener noreferrer">${e(label)}${item.official ? ' · 场馆官网' : ''} ↗</a><span>${e(item.date_text)}</span></li>` : '';
      }).join('');
      const paragraphs = Array.isArray(description.paragraphs) ? description.paragraphs.filter(text => typeof text === 'string' && text.trim()) : [];
      return `<article class="exhibition-reader" data-ui="exhibition-reader">
        <header class="exhibition-reader-head"><p class="exhibition-kicker">展览 ${row.types?.map(key => types[key]).filter(Boolean).join(' · ') || ''}</p>
          <h1>${e(title(row))}</h1><p class="exhibition-reader-deck">${e(town(row))} <span>${e(schedule(row))}</span></p></header>
        ${image ? `<figure class="exhibition-reader-figure"><img src="${e(image)}" alt="${e(title(row))}" decoding="async" referrerpolicy="no-referrer" data-ex-image>${credit ? `<figcaption>图源 ${e(credit)}</figcaption>` : ''}</figure>` : ''}
        <div class="exhibition-reader-grid"><section class="exhibition-introduction">
          <h2>${description.status === 'excerpt' ? '展讯摘要' : '展览介绍'}</h2>
          ${paragraphs.length ? `<div class="exhibition-prose" lang="ja">${paragraphs.map(line=>`<p>${e(line)}</p>`).join('')}</div>
            ${introUrl ? `<p class="exhibition-kicker"><a href="${e(introUrl)}" target="_blank" rel="noopener noreferrer">${e(sourceName(description.source))} · 来源原文 ↗</a></p>` : ''}`
            : `<p>暂未取得公开展览介绍。${origin && !row.is_demo ? `<a href="${e(origin)}" target="_blank" rel="noopener noreferrer">查看来源展讯 ↗</a>` : ''}</p>`}
          </section><aside class="exhibition-visit-info"><h2>观展信息</h2><p>${e(town(row))}</p><p>${e(schedule(row))}</p>
            ${row.date_conflict ? '<p class="compact-note">来源日期有出入，请核对场馆官网。</p>' : ''}
            ${official ? `<p><a href="${e(official)}" target="_blank" rel="noopener noreferrer">场馆官方展讯 ↗</a></p>` : ''}
            ${sourceList ? `<ul class="exhibition-evidence">${sourceList}</ul>` : origin && !row.is_demo ? `<p><a href="${e(origin)}" target="_blank" rel="noopener noreferrer">查看展览来源 ↗</a></p>` : ''}
          </aside></div>
        <form id="exhibition-record" data-ex-id="${e(id)}"><h3>我的观展记录</h3><div class="exhibition-record-fields">
          <label>标签<select name="status">${[['','未设置'],...Object.entries(statuses)].map(([v,n])=>option(v,n,record?.status || '')).join('')}</select></label>
          <label>评分<select name="rating">${[['','未评分'],...[1,2,3,4,5].map(n=>[n,n+' / 5'])].map(([v,n])=>option(v,n,record?.rating || '')).join('')}</select></label>
          <label class="exhibition-checkbox"><input type="checkbox" name="favorite" ${record?.favorite?'checked':''}> 收藏</label>
        </div><label class="exhibition-note">观后笔记<textarea name="note" rows="5" maxlength="4000" placeholder="记下作品和观感">${e(record?.note || '')}</textarea></label>
        <button class="button secondary" type="submit">保存记录</button></form></article>`;
    }
    function inlineReader(id, dataset) {
      if (dataset.mode !== 'demo') load();
      const row = catalog?.items?.find(item => item.id === id) || dataset.events?.find(item => item.id === id && item.event_type === 'exhibition');
      const stored = boot.exhibition_details?.entries?.[id];
      const excerpt = row?.evidence?.find(item => item.intro_excerpt);
      const description = stored?.paragraphs?.length && row?.evidence?.some(item => item.url === stored.url) ? stored
        : excerpt ? {status:'excerpt',paragraphs:[excerpt.intro_excerpt],source:excerpt.source,url:excerpt.url} : {};
      return '<a class="text-link exhibition-back" href="#exhibitions">← 返回展览目录</a>' + (row ? reader(row, description) : '<p role="status">正在查找展览，或该展览暂时无法读取。</p>');
    }
    function update(id, changes) {
      if (!current.has(id)) return;
      if (!records.has(id) && records.size >= 5000) { toast('观展记录已达到 5000 条，可先导出备份'); return; }
      const row = {id,status:null,favorite:false,rating:null,note:'',...records.get(id),...changes,title:title(current.get(id)).slice(0,600)};
      if (row.status || row.favorite || row.rating || row.note) records.set(id,row); else records.delete(id);
      persist('观展记录已保存'); rerender();
    }
    function goToResults() { $('exhibition-results')?.scrollIntoView({block:'start'}); }
    document.addEventListener('error', event => {
      if (event.target.matches?.('[data-ex-image]')) {
        const image = event.target.closest('a,figure');
        if (image) image.hidden = true;
        event.target.closest('.exhibition-card')?.classList.remove('exhibition-card--pictured');
      }
    }, true);
    document.addEventListener('toggle', event => {
      if (event.target.matches?.('.exhibition-filter-panel') && event.target.isConnected) filtersOpen = event.target.open;
    }, true);
    document.addEventListener('click', event => {
      const button = event.target.closest?.('button');
      if (!button || !isActive()) return;
      const d = button.dataset;
      if ('exScope' in d) { filter.scope=d.exScope; filter.prefecture='all'; filter.page=1; rerender(); }
      else if ('exMine' in d) {
        const open = filter.personal !== 'records';
        Object.assign(filter,{personal:open ? 'records' : 'all',scope:open ? 'all' : 'JP',prefecture:'all',medium:'all',stage:'all',query:'',page:1});
        rerender();
      }
      else if ('exWant' in d) update(d.exWant,{ status:records.get(d.exWant)?.status === 'want' ? null : 'want' });
      else if ('exFavorite' in d) update(d.exFavorite,{favorite:!records.get(d.exFavorite)?.favorite});
      else if ('exClosing' in d) { filter.stage='closing'; filter.page=1; rerender(); goToResults(); }
      else if ('exImportant' in d) { filter.stage='important'; filter.page=1; rerender(); goToResults(); }
      else if ('exPage' in d && !button.disabled) { filter.page=Number(d.exPage); rerender(); goToResults(); }
      else if ('exRetry' in d) { failed=false; rerender(); }
      else if ('exImport' in d) $('exhibition-import').click();
      else if ('exExport' in d) {
        const url = URL.createObjectURL(new Blob([JSON.stringify(log(),null,2)],{type:'application/json'}));
        const link = document.createElement('a'); link.href=url; link.download='幕间休息-观展记录.json'; link.click();
        setTimeout(()=>URL.revokeObjectURL(url),3000);
      }
    });
    document.addEventListener('change',async event => {
      const input = event.target;
      if (!isActive()) return;
      const field = input.dataset.exFilter;
      if (own(filter,field)) {
        filter[field]=field === 'page' ? Number(input.value) : input.value;
        if (field !== 'page') filter.page=1;
        rerender();
        if (field === 'page') goToResults();
      }
      if (input.id === 'exhibition-import' && input.files?.[0]) try {
        if (input.files[0].size > 25_000_000) throw new Error('观展记录文件过大');
        const imported = parseLog(JSON.parse(await input.files[0].text())), combined = new Map([...imported,...records]);
        if (combined.size > 5000) throw new Error('备份超过 5000 条记录');
        records=combined; persist('观展备份已导入，原有记录优先'); rerender();
      } catch (error) { toast(error.message); input.value=''; }
    });
    document.addEventListener('input',event => {
      const input = event.target;
      if (!input.hasAttribute?.('data-ex-search') || !isActive() || event.isComposing) return;
      filter.query=input.value; filter.page=1;
      const end = input.selectionEnd;
      rerender();
      const next=document.querySelector('[data-ex-search]');
      next?.focus({preventScroll:true});
      if (end !== null) next?.setSelectionRange(end,end);
    });
    document.addEventListener('submit',event => {
      if (event.target.id !== 'exhibition-record') return;
      event.preventDefault();
      const data = new FormData(event.target);
      update(event.target.dataset.exId,{status:data.get('status') || null,rating:Number(data.get('rating')) || null,
        favorite:data.has('favorite'),note:String(data.get('note')).trim()});
    });
    return { view, reader, inlineReader };
  }
  const api = { create, phase, closingDays, rank, spotlight, parseLog };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureExhibitions = api;
})(typeof window !== 'undefined' ? window : globalThis);
