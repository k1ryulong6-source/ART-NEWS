(function (root) {
  'use strict';
  const activity = {
    film: '电影放映与上映', cinema_screening: '艺术影院放映', cinema_release: '院线上映',
    festival_screening: '影展放映', streaming_release: '流媒体上线', exhibition: '展览开幕与闭展',
    call_deadline: '摄影征集截止', all: '全部活动'
  };
  const theatres = ['cinema_screening','cinema_release','festival_screening'];
  const normalize = value => String(value || '').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
  const isExhibition = row => row.event_type === 'exhibition';

  function deduplicate(rows) {
    const events = new Map();
    const confidence = row => Number(Boolean(row.official || row.evidence_status === 'official_confirmed'));
    for (const row of rows) {
      const title = normalize(row.title_original || row.title_zh);
      const kind = row.event_type;
      if (!title || !row.start_date || !activity[kind] || row.evidence_status === 'unverified') continue;
      const time = row.start_at ? Date.parse(row.start_at) : null;
      const place = kind === 'streaming_release' ? [row.platform || row.source_id || row.evidence_url, row.market || row.country]
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
      events.set(key,{...chosen,origins,date_conflict:Boolean(chosen.date_conflict || conflict)});
    }
    return [...events.values()];
  }

  function inArea(row, area, kind) {
    if (kind === 'streaming_release' || area === 'global') return true;
    if (row.country === 'GLOBAL' && row.event_type === 'call_deadline') return true;
    if (area === 'japan') return row.country === 'JP';
    if (area === 'tokyo') return row.country === 'JP' && (row.prefecture === '13' || ['东京','東京都','東京'].includes(row.city)
      || (row.event_type === 'cinema_release' && !row.city && !row.prefecture));
    return row.country === area;
  }

  function calendarEntries(rows, month) {
    const entries = [];
    for (const row of rows) {
      if (['cancelled','postponed','needs_confirmation','tentative'].includes(row.status)) continue;
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
      || String(a.row.title_zh || a.row.title_original).localeCompare(String(b.row.title_zh || b.row.title_original)));
  }

  function create({C,boot,server,exhibitions,isActive,rerender}) {
    const e = C.escape, pageSize = 12;
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
    function open(dataset, type, region, day) {
      sync(dataset); kind = type; area = region;
      position(day);
    }
    function item({row, day, label}) {
      const proof = C.safeUrl(row.evidence_url), programme = C.safeUrl(row.programme_url);
      const booking = C.safeUrl(row.booking_url), watch = C.safeUrl(row.watch_url);
      const title = e(row.title_zh || row.title_original);
      const ref = url => `href="${e(url)}" target="_blank" rel="noopener noreferrer"`;
      const titleLink = row.exhibition_id ? `<a href="#exhibition/${encodeURIComponent(row.exhibition_id)}">${title}</a>`
        : row.source_id && proof ? `<a ${ref(programme || proof)}>${title}</a>`
        : `<button class="text-link" data-detail="${e(row.id)}" data-type="event">${title}</button>`;
      const country = row.country === 'GLOBAL' ? '' : C.countryLabels[row.country] || row.country;
      const place = row.prefecture_name || row.city || (row.country === 'JP' && row.event_type === 'cinema_release' ? '日本院线' : country);
      const subtitle = row.event_type === 'streaming_release' ? [row.platform,row.market || country || '上线地区以来源为准']
        : [place,row.venue,row.auditorium];
      const timing = row.start_at ? row.start_at.slice(11,16) : '';
      const time = [!chosenDay && day ? C.dateLabel(day).slice(5) : '',timing].filter(Boolean).join(' ');
      const sources = row.origins?.map(({url,name})=>C.safeUrl(url) ? `<a class="text-link" ${ref(C.safeUrl(url))}>${e(name || '来源')} ↗</a>` : '').filter(Boolean).join(' ');
      return `<article class="calendar-entry" data-cal-id="${e(row.id)}" data-cal-kind="${e(row.event_type)}">
        <div class="calendar-entry-time"><span>${e(time || label)}</span>${time ? `<small>${e(label)}</small>` : ''}</div>
        <div class="calendar-entry-body"><h3>${titleLink}</h3><p>${subtitle.filter(Boolean).map(e).join(' · ')}${row.date_conflict ? ' · 展期有出入' : ''}</p>
        ${sources || booking || watch ? `<div class="calendar-entry-links">${sources || ''}${booking ? ` <a class="text-link" ${ref(booking)}>购票 ↗</a>` : ''}${watch ? ` <a class="text-link" ${ref(watch)}>平台 ↗</a>` : ''}</div>` : ''}</div></article>`;
    }
    function view(dataset, disabledSources) {
      sync(dataset);
      const live = dataset.mode !== 'demo';
      const showExhibitions = kind === 'exhibition' || kind === 'all';
      const showFilm = !['exhibition','call_deadline'].includes(kind);
      if (live && showFilm) loadFilm();
      const inventory = live && showExhibitions ? exhibitions?.calendarInventory() : null;
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
      const legacy = dataset.events.filter(row=>!disabled(row)
        && !(isExhibition(row) && (inventory?.includesLegacy || exhibitions?.hidden(row.id)))).map(row=>{
        const ids = [...new Set(eventSources.get(row.id) || [])];
        return ids.length === 1 ? {...row,source_name:sourceNames.get(ids[0])} : row;
      });
      const additions = (inventory?.entries || []).filter(row=>!disabled(row));
      const all = deduplicate([...legacy, ...(live ? film?.items || [] : []), ...additions]);
      const rows = all.filter(row=>inArea(row,area,kind)
        && (kind === 'all' || (kind === 'film' ? theatres.includes(row.event_type) : kind === row.event_type)));
      const entries = calendarEntries(rows,month), byDay = new Map();
      for (const {day} of entries) if (day) byDay.set(day,(byDay.get(day) || 0)+1);
      const [year,m] = month.split('-').map(Number);
      const first = new Date(Date.UTC(year,m-1,1)).getUTCDay(), length = new Date(Date.UTC(year,m,0)).getUTCDate();
      const blank = '<div class="calendar-day blank" aria-hidden="true"></div>';
      const days = Array.from({length:first},()=>blank);
      for (let n=1;n<=length;n++) {
        const day = month + '-' + String(n).padStart(2,'0'), count = byDay.get(day) || 0;
        days.push(`<button class="calendar-day ${day===dateToday?'reference':''} ${day===chosenDay?'selected':''}" data-cal-day="${day}" aria-label="${day}，${count} 项活动" aria-pressed="${day===chosenDay}"><span>${n}</span>${count ? `<span class="calendar-dot film">${count} 项</span>` : ''}</button>`);
      }
      while (days.length % 7) days.push(blank);
      const visible = chosenDay ? entries.filter(event=>event.day===chosenDay) : entries;
      const pages = Math.max(1,Math.ceil(visible.length / pageSize));
      page = Math.min(page,pages);
      const pageRows = visible.slice((page-1)*pageSize,page*pageSize);
      const next = entries.find(event=>event.day && event.day >= (chosenDay || dateToday));
      const other = [...new Set(all.map(row=>row.country))].filter(code=>code && code !== 'JP' && code !== 'GLOBAL').sort();
      const regions = [['tokyo','东京'],['japan','日本全国'],['global','全球'],...other.map(code=>[code,C.countryLabels[code] || code])];
      const select = (name, label, choices, current, disable = false) => `<label>${label}<select data-cal-${name} aria-label="${label}" ${disable?'disabled':''}>${choices.map(([value,label])=>`<option value="${e(value)}" ${value===current?'selected':''}>${e(label)}</option>`).join('')}</select></label>`;
      const sourceRows = Object.values(film?.sources || {}).map(source=>{
        const url = C.safeUrl(source.url);
        const status = source.status === 'success' ? '本次核对 ' + Number(source.verified_this_run) + ' 条'
          : source.reason === 'source_crawl_disallowed' ? '来源限制自动采集' : '本次读取失败，保留已取得记录';
        return `<li>${url?`<a href="${e(url)}" target="_blank" rel="noopener noreferrer">${e(source.name)} ↗</a>`:e(source.name)} · ${status}</li>`;
      }).join('');
      return `<div class="calendar-desk" data-ui="calendar"><div class="calendar-pickers">
        ${select('area','地区',regions,kind==='streaming_release'?'global':area,kind==='streaming_release')}
        ${select('kind','活动',Object.entries(activity),kind)}</div>
        <div class="calendar-panel"><div class="calendar-toolbar"><h2>${year} 年 ${m} 月</h2><div class="month-controls"><button data-cal-month="-1" aria-label="上个月">←</button><button data-cal-today>今天</button><button data-cal-month="1" aria-label="下个月">→</button></div></div>
        <div class="week-row">${['日','一','二','三','四','五','六'].map(day=>'<div>'+day+'</div>').join('')}</div><div class="calendar-days">${days.join('')}</div></div>
        <section class="event-list" id="calendar-results"><div class="section-title"><h2>${chosenDay?e(C.dateLabel(chosenDay)):'本月排期'} <span class="count-label" data-cal-count="${visible.length}">${visible.length} 项</span></h2>
        <button class="text-link" ${chosenDay?'data-cal-whole':'data-cal-today'}>${chosenDay?'看本月清单':'回到今天'}</button></div>
        ${pending || inventory?.pending ? '<p class="compact-note" role="status">正在读取更多排期…</p>' : ''}
        ${showFilm && failed ? '<p class="compact-note">艺术影院和流媒体排期暂时无法载入。 <button class="text-link" data-cal-retry>重试</button></p>' : ''}
        ${inventory?.failed ? '<p class="compact-note">展览目录暂时无法载入，先显示已保存的活动。</p>' : ''}
        ${pageRows.map(item).join('') || '<p class="compact-note">所选日期没有匹配的排期。</p>'}
        ${!visible.length && next?.day ? `<button class="text-link" data-cal-day="${next.day}">查看 ${e(C.dateLabel(next.day))} 的排期 ↗</button>` : ''}
        ${pages>1 ? `<div class="exhibition-pager"><button class="exhibition-chip" data-cal-page="${page-1}" ${page===1?'disabled':''}>上一页</button><span>第 ${page} / ${pages} 页</span><button class="exhibition-chip" data-cal-page="${page+1}" ${page===pages?'disabled':''}>下一页</button></div>` : ''}</section>
        <details class="exhibition-coverage"><summary>排期来源</summary><p>院线上映、影展、摄影征集与展览沿用资讯库的已确认排期。展览目录提供开幕与闭展日期。影院场次以当地时间显示，月度片单列入本月清单。</p>
        ${sourceRows ? '<ul>'+sourceRows+'</ul>' : ''}${boot.exhibition_report ? `<p><a href="${e(boot.exhibition_report)}">展览收录报告 ↗</a></p>` : ''}</details>
        </div>`;
    }
    document.addEventListener('change',event=>{
      if (!isActive()) return;
      if (event.target.matches('[data-cal-area]')) area=event.target.value;
      else if (event.target.matches('[data-cal-kind]')) {
        kind=event.target.value;
        if (kind === 'streaming_release') chosenDay=null;
      }
      else return;
      page=1; rerender();
    });
    document.addEventListener('click',event=>{
      const button = event.target.closest?.('button');
      if (!isActive() || !button || button.disabled) return;
      const d=button.dataset;
      if ('calDay' in d) { chosenDay=d.calDay; page=1; }
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
    return {view,open};
  }
  const api = {create,deduplicate,calendarEntries,inArea};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureCalendar = api;
})(typeof window !== 'undefined' ? window : globalThis);
