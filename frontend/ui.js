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
    function meta(row) {
      const place = C.locations(row).length ? `<span>${e(C.locationLabel(row))}</span>` : '';
      return `<div class="meta"><span class="channel-tag">${e(C.channels[row.channel] || '文化')}</span>${row.kind === 'industry_buzz' ? '<span>圈内</span>' : ''}${place}${status(row)}</div>`;
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
      return `<article class="content-card${art ? ' has-art' : ''}" data-ui="news-card">${art}<div class="card-body">${meta(row)}<h3 lang="${titleLang(row)}"><a class="card-title" href="${link(row)}">${e(C.displayTitle(row))}</a></h3><a class="card-summary-link" href="${link(row)}" tabindex="-1"><p class="card-summary" lang="${summaryLang(row)}">${e(summary(row))}</p></a><div class="card-footer">${byline(row)}${ctx.saveButton('content', row.id)}</div>${showStatus && saved ? `<select class="bookmark-status" data-bookmark-status="${e(saved.id)}" aria-label="收藏状态">${Object.entries(C.statusNames).map(([k,v]) => `<option value="${k}" ${saved.status === k ? 'selected' : ''}>${v}</option>`).join('')}</select>` : ''}</div></article>`;
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
    function frontpage(rows, agenda = '') {
      if (!rows.length) return '';
      const [lead, ...rest] = rows;
      const column = (name, items, render) => items.length ? `<h2 class="column-heading">${name}</h2>${items.map(render).join('')}` : '';
      const seconds = rest.slice(7, 9);
      return `<div class="broadsheet" data-ui="frontpage"><aside class="news-column brief-column">${column('简讯', rest.slice(0, 4), brief)}${agenda}</aside><section class="lead-column">${feature(lead)}${seconds.length ? `<div class="second-stories">${seconds.map(row => card(row)).join('')}</div>` : ''}</section><aside class="news-column focus-column">${column('焦点', rest.slice(4, 7), row => card(row))}</aside></div>${rest.length > 9 ? `<section class="news-strip"><h2 class="column-heading">更多报道</h2><div class="card-grid">${rest.slice(9).map(row => card(row)).join('')}</div></section>` : ''}`;
    }
    return { heading, meta, card, brief, feature, pagination, frontpage };
  }
  const api = { version: 1, create };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureUI = api;
})(typeof window !== 'undefined' ? window : globalThis);
