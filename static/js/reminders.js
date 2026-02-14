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
  const audio = new Audio("/static/sounds/remind.mp3");
  audio.preload = "auto";
  let audioUnlocked = false;

  async function unlockAudio() {
    try {
      const oldVol = audio.volume;
      audio.volume = 0;        // 关键：不是 muted
      await audio.play();      // 必须发生在用户点击回调里
      audio.pause();
      audio.currentTime = 0;
      audio.volume = oldVol;   // 恢复
      audioUnlocked = true;
      toast("✅ 系统通知和声音提醒已启用");
    } catch (e) {
      audioUnlocked = false;
      console.warn("unlockAudio failed:", e);
      toast("⚠️ 声音未启用：浏览器阻止播放。再点一次按钮试试");
    }
  }

  function playSound() {
    const p = audio.play();
    if (p?.catch) {
      p.catch(e => console.warn("playSound blocked:", e));
    }
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

        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("LocalLife 提醒", { body: msg });
        }

        if (audioUnlocked) {
          audio.currentTime = 0;
          playSound();
        } else {
          // 没解锁就提示用户：点一次按钮即可启用声音
          toast("🔇 声音未启用：点“开启系统通知”以启用声音提醒");
        }
      });

    } catch (e) {
      console.error("reminder poll failed:", e);
      toast("提醒轮询失败：请打开控制台查看错误");
    }
  }

  // 轮询频率：30s（后面可做更智能的：按最近 remind_at 动态调整）
  setInterval(poll, 30000);
  poll();

  // 绑定“开启系统通知”按钮（不要一上来就弹权限请求，会很烦）
  const btnToggle = document.getElementById("btn-notify-toggle");
  const badge = document.getElementById("notify-badge");

  const dlg = document.getElementById("notify-help");
  const btnHelpClose = document.getElementById("btn-help-close");
  btnHelpClose?.addEventListener("click", () => dlg?.close());

  function setBadge(text, kind) {
    if (!badge) return;
    badge.textContent = text;
    // kind: ok / warn / bad / off
    badge.dataset.kind = kind;
  }

  // 可选：给 badge 做颜色（不想改 CSS 也能先不做）
  /*
  在 app.css 里加：
  #notify-badge[data-kind="ok"]{ background: rgba(80,200,140,.14); }
  #notify-badge[data-kind="warn"]{ background: rgba(255,200,80,.14); }
  #notify-badge[data-kind="bad"]{ background: rgba(255,90,120,.14); }
  #notify-badge[data-kind="off"]{ background: rgba(255,255,255,.06); }
  */

  function renderNotifyUI() {
    if (!("Notification" in window)) {
      btnToggle && (btnToggle.textContent = "系统通知：不支持");
      btnToggle && (btnToggle.disabled = true);
      setBadge("通知：浏览器不支持", "off");
      return;
    }

    const p = Notification.permission; // granted / denied / default
    if (p === "granted") {
      btnToggle && (btnToggle.textContent = "关闭系统通知");
      btnToggle && (btnToggle.disabled = false);
      setBadge("通知：已开启", "ok");
    } else if (p === "denied") {
      btnToggle && (btnToggle.textContent = "通知被阻止：去浏览器设置");
      btnToggle && (btnToggle.disabled = false);
      setBadge("通知：已阻止", "bad");
    } else {
      // default
      btnToggle && (btnToggle.textContent = "开启系统通知");
      btnToggle && (btnToggle.disabled = false);
      setBadge("通知：未授权", "warn");
    }
  }

  btnToggle?.addEventListener("click", async () => {
    if (!("Notification" in window)) return;

    const p = Notification.permission;
    if (p === "default") {
      const perm = await Notification.requestPermission(); // Promise -> granted/denied/default
      renderNotifyUI();
      if (perm !== "granted") {
        // 你可以 toast 一下：没授权也会继续用页面内提醒
        // toast("系统通知未开启：仍会用页面内提示提醒你。");
      }
      return;
    }

    // granted 或 denied：无法用代码“撤销/重置”，只能指引用户去站点设置
    dlg?.showModal();
  });

  renderNotifyUI();

})();
