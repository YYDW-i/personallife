(() => {
  "use strict";
  const form = document.querySelector("#iching-form");
  if (!form) return;
  const result = document.querySelector("#result-container");
  const status = document.querySelector("#cast-status");
  const submit = form.querySelector('[type="submit"]');
  const escape = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[char]));
  let busy = false;
  async function post(url, body) {
    const response = await fetch(url, {method: "POST", body,
      headers: {"X-CSRFToken": form.elements.csrfmiddlewaretoken.value}});
    if (response.redirected) throw new Error("登录已过期，请刷新页面后重新登录。");
    let data;
    try { data = await response.json(); } catch { throw new Error("服务响应异常，请稍后重试。"); }
    if (!response.ok) throw new Error(data.error || "请求失败，请稍后重试。");
    return data;
  }
  function setBusy(value) {
    busy = value;
    submit.disabled = value;
    form.setAttribute("aria-busy", String(value));
  }
  async function interpret(token) {
    const panel = result.querySelector("#ai-section-placeholder");
    panel.innerHTML = '<div class="iching-busy" role="status">AI 正在生成译文与建议，格式异常时会自动重试一次…</div>';
    const body = new FormData();
    body.set("token", token);
    try {
      const data = await post(form.dataset.aiUrl, body);
      panel.innerHTML = data.html; // Server template autoescapes all AI content.
    } catch (error) {
      panel.innerHTML = '<p class="iching-error" role="alert"></p><button type="button" class="btn secondary" data-ai-retry>重试当前卦象的 AI 解读</button>';
      panel.querySelector("p").textContent = error.message;
      panel.querySelector("button").dataset.token = token;
    }
  }
  function render(data) {
    const hex = (title, item, lines) => item
      ? '<article class="iching-panel"><h3>' + escape(title) + ' · ' + escape(item.name) + ' ' + escape(item.symbol) +
        '</h3><pre>' + lines.map(escape).join("\n") + '</pre><p class="iching-prose">' + escape(item.scripture) + '</p></article>'
      : '<article class="iching-panel"><h3>之卦</h3><p class="muted">本次无动爻，以本卦为主。</p></article>';
    result.innerHTML = '<section class="glass card"><div class="card-title">本次卦象</div>' +
      (data.question ? '<p class="muted">思考的问题：' + escape(data.question) + '</p>' : '') +
      '<div class="iching-pair">' + hex("本卦", data.primary, data.primary_lines) + hex("之卦", data.relating, data.relating_lines) +
      '</div><span class="iching-chip">' + (data.moving_lines.length ? '动爻：第 ' + data.moving_lines.join("、") + ' 爻' : '无动爻') +
      '</span><div id="ai-section-placeholder" aria-live="polite"></div>' +
      '<details style="margin-top:24px" open><summary>查看六爻原文与三币结果（从初爻到上爻）</summary><div class="iching-line-grid">' +
      data.primary.lines.map((line, i) => {
        const moving = data.moving_lines.includes(i + 1);
        const changed = moving && data.relating?.lines[i];
        return '<article class="iching-panel"><h3>' + escape(line.name) + (moving ? ' <span class="iching-chip">动爻</span>' : '') +
          '</h3><div class="iching-coins" aria-label="三枚硬币的结果">' + data.coin_results[i].map(coin =>
            '<span class="iching-coin" title="' + (coin === 3 ? '正面 3' : '反面 2') + '">' + (coin === 3 ? '●' : '○') + '</span>').join('') +
          '</div><p class="iching-prose">' + escape(line.scripture) + '</p>' +
          (changed ? '<p class="muted">之卦 ' + escape(changed.name) + '：' + escape(changed.scripture) + '</p>' : '') + '</article>';
      }).join('') + '</div></details></section>';
  }
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    status.textContent = "正在起卦…";
    const body = new FormData(form);
    const useAI = body.get("use_ai") === "1";
    body.delete("use_ai"); // Show the local result before waiting for the provider.
    try {
      const data = await post(form.dataset.castUrl, body);
      render(data);
      status.textContent = "卦象已生成。";
      if (useAI) await interpret(data.ai_token);
    } catch (error) { status.textContent = error.message; }
    finally { setBusy(false); }
  });
  result.addEventListener("click", async event => {
    const button = event.target.closest("[data-ai-retry]");
    if (!button || busy) return;
    const token = button.dataset.token;
    setBusy(true);
    try { await interpret(token); } finally { setBusy(false); }
  });
})();
