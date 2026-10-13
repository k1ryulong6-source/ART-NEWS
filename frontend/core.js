(function (root) {
  'use strict';
  const channels = { film: '电影', art: '艺术', photography: '摄影' };
  const kinds = { news: '资讯', interview: '访谈', work: '作品', photobook: '摄影集', industry_buzz: '圈内动态' };
  const eventTypes = { cinema_release: '院线上映', festival_screening: '影展放映', streaming_release: '流媒体上线', exhibition: '展览', call_deadline: '征集截止' };
  const statusNames = { want_to_see: '想看', planning: '准备去', seen: '已看过' };
  const evidenceNames = { official_confirmed: '官方确认', media_reported: '媒体报道', firsthand_response: '当事人回应', unverified: '未证实' };
  const locationLabel = row => row.city || ({ JP: '日本', CN: '中国' }[row.country]) || '国际';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const safeUrl = value => { try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : ''; } catch { return ''; } };
  const dateNumber = value => { if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null; const [y, m, d] = value.split('-').map(Number), date = new Date(Date.UTC(y, m - 1, d)); return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d ? date.getTime() / 86400000 : null; };
  const localDate = timezone => { const parts = new Intl.DateTimeFormat('en', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date()); const get = type => parts.find(part => part.type === type).value; return `${get('year')}-${get('month')}-${get('day')}`; };
  const daysBetween = (start, end) => { const a = dateNumber(start), b = dateNumber(end); return a === null || b === null ? null : b - a; };
  const dateLabel = value => value ? value.replace(/-/g, '.') : '时间待确认';
  function matches(row, filters = {}) {
    if (row.source_id && filters.disabledSources?.includes(row.source_id)) return false;
    if (filters.disabledEventIds?.includes(row.id)) return false;
    if (filters.channel && filters.channel !== 'all' && row.channel !== filters.channel) return false;
    if (filters.kind && filters.kind !== 'all' && row.kind !== filters.kind && row.event_type !== filters.kind) return false;
    if (filters.country && filters.country !== 'all' && row.country !== filters.country) return false;
    if (filters.city && filters.city !== 'all') {
      const country = { 东京: 'JP', 京都: 'JP', 大阪: 'JP', 上海: 'CN', 北京: 'CN' }[filters.city];
      if (country && row.country !== country) return false;
      if (row.city && row.city !== filters.city) return false;
    }
    if (filters.buzz === false && row.kind === 'industry_buzz') return false;
    const needle = (filters.query || '').trim().toLocaleLowerCase();
    return !needle || [row.title_zh, row.title_original, row.summary_zh, row.city, row.venue].join(' ').toLocaleLowerCase().includes(needle);
  }
  function selectToday(rows, preferences) {
    const limit = preferences.daily_selection_limit || 10;
    const buzz = preferences.industry_buzz || { enabled: true, max_share: 0.1 };
    const interests = [...(preferences.interests || []), ...(preferences.followed_entities || [])];
    const scored = rows.filter(r => r.evidence_status !== 'unverified' && (buzz.enabled || r.kind !== 'industry_buzz')).map(row => {
      const text = [row.title_original, row.title_zh, row.summary_zh].join(' ');
      const score = interests.filter(x => x && text.includes(x)).length * 4 + (row.city === preferences.default_city ? 2 : 0);
      return { ...row, selection_reason: score >= 4 ? '与你关注的主题相关' : row.city === preferences.default_city ? `发生在你关注的${preferences.default_city}` : '值得留意的文化动态', score };
    }).sort((a, b) => b.score - a.score || String(b.published_at || '').localeCompare(String(a.published_at || '')));
    const selected = [], deferred = [];
    let buzzCount = 0;
    const maxBuzz = Math.floor(limit * (buzz.max_share ?? 0.1));
    for (const row of scored) {
      if (row.kind === 'industry_buzz') {
        if (buzzCount < maxBuzz) { deferred.push(row); buzzCount++; }
      } else if (selected.length < limit) selected.push(row);
    }
    // Keep the ratio bounded even when fewer than the configured limit exist.
    const allowed = buzz.enabled && buzz.max_share > 0 ? Math.min(deferred.length, buzz.max_share === 1 ? limit : Math.floor(selected.length * buzz.max_share / (1 - buzz.max_share))) : 0;
    return [...selected.slice(0, limit - allowed), ...deferred.slice(0, allowed)].slice(0, limit);
  }
  function eventState(event, reference) {
    if (event.date_precision !== 'day') return { label: event.date_precision === 'month' ? '月份已公布' : '时间待确认', tone: 'muted' };
    const untilStart = daysBetween(reference, event.start_date);
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
    if (!['Asia/Tokyo', 'Asia/Shanghai', 'UTC'].includes(preferences.reading_timezone)) throw new Error('时区无效');
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
      lines.push('BEGIN:VEVENT', 'UID:' + clean(event.id) + '@culture-desk.local', 'DTSTAMP:' + new Date().toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z', 'DTSTART;VALUE=DATE:' + event.start_date.replace(/-/g, ''), 'DTEND;VALUE=DATE:' + end.replace(/-/g, ''), 'SUMMARY:' + clean(event.title_zh || event.title_original), 'LOCATION:' + clean([event.city, event.venue].filter(Boolean).join(' ')), 'DESCRIPTION:' + clean((event.is_demo ? '虚构示例，不能作为实际安排。 ' : '') + (event.closure_note || '开放日与预约请核对原文。')), 'URL:' + safeUrl(event.evidence_url), 'END:VEVENT');
    }
    lines.push('END:VCALENDAR');
    // RFC 5545 folds at 75 octets, not 75 Unicode characters.
    const encoder = new TextEncoder();
    return lines.map(line => { let parts = [], current = '', size = 0; for (const char of line) { const bytes = encoder.encode(char).length; if (size + bytes > 75) { parts.push(current); current = ' '; size = 1; } current += char; size += bytes; } parts.push(current); return parts.join('\r\n'); }).join('\r\n') + '\r\n';
  }
  const api = { channels, kinds, eventTypes, statusNames, evidenceNames, locationLabel, escape, safeUrl, daysBetween, dateLabel, localDate, matches, selectToday, eventState, validateImport, calendarFile };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureCore = api;
})(typeof window !== 'undefined' ? window : globalThis);
