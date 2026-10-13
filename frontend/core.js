(function (root) {
  'use strict';
  const channels = { film: '电影', art: '艺术', photography: '摄影' };
  const kinds = { news: '资讯', interview: '访谈', work: '作品', photobook: '摄影集', industry_buzz: '圈内动态' };
  const eventTypes = { cinema_release: '院线上映', festival_screening: '影展放映', streaming_release: '流媒体上线', exhibition: '展览', call_deadline: '征集截止' };
  const statusNames = { want_to_see: '想看', planning: '准备去', seen: '已看过' };
  const evidenceNames = { official_confirmed: '官方确认', media_reported: '媒体报道', firsthand_response: '当事人回应', unverified: '未证实' };
  const registry = root.CULTURE_BOOTSTRAP?.regions || (typeof module !== 'undefined' && module.exports ? require('../config/regions.json') : { regions: [], languages: {} });
  const countryLabels = { ...Object.fromEntries(registry.regions.map(r => [r.code, r.label])), GLOBAL: '全球征集' };
  const cityCountries = Object.fromEntries(registry.regions.flatMap(r => r.cities.map(city => [city, r.code])));
  const languageLabels = registry.languages;
  const locations = row => {
    if (row.locations_json) { try { const values = JSON.parse(row.locations_json); if (Array.isArray(values) && values.length) return values; } catch {} }
    return row.country ? [{ country: row.country, city: row.city }] : [];
  };
  const locationLabel = row => { const names = locations(row).map(place => place.city || countryLabels[place.country] || place.country); return names.length ? (row.geography_status === 'mentioned' ? '涉及 ' : '') + [...new Set(names)].join(' / ') : '地点未说明'; };
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const safeUrl = value => { try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : ''; } catch { return ''; } };
  const dateNumber = value => { if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null; const [y, m, d] = value.split('-').map(Number), date = new Date(Date.UTC(y, m - 1, d)); return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d ? date.getTime() / 86400000 : null; };
  const localDate = (timezone, instant = new Date()) => { const parts = new Intl.DateTimeFormat('en', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(instant); const get = type => parts.find(part => part.type === type).value; return `${get('year')}-${get('month')}-${get('day')}`; };
  const daysBetween = (start, end) => { const a = dateNumber(start), b = dateNumber(end); return a === null || b === null ? null : b - a; };
  const dateLabel = value => value ? value.replace(/-/g, '.') : '时间待确认';
  function matches(row, filters = {}) {
    if (row.source_id && filters.disabledSources?.includes(row.source_id)) return false;
    if (filters.disabledEventIds?.includes(row.id)) return false;
    if (filters.channel && filters.channel !== 'all' && row.channel !== filters.channel) return false;
    if (filters.kind && filters.kind !== 'all' && row.kind !== filters.kind && row.event_type !== filters.kind) return false;
    const places = locations(row);
    if (filters.country && filters.country !== 'all' && (filters.country === 'unknown' ? places.length > 0 : !places.some(place => place.country === filters.country))) return false;
    if (filters.city && filters.city !== 'all' && !places.some(place => place.city === filters.city || (!place.city && place.country === cityCountries[filters.city] && (['cinema_release', 'streaming_release'].includes(row.event_type) || place.basis === 'source_structured')))) return false;
    if (filters.language && filters.language !== 'all' && row.language && row.language !== filters.language) return false;
    if (filters.buzz === false && row.kind === 'industry_buzz') return false;
    const needle = (filters.query || '').trim().toLocaleLowerCase();
    return !needle || [row.title_zh, row.title_original, row.summary_zh, row.city, row.venue].join(' ').toLocaleLowerCase().includes(needle);
  }
  function isCurrentContent(row, reference, linkedEvents = [], maxAge = 30) {
    const published = row.published_at?.slice(0, 10);
    const age = daysBetween(published, reference);
    if (age !== null) return age >= -1 && age <= maxAge;
    // A date from a real calendar can support an undated listing, but the
    // fetch timestamp never becomes an invented publication date.
    return linkedEvents.some(event => {
      if (event.date_precision !== 'day') return false;
      if (eventInstant(event) && new Date(eventInstant(event)) <= new Date()) return false;
      const today = event.is_demo ? reference : localDate(event.timezone);
      const start = daysBetween(today, event.start_date), end = daysBetween(today, event.end_date || event.start_date);
      return start !== null && end !== null && (event.event_type === 'call_deadline' ? start >= 0 && start <= 120 : start <= 14 && end >= 0);
    });
  }
  function selectToday(rows, preferences, context = null) {
    const limit = preferences.daily_selection_limit || 10;
    const buzz = preferences.industry_buzz || { enabled: true, max_share: 0.1 };
    const interests = [...(preferences.interests || []), ...(preferences.followed_entities || [])];
    const scored = rows.filter(r => r.evidence_status !== 'unverified' && (buzz.enabled || r.kind !== 'industry_buzz') && (!context || isCurrentContent(r, context.reference_date, (context.content_events || []).filter(link => link.content_id === r.id).map(link => (context.events || []).find(event => event.id === link.event_id)).filter(Boolean), preferences.recent_news_days || 30))).map(row => {
      const text = [row.title_original, row.title_zh, row.summary_zh].join(' ').toLocaleLowerCase();
      const synonyms = { 电影: ['film', 'cinema', 'película'], 艺术: ['art', 'exhibition'], 摄影: ['photograph', '写真'], 摄影集: ['photobook', '写真集'], 电影访谈: ['interview'], 街头摄影: ['street photography'] };
      const interestScore = interests.filter(x => x && [x, ...(synonyms[x] || [])].some(term => text.includes(term.toLocaleLowerCase()))).length * 4;
      const cityBoost = preferences.news_scope === 'follow_city' && row.city === preferences.default_city;
      const score = interestScore + (cityBoost ? 2 : 0);
      return { ...row, selection_reason: score >= 4 ? '与你关注的主题相关' : cityBoost ? `发生在你关注的${preferences.default_city}` : '全球文化动态', score };
    }).sort((a, b) => b.score - a.score || String(b.published_at || '').localeCompare(String(a.published_at || '')));
    // Balance channels and publishers before filling spare slots by relevance.
    const balanced = [], remaining = [...scored];
    const sourceCounts = {}, channelCounts = {};
    while (remaining.length) {
      let best = 0, bestScore = -Infinity;
      remaining.forEach((row, index) => { const value = row.score - (sourceCounts[row.source_id] || 0) * 6 - (channelCounts[row.channel] || 0) * 4; if (value > bestScore) { best = index; bestScore = value; } });
      const [row] = remaining.splice(best, 1); balanced.push(row);
      sourceCounts[row.source_id] = (sourceCounts[row.source_id] || 0) + 1;
      channelCounts[row.channel] = (channelCounts[row.channel] || 0) + 1;
    }
    const selected = [], deferred = [];
    let buzzCount = 0;
    const maxBuzz = Math.floor(limit * (buzz.max_share ?? 0.1));
    for (const row of balanced) {
      if (row.kind === 'industry_buzz') {
        if (buzzCount < maxBuzz) { deferred.push(row); buzzCount++; }
      } else if (selected.length < limit) selected.push(row);
    }
    // Keep the ratio bounded even when fewer than the configured limit exist.
    const allowed = buzz.enabled && buzz.max_share > 0 ? Math.min(deferred.length, buzz.max_share === 1 ? limit : Math.floor(selected.length * buzz.max_share / (1 - buzz.max_share))) : 0;
    return [...selected.slice(0, limit - allowed), ...deferred.slice(0, allowed)].slice(0, limit);
  }
  const eventInstant = event => event.event_type === 'call_deadline' ? event.deadline_at : event.start_at;
  const timeLabel = event => { const value = eventInstant(event); return value ? new Intl.DateTimeFormat('zh-CN', { timeZone: event.timezone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value)) + ' · ' + event.timezone : dateLabel(event.start_date) + (event.time_status === 'conflict' ? ' · 时刻有冲突' : ''); };
  function eventState(event, reference, instant = new Date()) {
    if (event.date_precision !== 'day') return { label: event.date_precision === 'month' ? '月份已公布' : '时间待确认', tone: 'muted' };
    const untilStart = daysBetween(reference, event.start_date);
    if (event.event_type === 'call_deadline') {
      if ((event.deadline_at && new Date(event.deadline_at) <= instant) || untilStart < 0) return { label: '已截止', tone: 'muted' };
      if (untilStart === 0) return { label: event.time_status === 'conflict' ? '今日截止 · 时刻需核对' : '今日截止', tone: 'urgent' };
      return { label: `${untilStart} 天后截止`, tone: untilStart <= 7 ? 'urgent' : 'upcoming' };
    }
    if (event.start_at && new Date(event.start_at) <= instant && !event.end_at) return { label: '已开始', tone: 'muted' };
    const untilEnd = daysBetween(reference, event.end_date);
    if (untilEnd !== null && untilEnd < 0) return { label: '已结束', tone: 'muted' };
    if (untilStart !== null && untilStart > 0) return { label: `${untilStart} 天后${event.event_type === 'exhibition' ? '开幕' : '开始'}`, tone: 'upcoming' };
    if (untilEnd !== null && untilEnd <= 7) return { label: untilEnd === 0 ? '今日结束' : `还有 ${untilEnd} 天结束`, tone: 'urgent' };
    if (event.event_type === 'exhibition') return { label: '正在展出', tone: 'active' };
    return { label: untilStart === 0 ? '今日开始' : '已开始', tone: 'active' };
  }
  function validateImport(data, dataset, defaults) {
    if (!data || data.schema_version !== 1 || !Array.isArray(data.bookmarks) || !data.preferences || data.bookmarks.length > 5000) throw new Error('不是兼容的映间导出文件');
    const preferences = { ...defaults, ...data.preferences };
    if (!Number.isInteger(preferences.daily_selection_limit) || preferences.daily_selection_limit < 1 || preferences.daily_selection_limit > 50) throw new Error('精选数量无效');
    if (!Array.isArray(preferences.interests) || !Array.isArray(preferences.followed_entities) || [...preferences.interests, ...preferences.followed_entities].some(x => typeof x !== 'string' || x.length > 200)) throw new Error('兴趣或关注名单无效');
    if (typeof preferences.default_city !== 'string' || preferences.default_city.length > 80) throw new Error('城市无效');
    if (preferences.disabled_sources && (!Array.isArray(preferences.disabled_sources) || preferences.disabled_sources.some(id => typeof id !== 'string'))) throw new Error('来源设置无效');
    const buzz = preferences.industry_buzz;
    if (!buzz || typeof buzz.enabled !== 'boolean' || typeof buzz.max_share !== 'number' || buzz.max_share < 0 || buzz.max_share > 1) throw new Error('圈内动态设置无效');
    try { localDate(preferences.reading_timezone); } catch { throw new Error('时区无效'); }
    if (!['global', 'follow_city'].includes(preferences.news_scope)) throw new Error('阅读范围无效');
    preferences.industry_buzz = { ...buzz, include_unverified_in_today: false };
    preferences.excluded_topics = defaults.excluded_topics;
    const seen = new Map();
    for (const row of data.bookmarks) {
      const type = row.content_id ? 'content' : 'event', id = row.content_id || row.event_id;
      if (Boolean(row.content_id) === Boolean(row.event_id) || !statusNames[row.status]) throw new Error('收藏格式无效');
      const records = type === 'content' ? dataset.content : dataset.events;
      if (!records.some(x => x.id === id)) throw new Error('收藏引用了不存在的内容，请先恢复对应内容库');
      if (typeof (row.note || '') !== 'string' || (row.note || '').length > 2000) throw new Error('收藏备注无效');
      seen.set(`${type}:${id}`, { ...row, note: row.note || '' });
    }
    return { schema_version: 1, preferences, bookmarks: [...seen.values()] };
  }
  function calendarFile(events) {
    const clean = value => String(value || '').replace(/\\/g, '\\\\').replace(/\r\n|\r|\n/g, '\\n').replace(/,/g, '\\,').replace(/;/g, '\\;');
    const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Culture Desk//Personal Culture Calendar//ZH', 'CALSCALE:GREGORIAN'];
    for (const event of events) {
      if (event.date_precision !== 'day' || dateNumber(event.start_date) === null) continue;
      const end = new Date((dateNumber(event.end_date || event.start_date) + 1) * 86400000).toISOString().slice(0, 10);
      const value = eventInstant(event);
      const stamp = date => new Date(date).toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
      const dates = value ? ['DTSTART:' + stamp(value), ...(event.end_at ? ['DTEND:' + stamp(event.end_at)] : [])] : ['DTSTART;VALUE=DATE:' + event.start_date.replace(/-/g, ''), 'DTEND;VALUE=DATE:' + end.replace(/-/g, '')];
      const notes = [event.is_demo ? '虚构示例，不能作为实际安排。' : '', event.time_note, event.closure_note || '开放日与预约请核对原文。', event.price_text, event.eligibility_note, event.booking_url].filter(Boolean).join(' ');
      lines.push('BEGIN:VEVENT', 'UID:' + clean(event.id) + '@culture-desk.local', 'DTSTAMP:' + stamp(new Date()), ...dates, 'SUMMARY:' + clean(event.title_zh || event.title_original), 'LOCATION:' + clean([event.city, event.venue].filter(Boolean).join(' ')), 'DESCRIPTION:' + clean(notes), 'URL:' + safeUrl(event.evidence_url), 'END:VEVENT');
    }
    lines.push('END:VCALENDAR');
    // RFC 5545 folds at 75 octets, not 75 Unicode characters.
    const encoder = new TextEncoder();
    return lines.map(line => { let parts = [], current = '', size = 0; for (const char of line) { const bytes = encoder.encode(char).length; if (size + bytes > 75) { parts.push(current); current = ' '; size = 1; } current += char; size += bytes; } parts.push(current); return parts.join('\r\n'); }).join('\r\n') + '\r\n';
  }
  const api = { channels, kinds, eventTypes, statusNames, evidenceNames, countryLabels, cityCountries, languageLabels, registry, locations, locationLabel, escape, safeUrl, daysBetween, dateLabel, localDate, matches, isCurrentContent, selectToday, eventInstant, timeLabel, eventState, validateImport, calendarFile };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureCore = api;
})(typeof window !== 'undefined' ? window : globalThis);
