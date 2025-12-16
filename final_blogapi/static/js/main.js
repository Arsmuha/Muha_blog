(function () {
  // Theme
  const select = document.getElementById('themeSelect');
  const key = 'theme';
  const saved = localStorage.getItem(key) || 'system';

  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(key, theme);
  }

  if (select) {
    select.value = saved;
    apply(saved);
    select.addEventListener('change', () => apply(select.value));
  } else {
    apply(saved);
  }

  // Simple helpers
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      ...opts,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(text || res.statusText);
    }
    return res.json().catch(() => ({}));
  }

  // Like/Dislike/Favorite buttons
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;

    const action = btn.dataset.action;
    const postId = btn.dataset.postId;
    if (!postId) return;

    try {
      if (action === 'like') await api(`/api/posts/${postId}/like`, { method: 'POST' });
      if (action === 'dislike') await api(`/api/posts/${postId}/dislike`, { method: 'POST' });
      if (action === 'favorite') await api(`/api/posts/${postId}/favorite`, { method: 'POST' });
      location.reload();
    } catch (err) {
      alert('Ошибка: ' + err.message);
    }
  });

  // Comment submit via API
  const form = document.getElementById('commentForm');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const postId = form.dataset.postId;
      const content = form.querySelector('textarea[name="content"]').value.trim();
      if (!content) return;

      try {
        await api(`/api/posts/${postId}/comments`, {
          method: 'POST',
          body: JSON.stringify({ content }),
        });
        form.reset();
        // Let WS update comments or just reload for simplicity:
        location.reload();
      } catch (err) {
        alert('Ошибка: ' + err.message);
      }
    });
  }

  // WebSocket notifications
  const wsStatus = document.getElementById('wsStatus');
  function setWs(text) { if (wsStatus) wsStatus.textContent = text; }

  try {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.addEventListener('open', () => setWs('WS: online'));
    ws.addEventListener('close', () => setWs('WS: offline'));
    ws.addEventListener('message', (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        // Minimal toast via console; can be expanded
        console.log('[WS]', msg);
      } catch (_) {}
    });
  } catch (_) {}

  // Register Service Worker (PWA)
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(() => {});
  }
})();