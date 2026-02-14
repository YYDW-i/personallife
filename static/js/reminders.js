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
  const btn = document.getElementById("btn-enable-notify");
  const hint = document.getElementById("notify-hint");

  function refreshHint() {
    if (!("Notification" in window)) {
      hint && (hint.textContent = "（浏览器不支持系统通知）");
      return;
    }
    hint && (hint.textContent = `（当前权限：${Notification.permission}）`);
  }
  function safeToast(msg) { try { toast(msg); } catch(e) {} }

  btn && btn.addEventListener("click", async () => {
  // 1) 通知权限
    await unlockAudio();
    if ("Notification" in window) {
      const perm = await Notification.requestPermission();
      refreshHint();
      if (perm !== "granted") toast("系统通知未开启：仍会用页面内提示提醒你。");
    }

  });


  refreshHint();
})();
