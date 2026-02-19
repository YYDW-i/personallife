// static/news/news.js
(function () {
  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let c of cookies) {
      c = c.trim();
      if (c.startsWith(name + "=")) return decodeURIComponent(c.substring(name.length + 1));
    }
    return null;
  }

  const csrftoken = getCookie("csrftoken");

  async function postToggle(url, field) {
    const body = new URLSearchParams();
    body.set("field", field);

    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": csrftoken || "",
        "X-Requested-With": "XMLHttpRequest",
      },
      body,
    });
    if (!res.ok) throw new Error("Network error");
    return await res.json();
  }

  function setBtnActive(btn, active) {
    btn.classList.toggle("active", !!active);
    // 可选：给按钮文字加个状态提示
    const onText = btn.dataset.onText;
    const offText = btn.dataset.offText;
    if (onText && offText) btn.textContent = active ? onText : offText;
  }

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-news-toggle]");
    if (!btn) return;

    e.preventDefault();

    const url = btn.dataset.url;
    const field = btn.dataset.field;

    btn.disabled = true;
    try {
      const data = await postToggle(url, field);
      if (data && data.ok) setBtnActive(btn, data.value);
    } catch (err) {
      console.warn(err);
      alert("操作失败（网络或权限问题）。");
    } finally {
      btn.disabled = false;
    }
  });
})();
