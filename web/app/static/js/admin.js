// Admin dashboard: switch sections from the sidebar without reloading.
(function () {
  "use strict";
  const items = [...document.querySelectorAll(".adm-nav__item[data-panel]")];
  const panels = [...document.querySelectorAll(".adm-panel")];
  if (!items.length || !panels.length) return;

  function show(name) {
    const target = panels.some((p) => p.id === "panel-" + name) ? name : null;
    const pick = target || (panels[0].id || "").replace("panel-", "");
    panels.forEach((p) => p.classList.toggle("is-active", p.id === "panel-" + pick));
    items.forEach((b) => b.classList.toggle("is-active", b.dataset.panel === pick));
  }

  items.forEach((b) =>
    b.addEventListener("click", () => {
      const name = b.dataset.panel;
      show(name);
      if (history.replaceState) history.replaceState(null, "", "#" + name);
      else location.hash = name;
    }));

  // Open the section from the URL hash, else the first one (escalations).
  show((location.hash || "").replace("#", ""));
})();
