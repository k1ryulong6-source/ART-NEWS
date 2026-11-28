(function (root) {
  'use strict';
  const activity = {
    film: '电影放映与上映', cinema_screening: '艺术影院放映', cinema_release: '院线上映', cinema_showing: '日本院线在映',
    festival_screening: '影展放映', streaming_release: '流媒体首播', exhibition: '展览开幕与闭展',
    all: '全部活动'
  };
  const theatres = ['cinema_screening','cinema_release','festival_screening'];
  const unavailable = ['cancelled','postponed','needs_confirmation','tentative'];
  const isFilm = row => theatres.includes(row.event_type) || row.event_type === 'streaming_release';
  const normalize = value => String(value || '').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
  const isExhibition = row => row.event_type === 'exhibition';
  const filmTitle = row => row.movie?.title_zh || row.movie?.original_title || row.title_original;
  const entryTitle = row => isFilm(row) && !row.is_demo ? filmTitle(row) : row.title_zh || row.title_original;
  const mergeMovie = (primary, secondary) => primary && secondary ? {...secondary,...primary} : primary || secondary;

  function deduplicate(rows) {
    const events = new Map();
    const confidence = row => Number(Boolean(row.official || row.evidence_status === 'official_confirmed'));
    for (const row of rows) {
      const title = row.premiere_title ? normalize(row.premiere_title)
        : row.movie?.douban_id ? 'douban:' + row.movie.douban_id : normalize(row.title_original || row.title_zh);
      const kind = row.event_type;
      if (!title || !row.start_date || !activity[kind] || row.evidence_status === 'unverified') continue;
      const time = row.start_at ? Date.parse(row.start_at) : null;
      const place = kind === 'streaming_release' ? [row.platform]
        : [row.country,row.prefecture || row.city,row.venue && normalize(row.venue_name || row.venue),row.auditorium];
      const key = JSON.stringify([kind,title,row.start_date,...place,time]);
      const previous = events.get(key);
      const evidence = {url:row.evidence_url,name:row.source_name};
      if (!previous) {
        events.set(key,{...row,origins:evidence.url ? [evidence] : []});
        continue;
      }
      const origins = previous.origins.some(source=>source.url === evidence.url) || !evidence.url
        ? previous.origins : [...previous.origins,evidence];
      const conflict = isExhibition(row) && previous.end_date && row.end_date && previous.end_date !== row.end_date;
      const chosen = Number(Boolean(row.exhibition_id)) > Number(Boolean(previous.exhibition_id)) || confidence(row) > confidence(previous) ? row : previous;
      const alternate = chosen === row ? previous : row;
      events.set(key,{...chosen,movie:mergeMovie(chosen.movie,alternate.movie),origins,
        image_url:chosen.image_url || alternate.image_url,poster_url:chosen.poster_url || alternate.poster_url,
        artwork_url:chosen.artwork_url || alternate.artwork_url, booking_url:chosen.booking_url || alternate.booking_url,
        watch_url:chosen.watch_url || alternate.watch_url, programme_url:chosen.programme_url || alternate.programme_url,
        date_conflict:Boolean(chosen.date_conflict || conflict)});
    }
    return [...events.values()];
  }

  function inArea(row, area, kind) {
    if (kind === 'streaming_release' || (kind === 'all' && row.event_type === 'streaming_release') || area === 'global') return true;
    if (area === 'japan') return row.country === 'JP';
    if (area === 'tokyo') return row.country === 'JP' && (row.prefecture === '13' || ['东京','東京都','東京'].includes(row.city)
      || (row.event_type === 'cinema_release' && !row.city && !row.prefecture));
    return row.country === area;
  }

  function calendarEntries(rows, month) {
    const entries = [];
    for (const row of rows) {
      if (!activity[row.event_type] || !row.start_date) continue;
      if (unavailable.includes(row.status)) continue;
      const opening = row.date_precision === 'day' ? row.start_date : null;
      if (row.start_date.startsWith(month) && ['day','month'].includes(row.date_precision)) {
        entries.push({row,day:opening,label:opening ? isExhibition(row) ? '开展' : activity[row.event_type] : '仅公布月份'});
      }
      if (isExhibition(row) && opening && row.end_date?.startsWith(month) && row.end_date !== opening) {
        entries.push({row,day:row.end_date,label:'闭展'});
      }
    }
    // Unspecified days stay in a month-level listing and never occupy a day on the grid.
    return entries.sort((a,b)=>(a.day || '9999').localeCompare(b.day || '9999')
      || String(a.row.start_at || '').localeCompare(String(b.row.start_at || ''))
      || String(entryTitle(a.row)).localeCompare(String(entryTitle(b.row))));
  }

  function groupSchedule(entries) {
    const grouped = new Map();
    for (const entry of entries) {
      const {row, day} = entry;
      const timed = ['cinema_screening','festival_screening'].includes(row.event_type) && row.start_at && row.venue;
      const work = row.movie?.douban_id || [normalize(row.title_original),row.programme_url || row.evidence_url];
      const key = timed
        ? JSON.stringify([row.event_type,day,row.country,row.city,normalize(row.venue),work])
        : JSON.stringify([row.id,day,entry.label]);
      if (!grouped.has(key)) grouped.set(key,{...entry,screenings:[]});
      const group = grouped.get(key);
      if (group.row !== row && row.movie) group.row = {...group.row,movie:mergeMovie(group.row.movie,row.movie)};
      if (timed) group.screenings.push(row);
    }
    return [...grouped.values()];
  }

  function create({C,boot,server,exhibitions,isActive,rerender}) {
    const e = C.escape, pageSize = 12;
    const ref = url => `href="${e(url)}" target="_blank" rel="noopener noreferrer"`;
    const clocks = new Map();
    const landscape = new Map();
    let mode, dateToday, month, chosenDay, page = 1, area = 'tokyo', kind = 'film';
    let film = !server && boot.film_calendar || null, pending = false, failed = false;
    function loadFilm() {
      const url = server ? '/film-calendar.json' : boot.film_store;
      if (!url || film || pending || failed || location.protocol === 'file:') return;
      pending = true;
      C.fetchTimed(url,{},15000).then(response=>{
        if (!response.ok) throw new Error('calendar_unavailable');
        return response.json();
      }).then(data=>{
        if (data?.schema_version !== 1 || !Array.isArray(data.items)) throw new Error('calendar_invalid');
        film = data;
      }).catch(()=>{ failed=true; }).finally(()=>{ pending=false; if (isActive()) rerender(); });
    }
    function position(day, reference = dateToday) {
      const date = day || reference;
      month = date.slice(0,7); chosenDay = date; page = 1;
    }
    function sync(dataset) {
      dateToday = dataset.mode === 'demo' ? dataset.reference_date : C.localDate('Asia/Tokyo');
      if (mode !== dataset.mode) {
        mode = dataset.mode;
        position(dateToday);
      }
    }
    const listState = () => ({mode,month,chosenDay,page,area,kind});
    function restoreList(saved, dataset) {
      sync(dataset);
      if (saved?.mode === mode) ({month,chosenDay,page,area,kind} = saved);
    }
    const isLoading = () => pending || ((kind === 'all' || kind === 'exhibition') && exhibitions?.isLoading());

    function cover(row, alt = '', eager = true) {
      const movie = row.movie;
      const candidates = [movie?.poster_url,row.poster_url,row.image_url,movie?.artwork_url,row.artwork_url];
      const [imageUrl,...backups] = new Set(candidates.map(C.safeImageUrl).filter(Boolean));
      const fallback = backups.length ? ` data-calendar-backups="${e(JSON.stringify(backups))}"` : '';
      return imageUrl ? {landscape:landscape.get(imageUrl),html:`<img src="${e(imageUrl)}" alt="${e(alt)}" loading="${eager ? 'eager' : 'lazy'}" decoding="async" referrerpolicy="no-referrer" data-calendar-poster${fallback}>`} : null;
    }
    function placeLabels(row) {
      const country = row.country === 'GLOBAL' ? '' : C.countryLabels[row.country] || row.country;
      const place = row.prefecture_name || row.city || country;
      return [...new Set((row.event_type === 'streaming_release' ? [row.platform,row.market || country] : [row.venue,place]).filter(Boolean))];
    }
    function screeningTimes(slots) {
      return slots.map(slot=>{
        const instant = C.eventInstant(slot), date = new Date(instant);
        if (!instant || Number.isNaN(date.getTime())) return '';
        const zone = slot.timezone;
        if (!clocks.has(zone)) clocks.set(zone,new Intl.DateTimeFormat('zh-CN',{timeZone:zone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}));
        const time = `<time datetime="${e(instant)}">${e(clocks.get(zone).format(date))}</time>`;
        const label = time + (slot.auditorium ? ` <span>${e(slot.auditorium)}</span>` : '');
        const ticket = !slot.is_demo && C.safeUrl(slot.booking_url);
        return `<li>${ticket ? `<a ${ref(ticket)} title="购票">${label} ↗</a>` : label}</li>`;
      }).join('');
    }
    function upcomingScreenings(row,disabledSources) {
      const url = row.programme_url || row.evidence_url;
      if (!url || row.is_demo || row.event_type !== 'cinema_release') return [];
      const instant = Date.now();
      const entries = forSources(film?.items,disabledSources).filter(slot=>slot.event_type === 'cinema_screening'
        && slot.programme_url === url && slot.country === row.country && Date.parse(slot.start_at) > instant
        && slot.evidence_status !== 'unverified' && !unavailable.includes(slot.status));
      return groupSchedule(entries.map(slot=>({row:slot,day:slot.start_date}))).slice(0,4);
    }
    function item({row, label, screenings}, index) {
      const booking = C.safeUrl(row.booking_url), watch = C.safeUrl(row.watch_url);
      const movie = row.movie, title = entryTitle(row);
      const url = row.exhibition_id ? '#exhibition/' + encodeURIComponent(row.exhibition_id) : C.calendarRoute(row.id);
      const image = cover(row,'',index < 3);
      const poster = image ? `<a class="calendar-poster${image.landscape ? ' landscape' : ''}" data-calendar-art href="${e(url)}" tabindex="-1" aria-hidden="true">${image.html}</a>` : '';
      const subtitle = placeLabels(row);
      const slots = screenings.length ? screenings : row.start_at ? [row] : [];
      const timings = screeningTimes(slots);
      const shortLabel = label === activity.cinema_screening ? '艺术影院' : label;
      const sourceMap = row.premiere_source_url ? new Map([[row.premiere_source_url,'首播公告']])
        : new Map((screenings.length ? screenings : [row]).flatMap(slot=>slot.origins || []).map(source=>[source.url,source.name]));
      const sources = [...sourceMap].flatMap(([url,name])=>C.safeUrl(url) ? [`<a ${ref(C.safeUrl(url))}>${e(name || '排期来源')} ↗</a>`] : []);
      const douban = C.safeUrl(movie?.douban_url);
      if (douban) sources.push(`<a ${ref(douban)}>豆瓣 ↗</a>`);
      if (booking && !slots.length) sources.push(`<a ${ref(booking)}>${row.start_date?'购票':'查场次'} ↗</a>`);
      if (watch) sources.push(`<a ${ref(watch)}>观看 ↗</a>`);
      return `<article class="calendar-entry${poster ? ' has-poster' : ''}" data-cal-id="${e(row.id)}" data-cal-kind="${e(row.event_type)}">
        ${poster}<div class="calendar-entry-body"><p class="calendar-entry-meta">${[shortLabel,...subtitle].filter(Boolean).map(e).join(' · ')}${row.date_conflict ? ' · 展期有出入' : ''}</p>
        <h3><a href="${e(url)}">${e(title)}</a></h3>
        ${isFilm(row) && row.title_original !== title ? `<p class="calendar-original">${e(row.title_original)}</p>` : ''}
        ${timings ? `<ul class="calendar-times" aria-label="当地时间">${timings}</ul>` : ''}
        ${sources.length ? `<div class="calendar-entry-links">${sources.join('')}</div>` : ''}</div></article>`;
    }
    const withMovie = row => film?.films?.[row.id] ? {...row,movie:film.films[row.id]} : row;
    const forSources = (rows,disabledSources) => (rows || []).filter(row=>!disabledSources.includes(row.source_id));
    function scheduleRows(dataset,disabledSources,inventory,day) {
      const sourceNames = new Map([...(boot.sources?.sources || []), ...(dataset.sources || [])].map(row=>[row.id,row.name]));
      const eventSources = new Map(Object.entries(boot.calendar_event_sources || {}));
      if (server) {
        const articleSources = new Map(dataset.content.map(row=>[row.id,row.source_id]));
        for (const link of dataset.content_events) {
          const source = articleSources.get(link.content_id);
          if (source) eventSources.set(link.event_id,[...(eventSources.get(link.event_id) || []),source]);
        }
      }
      const disabled = row => {
        const ids = eventSources.get(row.id);
        return ids?.length && ids.every(id=>disabledSources.includes(id));
      };
      const legacy = dataset.events.filter(row=>(!day || row.start_date === day) && !disabled(row)
        && !(isExhibition(row) && (inventory?.includesLegacy || exhibitions?.hidden(row.id)))).map(row=>{
        const ids = [...new Set(eventSources.get(row.id) || [])];
        return ids.length === 1 ? {...row,source_name:sourceNames.get(ids[0])} : row;
      });
      const additions = (inventory?.entries || []).filter(row=>!disabled(row));
      const filmRows = dataset.mode === 'demo' ? [] : forSources(film?.items,disabledSources).filter(row=>!day || row.start_date === day);
      return deduplicate([...legacy,...filmRows,...additions].filter(C.calendarEventAllowed).map(withMovie));
    }

    function detail(dataset,id,disabledSources,{relatedImage,save}) {
      const live = dataset.mode !== 'demo';
      const showing = live && film?.now_showing?.find(row=>row.id === id);
      const found = showing || dataset.events.find(row=>row.id === id) || (live && film?.items.find(row=>row.id === id));
      const raw = found && C.calendarEventAllowed(found) && found;
      const movieDetail = !raw || isFilm(raw);
      if (live && movieDetail) loadFilm();
      const back = '<div class="reader-toolbar"><button class="text-link" data-action="reader-back">‹ 返回</button>' + (raw ? save : '') + '</div>';
      if ((movieDetail && pending) || !raw) {
        const message = pending ? '正在载入排期…' : failed ? '排期暂时无法载入。 <button class="text-link" data-cal-retry>重试</button>' : '这条排期暂时无法显示。';
        return {html:`<article class="reader-page calendar-reader" data-ui="calendar-reader">${back}<p role="status">${message}</p></article>`};
      }
      const day = raw.start_date;
      const grouped = day && activity[raw.event_type] && groupSchedule(calendarEntries(scheduleRows(dataset,disabledSources,null,day),day.slice(0,7)))
        .find(entry=>entry.row.id === id || entry.screenings.some(slot=>slot.id === id));
      const row = grouped?.row || withMovie(raw), screenings = grouped?.screenings || [];
      const title = entryTitle(row), badge = showing ? '在映' : C.eventTypes[row.event_type] || activity[row.event_type];
      const alternate = row.title_original && normalize(title) !== normalize(row.title_original) ? row.title_original : '';
      const dates = [...new Set([row.start_date,row.end_date].filter(Boolean))].map(C.dateLabel).join(' — ');
      const place = placeLabels(row).join(' · ');
      const picture = cover({...row,image_url:row.image_url || relatedImage(row.id)},title);
      const profile = film?.profiles?.[row.movie?.profile_id];
      const language = profile && !profile.language?.startsWith('zh') ? C.languageLabels[profile.language] : '';
      const article = profile?.article_id;
      const credits = isFilm(row) && [profile?.directors?.length && `导演 ${profile.directors.join('、')}`,
        (profile?.year || row.film_year) && String(profile?.year || row.film_year),
        profile?.runtime_minutes && `${profile.runtime_minutes} 分钟`].filter(Boolean).join(' · ');
      const introduction = profile?.text ? `<section class="calendar-reader-intro"><h2>${row.program ? '片单简介' : '影片简介'}${language ? ` <small>${e(language)}</small>` : ''}</h2>
        <p lang="${e(profile.language || '')}">${e(profile.text)}</p>${article ? `<a class="text-link" href="${e(C.readerRoute(article))}">阅读站内介绍 ↗</a>` : ''}</section>`
        : isFilm(row) && !row.is_demo && !row.program ? '<p class="calendar-reader-note">暂未收录影片简介。</p>' : '';
      const slots = screenings.length ? screenings : [row];
      const times = screeningTimes(slots);
      const timeLabel = {call_deadline:'截止时刻',streaming_release:'上线时间',exhibition:'活动时间'}[row.event_type] || '放映场次';
      const upcoming = times ? [] : upcomingScreenings(row,disabledSources);
      const links = new Map();
      const bookingCaption = showing ? '查场次' : row.event_type === 'call_deadline' ? '报名' : '购票';
      if (!row.is_demo) for (const [value,label] of [
        [row.watch_url,'观看'],[!times && row.booking_url,bookingCaption], [row.premiere_source_url,'首播公告'],[row.evidence_url,'排期来源'],
        [row.programme_url,'影片资料'],[profile?.source_url,'简介来源'],[row.movie?.douban_url,'豆瓣']
      ]) {
        const url = C.safeUrl(value);
        if (url && !links.has(url)) links.set(url,label);
      }
      const status = {cancelled:'已取消',postponed:'已延期',tentative:'日期待确认',needs_confirmation:'日期待确认'}[row.status];
      const notes = [status,row.booking_status === 'sold_out' && '已售罄',row.price_text,row.time_note,row.closure_note,row.eligibility_note].filter(Boolean);
      return {title,html:`<article class="reader-page calendar-reader" data-ui="calendar-reader">${back}
        <header><div class="eyebrow"><span class="channel-tag">${e(badge || '活动')}</span>${dates ? `<span>${e(dates)}</span>` : ''}${row.is_demo ? '<span>示例</span>' : ''}</div>
        <h1>${e(title)}</h1>${alternate ? `<p class="calendar-original">${e(alternate)}</p>` : ''}${place ? `<p class="calendar-reader-place">${e(place)}</p>` : ''}</header>
        ${credits ? `<p class="calendar-reader-credits">${e(credits)}</p>` : ''}
        ${introduction || picture ? `<div class="calendar-reader-feature${introduction && picture ? ' has-cover' : ''}">
          ${picture ? `<figure class="calendar-reader-cover" data-calendar-art>${picture.html}</figure>` : ''}${introduction}</div>` : ''}
        ${times ? `<section class="calendar-reader-times"><h2>${timeLabel} <small>${row.timezone === 'Asia/Tokyo' ? '东京时间' : '当地时间'}</small></h2><ul class="calendar-times">${times}</ul></section>` : ''}
        ${upcoming.length ? `<section class="calendar-reader-times"><h2>已收录的近期场次 <small>当地时间</small></h2>${upcoming.map(entry=>`
          <div class="calendar-reader-showtime"><p>${e(C.dateLabel(entry.day))} · ${e(entry.row.venue)}</p><ul class="calendar-times">${screeningTimes(entry.screenings)}</ul></div>`).join('')}</section>` : ''}
        ${notes.map(note=>`<p class="calendar-reader-note">${e(note)}</p>`).join('')}
        ${links.size ? `<div class="calendar-reader-links">${[...links].map(([url,label])=>`<a ${ref(url)}>${label} ↗</a>`).join('')}</div>` : ''}</article>`};
    }

    function view(dataset, disabledSources) {
      sync(dataset);
      const live = dataset.mode !== 'demo';
      const showExhibitions = kind === 'exhibition' || kind === 'all';
      const showFilm = kind !== 'exhibition';
      const showCatalogue = kind === 'cinema_showing';
      if (live && showFilm) loadFilm();
      const inventory = live && showExhibitions ? exhibitions?.calendarInventory() : null;
      const all = showCatalogue ? [] : scheduleRows(dataset,disabledSources,inventory);
      const rows = all.filter(row=>inArea(row,area,kind)
        && (kind === 'all' || (kind === 'film' ? theatres.includes(row.event_type) : kind === row.event_type)));
      const entries = groupSchedule(calendarEntries(rows,month)), byDay = new Map();
      for (const {day} of entries) if (day) byDay.set(day,(byDay.get(day) || 0)+1);
      const [year,m] = month.split('-').map(Number);
      const first = new Date(Date.UTC(year,m-1,1)).getUTCDay(), length = new Date(Date.UTC(year,m,0)).getUTCDate();
      const blank = '<div class="calendar-day blank" aria-hidden="true"></div>';
      const days = Array.from({length:first},()=>blank);
      for (let n=1;n<=length;n++) {
        const day = month + '-' + String(n).padStart(2,'0'), count = byDay.get(day) || 0;
        days.push(`<button class="calendar-day ${day===dateToday?'reference':''} ${day===chosenDay?'selected':''}" data-cal-day="${day}" aria-label="${day}，${count} 项活动" aria-pressed="${day===chosenDay}"><span>${n}</span>${count ? `<span class="calendar-activity-count">${count}</span>` : ''}</button>`);
      }
      while (days.length % 7) days.push(blank);
      const visible = showCatalogue ? (live ? forSources(film?.now_showing,disabledSources) : []).map(row=>({row:withMovie(row),label:'在映',screenings:[]}))
        : chosenDay ? entries.filter(event=>event.day===chosenDay) : entries;
      const pages = Math.max(1,Math.ceil(visible.length / pageSize));
      page = Math.min(page,pages);
      const pageRows = visible.slice((page-1)*pageSize,page*pageSize);
      const listing = pageRows.map((entry,index)=>{
        const dateHeader = !showCatalogue && !chosenDay && (index===0 || entry.day!==pageRows[index-1].day)
          ? `<h3 class="calendar-date-heading">${entry.day ? e(C.dateLabel(entry.day)) : '日期待定'}</h3>` : '';
        return dateHeader + item(entry,index);
      }).join('');
      const next = entries.find(event=>event.day && event.day >= (chosenDay || dateToday));
      const other = [...new Set(all.map(row=>row.country))].filter(code=>code && code !== 'JP' && code !== 'GLOBAL').sort();
      const regions = [['tokyo','东京'],['japan','日本全国'],['global','全球'],...other.map(code=>[code,C.countryLabels[code] || code])];
      const select = (name, label, choices, current, disable = false) => `<label>${label}<select data-cal-${name} aria-label="${label}" ${disable?'disabled':''}>${choices.map(([value,label])=>`<option value="${e(value)}" ${value===current?'selected':''}>${e(label)}</option>`).join('')}</select></label>`;
      const sourceRows = Object.values(film?.sources || {}).map(source=>{
        const url = C.safeUrl(source.url);
        const status = source.status === 'success' ? '本次核对 ' + Number(source.verified_this_run) + ' 条'
          : source.reason === 'source_crawl_disallowed' ? '来源限制自动采集' : '本次读取失败，保留已取得记录';
        const remaining = source.unclassified ? ` · ${Number(source.unclassified)} 项待确认类型或日期` : '';
        const unread = Object.keys(source.failed_pages || {}).length;
        return `<li>${url?`<a href="${e(url)}" target="_blank" rel="noopener noreferrer">${e(source.name)} ↗</a>`:e(source.name)} · ${status}${remaining}${unread?` · ${unread} 个排期页读取失败`:''}</li>`;
      }).join('');
      const fixedArea = showCatalogue ? 'japan' : kind === 'streaming_release' ? 'global' : null;
      const catalogueState = film?.sources?.['eiga-showing'];
      const emptyText = showCatalogue ? '暂未取得日本院线在映片单。' : '所选日期没有匹配的排期。';
      return `<div class="calendar-desk" data-ui="calendar"><div class="calendar-sidebar"><div class="calendar-pickers">
        ${select('area','地区',regions,fixedArea || area,Boolean(fixedArea))}
        ${select('kind','活动',Object.entries(activity),kind)}</div>
        ${showCatalogue ? '' : `<div class="calendar-panel"><div class="calendar-toolbar"><h2>${year} 年 ${m} 月</h2><div class="month-controls"><button data-cal-month="-1" aria-label="上个月">←</button><button data-cal-today>东京今天</button><button data-cal-month="1" aria-label="下个月">→</button></div></div>
        <div class="week-row">${['日','一','二','三','四','五','六'].map(day=>'<div>'+day+'</div>').join('')}</div><div class="calendar-days">${days.join('')}</div></div>`}</div>
        <section class="event-list" id="calendar-results"><div class="section-title"><h2>${showCatalogue?activity.cinema_showing:chosenDay?e(C.dateLabel(chosenDay)):'本月排期'} <span class="count-label" data-cal-count="${visible.length}">${visible.length} ${showCatalogue?'部':'项'}</span></h2>
        ${showCatalogue ? '' : `<button class="text-link" ${chosenDay?'data-cal-whole':'data-cal-day="'+dateToday+'"'}>${chosenDay?'看本月清单':'回到今天'}</button>`}</div>
        ${pending || inventory?.pending ? '<p class="compact-note" role="status">正在读取更多排期…</p>' : ''}
        ${showFilm && failed ? '<p class="compact-note">电影排期暂时无法载入。 <button class="text-link" data-cal-retry>重试</button></p>' : ''}
        ${showCatalogue && catalogueState?.status === 'failed' && visible.length ? '<p class="compact-note">本次核对未完成，显示上次取得的片单。</p>' : ''}
        ${inventory?.failed ? '<p class="compact-note">展览目录暂时无法载入，先显示已保存的活动。</p>' : ''}
        ${listing ? `<div class="calendar-listing${showFilm && kind!=='all'?' films':''}">${listing}</div>` : pending ? '' : `<p class="compact-note">${emptyText}</p>`}
        ${!visible.length && next?.day ? `<button class="text-link" data-cal-day="${next.day}">查看 ${e(C.dateLabel(next.day))} 的排期 ↗</button>` : ''}
        ${pages>1 ? `<div class="exhibition-pager"><button class="exhibition-chip" data-cal-page="${page-1}" ${page===1?'disabled':''}>上一页</button><span>第 ${page} / ${pages} 页</span><button class="exhibition-chip" data-cal-page="${page+1}" ${page===pages?'disabled':''}>下一页</button></div>` : ''}</section>
        <details class="exhibition-coverage"><summary>排期来源</summary><p>展览目录提供开幕与闭展日期。影院场次以当地时间显示。流媒体仅收录有首播依据的电影。</p>
        ${sourceRows ? '<ul>'+sourceRows+'</ul>' : ''}${boot.exhibition_report ? `<p><a href="${e(boot.exhibition_report)}">展览收录报告 ↗</a></p>` : ''}</details>
        </div>`;
    }
    document.addEventListener('load',event=>{
      const image = event.target;
      if (image.matches?.('[data-calendar-poster]')) {
        const wide = image.naturalWidth > image.naturalHeight;
        landscape.set(image.currentSrc,wide);
        image.closest('.calendar-poster')?.classList.toggle('landscape',wide);
      }
    },true);
    document.addEventListener('error',event=>{
      const image = event.target;
      if (!image.matches?.('[data-calendar-poster]')) return;
      const backups = JSON.parse(image.dataset.calendarBackups || '[]');
      if (backups.length) {
        image.src = backups.shift();
        image.dataset.calendarBackups = JSON.stringify(backups);
        return;
      }
      const art = image.closest('[data-calendar-art]');
      if (art) {
        art.hidden = true;
        art.closest('.calendar-reader-feature')?.classList.remove('has-cover');
      }
      image.closest('.calendar-entry')?.classList.remove('has-poster');
    },true);
    document.addEventListener('change',event=>{
      if (!isActive()) return;
      if (event.target.matches('[data-cal-area]')) area=event.target.value;
      else if (event.target.matches('[data-cal-kind]')) {
        kind=event.target.value;
        if (kind === 'streaming_release' || kind === 'cinema_release') chosenDay=null;
      }
      else return;
      page=1; rerender();
    });
    document.addEventListener('click',event=>{
      const button = event.target.closest?.('button');
      if (!isActive() || !button || button.disabled) return;
      const d=button.dataset;
      if ('calDay' in d) position(d.calDay);
      else if ('calWhole' in d) { chosenDay=null; page=1; }
      else if ('calToday' in d) position(dateToday);
      else if ('calRetry' in d) failed=false;
      else if ('calPage' in d) page=Number(d.calPage);
      else if ('calMonth' in d) {
        const [year,m] = month.split('-').map(Number);
        month = new Date(Date.UTC(year,m-1+Number(d.calMonth),1)).toISOString().slice(0,7);
        chosenDay=null; page=1;
      } else return;
      rerender();
      if ('calPage' in d) document.getElementById('calendar-results')?.scrollIntoView({block:'start'});
    });
    return {view,detail,listState,restoreList,isLoading};
  }
  const api = {create,deduplicate,calendarEntries,groupSchedule,inArea,entryTitle};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureCalendar = api;
})(typeof window !== 'undefined' ? window : globalThis);
