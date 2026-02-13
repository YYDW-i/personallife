(function () {
  const endpoint = window.REMINDER_ENDPOINT;
  if (!endpoint) return;

  const toastRoot = document.getElementById("toast-root");

  function toast(msg) {
    if (!toastRoot) return;
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = msg;
    toastRoot.appendChild(el);
    setTimeout(() => el.classList.add("show"), 30);
    setTimeout(() => {
      el.classList.remove("show");
      setTimeout(() => el.remove(), 250);
    }, 4500);
  }

  async function poll() {
    try {
      const res = await fetch(endpoint, { credentials: "same-origin" });
      const data = await res.json();
      const reminders = data.reminders || [];
      if (!reminders.length) return;

      reminders.forEach(r => {
        const msg = `⏰ 任务到点：${r.title}`;
        toast(msg);

        // 系统通知（需要权限；即使切到别的 tab 也能看到，前提是浏览器还开着）
        // Notifications API: https://developer.mozilla.org/... :contentReference[oaicite:7]{index=7}
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("LocalLife 提醒", { body: msg });
        }
      });
    } catch (e) {
      // 静默失败：不影响页面
    }
  }

  // 轮询频率：30s（后面可做更智能的：按最近 remind_at 动态调整）
  setInterval(poll, 30000);
  poll();

  // 绑定“开启系统通知”按钮（不要一上来就弹权限请求，会很烦）
  const btn = document.getElementById("btn-enable-notify");
  const hint = document.getElementById("notify-hint");

  function refreshHint() {
    if (!("Notification" in window)) {
      hint && (hint.textContent = "（浏览器不支持系统通知）");
      return;
    }
    hint && (hint.textContent = `（当前权限：${Notification.permission}）`);
  }

  btn && btn.addEventListener("click", async () => {
    if (!("Notification" in window)) return;
    const perm = await Notification.requestPermission();
    refreshHint();
    if (perm !== "granted") toast("系统通知未开启：仍会用页面内提示提醒你。");
  });

  refreshHint();
})();
