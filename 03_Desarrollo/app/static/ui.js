/* Utilidades compartidas de la interfaz */
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtSize = (b) => (b < 1024 ? b + " B" : b < 1048576 ? (b / 1024).toFixed(1) + " KB" : (b / 1048576).toFixed(1) + " MB");

  /* Tema claro/oscuro */
  const saved = (() => { try { return localStorage.getItem("theme"); } catch (e) { return null; } })();
  if (saved) document.documentElement.dataset.theme = saved;
  function toggleTheme() {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
    $$("[data-theme-icon]").forEach((i) => (i.className = "bi " + (next === "dark" ? "bi-sun" : "bi-moon-stars")));
  }

  /* Notificaciones */
  function toast(msg, type) {
    let box = $("#toasts");
    if (!box) { box = document.createElement("div"); box.id = "toasts"; document.body.appendChild(box); }
    const icons = { ok: "bi-check-circle-fill", bad: "bi-x-octagon-fill", warn: "bi-exclamation-triangle-fill" };
    const t = document.createElement("div");
    t.className = "toast " + (type || "");
    t.innerHTML = '<i class="bi ' + (icons[type] || "bi-info-circle-fill") + '"></i><div>' + esc(msg) + "</div>";
    box.appendChild(t);
    setTimeout(() => { t.style.opacity = "0"; t.style.transition = "opacity .3s"; setTimeout(() => t.remove(), 300); }, type === "bad" ? 7000 : 4200);
  }

  /* Markdown mínimo y seguro para respuestas del chatbot */
  function md(text) {
    let h = esc(text);
    h = h.replace(/^#{1,4}\s*(.+)$/gm, "<h4>$1</h4>")
         .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
         .replace(/`([^`]+)`/g, "<code>$1</code>")
         .replace(/^\s*[-•*]\s+(.+)$/gm, "&bull; $1")
         .replace(/\n/g, "<br>");
    return h.replace(/(<\/h4>)<br>/g, "$1");
  }

  async function api(url, opts) {
    const res = await fetch(url, Object.assign({ credentials: "same-origin" }, opts || {}));
    let data = null;
    try { data = await res.json(); } catch (e) {}
    if (res.status === 401) { window.location.href = "/login?next=" + encodeURIComponent(location.pathname); throw new Error("Sesión expirada"); }
    if (!res.ok) {
      let d = data && (data.detail || data.message);
      if (Array.isArray(d)) d = d.map((x) => x.msg).join("; ");
      throw new Error(d || "Error " + res.status);
    }
    return data;
  }

  /* Zona de carga robusta: click (label), arrastrar, pegar y validación */
  function dropzone(cfg) {
    const root = typeof cfg.root === "string" ? $(cfg.root) : cfg.root;
    const input = $("input[type=file]", root);
    const list = typeof cfg.list === "string" ? $(cfg.list) : cfg.list;
    const state = { files: [] };
    const ALLOWED = new Set(cfg.allowed);
    const extOf = (n) => (n.includes(".") ? n.split(".").pop().toLowerCase() : "");
    const kind = (e) => (e === "pdf" ? ["pdf", "bi-file-earmark-pdf"] : ["xlsx", "xls", "csv"].includes(e) ? ["xls", "bi-file-earmark-spreadsheet"] :
      ["docx", "doc", "txt"].includes(e) ? ["doc", "bi-file-earmark-text"] : ["img", "bi-file-earmark-image"]);

    function render() {
      if (!list) return;
      list.innerHTML = "";
      state.files.forEach((f, i) => {
        const e = extOf(f.name), k = kind(e);
        const row = document.createElement("div");
        row.className = "file";
        const icon = f.type.startsWith("image/") ? '<img class="thumb" alt="">' : '<div class="fi ' + k[0] + '"><i class="bi ' + k[1] + '"></i></div>';
        row.innerHTML = icon + '<div class="grow"><div class="fn">' + esc(f.name) + '</div><div class="fs">' + fmtSize(f.size) + " · ." + esc(e) + '</div></div><button type="button" title="Quitar" aria-label="Quitar ' + esc(f.name) + '"><i class="bi bi-x-lg"></i></button>';
        const img = $("img.thumb", row);
        if (img) img.src = URL.createObjectURL(f);
        $("button", row).onclick = () => { state.files.splice(i, 1); render(); notify(); };
        list.appendChild(row);
      });
    }
    function notify() { if (cfg.onChange) cfg.onChange(state.files); }
    function add(fileList) {
      let added = 0;
      for (const f of Array.from(fileList)) {
        const e = extOf(f.name);
        if (state.files.length >= cfg.max) { toast("Máximo " + cfg.max + " archivo(s) por envío.", "warn"); break; }
        if (!ALLOWED.has(e)) { toast("«" + f.name + "»: formato ." + (e || "?") + " no admitido.", "bad"); continue; }
        if (f.size === 0) { toast("«" + f.name + "» está vacío.", "bad"); continue; }
        if (f.size > cfg.maxMB * 1048576) { toast("«" + f.name + "» supera " + cfg.maxMB + " MB.", "bad"); continue; }
        if (state.files.some((x) => x.name === f.name && x.size === f.size)) continue;
        if (cfg.max === 1) state.files = [];
        state.files.push(f); added++;
      }
      render(); notify();
      return added;
    }
    input.addEventListener("change", () => { add(input.files); input.value = ""; });
    ["dragenter", "dragover"].forEach((ev) => root.addEventListener(ev, (e) => { e.preventDefault(); root.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => root.addEventListener(ev, (e) => { e.preventDefault(); root.classList.remove("over"); }));
    root.addEventListener("drop", (e) => { if (e.dataTransfer && e.dataTransfer.files.length) add(e.dataTransfer.files); });
    if (cfg.paste !== false) document.addEventListener("paste", (e) => {
      const fs = e.clipboardData && e.clipboardData.files;
      if (fs && fs.length) add(fs);
    });
    // evita que el navegador abra el archivo si se suelta fuera de la zona
    ["dragover", "drop"].forEach((ev) => window.addEventListener(ev, (e) => e.preventDefault()));
    return {
      get files() { return state.files; },
      clear() { state.files = []; render(); notify(); },
      add,
    };
  }

  function initShell() {
    const side = $("#side"), btn = $("#menuBtn");
    if (btn && side) {
      btn.onclick = () => side.classList.toggle("open");
      document.addEventListener("click", (e) => { if (side.classList.contains("open") && !side.contains(e.target) && !btn.contains(e.target)) side.classList.remove("open"); });
    }
    $$("[data-theme-toggle]").forEach((b) => (b.onclick = toggleTheme));
    const dark = document.documentElement.dataset.theme === "dark";
    $$("[data-theme-icon]").forEach((i) => (i.className = "bi " + (dark ? "bi-sun" : "bi-moon-stars")));
    $$("[data-href]").forEach((tr) => tr.addEventListener("click", (e) => { if (!e.target.closest("a,button")) location.href = tr.dataset.href; }));
  }
  document.addEventListener("DOMContentLoaded", initShell);

  window.UI = { $, $$, esc, fmtSize, toast, md, api, dropzone };
})();
