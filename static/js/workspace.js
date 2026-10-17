(() => {
  const menu = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const mobile = window.matchMedia('(max-width: 700px)');
  function syncNavigation() {
    if (sidebar) sidebar.inert = mobile.matches && !document.body.classList.contains('nav-open');
  }
  mobile.addEventListener('change', syncNavigation);
  syncNavigation();
  menu?.addEventListener('click', () => {
    const open = document.body.classList.toggle('nav-open');
    menu.setAttribute('aria-expanded', String(open));
    syncNavigation();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      document.body.classList.remove('nav-open');
      menu?.setAttribute('aria-expanded', 'false');
      syncNavigation();
    }
  });
  async function checkFocus() {
    if (!window.FOCUS_ENDPOINT || location.pathname.startsWith('/tasks/focus/') || document.hidden) return;
    try {
      const response = await fetch(window.FOCUS_ENDPOINT, {credentials: 'same-origin'});
      if (!response.ok) return;
      const data = await response.json();
      if (data.active && data.focus_url) location.assign(data.focus_url);
    } catch (_) { /* 本地服务短暂重启时下次重试。 */ }
  }
  checkFocus();
  setInterval(checkFocus, 10000);
})();
