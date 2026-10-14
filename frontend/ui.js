/* Presentation API v1. Edit these components without changing data or storage. */
(function (root) {
  'use strict';
  function create(ctx) {
    const C = ctx.C, e = C.escape;
    const link = row => e(C.readerRoute(row.id));
    const attention = row => ['P0', 'P1'].includes(C.priorityOf(row)?.priority) ? ctx.priorityBadge(row) : '';
    function meta(row) {
      const place = C.locations(row).length ? `<span>${e(C.locationLabel(row))}</span>` : '';
      return `<div class="meta"><span class="channel-tag">${e(C.channels[row.channel] || '文化')}</span>${row.kind === 'industry_buzz' ? '<span>圈内动态</span>' : ''}${place}${row.language !== 'zh' && !C.editorialReady(row) ? (C.machineReady(row) ? '<span class="copy-status">自动机翻</span>' : '<span class="copy-status">原文·待译</span>') : ''}</div>`;
    }
    function heading(title, subtitle) {
      return `<div class="page-heading"><div><h1>${e(title)}</h1></div></div>`;
    }
    function summary(row) {
      const value = C.readingSummary(row);
      return value;
    }
    function card(row, showStatus = false) {
      const saved = ctx.findBookmark('content', row.id);
      return `<article class="content-card" data-ui="news-card"><div class="card-art"><a class="card-image-link" href="${link(row)}" aria-label="${e('阅读：' + C.displayTitle(row))}">${ctx.artwork(row)}</a>${ctx.saveButton('content', row.id)}</div><div class="card-body">${meta(row)}<h3><a class="card-title" href="${link(row)}">${e(C.displayTitle(row))}</a></h3>${attention(row)}<a class="card-summary-link" href="${link(row)}"><p class="card-summary">${e(summary(row))}</p></a><div class="card-footer"><span>${e(ctx.sourceName(row).replace('（虚构）', ''))}</span><span class="demo-label">${row.is_demo ? '示例' : e(ctx.publicationLabel(row))}</span></div>${showStatus && saved ? `<select class="bookmark-status" data-bookmark-status="${e(saved.id)}" aria-label="收藏状态">${Object.entries(C.statusNames).map(([k,v]) => `<option value="${k}" ${saved.status === k ? 'selected' : ''}>${v}</option>`).join('')}</select>` : ''}</div></article>`;
    }
    function feature(row) {
      const blocks = C.editorialReady(row) || C.machineReady(row) ? C.articleBlocks(row,true) : C.articleBlocks(row);
      const paragraphs = blocks.filter(b => ['paragraph','quote'].includes(b.type) && !(b.text.length < 120 && /^(订阅(?:我们的|本刊|本报|免费)?(?:每日|每周)?.{0,5}(?:简报|通讯)[。.!！]?$|Subscribe to (?:our|the)|Sign up for (?:our|the))/i.test(b.text))).slice(0,6).map(b => b.text.slice(0,550));
      const copy = (paragraphs.length ? paragraphs : [summary(row)]).map(text=>`<p class="feature-summary">${e(text)}</p>`).join('');
      return `<article class="feature" data-ui="lead-story"><div class="feature-body"><div class="lead-kicker">本期头条</div>${meta(row)}<h2><a class="card-title" href="${link(row)}">${e(C.displayTitle(row))}</a></h2>${attention(row)}</div>${row.image_url ? `<div class="feature-art"><a class="card-image-link" href="${link(row)}" aria-label="${e('阅读：' + C.displayTitle(row))}">${ctx.artwork(row,true)}</a></div>` : ''}<div class="feature-text"><a class="card-summary-link feature-columns" href="${link(row)}">${copy}</a><div class="feature-footer"><span>${e(ctx.sourceName(row))}</span><a class="text-link" href="${link(row)}">${row.article_status === 'partial' ? '阅读公开部分' : '阅读全文'} →</a></div></div></article>`;
    }
    function pagination(total, page, size) {
      const count = Math.ceil(total / size);
      if (count <= 1) return '';
      return `<nav class="news-pagination" aria-label="资讯分页" data-ui="pagination"><button class="button secondary" data-list-page="${page-1}" ${page===1?'disabled':''}>← 上一页</button><label>第 <select id="article-page" aria-label="跳到资讯页">${Array.from({length:count},(_,i)=>`<option value="${i+1}" ${page===i+1?'selected':''}>${i+1}</option>`).join('')}</select> / ${count} 页</label><button class="button secondary" data-list-page="${page+1}" ${page===count?'disabled':''}>下一页 →</button></nav>`;
    }
    function frontpage(rows, agenda = '') {
      if (!rows.length) return '';
      const [lead,...rest] = rows;
      const column = (name,items) => `<h2 class="column-heading">${name}</h2>${items.map(row=>card(row)).join('')}`;
      return `<div class="broadsheet" data-ui="frontpage"><aside class="news-column brief-column">${column('国际简讯',rest.slice(0,4))}</aside><section class="lead-column">${feature(lead)}${rest.slice(7,9).map(row=>card(row)).join('')}</section><aside class="news-column focus-column">${column('文化焦点',rest.slice(4,7))}${agenda}</aside></div>${rest.length>9?`<section class="news-strip"><div class="section-title"><h2>文化动态</h2></div><div class="card-grid">${rest.slice(9).map(row=>card(row)).join('')}</div></section>`:''}`;
    }
    return { heading, meta, card, feature, pagination, frontpage };
  }
  const api = { version: 1, create };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.CultureUI = api;
})(typeof window !== 'undefined' ? window : globalThis);
