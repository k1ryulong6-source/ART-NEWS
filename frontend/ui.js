/* Presentation API v1. Edit these components without changing data or storage. */
(function (root) {
  'use strict';
  function create(ctx) {
    const C = ctx.C, e = C.escape;
    const link = row => e(C.readerRoute(row.id));
    const promo = /^(订阅(?:我们的|本刊|本报|免费)?(?:每日|每周)?.{0,5}(?:简报|通讯)[。.!！]?$|Subscribe to (?:our|the)|Sign up for (?:our|the))/i;
    function status(row) {
      if (row.language === 'zh' || C.editorialReady(row)) return '';
      return `<span class="copy-status">${C.machineReady(row) ? '自动机翻' : '原文·待译'}</span>`;
    }
    // Lists carry only what helps choosing a story; translation status is stated on the lead and in the reader.
    function meta(row, options = {}) {
      const place = C.locations(row).length ? `<span>${e(C.locationLabel(row))}</span>` : '';
      const parts = `${options.channel === false ? '' : `<span class="channel-tag">${e(C.channels[row.channel] || '文化')}</span>`}${row.kind === 'industry_buzz' && options.channel !== false ? '<span>圈内</span>' : ''}${place}${options.status === false ? '' : status(row)}`;
      return parts ? `<div class="meta">${parts}</div>` : '';
    }
    function heading(title) {
      return `<div class="page-heading"><h1>${e(title)}</h1></div>`;
    }
    const summary = row => C.readingSummary(row);
    const zh = 'zh-CN', foreign = row => e(row.language && row.language !== 'zh' ? row.language : zh);
    const summaryLang = row => (C.editorialReady(row) && row.editorial_excerpt_zh) || row.summary_zh || (C.machineReady(row) && row.translated_excerpt_zh) ? zh : foreign(row);
    const titleLang = row => C.displayTitle(row) === row.title_original ? foreign(row) : zh;
    const source = row => e(ctx.sourceName(row).replace('（虚构）', ''));
    function figure(row, cls, large = false) {
      const art = ctx.artwork(row, large);
      return art ? `<figure class="${cls}"><a class="card-image-link" href="${link(row)}" tabindex="-1" aria-label="${e('阅读：' + C.displayTitle(row))}">${art}</a></figure>` : '';
    }
    function byline(row) {
      return `<span class="byline">${source(row)}</span><span class="dateline">${row.is_demo ? '示例' : e(ctx.publicationLabel(row))}</span>`;
    }
    function card(row, showStatus = false, options = {}) {
      const saved = ctx.findBookmark('content', row.id);
      const art = options.art === false ? '' : figure(row, 'card-art');
      return `<article class="content-card${art ? ' has-art' : ''}${options.compact ? ' compact' : ''}" data-ui="news-card">${art}<div class="card-body">${meta(row, { channel: options.channel, status: false })}<h3 lang="${titleLang(row)}"><a class="card-title" href="${link(row)}">${e(C.displayTitle(row))}</a></h3><a class="card-summary-link" href="${link(row)}" tabindex="-1"><p class="card-summary" lang="${summaryLang(row)}">${e(summary(row))}</p></a><div class="card-footer">${byline(row)}${ctx.saveButton('content', row.id)}</div>${showStatus && saved ? `<select class="bookmark-status" data-bookmark-status="${e(saved.id)}" aria-label="收藏状态">${Object.entries(C.statusNames).map(([k,v]) => `<option value="${k}" ${saved.status === k ? 'selected' : ''}>${v}</option>`).join('')}</select>` : ''}</div></article>`;
    }
    const brief = row => card(row, false, { art: false });
    function feature(row) {
      const translated = C.editorialReady(row) || C.machineReady(row), blocks = translated ? C.articleBlocks(row, true) : C.articleBlocks(row);
      const paragraphs = blocks.filter(b => ['paragraph','quote'].includes(b.type) && !(b.text.length < 120 && promo.test(b.text))).slice(0, 6).map(b => b.text.slice(0, 550));
      const copyLang = paragraphs.length ? (translated || row.language === 'zh' ? zh : foreign(row)) : summaryLang(row);
      const copy = (paragraphs.length ? paragraphs : [summary(row)]).map(text => `<p class="feature-summary">${e(text)}</p>`).join('');
      return `<article class="feature" data-ui="lead-story"><div class="feature-body">${meta(row)}<h2 lang="${titleLang(row)}"><a class="card-title" href="${link(row)}">${e(C.displayTitle(row))}</a></h2></div>${row.image_url ? figure(row, 'feature-art', true) : ''}<div class="feature-text"><a class="card-summary-link feature-columns" href="${link(row)}" tabindex="-1" lang="${copyLang}">${copy}</a><div class="feature-footer">${byline(row)}<a class="text-link" href="${link(row)}">${row.article_status === 'partial' ? '公开部分' : '全文'} ›</a>${ctx.saveButton('content', row.id)}</div></div></article>`;
    }
    function pagination(total, page, size) {
      const count = Math.ceil(total / size);
      if (count <= 1) return '';
      return `<nav class="news-pagination" aria-label="资讯分页" data-ui="pagination"><button class="text-link" data-list-page="${page-1}" ${page===1?'disabled':''}>‹ 上一页</button><label>第 <select id="article-page" aria-label="跳到资讯页">${Array.from({length:count},(_,i)=>`<option value="${i+1}" ${page===i+1?'selected':''}>${i+1}</option>`).join('')}</select> 页 · 共 ${count} 页</label><button class="text-link" data-list-page="${page+1}" ${page===count?'disabled':''}>下一页 ›</button></nav>`;
    }
    // Front page: the lead across the page, then one desk per channel (the desk names the
    // channel, so stories carry no channel tag), then listings and industry notes.
    function frontpage(rows, listings = '', band = '') {
      if (!rows.length) return '';
      const [lead, ...rest] = rows;
      const buzz = rest.filter(row => row.kind === 'industry_buzz'), news = rest.filter(row => row.kind !== 'industry_buzz');
      const desks = [['film', '電影'], ['art', '藝術'], ['photography', '攝影']].map(([key, name], index) => [name, news.filter(row => row.channel === key || (index === 1 && !['film', 'art', 'photography'].includes(row.channel)))]);
      const desk = ([name, items]) => `<section class="desk"><h2 class="desk-name">${name}</h2>${items.map((row, i) => card(row, false, { channel: false, art: i === 0 ? undefined : false, compact: i > 0 })).join('') || '<p class="compact-note">今日暂无。</p>'}</section>`;
      const notes = buzz.length ? `<aside class="industry-notes"><h2 class="desk-name">圈內</h2>${buzz.map(row => card(row, false, { channel: false, art: false, compact: true })).join('')}</aside>` : '';
      return `<div class="broadsheet" data-ui="frontpage"><section class="lead-column">${feature(lead)}</section><div class="desks">${desks.map(desk).join('')}</div></div>${band}${listings || notes ? `<div class="frontpage-foot${notes ? '' : ' single'}">${listings}${notes}</div>` : ''}`;
    }
    // 一种关注 — an edited unit of regional media. `lookup(id)` returns the stored report, if any,
    // so titles follow the same Chinese/original rules as everywhere else.
    const shortDate = value => value ? `${Number(value.slice(5, 7))}.${value.slice(8, 10)}` : '';
    function attentionStory(item, lookup) {
      const row = lookup(item.id), title = row ? C.displayTitle(row) : item.title || item.title_original;
      const lang = row ? titleLang(row) : title === item.title_original && item.original_language !== 'zh' ? e(item.original_language || zh) : zh;
      return `<time datetime="${e(item.published_at || '')}">${e(shortDate(item.published_at))}</time><a class="card-title" href="${e(C.readerRoute(item.id))}" lang="${lang}">${e(title)}</a>`;
    }
    function attentionBand(unit, lookup) {
      const members = (unit?.members || []).filter(member => member.source_enabled !== false && member.recent_items?.length);
      if (!members.length) return '';
      return `<section class="attention-band" data-ui="attention"><div class="attention-head"><h2 class="desk-name attention-title"><a href="#attention">${e(unit.name)}</a></h2><p>${e(unit.description || '')}</p><a class="text-link" href="#attention">全部 ›</a></div><ol class="attention-members">${members.map(member => `<li><span class="attention-region">${e(member.focus_label)}</span><span class="attention-source" lang="${e(member.source_language || zh)}">${e(member.name)}</span><p class="attention-story">${attentionStory(member.recent_items[0], lookup)}</p></li>`).join('')}</ol></section>`;
    }
    function attentionPage(unit, lookup, stamp) {
      if (!unit) return '';
      const member = item => {
        const failed = item.collection_status && item.collection_status !== 'success';
        const tags = [...(item.specialties || []), C.languageLabels[item.source_language]].filter(Boolean);
        return `<article class="attention-member" id="attention-${e(item.source_id)}"><div class="attention-profile"><p class="attention-region">${e(item.focus_label)}</p><h2 class="attention-name" lang="${e(item.source_language || zh)}">${e(item.name)}</h2><p class="attention-why">${e(item.why)}</p><p class="attention-tags">${tags.map(e).join(' · ')}</p><p class="attention-state">${item.latest_publication_at ? `最近发布 ${e(shortDate(item.latest_publication_at))}` : '暂无发布日期'}${failed ? ' · <b>上次读取失败，以下为此前保存的报道</b>' : ''}${C.safeUrl(item.homepage_url) ? ` · <a class="text-link" href="${e(C.safeUrl(item.homepage_url))}" target="_blank" rel="noopener noreferrer">官网 ↗</a>` : ''}</p></div><div class="attention-reading"><ol class="attention-stories">${(item.recent_items || []).map(story => `<li>${attentionStory(story, lookup)}</li>`).join('') || '<li class="compact-note">暂无报道。</li>'}</ol><details class="attention-detail"><summary>来源状态</summary><p>最近成功读取 ${e(stamp(item.last_successful_fetch_at))} · 收录 ${item.article_count ?? 0} 篇 · 已存正文 ${item.with_body_count ?? 0} 篇 · AI全文 ${item.ai_translated_count ?? 0} 篇${item.list_audit_status === 'checked' ? ' · 列表已核对' : ''}</p></details></div></article>`;
      };
      return `<article class="attention-page" data-ui="attention-page"><header class="attention-masthead"><h1 class="attention-title">${e(unit.name)}</h1><p>${e(unit.description || '')}</p><details class="attention-detail"><summary>选择说明</summary><p>${e(unit.selection_basis || '')}</p>${unit.scope_note ? `<p>${e(unit.scope_note)}</p>` : ''}<p>${unit.enabled_source_count ?? unit.source_count ?? 0} 家媒体 · 收录 ${unit.article_count ?? 0} 篇 · 已存正文 ${unit.with_body_count ?? 0} 篇 · AI全文 ${unit.ai_translated_count ?? 0} 篇</p></details></header>${(unit.members || []).map(member).join('')}</article>`;
    }
    return { heading, meta, card, brief, feature, pagination, frontpage, attentionBand, attentionPage };
  }
  const api = { version: 1, create };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureUI = api;
})(typeof window !== 'undefined' ? window : globalThis);
