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
  const importanceLabels = ['常设展', '常规展', '专题与企划', '重点展'];
  const phaseOrder = { active: 0, upcoming: 1, unknown: 2, ended: 3, cancelled: 3, postponed: 3, needs_confirmation: 3 };
  const activeLimit = 100;
  const logFormat = 'culture-desk-exhibition-log-v1';
  const validId = /^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$/;
  const validVenue = /^venue-[a-f0-9]{24}$/;
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
    if (row.related_event || row.date_precision !== 'day' || [...paused, 'tentative'].includes(row.status) || ageOf(C,row.last_seen,today) > 14) return null;
    const windows = row.date_conflict
      ? (row.evidence || []).filter(x => x.status === 'scheduled' && ageOf(C,x.last_seen,today) <= 14).map(x => [x.start,x.end])
      : [[row.start_date,row.end_date]];
    const ends = windows.filter(([start]) => { const days = C.daysBetween(today,start); return days !== null && days <= 7; })
      .map(([,end]) => C.daysBetween(today,end)).filter(days => days !== null && days >= 0 && days <= 7);
    return ends.length ? Math.min(...ends) : null;
  }

  function decorate(C, row, log, today, venues, preference = {}) {
    const state = phase(C,row,today), close = closingDays(C,row,today), start = C.daysBetween(today,row.start_date);
    const recommendation = row.recommendation || {};
    const importance = recommendation.tier ?? (row.flags?.includes('permanent') ? 0 : 1);
    const programme = recommendation.programme ?? 0;
    const sourceSupport = recommendation.support ?? Number(Boolean(row.official));
    const firmDates = Number(!row.date_conflict && row.status !== 'tentative' && ageOf(C,row.last_seen,today) <= 14);
    const followed = venues?.has(row.venue_id) || false;
    const followedNew = followed && importance > 0 && !row.related_event && row.status !== 'tentative' && log?.status !== 'visited'
      && (state === 'upcoming' || (state === 'active' && start >= -14));
    const followedEntity = (preference.followed_entities || []).some(value => {
      const name = normal(value).trim();
      return name && normal(row.title_original + ' ' + (row.venue || '')).includes(name);
    });
    const photoInterest = row.types?.includes('photography') && (preference.interests || []).some(value => value === 'photography' || value === '摄影展' || value === '摄影');
    const personalInterest = Number(log?.status === 'want') * 2 + Number(followedEntity) + Number(Boolean(photoInterest));
    return { ...row, phase: state, close, start, importance, programme, sourceSupport, firmDates, personalInterest, log, followedNew };
  }

  function groupsWithStatus(items, records, status) {
    return new Set(items.filter(row => row.duplicate_group && records.get(row.id)?.status === status).map(row => row.duplicate_group));
  }

  function onePerEdition(rows, records) {
    const editions = new Map();
    const choice = row => Number(records.get(row.id)?.status === 'want') * 4 + Number(records.has(row.id)) * 2 + Number(row.id === row.duplicate_group);
    for (const row of rows) {
      const key = row.duplicate_group || row.id, selected = editions.get(key);
      if (!selected || choice(row) > choice(selected)) editions.set(key,row);
    }
    return [...editions.values()];
  }

  function compareRecommendation(a,b) {
    const opening = String(a.start_date || '').localeCompare(String(b.start_date || ''));
    return phaseOrder[a.phase] - phaseOrder[b.phase] || b.importance - a.importance || b.programme - a.programme
      || b.sourceSupport - a.sourceSupport || b.firmDates - a.firmDates || b.personalInterest - a.personalInterest
      || (a.phase === 'upcoming' ? opening : -opening) || a.id.localeCompare(b.id);
  }

  function rank(C, items, records, filters) {
    const needles = normal(filters.query).trim().split(/\s+/).filter(Boolean);
    const importanceOrder = ['top','upcoming','important'].includes(filters.stage);
    const publicList = ['all','venues'].includes(filters.personal);
    const hiddenGroups = groupsWithStatus(items,records,'uninterested');
    const visitedGroups = filters.stage === 'top' ? groupsWithStatus(items,records,'visited') : new Set();
    const ranked = items.filter(row => {
      if (publicList && row.related_event) return false;
      if (filters.scope === 'JP' && row.country !== 'JP') return false;
      if (filters.scope === 'world' && row.country === 'JP') return false;
      if (filters.prefecture !== 'all' && (row.prefecture || 'unknown') !== filters.prefecture) return false;
      if (filters.medium !== 'all' && !(row.types || []).includes(filters.medium)) return false;
      const log = records.get(row.id);
      if ((log?.status === 'uninterested') !== (filters.personal === 'uninterested')) return false;
      if (filters.personal !== 'uninterested' && hiddenGroups.has(row.duplicate_group)) return false;
      if (filters.personal === 'venues' && !filters.venues?.has(row.venue_id)) return false;
      if ((filters.personal === 'favorite' && !log?.favorite) || (filters.personal === 'records' && !log)) return false;
      if (own(statuses,filters.personal) && log?.status !== filters.personal) return false;
      const pref = filters.labels?.get(row.prefecture);
      const query = normal([row.title_original,row.title_zh,row.venue,row.area,row.city,pref?.name,pref?.original,
        ...(row.types || []).map(key => types[key])].join(' '));
      return needles.every(needle => query.includes(needle));
    }).map(row => decorate(C,row,records.get(row.id),filters.today(row.timezone),filters.venues,filters.preference))
      .filter(row => filters.stage === 'all' || (filters.stage === 'closing' && row.close !== null)
        || (filters.stage === 'top' && row.phase === 'active' && row.status !== 'tentative' && row.log?.status !== 'visited' && !visitedGroups.has(row.duplicate_group))
        || (filters.stage === 'important' && row.importance === 3 && row.status !== 'tentative' && ['active','upcoming'].includes(row.phase)) || filters.stage === row.phase)
      .sort((a,b) => {
        if (filters.stage === 'closing' || (!importanceOrder && filters.sort === 'closing')) {
          const planned = filters.stage === 'closing' ? Number(b.log?.status === 'want') - Number(a.log?.status === 'want') : 0;
          const end = row => ['active','upcoming'].includes(row.phase) ? row.end_date || '9999' : '9999';
          const close = planned || (a.close ?? 999) - (b.close ?? 999) || end(a).localeCompare(end(b));
          if (close) return close;
        }
        if (!importanceOrder && filters.sort === 'new') {
          const date = String(b.first_seen || '').localeCompare(String(a.first_seen || ''));
          if (date) return date;
        }
        if (filters.personal === 'venues' && a.followedNew !== b.followedNew) return Number(b.followedNew) - Number(a.followedNew);
        return compareRecommendation(a,b);
      });
    const results = publicList ? onePerEdition(ranked,records) : ranked;
    return filters.stage === 'top' ? results.slice(0,activeLimit) : results;
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

  function parseVenues(value) {
    const venues = value.venues === undefined ? [] : value.venues;
    if (!Array.isArray(venues) || venues.length > 5000) throw new Error('收藏场馆格式无效');
    const result = new Map();
    for (const row of venues) {
      if (!row || typeof row.id !== 'string' || !validVenue.test(row.id) || result.has(row.id) ||
          typeof row.name !== 'string' || !row.name.trim() || row.name.length > 600 ||
          typeof row.place !== 'string' || row.place.length > 120) throw new Error('收藏场馆格式无效');
      result.set(row.id, {id:row.id, name:row.name, place:row.place});
    }
    return result;
  }

  function create({ C, boot, server, toast, rerender, paginate, isActive, newspaperBody, readingMinutes }) {
    const e = C.escape, $ = id => document.getElementById(id), size = 18;
    const filter = { scope:'JP', prefecture:'all', medium:'all', stage:'top', personal:'all', sort:'recommended', query:'', page:1 };
    const scopes = [['JP','日本'],['world','日本以外'],['all','全球']];
    const sections = [['top','在展推荐'],['upcoming','即将开展'],['all','所有展期'],['active','正在展出（全部）'],['closing','7 天内闭展'],['important','重点展'],['ended','已闭展'],['unknown','展期待定']];
    const personal = [['all','全部展览'],['records','我的观展记录'],...Object.entries(statuses),['favorite','收藏'],['venues','收藏场馆的展览']];
    let catalog = !server && boot.japan_exhibitions || null, pending = false, failed = false, records = new Map(), current = new Map(), areas = new Map();
    let venues = new Map();
    const details = new Map(), detailPending = new Set(), detailFailed = new Set();
    let filtersOpen = false;
    let layoutFrame = 0;
    function layoutCards() {
      const list = document.querySelector('.exhibition-list');
      const width = list?.clientWidth;
      if (!width) return;
      const cards = [...list.querySelectorAll('.exhibition-card')];
      if (!cards.length) return;
      const style = root.getComputedStyle(list);
      const columns = Number(style.getPropertyValue('--exhibition-columns')) || 3;
      const gap = parseFloat(style.getPropertyValue('--exhibition-column-gap')) || 0;
      const columnWidth = (width - gap * (columns - 1)) / columns;
      const ratios = cards.map(card => {
        const img = card.querySelector('figure:not([hidden]) img');
        return img ? (img.naturalWidth / img.naturalHeight || 4 / 3) : 0;
      });
      // Plan from the bottom so a full row above cannot unnecessarily strand one poster at the end.
      const plan = Array(cards.length + 1);
      plan[cards.length] = {cost:0};
      for (let start = cards.length - 1; start >= 0; start--) {
        const maxCount = Math.min(columns, cards.length - start);
        for (let count = maxCount; count > 0; count--) {
          const line = ratios.slice(start, start + count);
          const height = (width - gap * (count - 1)) / line.reduce((sum, ratio) => sum + ratio, 0);
          if (count > 1 && (height > columnWidth * 1.6 || height * Math.min(...line) < columnWidth * 0.66)) continue;
          const cost = plan[start + count].cost + 1 + (count === 1 ? cards.length : 0);
          if (!plan[start] || cost < plan[start].cost) plan[start] = {count,cost};
        }
      }
      const rows = [];
      for (let start = 0; start < cards.length; start += plan[start].count) {
        const end = start + plan[start].count;
        rows.push({cards:cards.slice(start, end), ratios:ratios.slice(start, end)});
      }
      const existing = [...list.children].filter(node => node.classList.contains('exhibition-row'));
      const regroup = existing.length !== rows.length || rows.some((row, i) =>
        row.cards.length !== existing[i].children.length || row.cards.some((card, j) => card !== existing[i].children[j]));
      const focused = regroup && list.contains(document.activeElement) ? document.activeElement : null;
      const lines = rows.map((row, i) => {
        const line = regroup ? document.createElement('div') : existing[i];
        if (regroup) {
          line.className = 'exhibition-row';
          line.append(...row.cards);
        }
        line.style.setProperty('--exhibition-tracks', row.cards.length > 1
          ? row.ratios.map(ratio => `minmax(0, ${ratio}fr)`).join(' ') : 'minmax(0, 1fr)');
        if (row.cards.length === 1) line.style.setProperty('--exhibition-single-ratio', row.ratios[0] || 4 / 3);
        return line;
      });
      if (regroup) list.replaceChildren(...lines);
      focused?.focus({preventScroll:true});
    }
    function scheduleLayout() {
      if (layoutFrame) return;
      layoutFrame = root.requestAnimationFrame(() => {
        layoutFrame = 0;
        layoutCards();
      });
    }
    root.addEventListener('resize', scheduleLayout);
    document.addEventListener('load', event => {
      if (event.target.matches?.('.exhibition-card img')) scheduleLayout();
    }, true);
    function restore(value) {
      if (!value) { records.clear(); venues.clear(); return; }
      const saved = JSON.parse(value);
      const savedRecords = parseLog(saved), savedVenues = parseVenues(saved);
      records = savedRecords;
      venues = savedVenues;
    }
    try {
      restore(localStorage.getItem(logFormat));
    } catch { toast('浏览器的观展记录暂时无法读取'); }
    const log = () => ({ format:logFormat, records:[...records.values()], venues:[...venues.values()] });
    function persist(message) {
      try { localStorage.setItem(logFormat,JSON.stringify(log())); toast(message); }
      catch { toast('浏览器未能保存观展记录，可先导出备份'); }
    }
    function load() {
      if (catalog || pending || failed) return;
      const url = server ? '/exhibitions/catalogue.json' : boot.exhibition_store;
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
    const detailHref = row => '#exhibition/' + encodeURIComponent(row.id);
    const place = row => row.prefecture_name || areas.get(row.prefecture)?.name || row.city || C.countryLabels[row.country] || row.country || '';
    const town = row => [place(row),row.venue].filter(Boolean).join(' · ');
    const schedule = row => row.start_date
      ? C.dateLabel(row.start_date) + (row.end_date === row.start_date ? '' : row.end_date ? ' — ' + C.dateLabel(row.end_date) : row.date_precision === 'day' ? ' 起 · 闭展日期未公布' : ' · 具体日期待定')
      : '展期未公布';
    const option = (value,name,selected) => `<option value="${e(value)}" ${selected === value ? 'selected' : ''}>${e(name)}</option>`;
    const select = (field,pairs,label,selected = filter[field]) => `<label class="exhibition-select">${label}<select data-ex-filter="${field}">${pairs.map(([v,n])=>option(v,n,selected)).join('')}</select></label>`;
    const venueButton = (id, name) => id ? `<button class="text-link exhibition-action" data-ex-venue="${e(id)}" aria-label="${e((venues.has(id) ? '取消收藏场馆 ' : '收藏场馆 ') + name)}" aria-pressed="${venues.has(id)}">${venues.has(id) ? '★ 已收藏场馆' : '☆ 收藏场馆'}</button>` : '';
    function card(row, showImportance, stage, eagerImage) {
      const phaseShown = stage === row.phase || (stage === 'top' && row.phase === 'active');
      const closing = row.phase === 'active' && row.close !== null;
      const due = row.related_event || (closing ? (row.date_conflict ? '或' : '') + (row.close === 0 ? '今日闭展' : `${row.close} 天后闭展`)
        : phaseShown ? '' : phases[row.phase]);
      const picture = C.safeImageUrl(row.image_url);
      const hidden = row.log?.status === 'uninterested';
      const name = e(title(row)), destination = e(detailHref(row)), id = e(row.id);
      const notes = [row.followedNew && '收藏场馆新展', row.date_conflict && '日期有出入', row.status === 'tentative' && '暂定',
        row.log?.status === 'visited' && '去过', row.log?.rating && `我的评分 ${row.log.rating}/5`].filter(Boolean);
      const importanceReason = row.recommendation?.reason || '';
      return `<article class="exhibition-card" data-ex-id="${id}" data-importance="${row.importance}">
        ${picture ? `<figure class="exhibition-art"><a class="card-image-link exhibition-card-image" href="${destination}" data-ex-detail="${id}" tabindex="-1" aria-label="查看展览 ${name}"><img src="${e(picture)}" alt="" loading="${eagerImage ? 'eager' : 'lazy'}" decoding="async" referrerpolicy="no-referrer" data-ex-image></a></figure>` : ''}
        <div class="exhibition-card-body">${due || showImportance || notes.length ? `<div class="meta exhibition-kicker">
        ${due ? `<span class="${closing ? 'exhibition-urgent' : ''}">${e(due)}</span>` : ''}
        ${showImportance ? `<span class="exhibition-importance" title="${e(importanceReason)}">${importanceLabels[row.importance]}</span>` : ''}
        ${notes.map(note=>`<span>${e(note)}</span>`).join('')}</div>` : ''}
        <h3><a class="card-title exhibition-title" href="${destination}" data-ex-detail="${id}">${name}</a></h3>
        <p class="exhibition-place">${e(town(row))}</p><p class="exhibition-dates">${e(schedule(row))}</p>
        <div class="card-footer exhibition-actions">
          ${hidden ? '' : `<button class="text-link exhibition-action" data-ex-want="${id}" aria-pressed="${row.log?.status === 'want'}">${row.log?.status === 'want' ? '✓ 想去' : '想去'}</button>`}
          <button class="text-link exhibition-action" data-ex-favorite="${id}" aria-pressed="${Boolean(row.log?.favorite)}">${row.log?.favorite ? '★ 已收藏' : '☆ 收藏'}</button>
          <button class="text-link exhibition-action" data-ex-hide="${id}">${hidden ? '取消不感兴趣' : '不感兴趣'}</button>
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
      const searching = Boolean(filter.query.trim());
      const stage = filter.stage === 'top' && searching ? 'all' : filter.stage;
      const options = {...filter,stage,labels:areas,today,preference,venues};
      const all = [...current.values()];
      const list = rank(C,all,records,options);
      const highlights = filter.personal === 'all' && !searching && ['top','upcoming','all'].includes(stage);
      const closing = highlights ? rank(C,all,records,{...options,stage:'closing'}).filter(r=>r.log?.status !== 'visited') : [];
      const savedDue = closing.filter(r=>r.log?.status === 'want').length;
      const followed = highlights && venues.size ? rank(C,all,records,{...options,scope:'all',prefecture:'all',medium:'all',stage:'all',personal:'venues',sort:'recommended'}).filter(row=>row.followedNew) : [];
      const showImportance = ['top','upcoming','important'].includes(stage);
      const counts = importanceLabels.map((label, tier)=>list.filter(row=>row.importance === tier).length);
      const pages = Math.max(1,Math.ceil(list.length / size));
      const page = Math.min(pages,Math.max(1,filter.page));
      if (!pending) filter.page = page;
      const filterCount = Number(filter.scope !== 'JP') + ['prefecture','medium','personal'].filter(key => filter[key] !== 'all').length
        + Number(filter.sort !== 'recommended' && !showImportance);
      const showingFavorites = filter.personal === 'favorite';
      const sectionName = filter.personal === 'all' ? ({top:'正在展出',all:searching ? '展览检索结果' : '全部展览'})[stage] || sections.find(([key])=>key===stage)?.[1]
        : showingFavorites ? '收藏的展览' : personal.find(([key])=>key===filter.personal)?.[1];
      const resultCount = stage === 'top' ? '' : `<span class="count-label">${list.length} 场</span>`;
      const personalButton = (key, label) => `<button class="text-link exhibition-action" data-ex-personal="${key}"${key === 'records' ? ' data-ex-mine' : ''} aria-pressed="${filter.personal === key}">${label}</button>`;
      return `<div class="exhibition-page" data-ui="exhibition-desk"><div class="filters exhibition-controls">
        <div class="scope-links exhibition-personal" role="group" aria-label="个人展览">${personalButton('records','观展记录')}${personalButton('favorite','收藏')}</div>
        <button type="button" class="text-link exhibition-filter-toggle" data-ex-toggle-filters aria-controls="exhibition-filter-panel" aria-expanded="${filtersOpen}">筛选${filterCount ? ' · ' + filterCount : ''}<span aria-hidden="true"></span></button>
        <div id="exhibition-filter-panel" class="filter-selects exhibition-selects exhibition-filter-panel"${filtersOpen ? '' : ' hidden'}>${select('scope',scopes,'地区')}
          ${filter.scope !== 'world' ? select('prefecture',[['all','全部地区'],...[...areas.values()].map(a=>[a.code,a.name]),['unknown','地点待确认']],'都道府县') : ''}
          ${select('medium',[['all','全部类型'],...Object.entries(types)],'类型')}${select('stage',sections,'展期',stage)}${select('personal',personal,'个人标签')}
          ${showImportance ? '' : select('sort',[['recommended','推荐顺序'],['closing','闭展在先'],['new','最近收录']],'排序')}</div></div>
        ${pending ? '<p class="compact-note" role="status">正在读取日本展览目录…</p>' : failed ? '<p class="compact-note">日本目录暂未载入，以下显示现有活动。 <button class="text-link" data-ex-retry>重试</button></p>' : ''}
        ${followed.length ? `<section class="exhibition-section exhibition-deadlines" data-ui="venue-updates"><div class="exhibition-section-head"><h2>收藏场馆新展</h2><button class="text-link" data-ex-personal="venues">查看全部 ↗</button></div>
          <ul>${followed.slice(0,5).map(r=>`<li data-ex-id="${e(r.id)}"><span>${e(C.dateLabel(r.start_date))} ${r.phase === 'upcoming' ? '开展' : '已开展'}</span><a class="card-title exhibition-title" href="${e(detailHref(r))}">${e(title(r))}</a><span>${e(town(r))}</span></li>`).join('')}</ul></section>` : ''}
        ${showingFavorites ? `<section class="exhibition-section"><div class="exhibition-section-head"><h2>收藏的场馆</h2><span class="count-label">${venues.size} 个</span></div>
          ${venues.size ? `<ul class="exhibition-venue-list">${[...venues.values()].map(venue=>`<li><span>${e(venue.name)}${venue.place ? `<small>${e(venue.place)}</small>` : ''}</span>${venueButton(venue.id,venue.name)}</li>`).join('')}</ul>`
            : '<p class="compact-note">可在展览正文中收藏场馆。</p>'}</section>` : ''}
        ${filter.personal === 'all' ? `<div class="exhibition-stage-switch"><div class="tabs" role="group" aria-label="展览清单">${[['top','在展推荐'],['upcoming','即将开展'],['all','全部展览']].map(([key,label])=>`<button class="tab ${stage===key?'active':''}" data-ex-stage="${key}" aria-pressed="${stage===key}">${label}</button>`).join('')}</div>
          ${closing.length ? `<button class="text-link exhibition-deadline-jump" data-ex-closing>7 天内闭展 · ${closing.length} 场${savedDue ? ' · 想去 ' + savedDue + ' 场' : ''}</button>` : ''}</div>` : ''}
        <section class="exhibition-section" id="exhibition-results"><div class="exhibition-section-head" data-ex-count="${list.length}"><h2>${e(sectionName || '展览清单')}</h2>${resultCount}</div>
          ${showImportance && list.length ? `<p class="exhibition-tier-counts">${counts.map((amount,tier)=>amount ? `<span>${importanceLabels[tier]} ${amount}</span>` : '').reverse().join('')}</p>` : ''}
          <div class="exhibition-list">${list.slice(size*(page-1),size*page).map((row,index)=>card(row, showImportance, stage, index < 3)).join('') || `<p class="exhibition-empty">${showingFavorites ? '没有符合条件的收藏展览。' : '当前筛选没有展览。'}</p>`}</div>
          ${pages > 1 ? `<nav class="news-pagination" aria-label="展览分页"><button class="text-link" data-ex-page="${page-1}" ${page===1?'disabled':''}>‹ 上一页</button>
            <label>第 <select data-ex-filter="page" aria-label="展览页码">${Array.from({length:pages},(_,i)=>option(i+1,i+1,page)).join('')}</select> / ${pages} 页</label>
            <button class="text-link" data-ex-page="${page+1}" ${page===pages?'disabled':''}>下一页 ›</button></nav>` : ''}
        </section>${live && !showingFavorites ? coverage() : ''}
        <details class="exhibition-coverage"><summary>备份我的观展记录</summary><p>笔记、评分、标签和收藏场馆保存在本浏览器。换设备可导出再导入。</p>
          <div class="exhibition-actions"><button class="text-link exhibition-action" data-ex-export>导出</button><button class="text-link exhibition-action" data-ex-import>导入</button><input type="file" id="exhibition-import" accept=".json,application/json" hidden></div>
        </details></div>`;
    }

    function reader(row, description = {}, names = {}, tab = 'chinese') {
      const id = row.id, record = records.get(id), form = $('exhibition-record');
      const draft = form?.dataset.exId === id ? new FormData(form) : null;
      current.set(id, row);
      const origin = C.safeUrl(row.evidence_url);
      const sourceName = id => names[id] || catalog?.coverage?.sources?.[id]?.name || id;
      const image = C.safeImageUrl(description.image || row.image_url), credit = sourceName(description.image ? description.source : row.image_source);
      const official = C.safeUrl(description.official_url);
      const recommendation = row.recommendation;
      const recommendationUrl = C.safeUrl(recommendation?.url);
      const introUrl = C.safeUrl(description.url) || origin;
      const source = sourceName(description.source || row.source_id);
      const sourceList = [...(row.evidence || []),...(row.related_sources || [])].map(item => {
        const link = C.safeUrl(item.url), label = sourceName(item.source) || '展讯来源';
        return link ? `<li><a href="${e(link)}" target="_blank" rel="noopener noreferrer">${e(label)}${item.official ? ' · 场馆官网' : ''} ↗</a><span>${e(item.date_text)}</span></li>` : '';
      }).join('');
      const paragraphs = Array.isArray(description.paragraphs) ? description.paragraphs.filter(text => typeof text === 'string' && text.trim()) : [];
      const blocks = paragraphs.map(text=>({type:'paragraph',text}));
      const language = description.language || (paragraphs.length ? 'ja' : '');
      const shownTitle = tab === 'original' ? row.title_original || title(row) : title(row);
      const save = `<button class="text-link reader-save" data-ex-favorite="${e(id)}" aria-pressed="${Boolean(record?.favorite)}">${record?.favorite ? '★ 已收藏展览' : '☆ 收藏展览'}</button>`;
      const back = '<button class="text-link" data-action="reader-back">‹ 返回</button>';
      return `<article class="reader-page exhibition-reader" data-ui="exhibition-reader">
        <div class="reader-toolbar">${back}${save}${!row.is_demo && location.protocol !== 'file:' ? '<button class="text-link" data-action="share-exhibition">分享</button>' : ''}</div>
        <div class="eyebrow"><span class="channel-tag">${e(row.related_event || '展览')}</span>${source ? `<span>${e(source)}</span>` : ''}<span>${e(schedule(row))}</span>${blocks.length ? `<span class="reading-time">约 ${readingMinutes(blocks, language)} 分钟</span>` : ''}</div>
        <h1 lang="${e(shownTitle === row.title_zh ? 'zh-CN' : language)}">${e(shownTitle)}</h1>
        <div class="reader-tabs" role="tablist" aria-label="阅读内容"><button role="tab" aria-selected="${tab === 'chinese'}" data-reader-tab="chinese">正文</button><button role="tab" aria-selected="${tab === 'original'}" data-reader-tab="original">原文</button></div>
        <div class="reader-content" role="tabpanel">
          ${blocks.length && (tab !== 'original' || description.status === 'excerpt') ? `<p class="article-status original-pending">${description.status === 'excerpt' ? '来源短介' : '原文 · ' + e(C.languageLabels[language] || '外文')}</p>` : ''}
          <div class="reader-document" lang="${e(language)}">
            ${image ? `<figure class="article-image exhibition-reader-figure"><img src="${e(image)}" alt="${e(shownTitle)}" decoding="async" referrerpolicy="no-referrer"><figcaption>图片来源：${e(credit || source || '展览来源')}</figcaption></figure>` : ''}
            ${blocks.length ? newspaperBody(blocks) : `<div class="original-unavailable"><h2>暂未取得公开${row.related_event ? '活动' : '展览'}介绍</h2><p>日期、场馆和来源见下方。</p></div>`}
          </div>
        </div>
        ${introUrl && !row.is_demo ? `<div class="reader-source-link"><span>原文</span><a href="${e(introUrl)}" target="_blank" rel="noopener noreferrer">${e(introUrl)}</a></div>` : ''}
        <section class="exhibition-visit-info"><h2>观展信息</h2><p>${e(town(row))} · ${e(schedule(row))}</p>
          ${venueButton(row.venue_id,row.venue_name || row.venue)}
          ${row.date_conflict ? '<p class="compact-note">来源日期有出入，请核对场馆官网。</p>' : ''}
          ${official ? `<p><a href="${e(official)}" target="_blank" rel="noopener noreferrer">场馆官方展讯 ↗</a></p>` : ''}
          ${recommendation?.reason ? `<details class="exhibition-coverage"><summary>推荐依据</summary><p>${e(recommendation.reason)}${recommendationUrl ? ` <a href="${e(recommendationUrl)}" target="_blank" rel="noopener noreferrer">核对来源 ↗</a>` : ''}</p></details>` : ''}
          ${sourceList ? `<ul class="exhibition-evidence">${sourceList}</ul>` : ''}
        </section>
        <form id="exhibition-record" data-ex-id="${e(id)}"><h3>我的观展记录</h3><div class="exhibition-record-fields">
          <label>标签<select name="status">${[['','未设置'],...Object.entries(statuses)].map(([v,n])=>option(v,n,draft ? draft.get('status') : record?.status || '')).join('')}</select></label>
          <label>评分<select name="rating">${[['','未评分'],...[1,2,3,4,5].map(n=>[n,n+' / 5'])].map(([v,n])=>option(v,n,draft ? Number(draft.get('rating')) || '' : record?.rating || '')).join('')}</select></label>
          <label class="exhibition-checkbox"><input type="checkbox" name="favorite" ${(draft ? draft.has('favorite') : record?.favorite)?'checked':''}> 收藏展览</label>
        </div><label class="exhibition-note">观后笔记<textarea name="note" rows="5" maxlength="4000" placeholder="记下作品和观感">${e(draft ? draft.get('note') : record?.note || '')}</textarea></label>
        <button class="button secondary" type="submit">保存记录</button></form><div class="reader-toolbar reader-end">${back}${save}</div></article>`;
    }
    function inlineReader(id, dataset, tab) {
      const detail = details.get(id);
      if (detail) return reader(detail.item,detail.description,detail.sources,tab);
      const row = (dataset.mode !== 'demo' && catalog?.items?.find(item => item.id === id)) || dataset.events?.find(item => item.id === id && item.event_type === 'exhibition');
      const local = row && (row.is_demo || (!server && boot.exhibition_details));
      if (!local) {
        if (!detailPending.has(id) && !detailFailed.has(id)) {
          const root = server ? '/exhibitions/catalogue.json' : boot.exhibition_store;
          if (!root || location.protocol === 'file:') detailFailed.add(id);
          else {
            const url = new URL('items/' + encodeURIComponent(id) + '.json', new URL(root, document.baseURI));
            if (boot.exhibition_revision) url.searchParams.set('v',boot.exhibition_revision);
            detailPending.add(id);
            C.fetchTimed(url.href, {}, 15000).then(response => {
              if (!response.ok) throw new Error('exhibition_unavailable');
              return response.json();
            }).then(value => {
              if (value?.schema_version !== 1 || value.item?.id !== id) throw new Error('exhibition_invalid');
              details.set(id,value);
            }).catch(() => detailFailed.add(id)).finally(() => {
              detailPending.delete(id);
              if (isActive() && C.parseRoute(location.hash).id === id) rerender();
            });
          }
        }
        return `<article class="reader-page"><div class="reader-toolbar"><button class="text-link" data-action="reader-back">‹ 返回</button></div>
          <p class="article-status" role="status">${detailFailed.has(id) ? `展览正文未能载入。 <button class="text-link" data-ex-detail-retry="${e(id)}">重试</button>` : '正在载入正文…'}</p></article>`;
      }
      const stored = boot.exhibition_details?.entries?.[id];
      const excerpt = row?.evidence?.find(item => item.intro_excerpt);
      const description = stored?.paragraphs?.length && row?.evidence?.some(item => item.url === stored.url) ? stored
        : excerpt ? {status:'excerpt',paragraphs:[excerpt.intro_excerpt],source:excerpt.source,url:excerpt.url} : {};
      return reader(row,description,{},tab);
    }
    function update(id, changes) {
      if (!current.has(id)) return;
      if (!records.has(id) && records.size >= 5000) { toast('观展记录已达到 5000 条，可先导出备份'); return; }
      const row = {id,status:null,favorite:false,rating:null,note:'',...records.get(id),...changes,title:title(current.get(id)).slice(0,600)};
      if (row.status || row.favorite || row.rating || row.note) records.set(id,row); else records.delete(id);
      persist('观展记录已保存'); rerender();
    }
    function toggleVenue(id) {
      if (venues.has(id)) {
        venues.delete(id);
        persist('已取消收藏场馆');
      } else {
        const row = [...current.values()].find(item=>item.venue_id === id);
        if (!row || !validVenue.test(id)) return;
        if (venues.size >= 5000) { toast('收藏场馆已达到 5000 个，可先导出备份'); return; }
        venues.set(id,{id,name:(row.venue_name || row.venue).slice(0,600),place:place(row).slice(0,120)});
        persist('已收藏场馆，新展将在展览页优先显示');
      }
      rerender();
    }
    function personalView(personal) {
      Object.assign(filter,{personal,scope:personal === 'all' ? 'JP' : 'all',prefecture:'all',medium:'all',
        stage:personal === 'all' ? 'top' : 'all',query:'',sort:'recommended',page:1});
      rerender();
    }
    function setSearchQuery(query) {
      filter.query = query;
      filter.page = 1;
    }
    window.addEventListener('storage',event => {
      if (event.key !== logFormat) return;
      try { restore(event.newValue); if (isActive()) rerender(); } catch { /* Keep the last valid private log. */ }
    });
    function goToResults() { $('exhibition-results')?.scrollIntoView({block:'start'}); }
    function changeListPage(page) {
      if (!Number.isSafeInteger(page) || page < 1 || page === filter.page) return;
      paginate(() => { filter.page = page; });
      goToResults();
    }
    function restoreList(selection) {
      for (const field of Object.keys(filter)) if (own(selection,field)) filter[field] = selection[field];
      filtersOpen = Boolean(selection.filtersOpen);
    }
    document.addEventListener('error', event => {
      if (event.target.matches?.('[data-ex-image]')) {
        const image = event.target.closest('figure');
        if (image) image.hidden = true;
        if (event.target.closest('.exhibition-card')) scheduleLayout();
      }
    }, true);
    document.addEventListener('click', event => {
      const button = event.target.closest?.('button');
      if (!button || !isActive()) return;
      const d = button.dataset;
      if ('exToggleFilters' in d) {
        filtersOpen = !filtersOpen;
        button.setAttribute('aria-expanded', String(filtersOpen));
        $('exhibition-filter-panel').hidden = !filtersOpen;
      }
      else if ('exPersonal' in d) personalView(filter.personal === d.exPersonal ? 'all' : d.exPersonal);
      else if ('exStage' in d) { filter.stage=d.exStage; filter.sort='recommended'; filter.page=1; rerender(); }
      else if ('exVenue' in d) toggleVenue(d.exVenue);
      else if ('exHide' in d) update(d.exHide,{status:records.get(d.exHide)?.status === 'uninterested' ? null : 'uninterested'});
      else if ('exWant' in d) update(d.exWant,{ status:records.get(d.exWant)?.status === 'want' ? null : 'want' });
      else if ('exFavorite' in d) {
        const favorite = !records.get(d.exFavorite)?.favorite;
        const form = $('exhibition-record');
        if (form?.dataset.exId === d.exFavorite) form.elements.favorite.checked = favorite;
        update(d.exFavorite,{favorite});
      }
      else if ('exClosing' in d) { filter.stage='closing'; filter.page=1; rerender(); goToResults(); }
      else if ('exImportant' in d) { filter.stage='important'; filter.page=1; rerender(); goToResults(); }
      else if ('exPage' in d && !button.disabled) changeListPage(Number(d.exPage));
      else if ('exRetry' in d) { failed=false; rerender(); }
      else if ('exDetailRetry' in d) { detailFailed.delete(d.exDetailRetry); rerender(); }
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
        if (field === 'page') { changeListPage(Number(input.value)); return; }
        const focused = document.activeElement === input;
        if (field === 'personal') personalView(input.value);
        else {
          filter[field]=input.value;
          if (field === 'scope') filter.prefecture='all';
          filter.page=1;
          rerender();
        }
        if (focused) document.querySelector(`[data-ex-filter="${field}"]`)?.focus({preventScroll:true});
      }
      if (input.id === 'exhibition-import' && input.files?.[0]) try {
        if (input.files[0].size > 25_000_000) throw new Error('观展记录文件过大');
        const value = JSON.parse(await input.files[0].text());
        const combined = new Map([...parseLog(value),...records]), combinedVenues = new Map([...parseVenues(value),...venues]);
        if (combined.size > 5000 || combinedVenues.size > 5000) throw new Error('备份超过观展记录或场馆上限');
        records=combined; venues=combinedVenues; persist('观展备份已导入，原有记录优先'); rerender();
      } catch (error) { toast(error.message); input.value=''; }
    });
    document.addEventListener('submit',event => {
      if (event.target.id !== 'exhibition-record') return;
      event.preventDefault();
      const data = new FormData(event.target);
      update(event.target.dataset.exId,{status:data.get('status') || null,rating:Number(data.get('rating')) || null,
        favorite:data.has('favorite'),note:String(data.get('note')).trim()});
    });
    const readerTitle = (id, tab) => {
      const row = current.get(id);
      return row ? (tab === 'original' ? row.title_original || title(row) : title(row)) : '';
    };
    function calendarInventory() {
      load();
      const labels = new Map((catalog?.coverage?.prefectures || []).map(region=>[region.code,region.name]));
      const items = catalog?.items || [], hiddenGroups = groupsWithStatus(items,records,'uninterested');
      const eligible = items.filter(row=>!row.related_event && !hiddenGroups.has(row.duplicate_group) && records.get(row.id)?.status !== 'uninterested');
      const entries = onePerEdition(eligible,records).map(row=>({
        ...row, event_type:'exhibition', exhibition_id:row.id, prefecture_name:labels.get(row.prefecture), source_name:catalog.coverage?.sources?.[row.source_id]?.name,
      }));
      return {entries,pending,failed,includesLegacy:catalog?.includes_legacy_events};
    }
    const hidden = id => records.get(id)?.status === 'uninterested';
    return { view, layoutCards, inlineReader, readerTitle, calendarInventory, hidden, searchQuery: () => filter.query, setSearchQuery, listState: () => ({...filter, filtersOpen}), restoreList };
  }
  const api = { create, phase, closingDays, rank, parseLog, parseVenues };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureExhibitions = api;
})(typeof window !== 'undefined' ? window : globalThis);
