/* Casa Gracia — chat assistant widget.
   Stateless server: we keep the conversation in the browser (sessionStorage)
   and send the recent turns with each message. Icons only, no emoji. */
(function () {
  "use strict";
  var root = document.getElementById("cg-chat");
  if (!root) return;

  var panel = document.getElementById("cgChatPanel");
  var body = document.getElementById("cgChatBody");
  var form = document.getElementById("cgChatForm");
  var input = document.getElementById("cgChatInput");
  var sendBtn = document.getElementById("cgChatSend");
  var launch = document.getElementById("cgChatLaunch");
  var closeBtn = document.getElementById("cgChatClose");

  var TYPING = root.dataset.typing || "…";
  var WELCOME = root.dataset.welcome || "";
  var ERROR = root.dataset.error || "Error";
  var LANG = root.dataset.lang === "en" ? "en" : "es";  // page language
  // Separate history per language: the EN and ES sites keep distinct threads,
  // so switching language never mixes Spanish and English replies.
  var STORE_KEY = "cgChatHistory:" + LANG;
  var MAX_KEEP = 30;        // turns kept in storage
  var MAX_SEND = 16;        // prior turns sent to the server
  var POLL_MS = 6000;       // how often we check for human replies

  // One conversation thread per browser (shared across languages) so a human
  // reply from the admin reaches this widget regardless of the current page lang.
  var THREAD_ID = thread();
  var REPLY_CURSOR_KEY = "cgChatReplyCursor";
  var replyCursor = loadCursor();
  var pollTimer = null;

  var history = load();
  var started = false;

  function thread() {
    try {
      var t = sessionStorage.getItem("cgChatThread");
      if (!t) {
        t = (window.crypto && crypto.randomUUID) ? crypto.randomUUID()
          : "t-" + Date.now() + "-" + Math.random().toString(36).slice(2);
        sessionStorage.setItem("cgChatThread", t);
      }
      return t;
    } catch (e) { return "t-" + Date.now(); }
  }
  function loadCursor() {
    try { return parseInt(sessionStorage.getItem(REPLY_CURSOR_KEY), 10) || 0; }
    catch (e) { return 0; }
  }
  function saveCursor() {
    try { sessionStorage.setItem(REPLY_CURSOR_KEY, String(replyCursor)); }
    catch (e) { /* ignore */ }
  }

  function load() {
    try { return JSON.parse(sessionStorage.getItem(STORE_KEY)) || []; }
    catch (e) { return []; }
  }
  function persist() {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(history.slice(-MAX_KEEP))); }
    catch (e) { /* storage full / disabled — ignore */ }
  }

  // Absolute http(s) links OR same-origin booking links like /reservar?...
  var URL_RE = /(https?:\/\/[^\s)]+|\/reservar\?[^\s)]+)/g;
  function fillText(el, text) {
    // Render text with clickable links, safely (no innerHTML).
    var last = 0, m;
    URL_RE.lastIndex = 0;
    while ((m = URL_RE.exec(text)) !== null) {
      if (m.index > last) el.appendChild(document.createTextNode(text.slice(last, m.index)));
      var url = m[0];
      var a = document.createElement("a");
      a.href = url;
      if (url.charAt(0) !== "/") { a.target = "_blank"; a.rel = "noopener"; }
      a.textContent = url;
      el.appendChild(a);
      last = m.index + url.length;
    }
    if (last < text.length) el.appendChild(document.createTextNode(text.slice(last)));
  }

  function bubble(text, who) {
    var div = document.createElement("div");
    div.className = "cg-chat__msg cg-chat__msg--" + who + " cg-chat__msg--in";
    fillText(div, text);
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
    return div;
  }

  function typing() {
    var div = document.createElement("div");
    div.className = "cg-chat__msg cg-chat__msg--bot cg-chat__typing cg-chat__dots";
    div.innerHTML = "<span></span><span></span><span></span>";
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
    return div;
  }

  function render() {
    body.textContent = "";
    if (WELCOME) bubble(WELCOME, "bot");
    history.forEach(function (m) {
      bubble(m.content, m.role === "user" ? "user" : "bot");
    });
  }

  // --- Live human replies (admin -> widget) --------------------------------
  async function poll() {
    if (document.visibilityState !== "visible") return;
    try {
      var r = await fetch("/api/chat/replies?thread=" + encodeURIComponent(THREAD_ID) +
                          "&after=" + replyCursor, { headers: { "Accept": "application/json" } });
      if (!r.ok) return;
      var data = await r.json();
      var list = (data && data.replies) || [];
      for (var i = 0; i < list.length; i++) {
        if (!started) { render(); started = true; }
        bubble(list[i].text, "bot");
        history.push({ role: "assistant", content: list[i].text });
        if (list[i].id > replyCursor) replyCursor = list[i].id;
      }
      if (list.length) { persist(); saveCursor(); }
    } catch (e) { /* network hiccup — try again next tick */ }
  }
  function startPolling() {
    if (pollTimer) return;
    poll();
    pollTimer = setInterval(poll, POLL_MS);
  }
  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function open() {
    if (!started) { render(); started = true; }
    root.classList.add("is-open");
    panel.hidden = false;
    startPolling();
    setTimeout(function () { input.focus(); body.scrollTop = body.scrollHeight; }, 50);
  }
  function close() {
    root.classList.remove("is-open");
    panel.hidden = true;
    stopPolling();
  }

  async function send(text) {
    bubble(text, "user");
    var prior = history.slice(-MAX_SEND);
    history.push({ role: "user", content: text });
    persist();
    var tip = typing();
    sendBtn.disabled = true;
    try {
      var r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: prior, lang: LANG, thread_id: THREAD_ID })
      });
      var data = await r.json();
      tip.remove();
      var reply = (data && data.reply) || ERROR;
      bubble(reply, "bot");
      history.push({ role: "assistant", content: reply });
      persist();
    } catch (e) {
      tip.remove();
      bubble(ERROR, "bot");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  launch.addEventListener("click", open);
  closeBtn.addEventListener("click", close);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !panel.hidden) close();
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    send(text);
  });
})();
