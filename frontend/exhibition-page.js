(function () {
  'use strict';
  const C = window.CultureCore, boot = window.CULTURE_BOOTSTRAP, main = document.getElementById('main');
  const id = new URLSearchParams(location.search).get('id');
  const validId = id && /^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$/.test(id);
  let detail, failed;
  let toastTimer;
  const toast = message => {
    const status = document.getElementById('toast');
    status.textContent = message;
    status.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => status.classList.remove('show'), 3500);
  };
  if (!C || !window.CultureExhibitions) {
    main.innerHTML = '<p>展览暂时无法载入。<a href="./">重试 ↗</a></p>';
    return;
  }
  const directory = window.CultureExhibitions.create({
    C, boot, server: false, toast, rerender: render, isActive: () => true
  });
  const back = '<a class="text-link exhibition-back" href="./">← 返回展览目录</a>';
  function render() {
    if (!id) {
      main.innerHTML = '<h1 class="exhibition-edition-title">展览</h1>' + directory.view({ mode: 'live', events: [] }, {});
      return;
    }
    if (detail) {
      document.title = (detail.item.title_zh || detail.item.title_original) + ' · 幕间休息';
      main.innerHTML = back + directory.reader(detail.item, detail.description, detail.sources);
      return;
    }
    main.innerHTML = back + (failed
      ? '<p role="status">这条展览暂时无法打开。<button class="text-link" id="exhibition-reload">重新载入</button></p>'
      : '<p role="status">正在读取展览正文…</p>');
    document.getElementById('exhibition-reload')?.addEventListener('click', loadDetail);
  }
  function loadDetail() {
    failed = !validId;
    render();
    if (!validId) return;
    const query = boot.exhibition_revision ? '?v=' + encodeURIComponent(boot.exhibition_revision) : '';
    C.fetchTimed('items/' + encodeURIComponent(id) + '.json' + query, {}, 15000).then(response => {
      if (!response.ok) throw new Error('exhibition_item_unavailable');
      return response.json();
    }).then(value => {
      if (value?.schema_version !== 1 || value.item?.id !== id) throw new Error('exhibition_item_invalid');
      detail = value;
    }).catch(() => { failed = true; }).finally(render);
  }
  if (id) loadDetail();
  else render();
})();
